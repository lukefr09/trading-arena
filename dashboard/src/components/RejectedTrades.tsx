/**
 * RejectedTrades component - shows failed trades (entertaining constraint violations)
 */

import type { RejectedTrade } from '../types';

interface RejectedTradesProps {
  trades: RejectedTrade[];
}

export function RejectedTrades({ trades }: RejectedTradesProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="panel rejected-panel">
      <div className="panel-header">
        <span className="panel-title">Rejected Trades</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          constraint violations
        </span>
      </div>
      <div className="panel-content">
        <div className="rejected-feed">
          {trades.map((trade) => (
            <div key={trade.id} className="rejected-item">
              <div className="rejected-header">
                <span className="rejected-bot">{trade.bot_name}</span>
                <span className="rejected-time">{formatTime(trade.attempted_at)}</span>
              </div>
              <div className="rejected-trade">
                <span className={`trade-side ${trade.side.toLowerCase()}`}>
                  {trade.side}
                </span>
                <span className="trade-shares">{trade.shares}</span>
                <span className="trade-symbol">{trade.symbol}</span>
              </div>
              <div className="rejected-reason">{trade.reason}</div>
            </div>
          ))}

          {trades.length === 0 && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--spacing-lg)' }}>
              No rejected trades yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
