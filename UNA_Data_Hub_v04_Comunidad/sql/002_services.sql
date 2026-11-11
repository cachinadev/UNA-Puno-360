-- Public-service metadata only. No student, borrower or beneficiary records.
CREATE TABLE IF NOT EXISTS library_branches (
 id BIGSERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 address TEXT, opening_hours TEXT, source_url TEXT NOT NULL,
 verified BOOLEAN NOT NULL DEFAULT FALSE, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 geom geometry(Point,4326)
);
CREATE INDEX IF NOT EXISTS library_branches_geom_gist ON library_branches USING GIST(geom);
CREATE TABLE IF NOT EXISTS library_books (
 id BIGSERIAL PRIMARY KEY, external_id TEXT UNIQUE NOT NULL,
 title TEXT NOT NULL, authors TEXT[] NOT NULL DEFAULT '{}', publication_year INT,
 isbn TEXT, subject TEXT, branch_code TEXT REFERENCES library_branches(code),
 catalog_url TEXT NOT NULL, availability TEXT NOT NULL DEFAULT 'not_verified',
 source_label TEXT NOT NULL DEFAULT 'manual_verified', verified BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT valid_book_availability CHECK (availability IN ('available','unavailable','unknown','not_verified')),
 CONSTRAINT valid_publication_year CHECK(publication_year IS NULL OR publication_year BETWEEN 1450 AND 2200)
);
CREATE INDEX IF NOT EXISTS library_books_title_idx ON library_books USING GIN(to_tsvector('spanish',title));
CREATE INDEX IF NOT EXISTS library_books_branch_idx ON library_books(branch_code);
CREATE TABLE IF NOT EXISTS dining_locations (
 id BIGSERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 address TEXT, source_url TEXT NOT NULL, verified BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), geom geometry(Point,4326)
);
CREATE INDEX IF NOT EXISTS dining_locations_geom_gist ON dining_locations USING GIST(geom);
CREATE TABLE IF NOT EXISTS dining_menus (
 id BIGSERIAL PRIMARY KEY, location_code TEXT NOT NULL REFERENCES dining_locations(code),
 service_date DATE NOT NULL, meal_type TEXT NOT NULL, description TEXT NOT NULL,
 allergens TEXT[] NOT NULL DEFAULT '{}', source_url TEXT NOT NULL,
 verified BOOLEAN NOT NULL DEFAULT FALSE, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(location_code,service_date,meal_type),
 CONSTRAINT valid_meal_type CHECK(meal_type IN ('breakfast','lunch','dinner'))
);
CREATE INDEX IF NOT EXISTS dining_menus_date_idx ON dining_menus(service_date);
CREATE TABLE IF NOT EXISTS dining_announcements (
 id BIGSERIAL PRIMARY KEY, external_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
 body TEXT NOT NULL DEFAULT '', published_on DATE, deadline DATE,
 url TEXT NOT NULL, verified BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
