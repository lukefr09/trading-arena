/**
 * Bot routes - individual bot details and updates
 */

import { Hono } from 'hono';
import type { Env, Bot, Position, Trade } from '../types';
import { authMiddleware } from '../middleware/auth';

const bot = new Hono<{ Bindings: Env }>();

// S&P 500 symbols (subset for Turtle validation)
const SP500_SYMBOLS = new Set([
  'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'BRK.B',
  'UNH', 'XOM', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
  'LLY', 'PEP', 'KO', 'COST', 'AVGO', 'WMT', 'MCD', 'CSCO', 'TMO', 'ACN',
  'ABT', 'DHR', 'NEE', 'DIS', 'VZ', 'ADBE', 'WFC', 'PM', 'CMCSA', 'CRM',
  'NKE', 'TXN', 'RTX', 'BMY', 'UPS', 'QCOM', 'HON', 'ORCL', 'T', 'COP',
  'AMGN', 'INTC', 'IBM', 'CAT', 'SPGI', 'PLD', 'LOW', 'BA', 'GS', 'INTU',
  'SBUX', 'MDLZ', 'AMD', 'BLK', 'DE', 'AXP', 'ELV', 'GILD', 'LMT', 'ISRG',
  'ADI', 'CVS', 'BKNG', 'TJX', 'VRTX', 'REGN', 'SYK', 'TMUS', 'MMC', 'PGR',
  'ADP', 'ZTS', 'CI', 'LRCX', 'SCHW', 'NOW', 'MO', 'EOG', 'BDX', 'C',
  'PYPL', 'SO', 'ETN', 'DUK', 'SLB', 'CB', 'ITW', 'NOC', 'BSX', 'EQIX',
  'CME', 'APD', 'MU', 'SNPS', 'ATVI', 'ICE', 'AON', 'HUM', 'FCX', 'CSX',
  'CL', 'WM', 'GD', 'MCK', 'USB', 'EMR', 'PXD', 'KLAC', 'NSC', 'ORLY',
  'SHW', 'MAR', 'MCO', 'PNC', 'CDNS', 'NXPI', 'F', 'GM', 'ROP', 'HCA',
  'AZO', 'FDX', 'PSA', 'TRV', 'D', 'AEP', 'TFC', 'KMB', 'MRNA', 'OXY',
  'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'BND', 'AGG', 'TLT',
]);

// Hedge symbols for Doomer
const HEDGE_SYMBOLS = new Set([
  'SQQQ', 'UVXY', 'SH', 'SPXS', 'VXX', 'SDOW', 'SPXU', 'QID', 'SDS', 'TZA',
]);

// Leveraged/meme stocks for Degen
const DEGEN_FAVORITES = new Set([
  'TQQQ', 'SOXL', 'UPRO', 'SPXL', 'TECL', 'FAS', 'LABU', 'FNGU', 'WEBL',
  'GME', 'AMC', 'BBBY', 'DWAC', 'MARA', 'RIOT', 'COIN', 'HOOD', 'PLTR',
]);

// Crypto-related stocks
const CRYPTO_STOCKS = new Set(['COIN', 'MARA', 'RIOT', 'BITO']);

interface OrderRequest {
  side: 'BUY' | 'SELL';
  shares: number;
  symbol: string;
  reason?: string;
}

interface BotConstraints {
  maxPositionPct?: number;
  minCashPct?: number;
  maxCashPct?: number;
  sp500Only?: boolean;
  maxLongEquityPct?: number;
  requiresHedges?: boolean;
  noCrypto?: boolean;
  noLeverage?: boolean;
}

