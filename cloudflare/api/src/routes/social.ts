/**
 * Social routes - messages, all portfolios, round context
 */

import { Hono } from 'hono';
import type { Env } from '../types';
import { authMiddleware } from '../middleware/auth';

const social = new Hono<{ Bindings: Env }>();

interface Message {
  id: number;
  round: number;
  from_bot: string;
  to_bot: string | null;
  content: string;
  created_at: string;
}

interface SendMessageRequest {
  from_bot: string;
  to_bot?: string;
  content: string;
}

interface RejectedTrade {
  id: number;
  bot_id: string;
  symbol: string;
  side: string;
  shares: number;
  reason: string;
  round: number;
  attempted_at: string;
}

// GET /api/social/messages - Get recent messages (public)
social.get('/messages', async (c) => {
  const db = c.env.DB;
  const round = c.req.query('round');
  const limit = parseInt(c.req.query('limit') || '50');

  let query = `
    SELECT m.*, b.name as from_name
    FROM messages m
    JOIN bots b ON m.from_bot = b.id
  `;
  const params: (string | number)[] = [];

  if (round) {
    query += ' WHERE m.round = ?';
    params.push(parseInt(round));
  }

  query += ' ORDER BY m.created_at DESC LIMIT ?';
  params.push(limit);

  const result = await db.prepare(query).bind(...params).all();

  return c.json({
    messages: result.results.map(m => ({
      id: m.id,
      round: m.round,
      from_bot: m.from_bot,
      from_name: m.from_name,
      to_bot: m.to_bot,
      content: m.content,
      is_dm: m.to_bot !== null,
      created_at: m.created_at,
    })),
  });
});

// GET /api/social/messages/:botId - Get messages for a specific bot (including DMs to them)
social.get('/messages/:botId', async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('botId');
  const round = c.req.query('round');
  const limit = parseInt(c.req.query('limit') || '50');

  // Get public messages + DMs to this bot
  let query = `
    SELECT m.*, b.name as from_name
    FROM messages m
    JOIN bots b ON m.from_bot = b.id
    WHERE (m.to_bot IS NULL OR m.to_bot = ?)
  `;
  const params: (string | number)[] = [botId];

  if (round) {
    query += ' AND m.round = ?';
    params.push(parseInt(round));
  }

  query += ' ORDER BY m.created_at DESC LIMIT ?';
  params.push(limit);

  const result = await db.prepare(query).bind(...params).all();

  return c.json({
    messages: result.results.map(m => ({
      id: m.id,
      round: m.round,
      from_bot: m.from_bot,
      from_name: m.from_name,
      to_bot: m.to_bot,
      content: m.content,
      is_dm: m.to_bot !== null,
      created_at: m.created_at,
    })),
  });
});

// POST /api/social/messages - Send a message (authenticated)
social.post('/messages', authMiddleware, async (c) => {
  const db = c.env.DB;
  const body = await c.req.json<SendMessageRequest>();

  if (!body.from_bot || !body.content) {
    return c.json({ error: 'from_bot and content are required' }, 400);
  }

  // Get current round
  const game = await db.prepare('SELECT current_round FROM game WHERE id = 1').first();
  const currentRound = (game?.current_round as number) || 0;

  // Insert message
  const result = await db.prepare(`
    INSERT INTO messages (round, from_bot, to_bot, content)
    VALUES (?, ?, ?, ?)
  `).bind(
    currentRound,
    body.from_bot,
    body.to_bot || null,
    body.content
  ).run();

  // Broadcast to WebSocket
  try {
    const roomId = c.env.ARENA_ROOM.idFromName('main');
    const room = c.env.ARENA_ROOM.get(roomId);

    // Get bot name
    const bot = await db.prepare('SELECT name FROM bots WHERE id = ?').bind(body.from_bot).first();

    await room.fetch('http://internal/broadcast', {
      method: 'POST',
      body: JSON.stringify({
        type: 'message',
        data: {
          id: result.meta.last_row_id,
          round: currentRound,
          from_bot: body.from_bot,
          from_name: bot?.name,
          to_bot: body.to_bot || null,
          content: body.content,
          is_dm: !!body.to_bot,
        },
      }),
    });
  } catch {
    // Don't fail if broadcast fails
  }

  return c.json({
    success: true,
    message_id: result.meta.last_row_id,
    round: currentRound,
  });
});

