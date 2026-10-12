-- Star ratings + Vietnamese comment sentiment moderation.
-- Negative comments are flagged for human review, never auto-deleted.

CREATE TABLE IF NOT EXISTS listing_reviews (
    id                  SERIAL PRIMARY KEY,
    listing_id          INTEGER NOT NULL REFERENCES aggregated_listings(id) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating              SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment             TEXT NOT NULL CHECK (char_length(btrim(comment)) BETWEEN 10 AND 2000),
    sentiment_label     VARCHAR(20) NOT NULL CHECK (sentiment_label IN ('positive', 'neutral', 'negative')),
    negative_score      REAL NOT NULL CHECK (negative_score BETWEEN 0 AND 1),
    moderation_status   VARCHAR(20) NOT NULL DEFAULT 'published'
                            CHECK (moderation_status IN ('published', 'flagged', 'hidden')),
    model_version       VARCHAR(80) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (listing_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_listing_reviews_listing_created
    ON listing_reviews (listing_id, created_at DESC)
    WHERE moderation_status <> 'hidden';

CREATE INDEX IF NOT EXISTS idx_listing_reviews_flagged
    ON listing_reviews (created_at DESC)
    WHERE moderation_status = 'flagged';