const BOT_CONSTRAINTS: Record<string, BotConstraints> = {
  turtle: {
    maxPositionPct: 0.05,
    minCashPct: 0.30,
    sp500Only: true,
  },
  degen: {
    maxCashPct: 0.20,
  },
  boomer: {
    noCrypto: true,
    noLeverage: true,
  },
  quant: {
    // Must cite technical indicator - validated in commentary
  },
  doomer: {
    maxLongEquityPct: 0.30,
    requiresHedges: true,
  },
};

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

  // Alpaca credentials (from request body, not from Bot type)
  const bodyAny = body as Record<string, unknown>;
  if (bodyAny.alpaca_api_key !== undefined) {
    updates.push('alpaca_api_key = ?');
    values.push(bodyAny.alpaca_api_key);
  }
  if (bodyAny.alpaca_secret_key !== undefined) {
    updates.push('alpaca_secret_key = ?');
    values.push(bodyAny.alpaca_secret_key);
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

// POST /api/bot/:id/order - Execute a trade order (authenticated)
bot.post('/:id/order', authMiddleware, async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('id');
  const order = await c.req.json<OrderRequest>();

  // Validate request
  if (!order.side || !['BUY', 'SELL'].includes(order.side)) {
    return c.json({ success: false, reason: 'Invalid side. Must be BUY or SELL' }, 400);
  }
  if (!order.shares || order.shares <= 0) {
    return c.json({ success: false, reason: 'Invalid shares. Must be positive' }, 400);
  }
  if (!order.symbol) {
    return c.json({ success: false, reason: 'Symbol is required' }, 400);
  }

  const symbol = order.symbol.toUpperCase();

  // Get bot data
  const botRow = await db.prepare('SELECT * FROM bots WHERE id = ?').bind(botId).first();
  if (!botRow) {
    return c.json({ success: false, reason: 'Bot not found' }, 404);
  }

  const botCash = botRow.cash as number;
  const botTotalValue = botRow.total_value as number;
  const botType = botRow.type as string;

  // Get positions
  const positionsResult = await db.prepare(
    'SELECT * FROM positions WHERE bot_id = ?'
  ).bind(botId).all();

  const positions = positionsResult.results.map(p => ({
    symbol: p.symbol as string,
    shares: p.shares as number,
    avgCost: p.avg_cost as number,
    currentPrice: (p.current_price as number | null) || (p.avg_cost as number),
  }));

  // Get current price for the symbol (from most recent price data)
  // For now, we'll use a simple price lookup from existing positions or estimate
  // In production, this would fetch from a price service
  const existingPosition = positions.find(p => p.symbol === symbol);
  let currentPrice = existingPosition?.currentPrice;

  // If no existing position, try to get price from recent trades
  if (!currentPrice) {
    const recentTrade = await db.prepare(
      'SELECT price FROM trades WHERE symbol = ? ORDER BY executed_at DESC LIMIT 1'
    ).bind(symbol).first();
    currentPrice = recentTrade?.price as number | undefined;
  }

  // If still no price, we need one from the request or fail
  if (!currentPrice) {
    return c.json({
      success: false,
      reason: `No price data available for ${symbol}. Use get_price tool first.`,
    }, 400);
  }

  const tradeValue = order.shares * currentPrice;

  // Basic validation
  if (order.side === 'BUY') {
    if (tradeValue > botCash) {
      return c.json({
        success: false,
        reason: `Insufficient cash: need $${tradeValue.toFixed(2)}, have $${botCash.toFixed(2)}`,
      });
    }
  } else {
    const position = positions.find(p => p.symbol === symbol);
    const currentShares = position?.shares || 0;
    if (order.shares > currentShares) {
      return c.json({
        success: false,
        reason: `Insufficient shares: need ${order.shares}, have ${currentShares}`,
      });
    }
  }

  // Bot-specific constraint validation
  if (botType === 'baseline') {
    const constraints = BOT_CONSTRAINTS[botId];
    const validationError = validateBotConstraints(
      botId,
      constraints,
      order,
      symbol,
      positions,
      botCash,
      botTotalValue,
      tradeValue,
    );
    if (validationError) {
      return c.json({ success: false, reason: validationError });
    }
  }

  // Execute the trade
  let newCash = botCash;
  if (order.side === 'BUY') {
    newCash = botCash - tradeValue;

    // Update or create position
    const existingPos = positions.find(p => p.symbol === symbol);
    if (existingPos) {
      // Calculate new average cost
      const totalShares = existingPos.shares + order.shares;
      const totalCost = (existingPos.shares * existingPos.avgCost) + tradeValue;
      const newAvgCost = totalCost / totalShares;

      await db.prepare(`
        UPDATE positions SET shares = ?, avg_cost = ?, current_price = ?
        WHERE bot_id = ? AND symbol = ?
      `).bind(totalShares, newAvgCost, currentPrice, botId, symbol).run();
    } else {
      await db.prepare(`
        INSERT INTO positions (bot_id, symbol, shares, avg_cost, current_price)
        VALUES (?, ?, ?, ?, ?)
      `).bind(botId, symbol, order.shares, currentPrice, currentPrice).run();
    }
  } else {
    // SELL
    newCash = botCash + tradeValue;

    const existingPos = positions.find(p => p.symbol === symbol);
    if (existingPos) {
      const newShares = existingPos.shares - order.shares;
      if (newShares <= 0) {
        await db.prepare(
          'DELETE FROM positions WHERE bot_id = ? AND symbol = ?'
        ).bind(botId, symbol).run();
      } else {
        await db.prepare(`
          UPDATE positions SET shares = ?, current_price = ?
          WHERE bot_id = ? AND symbol = ?
        `).bind(newShares, currentPrice, botId, symbol).run();
      }
    }
  }

  // Recalculate total value
  const updatedPositionsResult = await db.prepare(
    'SELECT * FROM positions WHERE bot_id = ?'
  ).bind(botId).all();

  let positionsValue = 0;
  for (const p of updatedPositionsResult.results) {
    const price = (p.current_price as number | null) || (p.avg_cost as number);
    positionsValue += (p.shares as number) * price;
  }
  const newTotalValue = newCash + positionsValue;

  // Update bot cash and total value
  await db.prepare(`
    UPDATE bots SET cash = ?, total_value = ?, updated_at = datetime('now')
    WHERE id = ?
  `).bind(newCash, newTotalValue, botId).run();

  // Get current round
  const game = await db.prepare('SELECT current_round FROM game WHERE id = 1').first();
  const currentRound = (game?.current_round as number) || 0;

  // Record the trade
  const tradeResult = await db.prepare(`
    INSERT INTO trades (bot_id, symbol, side, shares, price, commentary, round, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `).bind(
    botId,
    symbol,
    order.side,
    order.shares,
    currentPrice,
    order.reason || null,
    currentRound,
  ).run();

  // Broadcast trade to WebSocket clients
  const roomId = c.env.ARENA_ROOM.idFromName('main');
  const room = c.env.ARENA_ROOM.get(roomId);

  await room.fetch('http://internal/broadcast', {
    method: 'POST',
    body: JSON.stringify({
      type: 'trade',
      data: {
        id: tradeResult.meta.last_row_id,
        bot_id: botId,
        bot_name: botRow.name,
        symbol,
        side: order.side,
        shares: order.shares,
        price: currentPrice,
        round: currentRound,
      },
    }),
  });

  return c.json({
    success: true,
    executed: {
      side: order.side,
      shares: order.shares,
      symbol,
      price: currentPrice,
    },
    new_cash: newCash,
    new_total_value: newTotalValue,
  });
});

