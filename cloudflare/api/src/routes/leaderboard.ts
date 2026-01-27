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
