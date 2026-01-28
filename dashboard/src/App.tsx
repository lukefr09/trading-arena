/**
 * Trading Arena Dashboard - Main App Component
 */

import { useCallback } from 'react';
import { Leaderboard } from './components/Leaderboard';
import { LiveFeed } from './components/LiveFeed';
import { ChatFeed } from './components/ChatFeed';
import { RejectedTrades } from './components/RejectedTrades';
import { PortfolioViewer } from './components/PortfolioViewer';
import { MarketStatus } from './components/MarketStatus';
import { useGameState } from './hooks/useGameState';
import { useWebSocket } from './hooks/useWebSocket';
import type { WebSocketStatus } from './types';
import './styles/bloomberg.css';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8787/ws';

function ConnectionIndicator({ status }: { status: WebSocketStatus }) {
  const statusText = {
    connecting: 'Connecting...',
    connected: 'Live',
    disconnected: 'Offline',
  };

  return (
    <div className={`connection-status ${status}`}>
      <span style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        backgroundColor: status === 'connected'
          ? 'var(--positive)'
          : status === 'connecting'
            ? 'var(--warning)'
            : 'var(--negative)',
        display: 'inline-block',
      }} />
      {statusText[status]}
    </div>
  );
}

export default function App() {
  const {
    state,
    leaderboard,
    recentTrades,
    messages,
    rejectedTrades,
    portfolios,
    loading,
    error,
    handleWebSocketMessage,
  } = useGameState();

  const onMessage = useCallback(handleWebSocketMessage, [handleWebSocketMessage]);

  const { status: wsStatus } = useWebSocket(WS_URL, {
    onMessage,
  });

  const formatValue = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="app" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--negative)' }}>Error: {error}</div>
      </div>
    );
  }

  const totalPoolValue = leaderboard.reduce((sum, bot) => sum + bot.total_value, 0);

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">
          <h1>Trading Arena</h1>
          <MarketStatus />
        </div>
        <div className="header-status">
          <div className="status-item">
            <span className="status-label">Status</span>
            <div
              className={`status-indicator ${state?.status || 'paused'}`}
              title={state?.status || 'paused'}
            />
            <span className="status-value" style={{ textTransform: 'uppercase' }}>
              {state?.status || 'paused'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Round</span>
            <span className="status-value">{state?.current_round || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Pool</span>
            <span className="status-value">{formatValue(totalPoolValue)}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Bots</span>
            <span className="status-value">{leaderboard.length}</span>
          </div>
          <ConnectionIndicator status={wsStatus} />
        </div>
      </header>

      <main className="main-content">
        <div className="left-column">
          <Leaderboard
            entries={leaderboard}
            currentRound={state?.current_round || 0}
          />
          <PortfolioViewer portfolios={portfolios} />
        </div>
        <div className="center-column">
          <LiveFeed trades={recentTrades} />
          <RejectedTrades trades={rejectedTrades} />
        </div>
        <div className="right-column">
          <ChatFeed messages={messages} />
        </div>
      </main>
    </div>
  );
}
