-- UGC (user-generated) listings: cho phép user tự ẩn tin của mình.
-- 'hidden' = user chủ động ẩn, tách bạch với expired(crawler mất tin) / flagged(risk).
-- Postgres không cho ADD VALUE trong transaction block chung với dùng ngay,
-- nhưng migration chạy riêng file nên an toàn.

ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'hidden';

-- posted_by đã thêm ở 30_users.sql (nullable FK users). Index để lọc tin của 1 user nhanh.
CREATE INDEX IF NOT EXISTS idx_listings_posted_by ON aggregated_listings (posted_by);
