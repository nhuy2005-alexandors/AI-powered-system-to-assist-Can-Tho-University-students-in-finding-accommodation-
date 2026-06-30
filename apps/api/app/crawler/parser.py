import json
import re
from pathlib import Path
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from .schemas import RawListing

SOURCES_DIR = Path(__file__).parent / "sources"

_ATTR_RE = re.compile(r"^(.*?)::attr\((.+)\)$")


def load_source_config(source: str) -> dict:
    path = SOURCES_DIR / f"{source}.json"
    if not path.exists():
        raise FileNotFoundError(f"Không có selector config cho nguồn '{source}': {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _split_attr(selector: str) -> tuple[str, str | None]:
    """'a.x::attr(href)' -> ('a.x', 'href'); 'span.p' -> ('span.p', None)."""
    m = _ATTR_RE.match(selector)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return selector.strip(), None


def _extract(node: Node, selector: str | None) -> str | None:
    """Lấy text hoặc attr từ node con đầu tiên khớp 1 trong các selector (phân tách bằng ',')."""
    if not selector:
        return None
    for raw in selector.split(","):
        css, attr = _split_attr(raw)
        found = node.css_first(css)
        if found is None:
            continue
        if attr:
            val = found.attributes.get(attr)
        else:
            val = found.text(strip=True)
        if val:
            return val
    return None


def _extract_all(node: Node, selector: str | None) -> list[str]:
    out: list[str] = []
    if not selector:
        return out
    for raw in selector.split(","):
        css, attr = _split_attr(raw)
        for found in node.css(css):
            val = found.attributes.get(attr) if attr else found.text(strip=True)
            if val:
                out.append(val)
    return out


def parse_list_page(html: str, config: dict) -> list[RawListing]:
    """Trích danh sách RawListing từ HTML 1 trang list.

    Item card = phần tử cha của `.post__thumb` (chứa cả thumb + anchor title).
    """
    sel = config["selectors"]
    base = config.get("base_url", "")
    source = config["source"]
    tree = HTMLParser(html)

    # mỗi thumb → đi lên card cha chứa đủ field
    cards: list[Node] = []
    for thumb in tree.css(sel["item"]):
        card = thumb.parent
        if card is not None:
            cards.append(card)

    listings: list[RawListing] = []
    for item in cards:
        anchor = item.css_first(sel.get("item_anchor", "a"))
        url = anchor.attributes.get(sel.get("item_url_attr", "href")) if anchor else None
        if url and base:
            url = urljoin(base, url)

        source_id = None
        if url:
            # id cuối path: /...-pr708173.html → 708173
            m = re.search(r"pr(\d+)\.html", url) or re.search(r"(\d{5,})", url)
            source_id = m.group(1) if m else url

        thumb_img = item.css_first(sel.get("thumb", "img"))
        images = []
        if thumb_img:
            src = thumb_img.attributes.get("src") or thumb_img.attributes.get("data-src")
            if src:
                images.append(src)

        listings.append(
            RawListing(
                source=source,
                source_id=source_id,
                source_url=url,
                title=_extract(item, sel.get("title")) or "",
                price_text=_extract(item, sel.get("price")),
                area_text=_extract(item, sel.get("area")),
                address=_extract(item, sel.get("address")),
                district=_extract(item, sel.get("district")),
                description=_extract(item, sel.get("description")),
                images=images,
                amenities_text=_extract(item, sel.get("amenities")),
            )
        )
    return listings


def parse_jsonld(html: str) -> dict | None:
    """Đọc JSON-LD schema.org (Hostel/Product/Place) — nguồn ổn định hơn CSS.

    Trả {name, description, address} nếu có, None nếu không.
    """
    tree = HTMLParser(html)
    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            if not isinstance(d, dict):
                continue
            if d.get("@type") in ("Hostel", "Product", "Place", "Apartment", "Accommodation", "Offer"):
                addr = d.get("address")
                street = addr.get("streetAddress") if isinstance(addr, dict) else None
                return {
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "address": street,
                }
    return None


def parse_detail_page(html: str, config: dict) -> dict:
    """Trích field bổ sung từ detail page: address đầy đủ (JSON-LD), price/area, images."""
    det = config.get("detail", {})
    tree = HTMLParser(html)
    result: dict = {}

    ld = parse_jsonld(html)
    if ld:
        result["address"] = ld.get("address")
        result["description"] = ld.get("description")
        if ld.get("name"):
            result["title"] = ld["name"]

    # price chính trên detail (selector riêng, fs-5 lớn)
    price = _extract(tree.root, det.get("price"))
    if price:
        result["price_text"] = price

    # images: gallery, ưu tiên data-src (lazy-load)
    img_attr = det.get("images_attr", "src")
    imgs: list[str] = []
    for img in tree.css(det.get("images", "img")):
        src = img.attributes.get(img_attr) or img.attributes.get("src")
        if src and "static123" in src and src not in imgs:
            imgs.append(src)
    if imgs:
        result["images"] = imgs

    return result


def list_page_urls(config: dict, mode: str) -> list[str]:
    """Sinh URL các trang list theo mode (incremental ít trang, full nhiều trang)."""
    n = config["incremental_pages"] if mode == "incremental" else config["full_pages"]
    tmpl = config["list_url"] + config.get("list_page_param", "")
    return [tmpl.format(page=p) for p in range(1, n + 1)]
