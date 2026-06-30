"""Smoke test net thật (KHÔNG ghi DB) — xác minh selector + geocode trên data sống.

Chạy: python -m app.crawler.smoke phongtro123
Cần mạng. Tôn trọng rate-limit (mất vài giây).
"""
import asyncio
import sys

from .fetcher import Fetcher
from .geocode import CTU_LAT, CTU_LNG, Geocoder, haversine_m
from .normalize import normalize
from .parser import list_page_urls, load_source_config, parse_detail_page, parse_list_page
from .pipeline import merge_detail


async def main(source: str) -> None:
    config = load_source_config(source)
    url = list_page_urls(config, "incremental")[0]
    print(f"[smoke] GET list: {url}")

    async with Fetcher() as fetcher, Geocoder() as geocoder:
        html = await fetcher.get(url)
        raws = parse_list_page(html, config)
        print(f"[smoke] parsed {len(raws)} listings từ list page\n")

        for raw in raws[:3]:
            n = normalize(raw)
            if n.source_url:
                try:
                    detail_html = await fetcher.get(n.source_url)
                    merge_detail(n, parse_detail_page(detail_html, config))
                except Exception as exc:  # noqa: BLE001
                    print(f"  (detail fail: {exc})")
            lat, lng, conf = await geocoder.geocode(n.address)
            dist = haversine_m(lat, lng, CTU_LAT, CTU_LNG) if lat else None
            print(f"- [{n.source_id}] {n.title[:50]}")
            print(f"    giá={n.price} | dt={n.area} | quận={n.district}")
            print(f"    địa chỉ={(n.address or '')[:70]}")
            print(f"    geocode=({lat},{lng}) conf={conf} | cách CTU={dist}m")
            print(f"    ảnh={len(n.images)} | url={n.source_url}\n")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "phongtro123"
    asyncio.run(main(src))
