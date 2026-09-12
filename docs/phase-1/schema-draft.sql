-- PriceWise Phase 1 schema draft (PostgreSQL).
-- Not applied yet. This is the planning contract for Phase 2 (database + first connector).

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TYPE retailer_status AS ENUM ('pilot', 'connected', 'delayed', 'error', 'disabled', 'planned');
CREATE TYPE match_decision AS ENUM ('auto', 'review', 'rejected', 'unmatched');
CREATE TYPE freshness_tier AS ENUM ('popular', 'normal', 'rare');
CREATE TYPE availability_status AS ENUM ('in_stock', 'out_of_stock', 'unknown');

CREATE TABLE retailers (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    logo_url        TEXT,
    website_url     TEXT NOT NULL,
    platform        TEXT,
    scraping_method TEXT NOT NULL,
    status          retailer_status NOT NULL DEFAULT 'planned',
    last_successful_sync TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE retailer_cities (
    retailer_id TEXT NOT NULL REFERENCES retailers(id),
    city        TEXT NOT NULL,
    PRIMARY KEY (retailer_id, city)
);

CREATE TABLE categories (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    parent_id   BIGINT REFERENCES categories(id)
);

CREATE TABLE products (
    id          BIGSERIAL PRIMARY KEY,
    brand       TEXT,
    name        TEXT NOT NULL,
    category_id BIGINT REFERENCES categories(id),
    description TEXT,
    image_url   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Canonical sellable unit. Multipacks are distinct variants.
CREATE TABLE product_variants (
    id            BIGSERIAL PRIMARY KEY,
    product_id    BIGINT NOT NULL REFERENCES products(id),
    variant_name  TEXT NOT NULL,
    pack_count    INTEGER NOT NULL DEFAULT 1 CHECK (pack_count >= 1),
    size_value    NUMERIC(12, 4) NOT NULL,
    size_unit     TEXT NOT NULL,          -- g, ml, piece (canonical)
    size_label    TEXT NOT NULL,          -- display: "1 kg", "2 × 1.5 L"
    barcode       TEXT UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, pack_count, size_value, size_unit)
);

CREATE TABLE retailer_products (
    id                     BIGSERIAL PRIMARY KEY,
    retailer_id            TEXT NOT NULL REFERENCES retailers(id),
    product_id             BIGINT REFERENCES products(id),
    variant_id             BIGINT REFERENCES product_variants(id),
    retailer_product_name  TEXT NOT NULL,
    retailer_product_url  TEXT NOT NULL,
    retailer_sku           TEXT,
    barcode                TEXT,
    image_url              TEXT,
    availability           availability_status NOT NULL DEFAULT 'unknown',
    match_confidence        NUMERIC(5, 2),
    match_decision          match_decision NOT NULL DEFAULT 'unmatched',
    city                   TEXT NOT NULL DEFAULT 'Karachi',
    UNIQUE (retailer_id, retailer_sku, city),
    UNIQUE (retailer_id, retailer_product_url)
);

CREATE INDEX retailer_products_barcode_idx ON retailer_products (barcode) WHERE barcode IS NOT NULL;
CREATE INDEX retailer_products_unmatched_idx ON retailer_products (match_decision) WHERE match_decision IN ('unmatched', 'review');

-- Never overwrite. Latest row is current price.
CREATE TABLE prices (
    id                   BIGSERIAL PRIMARY KEY,
    retailer_product_id  BIGINT NOT NULL REFERENCES retailer_products(id),
    price                NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    compare_at_price     NUMERIC(12, 2),
    discount             NUMERIC(12, 2),
    currency             CHAR(3) NOT NULL DEFAULT 'PKR',
    availability          availability_status NOT NULL,
    collected_at        TIMESTAMPTZ NOT NULL,
    source               TEXT NOT NULL,
    suspicious           BOOLEAN NOT NULL DEFAULT FALSE,
    suspicion_reason    TEXT
);

CREATE INDEX prices_retailer_product_collected_idx
    ON prices (retailer_product_id, collected_at DESC);

CREATE TABLE match_reviews (
    id                   BIGSERIAL PRIMARY KEY,
    retailer_product_id  BIGINT NOT NULL REFERENCES retailer_products(id),
    candidate_variant_id BIGINT REFERENCES product_variants(id),
    confidence           NUMERIC(5, 2) NOT NULL,
    status               match_decision NOT NULL DEFAULT 'review',
    reviewer_note        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at          TIMESTAMPTZ
);

CREATE TABLE collection_jobs (
    id              BIGSERIAL PRIMARY KEY,
    retailer_id     TEXT NOT NULL REFERENCES retailers(id),
    job_type        TEXT NOT NULL, -- search | product | catalog
    tier            freshness_tier NOT NULL DEFAULT 'normal',
    status          TEXT NOT NULL,
    started_at     TIMESTAMPTZ,
    finished_at    TIMESTAMPTZ,
    error           TEXT,
    items_upserted INTEGER DEFAULT 0
);

CREATE TABLE search_documents (
    variant_id  BIGINT PRIMARY KEY REFERENCES product_variants(id),
    tsv         tsvector NOT NULL
);

CREATE INDEX search_documents_tsv_idx ON search_documents USING GIN (tsv);
CREATE INDEX products_name_trgm_idx ON products USING GIN (name gin_trgm_ops);
CREATE INDEX retailer_products_name_trgm_idx ON retailer_products USING GIN (retailer_product_name gin_trgm_ops);
