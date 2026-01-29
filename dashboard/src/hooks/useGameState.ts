/**
 * Game state hook - fetches and manages game state with WebSocket updates
 */

import { useCallback, useEffect, useState } from 'react';
import type { GameState, LeaderboardEntry, Trade, WebSocketMessage, Message, RejectedTrade, BotPortfolio } from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';

interface UseGameStateReturn {
  state: GameState | null;
  leaderboard: LeaderboardEntry[];
  recentTrades: Trade[];
  messages: Message[];
  rejectedTrades: RejectedTrade[];
  portfolios: BotPortfolio[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  handleWebSocketMessage: (message: WebSocketMessage) => void;
}

export function useGameState(): UseGameStateReturn {
  const [state, setState] = useState<GameState | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [rejectedTrades, setRejectedTrades] = useState<RejectedTrade[]>([]);
  const [portfolios, setPortfolios] = useState<BotPortfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSocialData = useCallback(async () => {
    try {
      // Fetch messages, rejected trades, and portfolios in parallel
      const [messagesRes, rejectedRes, portfoliosRes] = await Promise.all([
        fetch(`${API_URL}/api/social/messages?limit=50`),
        fetch(`${API_URL}/api/social/rejected?limit=20`),
        fetch(`${API_URL}/api/social/portfolios`),
      ]);

      if (messagesRes.ok) {
        const data = await messagesRes.json() as { messages: Message[] };
        setMessages(data.messages);
      }

      if (rejectedRes.ok) {
        const data = await rejectedRes.json() as { rejected_trades: RejectedTrade[] };
        setRejectedTrades(data.rejected_trades);
      }

      if (portfoliosRes.ok) {
        const data = await portfoliosRes.json() as { portfolios: BotPortfolio[] };
        setPortfolios(data.portfolios);
      }
    } catch (err) {
      console.error('Failed to fetch social data:', err);
    }
  }, []);

  const fetchState = useCallback(async () => {
    try {
      // Fetch live leaderboard from Alpaca (updates DB too)
      const liveResponse = await fetch(`${API_URL}/api/leaderboard/live`);
      if (liveResponse.ok) {
        const liveData = await liveResponse.json() as {
          current_round: number;
          starting_cash: number;
          leaderboard: LeaderboardEntry[];
        };
        setLeaderboard(liveData.leaderboard);
      }

      // Fetch full state
      const response = await fetch(`${API_URL}/api/state`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json() as GameState;
      setState(data);

      // If live fetch failed, build leaderboard from state
      if (!liveResponse.ok) {
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
      }

      // Set recent trades
      setRecentTrades(data.recent_trades);

      // Also fetch social data
      await fetchSocialData();

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch state');
    } finally {
      setLoading(false);
    }
  }, [fetchSocialData]);

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'leaderboard': {
        const data = message.data as { round: number; leaderboard: LeaderboardEntry[] };
        if (!Array.isArray(data.leaderboard)) break;
        setLeaderboard(
          data.leaderboard
            .filter((bot): bot is LeaderboardEntry => bot != null && typeof bot.id === 'string')
            .map((bot, index) => ({
              ...bot,
              rank: index + 1,
            }))
        );
        setState(prev => prev ? { ...prev, current_round: data.round } : null);
        break;
      }

      case 'trade': {
        const trade = message.data as Trade;
        setRecentTrades(prev => [trade, ...prev.slice(0, 49)]);
        break;
      }

      case 'bot_update': {
        const data = message.data as { bot?: { id: string; total_value: number }; trades?: Trade[] };
        if (data.bot && typeof data.bot.id === 'string') {
          const botId = data.bot.id;
          const botValue = data.bot.total_value;
          setLeaderboard(prev => {
            const updated = prev
              .filter((entry): entry is LeaderboardEntry => entry != null && typeof entry.id === 'string')
              .map(entry =>
                entry.id === botId
                  ? { ...entry, total_value: botValue }
                  : entry
              );
            return updated.sort((a, b) => b.total_value - a.total_value)
              .map((entry, index) => ({ ...entry, rank: index + 1 }));
          });
        }
        if (data.trades && Array.isArray(data.trades) && data.trades.length > 0) {
          setRecentTrades(prev => [...data.trades!, ...prev].slice(0, 50));
        }
        break;
      }

      case 'round_start': {
        const data = message.data as { round: number };
        setState(prev => prev ? { ...prev, current_round: data.round } : null);
        break;
      }

      case 'message': {
        const msg = message.data as Message;
        setMessages(prev => [msg, ...prev.slice(0, 49)]);
        break;
      }

      case 'rejected_trade': {
        const rejected = message.data as RejectedTrade;
        setRejectedTrades(prev => [rejected, ...prev.slice(0, 19)]);
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
    messages,
    rejectedTrades,
    portfolios,
    loading,
    error,
    refresh: fetchState,
    handleWebSocketMessage,
  };
}