function validateBotConstraints(
  botId: string,
  constraints: BotConstraints | undefined,
  order: OrderRequest,
  symbol: string,
  positions: Array<{ symbol: string; shares: number; avgCost: number; currentPrice: number }>,
  cash: number,
  totalValue: number,
  tradeValue: number,
): string | null {
  if (!constraints) return null;

  // Turtle constraints
  if (botId === 'turtle') {
    // S&P 500 only
    if (constraints.sp500Only && !SP500_SYMBOLS.has(symbol)) {
      return `${symbol} not in S&P 500 universe`;
    }

    if (order.side === 'BUY') {
      // Max position size
      if (constraints.maxPositionPct) {
        const existingPos = positions.find(p => p.symbol === symbol);
        const existingValue = existingPos ? existingPos.shares * existingPos.currentPrice : 0;
        const newPositionValue = existingValue + tradeValue;
        const positionPct = newPositionValue / totalValue;

        if (positionPct > constraints.maxPositionPct) {
          return `Position would be ${(positionPct * 100).toFixed(1)}% > ${(constraints.maxPositionPct * 100)}% max allowed`;
        }
      }

      // Min cash
      if (constraints.minCashPct) {
        const cashAfter = cash - tradeValue;
        const cashPct = cashAfter / totalValue;

        if (cashPct < constraints.minCashPct) {
          return `Cash after trade would be ${(cashPct * 100).toFixed(1)}% < ${(constraints.minCashPct * 100)}% minimum`;
        }
      }
    }
  }

  // Degen constraints
  if (botId === 'degen' && order.side === 'SELL') {
    if (constraints.maxCashPct) {
      const cashAfter = cash + tradeValue;
      const cashPct = cashAfter / totalValue;

      if (cashPct > constraints.maxCashPct) {
        return `Cash after sale would be ${(cashPct * 100).toFixed(1)}% > ${(constraints.maxCashPct * 100)}% max - must stay invested`;
      }
    }
  }

  // Boomer constraints
  if (botId === 'boomer' && order.side === 'BUY') {
    if (constraints.noCrypto && CRYPTO_STOCKS.has(symbol)) {
      return `${symbol} is crypto-related - not allowed`;
    }
    if (constraints.noLeverage && DEGEN_FAVORITES.has(symbol)) {
      return `${symbol} is leveraged - not allowed`;
    }
  }

  // Doomer constraints
  if (botId === 'doomer') {
    const isHedge = HEDGE_SYMBOLS.has(symbol);

    // Calculate current long equity
    let longEquity = 0;
    for (const pos of positions) {
      if (!HEDGE_SYMBOLS.has(pos.symbol)) {
        longEquity += pos.shares * pos.currentPrice;
      }
    }

    if (order.side === 'BUY' && !isHedge && constraints.maxLongEquityPct) {
      const newLongEquity = longEquity + tradeValue;
      const longPct = newLongEquity / totalValue;

      if (longPct > constraints.maxLongEquityPct) {
        return `Long equity would be ${(longPct * 100).toFixed(1)}% > ${(constraints.maxLongEquityPct * 100)}% max`;
      }
    }

    if (order.side === 'SELL' && isHedge && constraints.requiresHedges) {
      // Check if this would remove all hedges
      const hedgePositions = positions.filter(p => HEDGE_SYMBOLS.has(p.symbol));
      const existingPos = hedgePositions.find(p => p.symbol === symbol);

      if (existingPos) {
        const remainingShares = existingPos.shares - order.shares;
        const otherHedges = hedgePositions.filter(p => p.symbol !== symbol);

        if (remainingShares <= 0 && otherHedges.length === 0) {
          return 'Must maintain at least one hedge position';
        }
      }
    }
  }

  return null;
}

