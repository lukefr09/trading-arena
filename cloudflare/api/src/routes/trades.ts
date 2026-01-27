/**
 * Trades routes - trade history and recording
 */

import { Hono } from 'hono';
import type { Env, Trade } from '../types';
import { authMiddleware } from '../middleware/auth';

const trades = new Hono<{ Bindings: Env }>();

// GET /api/trades - Get recent trades (public)
trades.get('/', async (c) => {
  const db = c.env.DB;
  const limit = parseInt(c.req.query('limit') || '50');
  const offset = parseInt(c.req.query('offset') || '0');
  const botId = c.req.query('bot_id');
  const round = c.req.query('round');

  let query = `
    SELECT t.*, b.name as bot_name
    FROM trades t
    JOIN bots b ON t.bot_id = b.id
  `;
  const conditions: string[] = [];
  const values: unknown[] = [];

  if (botId) {
    conditions.push('t.bot_id = ?');
    values.push(botId);
  }
  if (round) {
    conditions.push('t.round = ?');
    values.push(parseInt(round));
  }

  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }

  query += ' ORDER BY t.executed_at DESC LIMIT ? OFFSET ?';
  values.push(limit, offset);

  const result = await db.prepare(query).bind(...values).all();

  // Get total count for pagination
  let countQuery = 'SELECT COUNT(*) as count FROM trades t';
  if (conditions.length > 0) {
    countQuery += ' WHERE ' + conditions.join(' AND ');
  }
  const countResult = await db.prepare(countQuery)
    .bind(...values.slice(0, conditions.length))
    .first();

  return c.json({
    trades: result.results,
    pagination: {
      limit,
      offset,
      total: (countResult?.count as number) || 0,
    },
  });
});

// POST /api/trades - Record a new trade (authenticated)
trades.post('/', authMiddleware, async (c) => {
  const db = c.env.DB;
  const trade = await c.req.json<Trade>();

  const result = await db.prepare(`
    INSERT INTO trades (bot_id, symbol, side, shares, price, commentary, round, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
  `).bind(
    trade.bot_id,
    trade.symbol,
    trade.side,
    trade.shares,
    trade.price,
    trade.commentary,
    trade.round,
    trade.executed_at
  ).run();

  // Broadcast to WebSocket clients
  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  await room.fetch('http://internal/broadcast', {
    method: 'POST',
    body: JSON.stringify({
      type: 'trade',
      data: {
        ...trade,
        id: result.meta.last_row_id,
      },
    }),
  });

  return c.json({
    success: true,
    id: result.meta.last_row_id,
  });
});

// POST /api/trades/batch - Record multiple trades (authenticated)
trades.post('/batch', authMiddleware, async (c) => {
  const db = c.env.DB;
  const body = await c.req.json<{ trades: Trade[] }>();

  const stmt = db.prepare(`
    INSERT INTO trades (bot_id, symbol, side, shares, price, commentary, round, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
  `);

  const batch = body.trades.map(trade =>
    stmt.bind(
      trade.bot_id,
      trade.symbol,
      trade.side,
      trade.shares,
      trade.price,
      trade.commentary,
      trade.round,
      trade.executed_at
    )
  );

  await db.batch(batch);

  // Broadcast to WebSocket clients
  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  for (const trade of body.trades) {
    await room.fetch('http://internal/broadcast', {
      method: 'POST',
      body: JSON.stringify({
        type: 'trade',
        data: trade,
      }),
    });
  }

  return c.json({
    success: true,
    count: body.trades.length,
  });
});

export default trades;
