/**
 * PortfolioViewer component - shows detailed bot portfolios
 */

import { useState } from 'react';
import type { BotPortfolio } from '../types';

interface PortfolioViewerProps {
  portfolios: BotPortfolio[];
}

export function PortfolioViewer({ portfolios }: PortfolioViewerProps) {
  const [selectedBot, setSelectedBot] = useState<string | null>(null);

  const formatValue = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatReturn = (pct: number) => {
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  const selectedPortfolio = portfolios.find(p => p.id === selectedBot);

  return (
    <div className="panel portfolio-panel">
      <div className="panel-header">
        <span className="panel-title">Portfolios</span>
        {selectedBot && (
          <button
            className="close-btn"
            onClick={() => setSelectedBot(null)}
          >
            Back
          </button>
        )}
      </div>
      <div className="panel-content">
        {!selectedBot ? (
          <div className="portfolio-list">
            {portfolios.map((portfolio) => (
              <div
                key={portfolio.id}
                className="portfolio-item"
                onClick={() => setSelectedBot(portfolio.id)}
              >
                <div className="portfolio-item-header">
                  <span className="portfolio-rank">#{portfolio.rank}</span>
                  <span className="portfolio-name">{portfolio.name}</span>
                  <span className={`portfolio-return ${portfolio.return_pct >= 0 ? 'positive' : 'negative'}`}>
                    {formatReturn(portfolio.return_pct)}
                  </span>
                </div>
                <div className="portfolio-item-stats">
                  <span className="portfolio-value">{formatValue(portfolio.total_value)}</span>
                  <span className="portfolio-positions">
                    {portfolio.positions.length} position{portfolio.positions.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : selectedPortfolio && (
          <div className="portfolio-detail">
            <div className="portfolio-detail-header">
              <div className="portfolio-detail-name">
                <span className="portfolio-rank-large">#{selectedPortfolio.rank}</span>
                <span className="portfolio-name-large">{selectedPortfolio.name}</span>
                <span className={`badge ${selectedPortfolio.type}`}>
                  {selectedPortfolio.type.replace('_', ' ')}
                </span>
              </div>
              <div className={`portfolio-return-large ${selectedPortfolio.return_pct >= 0 ? 'positive' : 'negative'}`}>
                {formatReturn(selectedPortfolio.return_pct)}
              </div>
            </div>

            <div className="portfolio-stats">
              <div className="stat-box">
                <div className="stat-label">Total Value</div>
                <div className="stat-value">{formatValue(selectedPortfolio.total_value)}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Cash</div>
                <div className="stat-value">{formatValue(selectedPortfolio.cash)}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Invested</div>
                <div className="stat-value">{formatValue(selectedPortfolio.total_value - selectedPortfolio.cash)}</div>
              </div>
            </div>

            {selectedPortfolio.last_commentary && (
              <div className="portfolio-commentary">
                "{selectedPortfolio.last_commentary}"
              </div>
            )}

            <div className="positions-header">
              <span>Positions</span>
              <span>{selectedPortfolio.positions.length}</span>
            </div>

            <div className="positions-list">
              {selectedPortfolio.positions.length === 0 ? (
                <div className="no-positions">All cash - no positions</div>
              ) : (
                selectedPortfolio.positions.map((pos) => (
                  <div key={pos.symbol} className="position-item">
                    <div className="position-symbol">{pos.symbol}</div>
                    <div className="position-details">
                      <span className="position-shares">{pos.shares} shares</span>
                      <span className="position-value">{formatValue(pos.market_value)}</span>
                      <span className={`position-gain ${pos.gain_pct >= 0 ? 'positive' : 'negative'}`}>
                        {formatReturn(pos.gain_pct)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
