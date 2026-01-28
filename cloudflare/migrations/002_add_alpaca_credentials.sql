-- Migration: Add Alpaca paper trading credentials to bots table
-- Run this on existing databases to add the new columns

ALTER TABLE bots ADD COLUMN alpaca_api_key TEXT;
ALTER TABLE bots ADD COLUMN alpaca_secret_key TEXT;
