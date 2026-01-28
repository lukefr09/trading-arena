-- Migration: Add bot memories for persistent state across rounds
-- Enables bots to remember trade reasoning, rival notes, strategy evolution, and reflections

-- Memories table - stores both short-term and long-term memories
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL REFERENCES bots(id),
    round INTEGER NOT NULL,
    type TEXT NOT NULL,  -- 'trade', 'rival', 'strategy', 'reflection', 'note'
    content TEXT NOT NULL,  -- JSON or plain text
    importance INTEGER DEFAULT 5,  -- 1-10 scale (10 = most important, used for long-term retention)
    created_at TEXT DEFAULT (datetime('now'))
);

-- Index for fetching a bot's memories efficiently
CREATE INDEX IF NOT EXISTS idx_memories_bot ON memories(bot_id);

-- Index for fetching recent memories (by round)
CREATE INDEX IF NOT EXISTS idx_memories_bot_round ON memories(bot_id, round DESC);

-- Index for fetching by type
CREATE INDEX IF NOT EXISTS idx_memories_bot_type ON memories(bot_id, type);

-- Index for importance-based queries (long-term memory retrieval)
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(bot_id, importance DESC);
