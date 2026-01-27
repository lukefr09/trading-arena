/**
 * Type definitions for Trading Arena API
 */

export interface Env {
  DB: D1Database;
  ARENA_ROOM: DurableObjectNamespace;
  API_KEY: string;
  ENVIRONMENT: string;
}

export interface Bot {
  id: string;
  name: string;
  type: 'baseline' | 'free_agent';
  cash: number;
  total_value: number;
  session_id: string | null;
  last_commentary: string | null;
  enabled: boolean;
  updated_at: string | null;
  positions?: Position[];
}

export interface Position {
  id?: number;
  bot_id: string;
  symbol: string;
  shares: number;
  avg_cost: number;
  current_price: number | null;
}

export interface Trade {
  id?: number;
  bot_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  shares: number;
  price: number;
  commentary: string | null;
  round: number;
  executed_at: string | null;
}

export interface GameState {
  status: 'running' | 'paused';
  starting_cash: number;
  current_round: number;
  bots: Bot[];
  recent_trades: Trade[];
  created_at: string | null;
  updated_at: string | null;
}

export interface Snapshot {
  id?: number;
  bot_id: string;
  total_value: number;
  round: number;
  captured_at: string | null;
}

export interface WebSocketMessage {
  type: 'bot_update' | 'leaderboard' | 'trade' | 'round_start' | 'round_end';
  data: unknown;
}
