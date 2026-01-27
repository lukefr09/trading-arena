/**
 * LiveFeed component - shows real-time trades and commentary
 */

import type { Trade } from '../types';

interface LiveFeedProps {
  trades: Trade[];
}

export function LiveFeed({ trades }: LiveFeedProps) {
  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price);
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Live Feed</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          {trades.length} trades
        </span>
      </div>
      <div className="panel-content">
        <div className="live-feed">
          {trades.map((trade, index) => (
            <div
              key={trade.id || index}
              className={`feed-item trade-${trade.side.toLowerCase()}`}
            >
              <div className="feed-header">
                <span className="feed-bot">{trade.bot_name || trade.bot_id}</span>
                <span className="feed-time">{formatTime(trade.executed_at)}</span>
              </div>
              <div className="feed-trade">
                <span className={`trade-side ${trade.side.toLowerCase()}`}>
                  {trade.side}
                </span>
                <span className="trade-shares">{trade.shares}</span>
                <span className="trade-symbol">{trade.symbol}</span>
                <span className="trade-price">@ {formatPrice(trade.price)}</span>
              </div>
              {trade.commentary && (
                <div className="feed-commentary">"{trade.commentary}"</div>
              )}
            </div>
          ))}

          {trades.length === 0 && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--spacing-lg)' }}>
              No trades yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
