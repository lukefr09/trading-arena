-- Trading Arena D1 Database Schema

CREATE TABLE game (
    id INTEGER PRIMARY KEY DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'paused',
    starting_cash REAL NOT NULL DEFAULT 100000.00,
    current_round INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE bots (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'baseline' or 'free_agent'
    cash REAL NOT NULL,
    total_value REAL NOT NULL,
    session_id TEXT,
    last_commentary TEXT,
    enabled INTEGER DEFAULT 1,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL REFERENCES bots(id),
    symbol TEXT NOT NULL,
    shares REAL NOT NULL,
    avg_cost REAL NOT NULL,
    current_price REAL,
    UNIQUE(bot_id, symbol)
);

CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL REFERENCES bots(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'BUY' or 'SELL'
    shares REAL NOT NULL,
    price REAL NOT NULL,
    commentary TEXT,
    round INTEGER NOT NULL,
    executed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL REFERENCES bots(id),
    total_value REAL NOT NULL,
    round INTEGER NOT NULL,
    captured_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_trades_bot ON trades(bot_id);
CREATE INDEX idx_trades_round ON trades(round);
CREATE INDEX idx_positions_bot ON positions(bot_id);
CREATE INDEX idx_snapshots_bot ON snapshots(bot_id);
CREATE INDEX idx_snapshots_round ON snapshots(round);

-- Insert default game record
INSERT INTO game (id, status, starting_cash, current_round) VALUES (1, 'paused', 100000.00, 0);
