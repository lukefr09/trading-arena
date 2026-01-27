/**
 * BotCard component - detailed view of a single bot
 */

import type { Bot } from '../types';

interface BotCardProps {
  bot: Bot;
  startingCash: number;
}

export function BotCard({ bot, startingCash }: BotCardProps) {
  const returnPct = ((bot.total_value / startingCash) - 1) * 100;

  const formatValue = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatReturn = (pct: number) => {
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  const positionValue = bot.positions?.reduce((sum, pos) => {
    const price = pos.current_price ?? pos.avg_cost;
    return sum + (pos.shares * price);
  }, 0) ?? 0;

  return (
    <div className="bot-card">
      <div className="bot-card-header">
        <span className="bot-card-name">{bot.name}</span>
        <span className={`bot-card-badge ${bot.type}`}>
          {bot.type.replace('_', ' ')}
        </span>
      </div>

      <div className="bot-card-stats">
        <div className="stat">
          <span className="stat-label">Total Value</span>
          <span className="stat-value large">{formatValue(bot.total_value)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Return</span>
          <span
            className="stat-value large"
            style={{ color: returnPct >= 0 ? 'var(--positive)' : 'var(--negative)' }}
          >
            {formatReturn(returnPct)}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Cash</span>
          <span className="stat-value">{formatValue(bot.cash)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Positions</span>
          <span className="stat-value">{formatValue(positionValue)}</span>
        </div>
      </div>

      {bot.positions && bot.positions.length > 0 && (
        <div style={{ marginTop: 'var(--spacing-md)' }}>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 'var(--spacing-xs)' }}>
            Holdings
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--spacing-xs)' }}>
            {bot.positions.map((pos) => (
              <span
                key={pos.symbol}
                style={{
                  fontSize: '11px',
                  padding: '2px 6px',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--accent-blue)',
                }}
              >
                {pos.symbol}
              </span>
            ))}
          </div>
        </div>
      )}

      {bot.last_commentary && (
        <div style={{ marginTop: 'var(--spacing-md)', paddingTop: 'var(--spacing-sm)', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
            "{bot.last_commentary}"
          </div>
        </div>
      )}
    </div>
  );
}
