-- Scent Finder schema (Lakebase Postgres 17, pgvector + pg_trgm).
-- Recreates the tables: seed.py is the source of truth for fragrances and my_collection.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

DROP TABLE IF EXISTS chat_usage, wear_log, my_collection, fragrances CASCADE;

CREATE TABLE fragrances (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    house        TEXT NOT NULL,
    year         INT,
    perfumer     TEXT,
    family       TEXT NOT NULL,             -- woody, citrus, amber, floral, aromatic, chypre, leather, ...
    subfamily    TEXT,
    top_notes    TEXT[] NOT NULL DEFAULT '{}',  -- pyramid: curated rows only
    heart_notes  TEXT[] NOT NULL DEFAULT '{}',
    base_notes   TEXT[] NOT NULL DEFAULT '{}',
    notes        TEXT[] NOT NULL DEFAULT '{}',  -- every note, all sources; search runs on this
    accords      TEXT[] NOT NULL DEFAULT '{}',
    season       TEXT[] NOT NULL DEFAULT '{}',
    season_inferred BOOLEAN NOT NULL DEFAULT FALSE,  -- derived from family, not sourced
    price_band   TEXT CHECK (price_band IN ('budget','mid','niche','luxury')),  -- NULL = unknown
    gender       TEXT,
    description  TEXT,
    source       TEXT NOT NULL CHECK (source IN ('curated','doevent')),
    low_confidence BOOLEAN NOT NULL DEFAULT FALSE,  -- curated notes that are a best guess
    embedding    vector(1024),
    UNIQUE (name, house)
);

CREATE INDEX fragrances_name_trgm ON fragrances USING gin ((lower(name || ' ' || house)) gin_trgm_ops);
CREATE INDEX fragrances_notes ON fragrances USING gin (notes);
CREATE INDEX fragrances_embedding ON fragrances USING hnsw (embedding vector_cosine_ops);

CREATE TABLE my_collection (
    user_email   TEXT NOT NULL,                 -- signed-in user (X-Forwarded-Email in the app)
    fragrance_id INT NOT NULL REFERENCES fragrances(id),
    status       TEXT NOT NULL CHECK (status IN ('owned','sampled','wishlist')),
    rating       INT CHECK (rating BETWEEN 1 AND 5),
    notes        TEXT,
    PRIMARY KEY (user_email, fragrance_id)
);

CREATE TABLE wear_log (
    id           SERIAL PRIMARY KEY,
    user_email   TEXT NOT NULL,
    fragrance_id INT NOT NULL REFERENCES fragrances(id),
    worn_on      DATE NOT NULL DEFAULT CURRENT_DATE,
    rating       INT CHECK (rating BETWEEN 1 AND 5),
    context      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX wear_log_user ON wear_log (user_email, fragrance_id);

-- Per-user daily guide message counter (rate limit)
CREATE TABLE chat_usage (
    user_email TEXT NOT NULL,
    day        DATE NOT NULL DEFAULT CURRENT_DATE,
    messages   INT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_email, day)
);
