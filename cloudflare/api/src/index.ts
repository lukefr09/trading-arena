/**
 * Trading Arena API - Main Worker entry point
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import type { Env } from './types';
import state from './routes/state';
import leaderboard from './routes/leaderboard';
import bot from './routes/bot';
import trades from './routes/trades';
import social from './routes/social';
import memory from './routes/memory';
import { authMiddleware } from './middleware/auth';

// Re-export Durable Object
export { ArenaRoom } from './arena-room';

const app = new Hono<{ Bindings: Env }>();

// Global middleware
app.use('*', logger());
app.use('*', cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
}));

// Health check
app.get('/', (c) => {
  return c.json({
    name: 'Trading Arena API',
    version: '0.1.0',
    status: 'healthy',
  });
});

// Mount routes
app.route('/api/state', state);
app.route('/api/leaderboard', leaderboard);
app.route('/api/bot', bot);
app.route('/api/trades', trades);
app.route('/api/social', social);
app.route('/api/memory', memory);

// POST /api/round/increment - Increment round counter (authenticated)
app.post('/api/round/increment', authMiddleware, async (c) => {
  const db = c.env.DB;

  // Increment round
  await db.prepare(`
    UPDATE game
    SET current_round = current_round + 1,
        updated_at = datetime('now')
    WHERE id = 1
  `).run();

  // Get new round number
  const game = await db.prepare(
    'SELECT current_round FROM game WHERE id = 1'
  ).first();

  const newRound = (game?.current_round as number) || 0;

  // Create snapshots for all bots
  await db.prepare(`
    INSERT INTO snapshots (bot_id, total_value, round, captured_at)
    SELECT id, total_value, ?, datetime('now')
    FROM bots
    WHERE enabled = 1
  `).bind(newRound).run();

  // Broadcast round start
  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  await room.fetch('http://internal/broadcast', {
    method: 'POST',
    body: JSON.stringify({
      type: 'round_start',
      data: { round: newRound },
    }),
  });

  return c.json({ round: newRound });
});

// POST /api/broadcast - Broadcast message to WebSocket clients (authenticated)
app.post('/api/broadcast', authMiddleware, async (c) => {
  const body = await c.req.json();

  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  await room.fetch('http://internal/broadcast', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  return c.json({ success: true });
});

// WebSocket endpoint
app.get('/ws', async (c) => {
  const upgradeHeader = c.req.header('Upgrade');

  if (upgradeHeader !== 'websocket') {
    return c.json({ error: 'Expected websocket upgrade' }, 426);
  }

  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  return room.fetch(c.req.raw);
});

// GET /ws/connections - Get WebSocket connection count
app.get('/ws/connections', async (c) => {
  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  const response = await room.fetch('http://internal/connections');
  const data = await response.json();

  return c.json(data);
});

export default app;
