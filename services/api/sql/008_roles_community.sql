-- Role-aware workspaces and persistent community interactions.
ALTER TABLE community_users DROP CONSTRAINT IF EXISTS valid_role;
ALTER TABLE community_users ADD CONSTRAINT valid_role CHECK(role IN
 ('student','moderator','librarian','transport_operator','admin','superadmin'));

ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'general';
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS demo_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS community_posts_demo_key_unique ON community_posts(demo_key) WHERE demo_key IS NOT NULL;

ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS parent_id BIGINT REFERENCES community_comments(id) ON DELETE CASCADE;
ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS community_bookmarks(
 post_id BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES community_users(id) ON DELETE CASCADE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(post_id,user_id)
);
CREATE INDEX IF NOT EXISTS community_bookmarks_user_idx ON community_bookmarks(user_id,created_at DESC);