// GET /api/social/portfolios - Get all bot portfolios (public)
social.get('/portfolios', async (c) => {
  const db = c.env.DB;

  // Get game info
  const game = await db.prepare('SELECT starting_cash, current_round FROM game WHERE id = 1').first();
  const startingCash = (game?.starting_cash as number) || 100000;
  const currentRound = (game?.current_round as number) || 0;

  // Get all bots
  const botsResult = await db.prepare(`
    SELECT id, name, type, cash, total_value, last_commentary
    FROM bots
    ORDER BY total_value DESC
  `).all();

  // Get all positions
  const positionsResult = await db.prepare(`
    SELECT bot_id, symbol, shares, avg_cost, current_price
    FROM positions
  `).all();

  // Group positions by bot
  const positionsByBot: Record<string, Array<{
    symbol: string;
    shares: number;
    avg_cost: number;
    current_price: number | null;
    market_value: number;
    gain_pct: number;
  }>> = {};

  for (const p of positionsResult.results) {
    const botId = p.bot_id as string;
    if (!positionsByBot[botId]) {
      positionsByBot[botId] = [];
    }
    const currentPrice = (p.current_price as number | null) || (p.avg_cost as number);
    const marketValue = (p.shares as number) * currentPrice;
    const costBasis = (p.shares as number) * (p.avg_cost as number);
    const gainPct = costBasis > 0 ? ((marketValue - costBasis) / costBasis) * 100 : 0;

    positionsByBot[botId].push({
      symbol: p.symbol as string,
      shares: p.shares as number,
      avg_cost: p.avg_cost as number,
      current_price: currentPrice,
      market_value: marketValue,
      gain_pct: gainPct,
    });
  }

  const portfolios = botsResult.results.map((bot, index) => {
    const totalValue = bot.total_value as number;
    const returnPct = ((totalValue / startingCash) - 1) * 100;

    return {
      rank: index + 1,
      id: bot.id,
      name: bot.name,
      type: bot.type,
      cash: bot.cash,
      total_value: totalValue,
      return_pct: Math.round(returnPct * 100) / 100,
      last_commentary: bot.last_commentary,
      positions: positionsByBot[bot.id as string] || [],
    };
  });

  return c.json({
    round: currentRound,
    starting_cash: startingCash,
    portfolios,
  });
});

// GET /api/social/rejected - Get rejected trades (public)
social.get('/rejected', async (c) => {
  const db = c.env.DB;
  const round = c.req.query('round');
  const limit = parseInt(c.req.query('limit') || '20');

  let query = `
    SELECT r.*, b.name as bot_name
    FROM rejected_trades r
    JOIN bots b ON r.bot_id = b.id
  `;
  const params: (string | number)[] = [];

  if (round) {
    query += ' WHERE r.round = ?';
    params.push(parseInt(round));
  }

  query += ' ORDER BY r.attempted_at DESC LIMIT ?';
  params.push(limit);

  const result = await db.prepare(query).bind(...params).all();

  return c.json({
    rejected_trades: result.results.map(r => ({
      id: r.id,
      bot_id: r.bot_id,
      bot_name: r.bot_name,
      symbol: r.symbol,
      side: r.side,
      shares: r.shares,
      reason: r.reason,
      round: r.round,
      attempted_at: r.attempted_at,
    })),
  });
});

// POST /api/social/rejected - Record a rejected trade (authenticated)
social.post('/rejected', authMiddleware, async (c) => {
  const db = c.env.DB;

  interface RejectedTradeRequest {
    bot_id: string;
    symbol: string;
    side: string;
    shares: number;
    reason: string;
  }

  const body = await c.req.json<RejectedTradeRequest>();

  // Get current round
  const game = await db.prepare('SELECT current_round FROM game WHERE id = 1').first();
  const currentRound = (game?.current_round as number) || 0;

  const result = await db.prepare(`
    INSERT INTO rejected_trades (bot_id, symbol, side, shares, reason, round)
    VALUES (?, ?, ?, ?, ?, ?)
  `).bind(
    body.bot_id,
    body.symbol.toUpperCase(),
    body.side.toUpperCase(),
    body.shares,
    body.reason,
    currentRound
  ).run();

  // Broadcast to WebSocket
  try {
    const roomId = c.env.ARENA_ROOM.idFromName('main');
    const room = c.env.ARENA_ROOM.get(roomId);

    const bot = await db.prepare('SELECT name FROM bots WHERE id = ?').bind(body.bot_id).first();

    await room.fetch('http://internal/broadcast', {
      method: 'POST',
      body: JSON.stringify({
        type: 'rejected_trade',
        data: {
          id: result.meta.last_row_id,
          bot_id: body.bot_id,
          bot_name: bot?.name,
          symbol: body.symbol.toUpperCase(),
          side: body.side.toUpperCase(),
          shares: body.shares,
          reason: body.reason,
          round: currentRound,
        },
      }),
    });
  } catch {
    // Don't fail if broadcast fails
  }

  return c.json({ success: true, id: result.meta.last_row_id });
});

