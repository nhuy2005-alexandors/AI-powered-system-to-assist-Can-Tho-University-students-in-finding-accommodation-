-- Sprint 0.4: enable spatial + vector extensions on first boot
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- sanity table so healthcheck/migrations have something to hit early
CREATE TABLE IF NOT EXISTS _bootstrap (
    id          serial PRIMARY KEY,
    booted_at   timestamptz NOT NULL DEFAULT now()
);
INSERT INTO _bootstrap DEFAULT VALUES;
