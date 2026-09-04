-- Stateless Hybrid chatbot metadata.
-- The chatbot reads aggregated_listings only. It deliberately creates no
-- session, message, source-history or feedback tables.

ALTER TABLE aggregated_listings
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(120),
    ADD COLUMN IF NOT EXISTS embedded_content_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_listings_chatbot_candidates
    ON aggregated_listings (listing_type, quality_score DESC, freshness_score DESC)
    WHERE status = 'active' AND cleaning_status = 'cleaned';

-- Exact cosine search is appropriate for the current development target
-- (~1,000 listings). Add HNSW/IVFFlat only after production measurements show
-- that exact pgvector search is a bottleneck.
