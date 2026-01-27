/**
 * Type definitions for Trading Arena Dashboard
 */

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
  return_pct?: number;
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
  bot_name?: string;
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

export interface LeaderboardEntry {
  rank: number;
  id: string;
  name: string;
  type: 'baseline' | 'free_agent';
  total_value: number;
  return_pct: number;
  last_commentary: string | null;
  updated_at: string | null;
}

export interface LeaderboardResponse {
  current_round: number;
  starting_cash: number;
  leaderboard: LeaderboardEntry[];
}

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected';

export interface WebSocketMessage {
  type: 'connected' | 'bot_update' | 'leaderboard' | 'trade' | 'round_start' | 'round_end' | 'pong';
  data: unknown;
}
