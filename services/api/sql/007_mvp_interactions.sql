-- Persistent demonstration workflows. Existing service records are preserved.
ALTER TABLE library_books ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
ALTER TABLE library_books ADD COLUMN IF NOT EXISTS total_copies INTEGER NOT NULL DEFAULT 0 CHECK(total_copies>=0);
ALTER TABLE library_books ADD COLUMN IF NOT EXISTS available_copies INTEGER NOT NULL DEFAULT 0 CHECK(available_copies>=0);
ALTER TABLE library_books ADD COLUMN IF NOT EXISTS demo_record BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE library_books ADD CONSTRAINT library_copy_bounds CHECK(available_copies<=total_copies) NOT VALID;

CREATE TABLE IF NOT EXISTS library_reservations(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), reservation_number TEXT UNIQUE NOT NULL,
 user_id TEXT NOT NULL REFERENCES community_users(id) ON DELETE CASCADE,
 book_id BIGINT NOT NULL REFERENCES library_books(id),
 status TEXT NOT NULL DEFAULT 'requested' CHECK(status IN ('requested','confirmed','ready','collected','expired','cancelled')),
 pickup_deadline TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS library_reservation_active_unique ON library_reservations(user_id,book_id)
 WHERE status IN ('requested','confirmed','ready','collected');
CREATE INDEX IF NOT EXISTS library_reservation_user_idx ON library_reservations(user_id,created_at DESC);

ALTER TABLE dining_menus ADD COLUMN IF NOT EXISTS quota INTEGER NOT NULL DEFAULT 0 CHECK(quota>=0);
ALTER TABLE dining_menus ADD COLUMN IF NOT EXISTS demo_record BOOLEAN NOT NULL DEFAULT FALSE;
CREATE TABLE IF NOT EXISTS meal_reservations(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), confirmation_code TEXT UNIQUE NOT NULL,
 user_id TEXT NOT NULL REFERENCES community_users(id) ON DELETE CASCADE,
 menu_id BIGINT NOT NULL REFERENCES dining_menus(id),
 status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed','checked_in','cancelled')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(user_id,menu_id)
);

ALTER TABLE community_events ADD COLUMN IF NOT EXISTS capacity INTEGER CHECK(capacity IS NULL OR capacity>0);
ALTER TABLE community_events ADD COLUMN IF NOT EXISTS demo_record BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE community_events ADD COLUMN IF NOT EXISTS demo_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS community_events_demo_key_unique ON community_events(demo_key) WHERE demo_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS user_notifications(
 id BIGSERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES community_users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', target_url TEXT,
 read_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS user_notifications_unread_idx ON user_notifications(user_id,created_at DESC) WHERE read_at IS NULL;

CREATE TABLE IF NOT EXISTS user_preferences(
 user_id TEXT PRIMARY KEY REFERENCES community_users(id) ON DELETE CASCADE,
 theme TEXT NOT NULL DEFAULT 'system' CHECK(theme IN ('light','dark','system')),
 language TEXT NOT NULL DEFAULT 'es', transport_alerts BOOLEAN NOT NULL DEFAULT TRUE,
 reservation_alerts BOOLEAN NOT NULL DEFAULT TRUE, community_alerts BOOLEAN NOT NULL DEFAULT TRUE,
 semester TEXT, interests TEXT[] NOT NULL DEFAULT '{}', profile_public BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