// GET /api/bot/:id/credentials - Get Alpaca credentials (authenticated)
bot.get('/:id/credentials', authMiddleware, async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('id');

  const botRow = await db.prepare(
    'SELECT id, name, alpaca_api_key, alpaca_secret_key FROM bots WHERE id = ?'
  ).bind(botId).first();

  if (!botRow) {
    return c.json({ error: 'Bot not found' }, 404);
  }

  if (!botRow.alpaca_api_key || !botRow.alpaca_secret_key) {
    return c.json({ error: 'Alpaca credentials not configured for this bot' }, 400);
  }

  return c.json({
    name: botRow.name as string,
    alpaca_api_key: botRow.alpaca_api_key as string,
    alpaca_secret_key: botRow.alpaca_secret_key as string,
  });
});

// POST /api/bot/:id/trade - Record a trade executed via Alpaca (authenticated)
bot.post('/:id/trade', authMiddleware, async (c) => {
  const db = c.env.DB;
  const botId = c.req.param('id');

  interface TradeRecord {
    symbol: string;
    side: string;
    shares: number;
    price: number | null;
    commentary?: string;
  }

  const trade = await c.req.json<TradeRecord>();

  // Get bot to verify it exists
  const botRow = await db.prepare('SELECT * FROM bots WHERE id = ?').bind(botId).first();
  if (!botRow) {
    return c.json({ error: 'Bot not found' }, 404);
  }

  // Get current round
  const game = await db.prepare('SELECT current_round FROM game WHERE id = 1').first();
  const currentRound = (game?.current_round as number) || 0;

  // Record the trade
  const tradeResult = await db.prepare(`
    INSERT INTO trades (bot_id, symbol, side, shares, price, commentary, round, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `).bind(
    botId,
    trade.symbol.toUpperCase(),
    trade.side.toUpperCase(),
    trade.shares,
    trade.price,
    trade.commentary || null,
    currentRound,
  ).run();

  // Broadcast trade to WebSocket clients
  try {
    const roomId = c.env.ARENA_ROOM.idFromName('main');
    const room = c.env.ARENA_ROOM.get(roomId);

    await room.fetch('http://internal/broadcast', {
      method: 'POST',
      body: JSON.stringify({
        type: 'trade',
        data: {
          id: tradeResult.meta.last_row_id,
          bot_id: botId,
          bot_name: botRow.name,
          symbol: trade.symbol.toUpperCase(),
          side: trade.side.toUpperCase(),
          shares: trade.shares,
          price: trade.price,
          round: currentRound,
        },
      }),
    });
  } catch {
    // Don't fail if WebSocket broadcast fails
  }

  return c.json({ success: true, trade_id: tradeResult.meta.last_row_id });
});

export default bot;
