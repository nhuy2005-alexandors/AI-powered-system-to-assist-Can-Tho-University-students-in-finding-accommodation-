-- Community reports + moderation audit fields.
-- Safe to apply to an existing database created from 30_users.sql.

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolution_note TEXT;

UPDATE reports SET status = 'pending' WHERE status IS NULL;
UPDATE reports SET reason = 'other' WHERE reason IS NULL;
ALTER TABLE reports ALTER COLUMN status SET NOT NULL;
ALTER TABLE reports ALTER COLUMN reason SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reports_listing_status
    ON reports (listing_id, status);

-- A user may report the same listing again only after the previous report was resolved.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_open_reporter_listing
    ON reports (listing_id, reporter_id)
    WHERE status = 'pending' AND reporter_id IS NOT NULL;
