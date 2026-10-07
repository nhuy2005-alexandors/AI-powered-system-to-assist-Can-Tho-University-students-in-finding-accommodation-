-- Metadata for the existing 384-dimensional listing embedding.
-- Safe to apply to the handoff schema or the project schema.
ALTER TABLE public.aggregated_listings
    ADD COLUMN IF NOT EXISTS embedding_model TEXT,
    ADD COLUMN IF NOT EXISTS embedded_content_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;
