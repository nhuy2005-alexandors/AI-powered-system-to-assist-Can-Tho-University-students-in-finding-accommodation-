-- Listings + crawl bookkeeping. Runs AFTER 10-init.sql (postgis + vector enabled).

CREATE TYPE listing_status AS ENUM ('active', 'expired', 'flagged');

CREATE TABLE aggregated_listings (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    price           INTEGER,
    area            REAL,
    address         TEXT,
    district        VARCHAR(50),
    geom            GEOMETRY(Point, 4326),
    images          TEXT[],
    description     TEXT,

    -- nguồn
    source          VARCHAR(30) NOT NULL,
    source_url      TEXT,
    source_id       VARCHAR(100),
    content_hash    CHAR(64),
    minhash         BYTEA,

    -- AI sinh (geocode/risk/embedding điền ở pipeline sau)
    parsed_amenities    JSONB,
    risk_score          REAL DEFAULT 0,
    risk_reasons        TEXT[],
    distance_to_ctu     REAL,
    geocode_confidence  VARCHAR(10),
    embedding_vector    VECTOR(384),

    -- freshness / lifecycle
    status          listing_status DEFAULT 'active',
    first_seen      TIMESTAMPTZ DEFAULT now(),
    last_seen       TIMESTAMPTZ DEFAULT now(),
    miss_count      INTEGER DEFAULT 0,
    freshness_score REAL DEFAULT 1.0,
    updated_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (source, source_id)
);

CREATE INDEX idx_listings_geom ON aggregated_listings USING GIST (geom);
CREATE INDEX idx_listings_status_seen ON aggregated_listings (status, last_seen);
CREATE INDEX idx_listings_content_hash ON aggregated_listings (content_hash);

-- một dòng mỗi lần crawl một nguồn: health check + cursor incremental
CREATE TABLE crawl_runs (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(30) NOT NULL,
    mode            VARCHAR(12) NOT NULL,        -- 'incremental' | 'full'
    started_at      TIMESTAMPTZ DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    fetched         INTEGER DEFAULT 0,
    new_count       INTEGER DEFAULT 0,
    updated_count   INTEGER DEFAULT 0,
    expired_count   INTEGER DEFAULT 0,
    error           TEXT
);

CREATE INDEX idx_crawl_runs_source_started ON crawl_runs (source, started_at DESC);
