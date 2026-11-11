-- UNA Comunidad: fictitious demo users only; production requires institutional SSO.
CREATE TABLE IF NOT EXISTS community_users (
 id TEXT PRIMARY KEY, display_name TEXT NOT NULL CHECK(length(display_name) BETWEEN 2 AND 90),
 faculty TEXT, bio TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'student',
 is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT valid_role CHECK(role IN ('student','moderator','admin'))
);
CREATE TABLE IF NOT EXISTS community_groups (
 id BIGSERIAL PRIMARY KEY, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '', faculty TEXT, visibility TEXT NOT NULL DEFAULT 'public',
 created_by TEXT NOT NULL REFERENCES community_users(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(visibility IN ('public','private'))
);
CREATE TABLE IF NOT EXISTS community_memberships (
 group_id BIGINT NOT NULL REFERENCES community_groups(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES community_users(id),
 role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('member','owner','moderator')),
 joined_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(group_id,user_id)
);
CREATE INDEX IF NOT EXISTS community_memberships_user_idx ON community_memberships(user_id);
CREATE TABLE IF NOT EXISTS community_posts (
 id BIGSERIAL PRIMARY KEY, author_id TEXT NOT NULL REFERENCES community_users(id),
 group_id BIGINT REFERENCES community_groups(id),
 body TEXT NOT NULL CHECK(length(trim(body)) BETWEEN 1 AND 3000),
 status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('published','hidden','deleted')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS community_posts_feed_idx ON community_posts(created_at DESC,id DESC) WHERE status='published';
CREATE INDEX IF NOT EXISTS community_posts_group_idx ON community_posts(group_id,created_at DESC);
CREATE TABLE IF NOT EXISTS community_comments (
 id BIGSERIAL PRIMARY KEY, post_id BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
 author_id TEXT NOT NULL REFERENCES community_users(id),
 body TEXT NOT NULL CHECK(length(trim(body)) BETWEEN 1 AND 1000),
 status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('published','hidden','deleted')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS community_comments_post_idx ON community_comments(post_id,created_at);
CREATE TABLE IF NOT EXISTS community_reactions (
 post_id BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES community_users(id),
 kind TEXT NOT NULL CHECK(kind IN ('like','celebrate','support')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(post_id,user_id)
);
CREATE TABLE IF NOT EXISTS community_events (
 id BIGSERIAL PRIMARY KEY, organizer_id TEXT NOT NULL REFERENCES community_users(id),
 group_id BIGINT REFERENCES community_groups(id), title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '', location_name TEXT,
 starts_at TIMESTAMPTZ NOT NULL, ends_at TIMESTAMPTZ NOT NULL,
 status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('published','cancelled','hidden')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK(ends_at>starts_at)
);
CREATE INDEX IF NOT EXISTS community_events_start_idx ON community_events(starts_at) WHERE status='published';
CREATE TABLE IF NOT EXISTS community_event_attendees (
 event_id BIGINT NOT NULL REFERENCES community_events(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES community_users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(event_id,user_id)
);
CREATE TABLE IF NOT EXISTS community_reports (
 id BIGSERIAL PRIMARY KEY, reporter_id TEXT NOT NULL REFERENCES community_users(id),
 target_type TEXT NOT NULL CHECK(target_type IN ('post','comment','event')),
 target_id BIGINT NOT NULL, reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 5 AND 500),
 status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','reviewed','dismissed')),
 handled_by TEXT REFERENCES community_users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 handled_at TIMESTAMPTZ, UNIQUE(reporter_id,target_type,target_id)
);
CREATE INDEX IF NOT EXISTS community_reports_open_idx ON community_reports(status,created_at);
