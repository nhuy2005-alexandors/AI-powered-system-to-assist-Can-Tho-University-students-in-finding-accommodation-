-- Metadata for the explainable room-risk engine.
-- risk_score = 0 continues to mean "not evaluated" for legacy rows.
ALTER TABLE aggregated_listings
  ADD COLUMN IF NOT EXISTS risk_model VARCHAR(80),
  ADD COLUMN IF NOT EXISTS risk_evaluated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_aggregated_listings_risk_pending
  ON aggregated_listings (risk_evaluated_at, updated_at)
  WHERE status = 'active' AND cleaning_status = 'cleaned';
