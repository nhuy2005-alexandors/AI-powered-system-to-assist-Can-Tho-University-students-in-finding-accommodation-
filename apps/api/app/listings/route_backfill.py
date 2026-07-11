"""Backfill route_time_campus cho mọi tin có geom, qua ORS Matrix (1 call).

Chạy: ORS_API_KEY=... python -m app.listings.route_backfill
Xem docs/specs/Map_Routing.md. Chỉ tin có geom mới route được.
"""
import asyncio

from sqlalchemy import create_engine, text

from app.config import settings
from app.listings.routing import matrix_minutes


async def backfill() -> dict:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, ST_Y(geom) AS lat, ST_X(geom) AS lng "
                 "FROM aggregated_listings WHERE geom IS NOT NULL ORDER BY id")
        ).mappings().all()

    if not rows:
        engine.dispose()
        return {"total": 0, "routed": 0}

    points = [(r["lat"], r["lng"]) for r in rows]
    times = await matrix_minutes(points)  # [[khuI,II,III], ...] song song rows

    routed = 0
    with engine.begin() as conn:
        for r, t in zip(rows, times):
            if t is None:
                continue
            conn.execute(
                text("UPDATE aggregated_listings SET route_time_campus = :t WHERE id = :id"),
                {"t": t, "id": r["id"]},
            )
            routed += 1

    engine.dispose()
    return {"total": len(rows), "routed": routed}


if __name__ == "__main__":
    print("ROUTE BACKFILL:", asyncio.run(backfill()))
