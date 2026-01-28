-- Migration: Add social features (messages and rejected trades)
-- Run this to add chat/DM capability and track rejected trades for entertainment

-- Messages for public chat and DMs between bots
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round INTEGER NOT NULL,
    from_bot TEXT NOT NULL REFERENCES bots(id),
    to_bot TEXT REFERENCES bots(id),  -- NULL = public message, otherwise DM
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Rejected trades (for entertainment - showing blocked trades)
CREATE TABLE IF NOT EXISTS rejected_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL REFERENCES bots(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    shares REAL NOT NULL,
    reason TEXT NOT NULL,
    round INTEGER NOT NULL,
    attempted_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_round ON messages(round);
CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_bot);
CREATE INDEX IF NOT EXISTS idx_rejected_round ON rejected_trades(round);
