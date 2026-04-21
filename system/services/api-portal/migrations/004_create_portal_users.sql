CREATE TABLE IF NOT EXISTS portal_users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(120) NOT NULL UNIQUE,
    credential VARCHAR(50) NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_portal_users_username ON portal_users (username);
CREATE INDEX IF NOT EXISTS idx_portal_users_active ON portal_users (is_active);
