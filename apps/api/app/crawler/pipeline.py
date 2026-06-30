import logging

from .dedup import find_duplicates
from .fetcher import BlockedError, Fetcher
from .geocode import CTU_LAT, CTU_LNG, Geocoder, haversine_m
from .normalize import normalize
from .parser import (
    list_page_urls,
    load_source_config,
    parse_detail_page,
    parse_list_page,
)
from .repo import ListingRepo
from .schemas import NormalizedListing

log = logging.getLogger("crawler.pipeline")


def process_html_pages(source: str, pages_html: list[str]) -> list[NormalizedListing]:
    """Pure: HTML → parse → normalize → dedup. Test được không cần mạng/DB."""
    config = load_source_config(source)
    raws = []
    for html in pages_html:
        raws.extend(parse_list_page(html, config))

    normalized = [normalize(r) for r in raws]

    # cross-source dedup: bỏ bản trùng, gộp source_url giữ bản đại diện
    dup_map = find_duplicates(normalized)
    deduped = [n for i, n in enumerate(normalized) if i not in dup_map]
    log.info("source=%s parsed=%d deduped=%d", source, len(normalized), len(deduped))
    return deduped


def merge_detail(n: NormalizedListing, detail: dict) -> NormalizedListing:
    """Gộp field từ detail page vào listing đã normalize (address/images/price ưu tiên detail)."""
    import re

    from .normalize import compute_content_hash, parse_area, parse_price

    if detail.get("address"):
        n.address = detail["address"]
    if detail.get("description"):
        n.description = detail["description"]
    if detail.get("images"):
        n.images = detail["images"]
    if detail.get("price_text"):
        p = parse_price(detail["price_text"])
        if p:
            n.price = p
    # diện tích: list page thường thiếu → trích "dt 52m2", "45 m2" từ title/description
    if n.area is None:
        for text in (n.title, n.description):
            if not text:
                continue
            m = re.search(r"(\d+[.,]?\d*)\s*m2|(\d+[.,]?\d*)\s*m²", text, re.I)
            if m:
                n.area = parse_area(m.group(0))
                break
    n.content_hash = compute_content_hash(n)
    return n


async def run_source(
    source: str,
    mode: str,
    repo: ListingRepo,
    fetcher: Fetcher | None = None,
    geocoder: "Geocoder | None" = None,
) -> dict:
    """Crawl một nguồn theo mode. Ghi crawl_runs, upsert listings, geocode, freshness."""
    config = load_source_config(source)
    run_id = repo.start_run(source, mode)
    counts = {"fetched": 0, "new_count": 0, "updated_count": 0,
              "expired_count": 0, "error": None}

    own_fetcher = fetcher is None
    fetcher = fetcher or Fetcher()
    own_geocoder = geocoder is None
    geocoder = geocoder or Geocoder()
    try:
        pages_html: list[str] = []
        for url in list_page_urls(config, mode):
            try:
                pages_html.append(await fetcher.get(url))
                counts["fetched"] += 1
            except BlockedError as exc:
                # T1: bị chặn → log + alert + bỏ nguồn (không làm hỏng cả pipeline)
                counts["error"] = str(exc)
                log.warning("BLOCKED source=%s: %s", source, exc)
                break

        listings = process_html_pages(source, pages_html)

        # tầng 2: fetch detail page lấy đủ field (giới hạn cho incremental)
        max_detail = config.get("max_detail_incremental", 20) if mode == "incremental" else len(listings)
        for n in listings[:max_detail]:
            if not n.source_url:
                continue
            try:
                detail_html = await fetcher.get(n.source_url)
                merge_detail(n, parse_detail_page(detail_html, config))
            except BlockedError as exc:
                counts["error"] = str(exc)
                log.warning("BLOCKED detail source=%s: %s", source, exc)
                break
            except Exception as exc:  # noqa: BLE001 — 1 detail lỗi không làm hỏng cả run
                log.warning("detail fetch fail %s: %s", n.source_url, exc)

        # geocode (T2): address → lat/lng/confidence + distance_to_ctu
        for n in listings:
            lat, lng, conf = await geocoder.geocode(n.address)
            n.lat, n.lng, n.geocode_confidence = lat, lng, conf
            if lat is not None and lng is not None:
                n.distance_to_ctu = haversine_m(lat, lng, CTU_LAT, CTU_LNG)

        for n in listings:
            result = repo.upsert(n)
            if result == "new":
                counts["new_count"] += 1
            elif result == "updated":
                counts["updated_count"] += 1

        # full sweep: tin không thấy → miss_count++/expired
        if mode == "full":
            seen_ids = [n.source_id for n in listings if n.source_id]
            counts["expired_count"] = repo.mark_misses(source, seen_ids)

        repo.refresh_scores()
    except Exception as exc:  # noqa: BLE001 — ghi lỗi vào run rồi re-raise cho scheduler log
        counts["error"] = str(exc)
        repo.finish_run(run_id, **counts)
        raise
    finally:
        if own_fetcher:
            await fetcher.__aexit__(None, None, None)
        if own_geocoder:
            await geocoder.__aexit__(None, None, None)

    repo.finish_run(run_id, **counts)
    log.info("run done source=%s mode=%s %s", source, mode, counts)
    return counts
