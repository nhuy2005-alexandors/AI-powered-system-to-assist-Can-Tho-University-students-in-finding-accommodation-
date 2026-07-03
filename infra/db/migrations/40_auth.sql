-- Multi-provider auth. Runs AFTER 30_users.sql.
-- 1 user (danh tính người) có nhiều identity (cách đăng nhập).
-- Thiết kế mở rộng: local | google | ctu(MSSV) chỉ khác 'provider'.

CREATE TABLE user_identities (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider         VARCHAR(20) NOT NULL,      -- 'local' | 'google' | 'ctu'
    provider_user_id VARCHAR(255) NOT NULL,     -- email(local) | google sub | mssv(ctu)
    secret_hash      TEXT,                       -- bcrypt cho local/ctu; NULL cho oauth
    created_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE (provider, provider_user_id)
);
CREATE INDEX idx_identities_user ON user_identities (user_id);

-- password_hash trên users trở nên thừa (local password sống ở user_identities).
-- Giữ cột để không phá migration 30; không dùng nữa.
