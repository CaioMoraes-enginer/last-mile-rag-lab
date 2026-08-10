-- Extensao de vetores (pgvector). Precisa vir antes de usar o tipo "vector".
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela dos "chunks": pedacos do corpus com metadados, texto e embedding.
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL,
    document_title  TEXT,
    document_type   TEXT,
    page            INTEGER,
    section         TEXT,
    version         TEXT,
    effective_from  TIMESTAMPTZ,
    effective_to    TIMESTAMPTZ,
    zona            TEXT,
    entity_ids      TEXT[],
    content         TEXT NOT NULL,
    content_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', coalesce(content, ''))) STORED,
    embedding       vector(768),
    source_hash     TEXT,
    ingested_at     TIMESTAMPTZ DEFAULT now()
);

-- Indice para busca lexical (texto e IDs exatos como SG-BD, ORD-042).
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON chunks USING GIN (content_tsv);

-- Indices para filtros de metadados (zona, versao, documento).
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_zona     ON chunks (zona);
CREATE INDEX IF NOT EXISTS idx_chunks_version  ON chunks (version);
CREATE INDEX IF NOT EXISTS idx_chunks_effective_from ON chunks (effective_from);
CREATE INDEX IF NOT EXISTS idx_chunks_effective_to   ON chunks (effective_to);
CREATE INDEX IF NOT EXISTS idx_chunks_entity_ids ON chunks USING GIN (entity_ids);

-- Indice vetorial (HNSW, distancia cosseno) para busca por similaridade.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);
