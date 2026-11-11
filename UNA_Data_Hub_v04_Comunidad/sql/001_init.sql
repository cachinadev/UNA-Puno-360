CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS geo_places (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point,4326) NOT NULL,
    reviewed BOOLEAN NOT NULL DEFAULT false,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source,source_id),
    CONSTRAINT source_nonempty CHECK(length(source)>0),
    CONSTRAINT category_nonempty CHECK(length(category)>0)
);
CREATE INDEX IF NOT EXISTS geo_places_geom_gist ON geo_places USING GIST(geom);
CREATE INDEX IF NOT EXISTS geo_places_category_idx ON geo_places(category);
CREATE INDEX IF NOT EXISTS geo_places_tags_gin ON geo_places USING GIN(tags);
-- Only records with public metadata; never ingest personal student data here.
CREATE TABLE IF NOT EXISTS academic_records (
    source TEXT NOT NULL,
    identifier TEXT NOT NULL,
    title TEXT NOT NULL,
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    published TEXT,
    url TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(source,identifier)
);
