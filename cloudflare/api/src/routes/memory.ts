/**
 * Memory routes - persistent bot memories across rounds
 */

import { Hono } from 'hono';
import type { Env } from '../types';
import { authMiddleware } from '../middleware/auth';

const memory = new Hono<{ Bindings: Env }>();

// Valid memory types
const VALID_TYPES = ['trade', 'rival', 'strategy', 'reflection', 'note'] as const;
type MemoryType = typeof VALID_TYPES[number];

interface CreateMemoryRequest {
  bot_id: string;
  type: MemoryType;
  content: string;
  importance?: number;  // 1-10, default 5
}

interface Memory {
  id: number;
  bot_id: string;
  round: number;
  type: string;
  content: string;
  importance: number;
  created_at: string;
}

// POST /api/memory - Create a new memory (authenticated)
memory.post('/', authMiddleware, async (c) => {
  const db = c.env.DB;
  const body = await c.req.json<CreateMemoryRequest>();

  // Validate required fields
  if (!body.bot_id || !body.type || !body.content) {
    return c.json({ error: 'bot_id, type, and content are required' }, 400);
  }

  // Validate type
  if (!VALID_TYPES.includes(body.type)) {
    return c.json({
      error: `Invalid type. Must be one of: ${VALID_TYPES.join(', ')}`
    }, 400);
  }

  // Validate importance if provided
  const importance = body.importance ?? 5;
  if (importance < 1 || importance > 10) {
    return c.json({ error: 'Importance must be between 1 and 10' }, 400);
  }

  // Get current round
  const game = await db.prepare('SELECT current_round FROM game WHERE id = 1').first();
  const currentRound = (game?.current_round as number) || 0;

  // Insert memory
  const result = await db.prepare(`
    INSERT INTO memories (bot_id, round, type, content, importance)
    VALUES (?, ?, ?, ?, ?)
  `).bind(
    body.bot_id,
    currentRound,
    body.type,
    body.content,
    importance
  ).run();

  return c.json({
    success: true,
    memory_id: result.meta.last_row_id,
    round: currentRound,
  });
});

// GET /api/memory/:botId - Get memories for a bot (public)
memory.get('/:botId', async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('botId');
  const type = c.req.query('type');
  const count = parseInt(c.req.query('count') || '20');
  const minImportance = parseInt(c.req.query('min_importance') || '1');
  const targetBot = c.req.query('target_bot');  // For filtering rival notes about a specific bot

  // Build query
  let query = `
    SELECT id, bot_id, round, type, content, importance, created_at
    FROM memories
    WHERE bot_id = ?
  `;
  const params: (string | number)[] = [botId];

  // Filter by type if specified
  if (type && VALID_TYPES.includes(type as MemoryType)) {
    query += ' AND type = ?';
    params.push(type);
  }

  // Filter by minimum importance
  if (minImportance > 1) {
    query += ' AND importance >= ?';
    params.push(minImportance);
  }

  // Filter rival notes by target bot (searches content for bot ID)
  if (targetBot && type === 'rival') {
    query += ' AND content LIKE ?';
    params.push(`%${targetBot}%`);
  }

  // Order by round (most recent first), then importance
  query += ' ORDER BY round DESC, importance DESC, created_at DESC LIMIT ?';
  params.push(count);

  const result = await db.prepare(query).bind(...params).all();

  return c.json({
    bot_id: botId,
    count: result.results.length,
    memories: result.results.map(m => ({
      id: m.id,
      round: m.round,
      type: m.type,
      content: m.content,
      importance: m.importance,
      created_at: m.created_at,
    })),
  });
});

// GET /api/memory/:botId/context - Get organized memories for context injection
// Returns short-term (recent rounds) and long-term (high importance) memories
memory.get('/:botId/context', async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('botId');

  // Get current round
  const game = await db.prepare('SELECT current_round FROM game WHERE id = 1').first();
  const currentRound = (game?.current_round as number) || 0;

  // Short-term: Last 3 rounds (all memories)
  const shortTermRounds = 3;
  const shortTermResult = await db.prepare(`
    SELECT id, round, type, content, importance, created_at
    FROM memories
    WHERE bot_id = ? AND round > ?
    ORDER BY round DESC, created_at DESC
    LIMIT 30
  `).bind(botId, Math.max(0, currentRound - shortTermRounds)).all();

  // Long-term: High importance memories (7+) from older rounds
  const longTermResult = await db.prepare(`
    SELECT id, round, type, content, importance, created_at
    FROM memories
    WHERE bot_id = ? AND round <= ? AND importance >= 7
    ORDER BY importance DESC, round DESC
    LIMIT 20
  `).bind(botId, Math.max(0, currentRound - shortTermRounds)).all();

  // Active strategies (most recent strategy memory)
  const strategyResult = await db.prepare(`
    SELECT content, round
    FROM memories
    WHERE bot_id = ? AND type = 'strategy'
    ORDER BY round DESC, created_at DESC
    LIMIT 1
  `).bind(botId).first();

  // Rival notes (grouped by target, most recent per rival)
  const rivalResult = await db.prepare(`
    SELECT content, round, importance
    FROM memories
    WHERE bot_id = ? AND type = 'rival'
    ORDER BY round DESC, importance DESC
    LIMIT 15
  `).bind(botId).all();

  // Format short-term memories by type
  const shortTerm: Record<string, Array<{ content: string; round: number }>> = {};
  for (const m of shortTermResult.results) {
    const type = m.type as string;
    if (!shortTerm[type]) {
      shortTerm[type] = [];
    }
    shortTerm[type].push({
      content: m.content as string,
      round: m.round as number,
    });
  }

  // Format long-term memories
  const longTerm = longTermResult.results.map(m => ({
    type: m.type,
    content: m.content,
    round: m.round,
    importance: m.importance,
  }));

  return c.json({
    current_round: currentRound,
    short_term: shortTerm,
    long_term: longTerm,
    active_strategy: strategyResult ? {
      content: strategyResult.content,
      since_round: strategyResult.round,
    } : null,
    rival_notes: rivalResult.results.map(r => ({
      content: r.content,
      round: r.round,
    })),
  });
});

// DELETE /api/memory/:memoryId - Delete a specific memory (authenticated)
memory.delete('/:memoryId', authMiddleware, async (c) => {
  const db = c.env.DB;
  const memoryId = c.req.param('memoryId');

  await db.prepare('DELETE FROM memories WHERE id = ?').bind(memoryId).run();

  return c.json({ success: true });
});

export default memory;
