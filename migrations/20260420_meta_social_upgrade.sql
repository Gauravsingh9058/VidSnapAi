-- VidSnapAI Meta social connection upgrade
-- Apply this to existing databases that were created before the Meta OAuth implementation.

ALTER TABLE social_accounts ADD COLUMN username VARCHAR(120);
ALTER TABLE social_accounts ADD COLUMN page_id VARCHAR(120);
ALTER TABLE social_accounts ADD COLUMN meta_scopes TEXT;
ALTER TABLE social_accounts ADD COLUMN raw_metadata_json TEXT;
ALTER TABLE social_accounts ADD COLUMN last_error TEXT;

CREATE TABLE IF NOT EXISTS oauth_states (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'meta',
    platform VARCHAR(50) NOT NULL,
    state_hash VARCHAR(128) NOT NULL UNIQUE,
    redirect_uri VARCHAR(255) NOT NULL,
    social_account_id VARCHAR(36),
    expires_at DATETIME NOT NULL,
    used_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_social_account_selections (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    encrypted_user_token TEXT NOT NULL,
    token_expiry DATETIME,
    granted_scopes TEXT,
    raw_assets_json TEXT NOT NULL,
    reconnect_social_account_id VARCHAR(36),
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

UPDATE users
SET plan = 'lifetime'
WHERE plan IS NULL OR plan NOT IN ('lifetime');
