"""Backfill: re-geocode + re-extract area cho listing đã có address trong DB.

Dùng khi cải tiến geocode/area logic mà KHÔNG muốn crawl lại nguồn (nhanh hơn,
không tốn request phongtro123). Chỉ đọc address/description sẵn có → cập nhật
geom / distance_to_ctu / geocode_confidence / area.

Chạy: python -m app.crawler.backfill

QUAN TRỌNG — vì sao KHÔNG chặn hạ nhãn (2026-08-08): backfill chạy đúng vào lúc
logic geocode vừa siết lại, nên phần lớn việc của nó LÀ hạ nhãn sai xuống đúng
(vd 'high' do Nominatim trả place_of_worship → 'low'). Guard "chỉ ghi khi rank ≥
rank cũ" của bản backfill cũ sẽ vô hiệu hoá chính mục đích lần chạy này.

Cái phải chặn là hạ nhãn do LỖI MẠNG: Nominatim timeout cũng làm mọi tầng trượt
xuống bảng tra/tầng 5, nhìn y hệt một downgrade thật. Dùng `Geocoder.degraded` để
tách hai ca đó ra và bỏ qua dòng bị lỗi mạng (giữ nhãn cũ, đếm vào `skipped_net`).
"""
import asyncio
import logging

from sqlalchemy import create_engine, text

from ..config import settings
from .geocode import CTU_LAT, CTU_LNG, Geocoder, haversine_m
from .normalize import extract_area_from_text

log = logging.getLogger("crawler.backfill")

# Số dòng lỗi mạng LIÊN TIẾP thì coi là Nominatim đang chặn → dừng cả run.
# 5 đủ lớn để không nhầm với 1-2 request chập chờn, đủ nhỏ để không nện thêm
# hàng trăm request vào một server vừa trả 429.
_MAX_CONSECUTIVE_FAIL = 5

_UPDATE = text(
    "UPDATE aggregated_listings SET "
    "geom = CASE WHEN CAST(:lat AS DOUBLE PRECISION) IS NULL THEN geom "
    "  ELSE ST_SetSRID(ST_MakePoint(CAST(:lng AS DOUBLE PRECISION), "
    "  CAST(:lat AS DOUBLE PRECISION)), 4326) END, "
    "distance_to_ctu = COALESCE(CAST(:dist AS REAL), distance_to_ctu), "
    "geocode_confidence = :conf, "
    "area = CAST(:area AS REAL) "
    "WHERE id = :id"
)


async def backfill() -> dict:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, title, address, description, area, geocode_confidence AS old_conf "
                 "FROM aggregated_listings WHERE address IS NOT NULL ORDER BY id")
        ).mappings().all()

    stats = {"total": len(rows), "geocoded": 0, "area_filled": 0, "written": 0,
             "skipped_net": 0, "downgraded": 0, "upgraded": 0, "aborted": False,
             "high": 0, "medium": 0, "low": 0, "city": 0, "failed": 0}

    consecutive_fail = 0
    async with Geocoder() as geo:
        for r in rows:
            lat, lng, conf = await geo.geocode(r["address"])

            if geo.degraded:
                # Nominatim không trả lời cho dòng này → nhãn vừa tính KHÔNG đáng tin.
                # Giữ nguyên DB, đếm riêng để biết cần chạy lại bao nhiêu dòng.
                stats["skipped_net"] += 1
                consecutive_fail += 1
                log.warning("skip id=%s: Nominatim lỗi mạng, giữ nhãn cũ %r",
                            r["id"], r["old_conf"])
                # Circuit breaker: lỗi liên tiếp = server đang chặn mình (429), không
                # phải mạng chập chờn. Nện tiếp 500 dòng × 3 query vừa vô ích vừa vi
                # phạm usage policy Nominatim. Dừng sớm, chạy lại sau khi hết cooldown.
                # Đã dính 2026-08-08: probe tay dùng hết quota → backfill ăn 429 hàng loạt.
                if consecutive_fail >= _MAX_CONSECUTIVE_FAIL:
                    stats["aborted"] = True
                    log.error("DỪNG SỚM: %d dòng liên tiếp lỗi mạng — Nominatim đang chặn "
                              "(429?). Chờ cooldown rồi chạy lại.", consecutive_fail)
                    break
                continue
            consecutive_fail = 0

            stats[conf] = stats.get(conf, 0) + 1
            dist = haversine_m(lat, lng, CTU_LAT, CTU_LNG) if lat is not None else None

            area = r["area"]
            if area is None:
                new_area = extract_area_from_text(r["description"], r["title"])
                if new_area is not None:
                    area = new_area
                    stats["area_filled"] += 1

            old = r["old_conf"]
            if old != conf:
                rank = {"failed": 0, "city": 1, "low": 2, "medium": 3, "high": 4}
                if rank.get(conf, 0) < rank.get(old, 0):
                    stats["downgraded"] += 1
                else:
                    stats["upgraded"] += 1

            with engine.begin() as conn:
                conn.execute(
                    _UPDATE,
                    {"lat": lat, "lng": lng, "dist": dist, "conf": conf,
                     "area": area, "id": r["id"]},
                )
            stats["written"] += 1
            if lat is not None:
                stats["geocoded"] += 1

    engine.dispose()
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = asyncio.run(backfill())
    print("BACKFILL DONE:", result)
