-- Public answer cache is independent of private conversations.
CREATE TABLE IF NOT EXISTS chatbot_shared_answers (
    cache_key CHAR(64) NOT NULL,
    cache_scope CHAR(64) NOT NULL,
    response JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cache_key, cache_scope)
);
CREATE INDEX IF NOT EXISTS idx_chat_shared_expiry ON chatbot_shared_answers (expires_at);

-- Preserve indexing status and content while letting admins suspend a source.
-- Apply to all existing isolated corpora as well as public.
DO $$
DECLARE corpus RECORD;
BEGIN
    FOR corpus IN SELECT table_schema FROM information_schema.tables
        WHERE table_name='legal_documents'
          AND (table_schema='public' OR table_schema LIKE 'legal\_%' ESCAPE '\')
    LOOP
        EXECUTE format('ALTER TABLE %I.legal_documents ADD COLUMN IF NOT EXISTS admin_enabled BOOLEAN NOT NULL DEFAULT true', corpus.table_schema);
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS legal_document_admin_audit (
    id BIGSERIAL PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES users(id),
    corpus_schema TEXT NOT NULL,
    document_id BIGINT NOT NULL,
    before_data JSONB NOT NULL,
    after_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