// GET /api/social/context/:botId - Get full round context for a bot
social.get('/context/:botId', async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('botId');

  // Get game info
  const game = await db.prepare('SELECT starting_cash, current_round FROM game WHERE id = 1').first();
  const startingCash = (game?.starting_cash as number) || 100000;
  const currentRound = (game?.current_round as number) || 0;

  // Get leaderboard (all bots sorted by total_value)
  const botsResult = await db.prepare(`
    SELECT id, name, type, cash, total_value, last_commentary
    FROM bots
    ORDER BY total_value DESC
  `).all();

  const leaderboard = botsResult.results.map((bot, index) => ({
    rank: index + 1,
    id: bot.id,
    name: bot.name,
    type: bot.type,
    total_value: bot.total_value,
    return_pct: Math.round((((bot.total_value as number) / startingCash) - 1) * 100 * 100) / 100,
    last_commentary: bot.last_commentary,
  }));

  // Get recent trades (last 2 rounds)
  const tradesResult = await db.prepare(`
    SELECT t.*, b.name as bot_name
    FROM trades t
    JOIN bots b ON t.bot_id = b.id
    WHERE t.round >= ?
    ORDER BY t.executed_at DESC
    LIMIT 30
  `).bind(Math.max(0, currentRound - 1)).all();

  // Get recent rejected trades
  const rejectedResult = await db.prepare(`
    SELECT r.*, b.name as bot_name
    FROM rejected_trades r
    JOIN bots b ON r.bot_id = b.id
    WHERE r.round >= ?
    ORDER BY r.attempted_at DESC
    LIMIT 10
  `).bind(Math.max(0, currentRound - 1)).all();

  // Get messages (public + DMs to this bot)
  const messagesResult = await db.prepare(`
    SELECT m.*, b.name as from_name
    FROM messages m
    JOIN bots b ON m.from_bot = b.id
    WHERE m.round >= ? AND (m.to_bot IS NULL OR m.to_bot = ?)
    ORDER BY m.created_at DESC
    LIMIT 30
  `).bind(Math.max(0, currentRound - 1), botId).all();

  // Get all positions grouped by bot
  const positionsResult = await db.prepare(`
    SELECT bot_id, symbol, shares, avg_cost, current_price
    FROM positions
  `).all();

  const positionsByBot: Record<string, Array<{
    symbol: string;
    shares: number;
    market_value: number;
  }>> = {};

  for (const p of positionsResult.results) {
    const bid = p.bot_id as string;
    if (!positionsByBot[bid]) {
      positionsByBot[bid] = [];
    }
    const price = (p.current_price as number | null) || (p.avg_cost as number);
    positionsByBot[bid].push({
      symbol: p.symbol as string,
      shares: p.shares as number,
      market_value: (p.shares as number) * price,
    });
  }

  return c.json({
    round: currentRound,
    starting_cash: startingCash,
    your_bot_id: botId,
    leaderboard,
    positions_by_bot: positionsByBot,
    recent_trades: tradesResult.results.map(t => ({
      bot_id: t.bot_id,
      bot_name: t.bot_name,
      symbol: t.symbol,
      side: t.side,
      shares: t.shares,
      price: t.price,
      commentary: t.commentary,
      round: t.round,
      executed_at: t.executed_at,
    })),
    rejected_trades: rejectedResult.results.map(r => ({
      bot_id: r.bot_id,
      bot_name: r.bot_name,
      symbol: r.symbol,
      side: r.side,
      shares: r.shares,
      reason: r.reason,
      round: r.round,
    })),
    messages: messagesResult.results.map(m => ({
      from_bot: m.from_bot,
      from_name: m.from_name,
      to_bot: m.to_bot,
      content: m.content,
      is_dm: m.to_bot !== null,
      round: m.round,
    })),
  });
});

export default social;
