-- Route time thật (phút) từ mỗi tin tới 3 campus CTU, precompute qua ORS Matrix.
-- Index 0=khu I, 1=khu II, 2=khu III. NULL = chưa route (tin thiếu geom hoặc chưa backfill).
-- Số tĩnh (đường sá không đổi) → lưu cột, KHÔNG cache layer. Xem docs/specs/Map_Routing.md.
ALTER TABLE aggregated_listings ADD COLUMN IF NOT EXISTS route_time_campus REAL[];
