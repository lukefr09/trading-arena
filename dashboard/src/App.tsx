import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8787';

const botColors: Record<string, string> = {
  'degen': '#ff6b35',
  'diana': '#a855f7',
  'quant': '#06b6d4',
  'vince': '#ef4444',
  'boomer': '#d97706',
  'rei': '#8b5cf6',
  'gary': '#eab308',
  'turtle': '#22c55e',
  'mel': '#ec4899',
  'doomer': '#64748b',
  'test': '#888888',
};

interface Bot {
  rank: number;
  id: string;
  name: string;
  type: string;
  total_value: number;
  cash: number;
  return_pct: number;
  last_commentary: string | null;
  positions: Position[];
}

interface Position {
  symbol: string;
  shares: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  gain_pct: number;
}

interface Trade {
  id: number;
  bot_id: string;
  bot_name: string;
  symbol: string;
  side: string;
  shares: number;
  price: number;
  commentary: string | null;
  round: number;
  executed_at: string;
}

interface Message {
  id: number;
  from_bot: string;
  from_name: string;
  to_bot: string | null;
  content: string;
  is_dm: boolean;
  created_at: string;
}

interface TimelineEvent {
  id: string;
  type: 'trade' | 'chat';
  bot_id: string;
  bot_name: string;
  time: string;
  action?: string;
  qty?: number;
  symbol?: string;
  price?: number;
  message?: string;
  is_dm?: boolean;
}

interface GameState {
  status: string;
  current_round: number;
  starting_cash: number;
}

