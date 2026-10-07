-- User-owned conversation history. Deleting a conversation removes its cached answers.
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_owner
    ON chatbot_conversations (user_id, updated_at DESC, id);

CREATE TABLE IF NOT EXISTS chatbot_turns (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES chatbot_conversations(id) ON DELETE CASCADE,
    question TEXT NOT NULL CHECK (length(question) BETWEEN 2 AND 2000),
    response JSONB NOT NULL,
    cache_key CHAR(64),
    cache_scope CHAR(64) NOT NULL,
    cache_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_turns_conversation
    ON chatbot_turns (conversation_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_chat_turns_cache
    ON chatbot_turns (cache_key, cache_scope, cache_expires_at DESC)
    WHERE cache_key IS NOT NULL;
