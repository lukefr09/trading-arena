/**
 * Bot routes - individual bot details and updates
 */

import { Hono } from 'hono';
import type { Env, Bot, Position } from '../types';
import { authMiddleware } from '../middleware/auth';

const bot = new Hono<{ Bindings: Env }>();

// GET /api/bot/:id - Get individual bot details (public)
bot.get('/:id', async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('id');

  // Get bot
  const botRow = await db.prepare(
    'SELECT * FROM bots WHERE id = ?'
  ).bind(botId).first();

  if (!botRow) {
    return c.json({ error: 'Bot not found' }, 404);
  }

  // Get positions
  const positionsResult = await db.prepare(
    'SELECT * FROM positions WHERE bot_id = ?'
  ).bind(botId).all();

  // Get recent trades
  const tradesResult = await db.prepare(
    'SELECT * FROM trades WHERE bot_id = ? ORDER BY executed_at DESC LIMIT 20'
  ).bind(botId).all();

  // Get game info for return calculation
  const game = await db.prepare(
    'SELECT starting_cash FROM game WHERE id = 1'
  ).first();
  const startingCash = (game?.starting_cash as number) || 100000;

  const botData: Bot & { return_pct: number; trades: unknown[] } = {
    id: botRow.id as string,
    name: botRow.name as string,
    type: botRow.type as 'baseline' | 'free_agent',
    cash: botRow.cash as number,
    total_value: botRow.total_value as number,
    return_pct: ((botRow.total_value as number) / startingCash - 1) * 100,
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
    trades: tradesResult.results,
  };

  return c.json(botData);
});

// PUT /api/bot/:id - Update bot (authenticated)
bot.put('/:id', authMiddleware, async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('id');
  const body = await c.req.json<Partial<Bot>>();

  // Build update query
  const updates: string[] = [];
  const values: unknown[] = [];

  if (body.cash !== undefined) {
    updates.push('cash = ?');
    values.push(body.cash);
  }
  if (body.total_value !== undefined) {
    updates.push('total_value = ?');
    values.push(body.total_value);
  }
  if (body.session_id !== undefined) {
    updates.push('session_id = ?');
    values.push(body.session_id);
  }
  if (body.last_commentary !== undefined) {
    updates.push('last_commentary = ?');
    values.push(body.last_commentary);
  }
  if (body.enabled !== undefined) {
    updates.push('enabled = ?');
    values.push(body.enabled ? 1 : 0);
  }

  updates.push("updated_at = datetime('now')");
  values.push(botId);

  await db.prepare(
    `UPDATE bots SET ${updates.join(', ')} WHERE id = ?`
  ).bind(...values).run();

  // Update positions if provided
  if (body.positions) {
    // Clear existing
    await db.prepare(
      'DELETE FROM positions WHERE bot_id = ?'
    ).bind(botId).run();

    // Insert new
    for (const pos of body.positions) {
      await db.prepare(`
        INSERT INTO positions (bot_id, symbol, shares, avg_cost, current_price)
        VALUES (?, ?, ?, ?, ?)
      `).bind(
        botId,
        pos.symbol,
        pos.shares,
        pos.avg_cost,
        pos.current_price
      ).run();
    }
  }

  return c.json({ success: true });
});

export default bot;
