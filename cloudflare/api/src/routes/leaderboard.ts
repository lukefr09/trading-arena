/**
 * Leaderboard routes
 */

import { Hono } from 'hono';
import type { Env } from '../types';

const leaderboard = new Hono<{ Bindings: Env }>();

// GET /api/leaderboard - Get ranked bot list
leaderboard.get('/', async (c) => {
  const db = c.env.DB;

  // Get game info for starting cash
  const game = await db.prepare(
    'SELECT starting_cash, current_round FROM game WHERE id = 1'
  ).first();

  const startingCash = (game?.starting_cash as number) || 100000;
  const currentRound = (game?.current_round as number) || 0;

  // Get bots ordered by total value
  const result = await db.prepare(`
    SELECT
      id, name, type, cash, total_value, last_commentary, enabled, updated_at
    FROM bots
    WHERE enabled = 1
    ORDER BY total_value DESC
  `).all();

  const leaderboardData = result.results.map((bot, index) => ({
    rank: index + 1,
    id: bot.id,
    name: bot.name,
    type: bot.type,
    total_value: bot.total_value as number,
    return_pct: ((bot.total_value as number) / startingCash - 1) * 100,
    last_commentary: bot.last_commentary,
    updated_at: bot.updated_at,
  }));

  return c.json({
    current_round: currentRound,
    starting_cash: startingCash,
    leaderboard: leaderboardData,
  });
});

// GET /api/leaderboard/live - Fetch fresh data from Alpaca and update
leaderboard.get('/live', async (c) => {
  const db = c.env.DB;

  // Get game info
  const game = await db.prepare(
    'SELECT starting_cash, current_round FROM game WHERE id = 1'
  ).first();

  const startingCash = (game?.starting_cash as number) || 100000;
  const currentRound = (game?.current_round as number) || 0;

  // Get all bots with Alpaca credentials
  const botsResult = await db.prepare(`
    SELECT id, name, type, alpaca_api_key, alpaca_secret_key, enabled
    FROM bots
    WHERE enabled = 1
  `).all();

  const leaderboardData: Array<{
    rank: number;
    id: string;
    name: string;
    type: string;
    total_value: number;
    cash: number;
    return_pct: number;
    updated_at: string;
  }> = [];

  // Fetch live data from Alpaca for each bot
  for (const bot of botsResult.results) {
    const apiKey = bot.alpaca_api_key as string;
    const secretKey = bot.alpaca_secret_key as string;

    if (!apiKey || !secretKey) {
      // Skip bots without Alpaca credentials
      continue;
    }

    try {
      // Fetch account data from Alpaca
      const response = await fetch('https://paper-api.alpaca.markets/v2/account', {
        headers: {
          'APCA-API-KEY-ID': apiKey,
          'APCA-API-SECRET-KEY': secretKey,
        },
      });

      if (!response.ok) {
        console.error(`Alpaca API error for ${bot.id}: ${response.status}`);
        continue;
      }

      const account = await response.json() as { equity: string; cash: string };
      const equity = parseFloat(account.equity);
      const cash = parseFloat(account.cash);

      // Update database with fresh values
      await db.prepare(`
        UPDATE bots
        SET total_value = ?, cash = ?, updated_at = datetime('now')
        WHERE id = ?
      `).bind(equity, cash, bot.id).run();

      leaderboardData.push({
        rank: 0, // Will be set after sorting
        id: bot.id as string,
        name: bot.name as string,
        type: bot.type as string,
        total_value: equity,
        cash: cash,
        return_pct: ((equity / startingCash) - 1) * 100,
        updated_at: new Date().toISOString(),
      });
    } catch (error) {
      console.error(`Error fetching Alpaca data for ${bot.id}:`, error);
    }
  }

  // Sort by total value and assign ranks
  leaderboardData.sort((a, b) => b.total_value - a.total_value);
  leaderboardData.forEach((bot, index) => {
    bot.rank = index + 1;
  });

  return c.json({
    current_round: currentRound,
    starting_cash: startingCash,
    leaderboard: leaderboardData,
    refreshed_at: new Date().toISOString(),
  });
});

// GET /api/leaderboard/history - Get historical snapshots
leaderboard.get('/history', async (c) => {
  const db = c.env.DB;
  const limit = parseInt(c.req.query('limit') || '100');

  const result = await db.prepare(`
    SELECT
      s.bot_id,
      b.name,
      s.total_value,
      s.round,
      s.captured_at
    FROM snapshots s
    JOIN bots b ON s.bot_id = b.id
    ORDER BY s.round DESC, s.total_value DESC
    LIMIT ?
  `).bind(limit).all();

  return c.json({
    snapshots: result.results,
  });
});

export default leaderboard;
