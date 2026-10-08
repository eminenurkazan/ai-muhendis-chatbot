-- PostgreSQL + pgvector ilk şema.
-- Embedding modeli: Cloudflare @cf/baai/bge-m3, boyut: 1024.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    license TEXT,
    source_version TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_sources_name_version
        UNIQUE (name, source_version)
);

CREATE TABLE IF NOT EXISTS knowledge_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE RESTRICT,
    source_record_id TEXT NOT NULL,
    record_type TEXT NOT NULL DEFAULT 'ticket',
    domain TEXT NOT NULL DEFAULT 'general_it',
    title TEXT,
    raw_text TEXT,
    cleaned_text TEXT,
    problem TEXT NOT NULL,
    category TEXT,
    solution TEXT NOT NULL,
    resolution TEXT,
    resolution_confirmed BOOLEAN,
    source_comment_seq JSONB,
    solution_scope TEXT,
    limitations TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    review_status TEXT NOT NULL DEFAULT 'pending',
    index_status TEXT NOT NULL DEFAULT 'pending',
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_records_source_record
        UNIQUE (source_id, source_record_id),
    CONSTRAINT ck_knowledge_records_type
        CHECK (record_type IN ('ticket', 'qa', 'documentation')),
    CONSTRAINT ck_knowledge_records_domain
        CHECK (domain IN ('general_it', 'windows_server', 'oracle_db')),
    CONSTRAINT ck_knowledge_records_review_status
        CHECK (review_status IN ('pending', 'approved', 'excluded')),
    CONSTRAINT ck_knowledge_records_index_status
        CHECK (index_status IN ('pending', 'ready', 'error'))
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id UUID NOT NULL REFERENCES knowledge_records(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    embedding_model TEXT NOT NULL,
    record_content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_chunks_record_index
        UNIQUE (record_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_knowledge_records_search_state
    ON knowledge_records (review_status, index_status);

-- Pilot 10 kayıt için sıralı tarama yeterlidir. Veri büyüdüğünde HNSW/IVFFlat
-- indeksini benchmark sonucuna göre eklemek daha doğru olacaktır.
