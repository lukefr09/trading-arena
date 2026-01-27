/**
 * State routes - GET and POST game state
 */

import { Hono } from 'hono';
import type { Env, Bot, Position, Trade, GameState } from '../types';
import { authMiddleware } from '../middleware/auth';

const state = new Hono<{ Bindings: Env }>();

// GET /api/state - Get full game state (public)
state.get('/', async (c) => {
  const db = c.env.DB;

  // Get game state
  const game = await db.prepare(
    'SELECT * FROM game WHERE id = 1'
  ).first();

  if (!game) {
    return c.json({ error: 'Game not initialized' }, 404);
  }

  // Get all bots
  const botsResult = await db.prepare(
    'SELECT * FROM bots ORDER BY total_value DESC'
  ).all();

  const bots: Bot[] = [];

  for (const botRow of botsResult.results) {
    // Get positions for each bot
    const positionsResult = await db.prepare(
      'SELECT * FROM positions WHERE bot_id = ?'
    ).bind(botRow.id).all();

    bots.push({
      id: botRow.id as string,
      name: botRow.name as string,
      type: botRow.type as 'baseline' | 'free_agent',
      cash: botRow.cash as number,
      total_value: botRow.total_value as number,
      session_id: botRow.session_id as string | null,
      last_commentary: botRow.last_commentary as string | null,
      enabled: Boolean(botRow.enabled),
      updated_at: botRow.updated_at as string | null,
      positions: positionsResult.results.map(p => ({
        id: p.id as number,
        bot_id: p.bot_id as string,
        symbol: p.symbol as string,
        shares: p.shares as number,
        avg_cost: p.avg_cost as number,
        current_price: p.current_price as number | null,
      })),
    });
  }

  // Get recent trades (last 50)
  const tradesResult = await db.prepare(
    'SELECT * FROM trades ORDER BY executed_at DESC LIMIT 50'
  ).all();

  const recent_trades: Trade[] = tradesResult.results.map(t => ({
    id: t.id as number,
    bot_id: t.bot_id as string,
    symbol: t.symbol as string,
    side: t.side as 'BUY' | 'SELL',
    shares: t.shares as number,
    price: t.price as number,
    commentary: t.commentary as string | null,
    round: t.round as number,
    executed_at: t.executed_at as string | null,
  }));

  const gameState: GameState = {
    status: game.status as 'running' | 'paused',
    starting_cash: game.starting_cash as number,
    current_round: game.current_round as number,
    bots,
    recent_trades,
    created_at: game.created_at as string | null,
    updated_at: game.updated_at as string | null,
  };

  return c.json(gameState);
});

// POST /api/state - Update full game state (authenticated)
state.post('/', authMiddleware, async (c) => {
  const db = c.env.DB;
  const body = await c.req.json<Partial<GameState>>();

  // Update game record
  if (body.status !== undefined || body.current_round !== undefined) {
    const updates: string[] = [];
    const values: unknown[] = [];

    if (body.status !== undefined) {
      updates.push('status = ?');
      values.push(body.status);
    }
    if (body.current_round !== undefined) {
      updates.push('current_round = ?');
      values.push(body.current_round);
    }
    updates.push("updated_at = datetime('now')");

    await db.prepare(
      `UPDATE game SET ${updates.join(', ')} WHERE id = 1`
    ).bind(...values).run();
  }

  // Update bots if provided
  if (body.bots) {
    for (const bot of body.bots) {
      // Upsert bot
      await db.prepare(`
        INSERT INTO bots (id, name, type, cash, total_value, session_id, last_commentary, enabled, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
          cash = excluded.cash,
          total_value = excluded.total_value,
          session_id = excluded.session_id,
          last_commentary = excluded.last_commentary,
          enabled = excluded.enabled,
          updated_at = datetime('now')
      `).bind(
        bot.id,
        bot.name,
        bot.type,
        bot.cash,
        bot.total_value,
        bot.session_id ?? null,
        bot.last_commentary ?? null,
        bot.enabled ? 1 : 0
      ).run();

      // Update positions
      if (bot.positions) {
        // Clear existing positions
        await db.prepare(
          'DELETE FROM positions WHERE bot_id = ?'
        ).bind(bot.id).run();

        // Insert new positions
        for (const pos of bot.positions) {
          await db.prepare(`
            INSERT INTO positions (bot_id, symbol, shares, avg_cost, current_price)
            VALUES (?, ?, ?, ?, ?)
          `).bind(
            bot.id,
            pos.symbol,
            pos.shares,
            pos.avg_cost,
            pos.current_price
          ).run();
        }
      }
    }
  }

  return c.json({ success: true });
});

export default state;
