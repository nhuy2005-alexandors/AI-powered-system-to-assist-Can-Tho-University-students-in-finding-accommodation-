CREATE TABLE IF NOT EXISTS ctu_ktx_years (
    id BIGSERIAL PRIMARY KEY,
    academic_year VARCHAR(9) NOT NULL UNIQUE CHECK (academic_year ~ '^20[0-9]{2}-20[0-9]{2}$'),
    payload JSONB NOT NULL,
    published_payload JSONB,
    revision INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT false,
    archived BOOLEAN NOT NULL DEFAULT false,
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    CHECK (NOT is_active OR (published_payload IS NOT NULL AND NOT archived))
);
CREATE UNIQUE INDEX IF NOT EXISTS ctu_ktx_one_active_year ON ctu_ktx_years(is_active) WHERE is_active;
CREATE TABLE IF NOT EXISTS ctu_ktx_admin_audit (
    id BIGSERIAL PRIMARY KEY,
    year_id BIGINT REFERENCES ctu_ktx_years(id),
    actor_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO ctu_ktx_years(academic_year,payload,published_payload,is_active,published_at)
SELECT '2026-2027',payload || '{"academic_year":"2026-2027"}'::jsonb,
       payload || '{"academic_year":"2026-2027"}'::jsonb,true,updated_at
FROM ctu_ktx_catalog WHERE id=1 AND NOT EXISTS(SELECT 1 FROM ctu_ktx_years)
ON CONFLICT(academic_year) DO NOTHING;
