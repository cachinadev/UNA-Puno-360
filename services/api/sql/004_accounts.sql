-- Execute AFTER 003_community.sql. Idempotent migration.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
ALTER TABLE community_users DROP CONSTRAINT IF EXISTS valid_role;
ALTER TABLE community_users ADD CONSTRAINT valid_role CHECK(role IN ('student','moderator','admin','superadmin'));
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS account_status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS auth_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS failed_logins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
ALTER TABLE community_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE UNIQUE INDEX IF NOT EXISTS community_users_email_lower_idx ON community_users(lower(email)) WHERE email IS NOT NULL;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='community_account_status_check') THEN
  ALTER TABLE community_users ADD CONSTRAINT community_account_status_check CHECK(account_status IN ('pending','active','suspended','banned'));
 END IF;
END $$;
CREATE TABLE IF NOT EXISTS auth_sessions(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id TEXT NOT NULL REFERENCES community_users(id) ON DELETE CASCADE,
 refresh_hash TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ,
 user_agent TEXT, last_used TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS auth_sessions_user_idx ON auth_sessions(user_id) WHERE revoked_at IS NULL;
CREATE TABLE IF NOT EXISTS auth_one_time_tokens(
 id BIGSERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES community_users(id) ON DELETE CASCADE,
 purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')), token_hash TEXT NOT NULL UNIQUE,
 expires_at TIMESTAMPTZ NOT NULL, consumed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS auth_one_time_user_idx ON auth_one_time_tokens(user_id,purpose);
CREATE TABLE IF NOT EXISTS admin_audit(
 id BIGSERIAL PRIMARY KEY, actor_id TEXT REFERENCES community_users(id),
 target_id TEXT, action TEXT NOT NULL, details JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS admin_audit_date_idx ON admin_audit(created_at DESC);