export default function TradingArena() {
  const [selectedBot, setSelectedBot] = useState<string | null>(null);
  const [bots, setBots] = useState<Bot[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);

  const formatNum = (n: number, decimals = 2) =>
    n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  const formatPL = (n: number) => (n >= 0 ? '+' : '') + formatNum(n);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const fetchData = useCallback(async () => {
    try {
      const [portfoliosRes, stateRes, tradesRes, messagesRes] = await Promise.all([
        fetch(`${API_URL}/api/social/portfolios`),
        fetch(`${API_URL}/api/state`),
        fetch(`${API_URL}/api/trades?limit=50`),
        fetch(`${API_URL}/api/social/messages?limit=50`),
      ]);

      if (portfoliosRes.ok) {
        const data = await portfoliosRes.json();
        setBots(data.portfolios || []);
      }

      if (stateRes.ok) {
        const data = await stateRes.json();
        setGameState({
          status: data.status,
          current_round: data.current_round,
          starting_cash: data.starting_cash,
        });
      }

      const trades: Trade[] = tradesRes.ok ? (await tradesRes.json()).trades || [] : [];
      const messages: Message[] = messagesRes.ok ? (await messagesRes.json()).messages || [] : [];

      const tradeEvents: TimelineEvent[] = trades.map(t => ({
        id: `trade-${t.id}`,
        type: 'trade',
        bot_id: t.bot_id,
        bot_name: t.bot_name || t.bot_id,
        time: t.executed_at,
        action: t.side,
        qty: t.shares,
        symbol: t.symbol,
        price: t.price,
      }));

      const chatEvents: TimelineEvent[] = messages.map(m => ({
        id: `msg-${m.id}`,
        type: 'chat',
        bot_id: m.from_bot,
        bot_name: m.from_name || m.from_bot,
        time: m.created_at,
        message: m.content,
        is_dm: m.is_dm,
      }));

      const combined = [...tradeEvents, ...chatEvents]
        .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

      setTimeline(combined);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const selectedPortfolio = bots.find(b => b.id === selectedBot);
  const totalPool = bots.reduce((sum, b) => sum + b.total_value, 0);

  const styles: Record<string, React.CSSProperties> = {
    container: {
      minHeight: '100vh',
      backgroundColor: '#0d1117',
      color: '#c9d1d9',
      fontFamily: "'IBM Plex Mono', 'Consolas', monospace",
      fontSize: '12px',
      lineHeight: '1.4',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '6px 12px',
      backgroundColor: '#161b22',
      borderBottom: '1px solid #30363d',
    },
    headerTitle: {
      color: '#ff9f1c',
      fontWeight: '700',
      fontSize: '13px',
      letterSpacing: '0.5px',
    },
    headerStats: {
      display: 'flex',
      gap: '24px',
      fontSize: '11px',
    },
    headerStat: {
      display: 'flex',
      gap: '6px',
    },
    label: {
      color: '#6e7681',
    },
    value: {
      color: '#c9d1d9',
    },
    valueGreen: {
      color: '#3fb950',
    },
    valueRed: {
      color: '#f85149',
    },
    valueAmber: {
      color: '#ff9f1c',
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: selectedBot ? '240px 1fr 320px' : '240px 1fr',
      height: 'calc(100vh - 37px)',
    },
    panel: {
      borderRight: '1px solid #30363d',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    },
    panelHeader: {
      padding: '4px 8px',
      backgroundColor: '#21262d',
      borderBottom: '1px solid #30363d',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      fontSize: '10px',
      fontWeight: '600',
      color: '#ff9f1c',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    panelContent: {
      flex: 1,
      overflowY: 'auto',
      padding: '4px 0',
    },
    leaderboardRow: {
      display: 'grid',
      gridTemplateColumns: '20px 70px 1fr 60px',
      padding: '3px 8px',
      cursor: 'pointer',
      borderLeft: '2px solid transparent',
    },
    leaderboardRowSelected: {
      backgroundColor: '#21262d',
    },
    rank: {
      color: '#6e7681',
      textAlign: 'right',
      paddingRight: '8px',
    },
    botName: {
      fontWeight: '600',
    },
    feedItem: {
      padding: '2px 8px',
      display: 'grid',
      gridTemplateColumns: '62px 60px 1fr',
      gap: '8px',
      borderLeft: '2px solid transparent',
    },
    feedTrade: {
      backgroundColor: '#161b22',
    },
    feedTime: {
      color: '#6e7681',
      fontSize: '10px',
    },
    feedBot: {
      fontWeight: '600',
      fontSize: '11px',
    },
    feedContent: {
      color: '#c9d1d9',
    },
    tradeTag: {
      fontSize: '9px',
      fontWeight: '700',
      padding: '1px 4px',
      marginRight: '6px',
    },
    portfolioStat: {
      display: 'flex',
      justifyContent: 'space-between',
      padding: '2px 8px',
      borderBottom: '1px solid #21262d',
    },
    positionRow: {
      display: 'grid',
      gridTemplateColumns: '50px 40px 60px 60px 55px',
      padding: '2px 8px',
      fontSize: '11px',
    },
    positionHeader: {
      color: '#6e7681',
      borderBottom: '1px solid #30363d',
      marginBottom: '2px',
    },
  };

  if (loading) {
    return (
      <div style={{ ...styles.container, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#ff9f1c' }}>Loading...</span>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={styles.headerTitle}>TRADING ARENA</span>
          <span style={{ color: gameState?.status === 'running' ? '#3fb950' : '#f85149', fontSize: '10px' }}>
            {gameState?.status === 'running' ? '● LIVE' : '○ PAUSED'}
          </span>
        </div>
        <div style={styles.headerStats}>
          <div style={styles.headerStat}>
            <span style={styles.label}>RND</span>
            <span style={styles.valueAmber}>{gameState?.current_round || 0}</span>
          </div>
          <div style={styles.headerStat}>
            <span style={styles.label}>POOL</span>
            <span style={styles.valueGreen}>${formatNum(totalPool, 0)}</span>
          </div>
          <div style={styles.headerStat}>
            <span style={styles.label}>BOTS</span>
            <span style={styles.value}>{bots.length}</span>
          </div>
          <div style={styles.headerStat}>
            <span style={styles.label}>START</span>
            <span style={styles.value}>${formatNum(gameState?.starting_cash || 100000, 0)}</span>
          </div>
        </div>
      </header>

      <div style={styles.grid}>
        <div style={styles.panel}>
          <div style={styles.panelHeader}>
            <span>Leaderboard</span>
          </div>
          <div style={styles.panelContent}>
            {bots.map((bot) => (
              <div
                key={bot.id}
                onClick={() => setSelectedBot(selectedBot === bot.id ? null : bot.id)}
                style={{
                  ...styles.leaderboardRow,
                  ...(selectedBot === bot.id ? styles.leaderboardRowSelected : {}),
                  borderLeftColor: selectedBot === bot.id ? (botColors[bot.id] || '#888') : 'transparent',
                }}
              >
                <span style={styles.rank}>{bot.rank}</span>
                <span style={{ ...styles.botName, color: botColors[bot.id] || '#888' }}>{bot.name}</span>
                <span style={{ color: '#8b949e', fontSize: '11px' }}>
                  {formatNum(bot.total_value, 0)}
                </span>
                <span style={{ textAlign: 'right', color: bot.return_pct >= 0 ? '#3fb950' : '#f85149' }}>
                  {formatPL(bot.return_pct)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ ...styles.panel, borderRight: selectedBot ? '1px solid #30363d' : 'none' }}>
          <div style={styles.panelHeader}>
            <span>Live Feed</span>
            <span style={{ color: '#6e7681', fontWeight: '400' }}>{timeline.length} events</span>
          </div>
          <div style={styles.panelContent}>
            {timeline.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#6e7681' }}>
                No activity yet
              </div>
            ) : (
              timeline.map((event) => (
                <div
                  key={event.id}
                  style={{
                    ...styles.feedItem,
                    ...(event.type === 'trade' ? styles.feedTrade : {}),
                    borderLeftColor: event.type === 'trade'
                      ? (event.action === 'BUY' ? '#3fb950' : event.action === 'SELL' ? '#f85149' : '#6e7681')
                      : 'transparent',
                  }}
                >
                  <span style={styles.feedTime}>{formatTime(event.time)}</span>
                  <span
                    style={{ ...styles.feedBot, color: botColors[event.bot_id] || '#888', cursor: 'pointer' }}
                    onClick={() => setSelectedBot(event.bot_id)}
                  >
                    {event.bot_name}
                  </span>
                  <span style={styles.feedContent}>
                    {event.type === 'trade' ? (
                      <>
                        <span style={{
                          ...styles.tradeTag,
                          backgroundColor: event.action === 'BUY' ? '#238636' : event.action === 'SELL' ? '#da3633' : '#30363d',
                          color: '#fff',
                        }}>
                          {event.action}
                        </span>
                        <span>
                          <span style={{ color: '#c9d1d9' }}>{event.qty}</span>
                          <span style={{ color: '#ff9f1c', marginLeft: '4px', fontWeight: '600' }}>{event.symbol}</span>
                          <span style={{ color: '#6e7681' }}> @ </span>
                          <span style={{ color: '#c9d1d9' }}>${event.price?.toFixed(2)}</span>
                        </span>
                      </>
                    ) : (
                      <span>
                        {event.is_dm && <span style={{ color: '#a855f7', marginRight: '4px' }}>[DM]</span>}
                        {event.message}
                      </span>
                    )}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {selectedBot && selectedPortfolio && (
          <div style={styles.panel}>
            <div style={styles.panelHeader}>
              <span style={{ color: botColors[selectedBot] || '#888' }}>{selectedPortfolio.name}</span>
              <span
                style={{ color: '#6e7681', fontWeight: '400', cursor: 'pointer' }}
                onClick={() => setSelectedBot(null)}
              >
                x
              </span>
            </div>
            <div style={styles.panelContent}>
              <div style={{ borderBottom: '1px solid #30363d', marginBottom: '4px' }}>
                <div style={styles.portfolioStat}>
                  <span style={styles.label}>Equity</span>
                  <span style={styles.value}>${formatNum(selectedPortfolio.total_value)}</span>
                </div>
                <div style={styles.portfolioStat}>
                  <span style={styles.label}>Cash</span>
                  <span style={styles.value}>${formatNum(selectedPortfolio.cash)}</span>
                </div>
                <div style={styles.portfolioStat}>
                  <span style={styles.label}>Invested</span>
                  <span style={styles.value}>${formatNum(selectedPortfolio.total_value - selectedPortfolio.cash)}</span>
                </div>
                <div style={styles.portfolioStat}>
                  <span style={styles.label}>Return</span>
                  <span style={selectedPortfolio.return_pct >= 0 ? styles.valueGreen : styles.valueRed}>
                    {formatPL(selectedPortfolio.return_pct)}%
                  </span>
                </div>
              </div>

              <div style={{ ...styles.positionRow, ...styles.positionHeader }}>
                <span>SYM</span>
                <span style={{ textAlign: 'right' }}>QTY</span>
                <span style={{ textAlign: 'right' }}>AVG</span>
                <span style={{ textAlign: 'right' }}>LAST</span>
                <span style={{ textAlign: 'right' }}>P&L%</span>
              </div>

              {selectedPortfolio.positions.length === 0 ? (
                <div style={{ padding: '8px', color: '#6e7681', textAlign: 'center' }}>
                  All cash - no positions
                </div>
              ) : (
                selectedPortfolio.positions.map((pos, i) => (
                  <div key={i} style={styles.positionRow}>
                    <span style={{ color: '#ff9f1c', fontWeight: '600' }}>{pos.symbol}</span>
                    <span style={{ textAlign: 'right', color: '#8b949e' }}>{pos.shares}</span>
                    <span style={{ textAlign: 'right', color: '#8b949e' }}>{pos.avg_cost?.toFixed(2) || '-'}</span>
                    <span style={{ textAlign: 'right' }}>{pos.current_price?.toFixed(2) || '-'}</span>
                    <span style={{ textAlign: 'right', color: (pos.gain_pct || 0) >= 0 ? '#3fb950' : '#f85149' }}>
                      {pos.gain_pct != null ? `${pos.gain_pct >= 0 ? '+' : ''}${pos.gain_pct.toFixed(1)}%` : '-'}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }
      `}</style>
    </div>
  );
}
