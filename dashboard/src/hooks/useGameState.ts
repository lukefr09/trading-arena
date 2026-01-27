/**
 * Game state hook - fetches and manages game state with WebSocket updates
 */

import { useCallback, useEffect, useState } from 'react';
import type { GameState, LeaderboardEntry, Trade, WebSocketMessage } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8787';

interface UseGameStateReturn {
  state: GameState | null;
  leaderboard: LeaderboardEntry[];
  recentTrades: Trade[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  handleWebSocketMessage: (message: WebSocketMessage) => void;
}

export function useGameState(): UseGameStateReturn {
  const [state, setState] = useState<GameState | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/state`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json() as GameState;
      setState(data);

      // Build leaderboard from bots
      const startingCash = data.starting_cash;
      const sortedBots = [...data.bots].sort((a, b) => b.total_value - a.total_value);
      const lb: LeaderboardEntry[] = sortedBots.map((bot, index) => ({
        rank: index + 1,
        id: bot.id,
        name: bot.name,
        type: bot.type,
        total_value: bot.total_value,
        return_pct: ((bot.total_value / startingCash) - 1) * 100,
        last_commentary: bot.last_commentary,
        updated_at: bot.updated_at,
      }));
      setLeaderboard(lb);

      // Set recent trades
      setRecentTrades(data.recent_trades);

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch state');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'leaderboard': {
        const data = message.data as { round: number; leaderboard: LeaderboardEntry[] };
        setLeaderboard(data.leaderboard.map((bot, index) => ({
          ...bot,
          rank: index + 1,
        })));
        setState(prev => prev ? { ...prev, current_round: data.round } : null);
        break;
      }

      case 'trade': {
        const trade = message.data as Trade;
        setRecentTrades(prev => [trade, ...prev.slice(0, 49)]);
        break;
      }

      case 'bot_update': {
        const data = message.data as { bot: { id: string; total_value: number }; trades: Trade[] };
        setLeaderboard(prev => {
          const updated = prev.map(entry =>
            entry.id === data.bot.id
              ? { ...entry, total_value: data.bot.total_value }
              : entry
          );
          return updated.sort((a, b) => b.total_value - a.total_value)
            .map((entry, index) => ({ ...entry, rank: index + 1 }));
        });
        if (data.trades.length > 0) {
          setRecentTrades(prev => [...data.trades, ...prev].slice(0, 50));
        }
        break;
      }

      case 'round_start': {
        const data = message.data as { round: number };
        setState(prev => prev ? { ...prev, current_round: data.round } : null);
        break;
      }

      default:
        break;
    }
  }, []);

  useEffect(() => {
    fetchState();

    // Poll every 30 seconds as backup
    const pollInterval = setInterval(fetchState, 30000);

    return () => {
      clearInterval(pollInterval);
    };
  }, [fetchState]);

  return {
    state,
    leaderboard,
    recentTrades,
    loading,
    error,
    refresh: fetchState,
    handleWebSocketMessage,
  };
}
