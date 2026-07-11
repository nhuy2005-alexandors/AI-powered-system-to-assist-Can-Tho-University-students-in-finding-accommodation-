-- Phân loại đối tượng + điểm chất lượng cho tầng làm sạch đa tầng.
-- listing_type: tách trọ SV khỏi nhà nguyên căn/mặt bằng (chống lẫn đối tượng).
-- quality_score: backend xếp hạng, AI biết độ tin.

CREATE TYPE listing_type_enum AS ENUM ('phong_tro', 'nha_nguyen_can', 'mat_bang', 'khac');

ALTER TABLE aggregated_listings
    ADD COLUMN IF NOT EXISTS listing_type listing_type_enum DEFAULT 'khac',
    ADD COLUMN IF NOT EXISTS quality_score REAL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_listings_type ON aggregated_listings (listing_type);
CREATE INDEX IF NOT EXISTS idx_listings_quality ON aggregated_listings (quality_score DESC);
