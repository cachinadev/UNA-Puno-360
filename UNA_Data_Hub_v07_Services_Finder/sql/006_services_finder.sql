-- UNA Conecta 360 v0.7: curated public campus service facilities.
-- Geometry WGS84 point; only PUBLIC business/facility metadata.
CREATE TABLE IF NOT EXISTS campus_facilities (
 id BIGSERIAL PRIMARY KEY,
 source TEXT NOT NULL CHECK (source IN ('osm','operator','demo')),
 source_id TEXT NOT NULL,
 name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 180),
 category TEXT NOT NULL CHECK (category IN
  ('food','cafe','printing','copies','bathroom','medical','medical_tests','pharmacy','water','wifi','atm','other')),
 description TEXT,
 address TEXT,
 location_hint TEXT,
 opening_hours TEXT,
 contact_public TEXT,
 accessibility TEXT CHECK (accessibility IN ('yes','limited','no','unknown')) DEFAULT 'unknown',
 cost_info TEXT,
 tags JSONB NOT NULL DEFAULT '{}'::jsonb,
 geom geometry(Point,4326) NOT NULL,
 reviewed BOOLEAN NOT NULL DEFAULT false,
 public_enabled BOOLEAN NOT NULL DEFAULT false,
 verified_at TIMESTAMPTZ,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE (source, source_id)
);
CREATE INDEX IF NOT EXISTS campus_facilities_geom_gist ON campus_facilities USING GIST (geom);
CREATE INDEX IF NOT EXISTS campus_facilities_cat_public_idx ON campus_facilities(category, public_enabled, reviewed);
CREATE INDEX IF NOT EXISTS campus_facilities_tags_idx ON campus_facilities USING GIN (tags);
CREATE TABLE IF NOT EXISTS campus_facility_audit (
 id BIGSERIAL PRIMARY KEY,
 actor_id TEXT NOT NULL,
 facility_id BIGINT,
 action TEXT NOT NULL,
 details JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
