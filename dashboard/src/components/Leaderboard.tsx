/**
 * Leaderboard component - shows ranked bots
 */

import type { LeaderboardEntry } from '../types';
import { formatDayTime } from '../utils';

interface LeaderboardProps {
  entries: LeaderboardEntry[];
}

export function Leaderboard({ entries }: LeaderboardProps) {
  const formatValue = (value: number | undefined) => {
    if (value == null) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatReturn = (pct: number | undefined) => {
    if (pct == null) return '—';
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  const getRankClass = (rank: number) => {
    if (rank === 1) return 'rank-1';
    if (rank === 2) return 'rank-2';
    if (rank === 3) return 'rank-3';
    return '';
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Leaderboard</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          {formatDayTime()}
        </span>
      </div>
      <div className="panel-content">
        <div className="leaderboard">
          {entries.filter(entry => entry?.id != null).map((entry) => (
            <div
              key={entry.id}
              className={`leaderboard-item ${getRankClass(entry.rank)}`}
            >
              <span className="rank">#{entry.rank}</span>
              <div>
                <div className="bot-name">{entry.name}</div>
                <div className="bot-type">{entry.type?.replace('_', ' ') ?? ''}</div>
              </div>
              <div className="bot-value">{formatValue(entry.total_value)}</div>
              <div className={`bot-return ${(entry.return_pct ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatReturn(entry.return_pct)}
              </div>
            </div>
          ))}

          {entries.length === 0 && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--spacing-lg)' }}>
              No bots registered
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
