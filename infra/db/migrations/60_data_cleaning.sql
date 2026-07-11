-- Add data cleaning fields to aggregated_listings

CREATE TYPE cleaning_status_type AS ENUM ('raw', 'cleaned', 'rejected');

ALTER TABLE aggregated_listings
ADD COLUMN cleaning_status cleaning_status_type DEFAULT 'raw',
ADD COLUMN is_imputed_area BOOLEAN DEFAULT false,
ADD COLUMN cleaning_logs TEXT;

CREATE INDEX idx_listings_cleaning_status ON aggregated_listings (cleaning_status);
