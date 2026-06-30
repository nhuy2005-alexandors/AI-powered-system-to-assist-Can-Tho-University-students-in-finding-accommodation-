-- Người dùng + AI vectors + tương tác. Runs AFTER 20_listings.sql.

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT,                       -- NULL nếu OAuth
    name            VARCHAR(100),
    avatar_url      TEXT,
    phone           VARCHAR(20),                -- lộ khi matching accept
    role            VARCHAR(20) DEFAULT 'user', -- 'guest'|'user'|'admin'
    preference_vector VECTOR(384),              -- T5 recommend
    email_verified  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- listings.posted_by tham chiếu users (UGC). Thêm sau khi users tồn tại.
ALTER TABLE aggregated_listings
    ADD COLUMN posted_by INTEGER REFERENCES users(id);

CREATE TABLE roommate_profiles (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sleep_time      INTEGER,                    -- 0 sớm | 1 thường | 2 cú đêm
    cleanliness     INTEGER,                    -- 1-5
    smoke           BOOLEAN,
    noise_tolerance INTEGER,                    -- 1-5
    gender_pref     INTEGER,                    -- 0 không quan tâm | 1 nam | 2 nữ
    bio             TEXT,
    matching_vector VECTOR(384),                -- T7
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_interactions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id  INTEGER NOT NULL REFERENCES aggregated_listings(id) ON DELETE CASCADE,
    type        VARCHAR(20) NOT NULL,           -- view|bookmark|click_source|click_phone
    duration_ms INTEGER,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_interactions_user ON user_interactions (user_id, created_at DESC);

CREATE TABLE reports (
    id          SERIAL PRIMARY KEY,
    listing_id  INTEGER NOT NULL REFERENCES aggregated_listings(id) ON DELETE CASCADE,
    reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reason      VARCHAR(50),                    -- wrong_price|expired|scam|other
    note        TEXT,
    status      VARCHAR(20) DEFAULT 'pending',  -- pending|reviewed|dismissed
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_reports_status ON reports (status);

CREATE TABLE match_requests (
    id          SERIAL PRIMARY KEY,
    from_user   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score       REAL,
    status      VARCHAR(20) DEFAULT 'pending',  -- pending|accepted|rejected
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (from_user, to_user)
);
CREATE INDEX idx_match_to_user ON match_requests (to_user, status);

-- tiêu chí tìm kiếm đã lưu → thông báo tin mới khớp (FR-8.1)
CREATE TABLE saved_searches (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    criteria    JSONB NOT NULL,                 -- {min_price, max_price, district, amenities[]}
    created_at  TIMESTAMPTZ DEFAULT now()
);
