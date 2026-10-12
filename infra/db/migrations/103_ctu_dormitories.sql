-- A shared, versioned KTX catalogue and real multilingual E5 search vectors.
CREATE TABLE IF NOT EXISTS ctu_ktx_catalog (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload JSONB NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ctu_ktx_search_documents (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('room_type', 'dormitory', 'fact', 'source_clause')),
    source_id TEXT NOT NULL,
    content TEXT NOT NULL,
    normalized_content TEXT NOT NULL,
    metadata JSONB NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    embedding_vector VECTOR(384) NOT NULL,
    embedding_model TEXT NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ctu_ktx_documents_kind ON ctu_ktx_search_documents (kind, source_id);
CREATE INDEX IF NOT EXISTS idx_ctu_ktx_documents_text ON ctu_ktx_search_documents
    USING GIN (to_tsvector('simple', normalized_content));
