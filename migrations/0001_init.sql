-- 0001_init: documents and chunks, with vector search enabled.

CREATE EXTENSION IF NOT EXISTS vector;

-- One row per source page we have collected.
CREATE TABLE documents (
    id            BIGSERIAL PRIMARY KEY,
    country       TEXT        NOT NULL,                 -- e.g. 'IE', 'GB', 'CA'
    visa_category TEXT        NOT NULL,                 -- e.g. 'student', 'graduate'
    source_url    TEXT        NOT NULL UNIQUE,
    title         TEXT        NOT NULL,
    content_hash  TEXT        NOT NULL,                 -- detects page changes (freshness job)
    retrieved_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per piece of a document that we embed and retrieve.
CREATE TABLE chunks (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT      NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER     NOT NULL,                 -- position within the document
    section_title TEXT,
    text          TEXT        NOT NULL,
    token_count   INTEGER     NOT NULL,
    -- Dimension must match the embedding model. 1024 is a placeholder until we pick the model.
    embedding     vector(1024),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

-- Approximate nearest-neighbour index for cosine similarity.
CREATE INDEX chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Fast country / category filtering before or alongside vector search.
CREATE INDEX documents_country_category_idx ON documents (country, visa_category);
CREATE INDEX chunks_document_id_idx ON chunks (document_id);
