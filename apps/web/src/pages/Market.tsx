import React from 'react';
import { Activity, BarChart2, TrendingUp, TrendingDown, Eye } from 'lucide-react';

const mockMarketPairs = [
  { symbol: 'BTCUSDT', volume: '1.2B', trend: 'UP', regime: 'Bullish Trending', score: 85, funding: 0.0100 },
  { symbol: 'ETHUSDT', volume: '800M', trend: 'UP', regime: 'Volatile Bullish', score: 72, funding: 0.0150 },
  { symbol: 'SOLUSDT', volume: '450M', trend: 'DOWN', regime: 'Bearish Pullback', score: 35, funding: -0.0050 },
  { symbol: 'XRPUSDT', volume: '200M', trend: 'SIDEWAYS', regime: 'Ranging', score: 50, funding: 0.0100 },
  { symbol: 'DOGEUSDT', volume: '150M', trend: 'UP', regime: 'Breakout', score: 92, funding: 0.0250 },
];

const Market = () => {
  return (
    <div className="page-container">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-gradient">Market Radar</h1>
          <p className="text-muted">Real-time intelligence and regime detection</p>
        </div>
        <button className="btn btn-primary"><Activity size={16} /> Live Feed Active</button>
      </div>

      <div className="grid-3 mb-6">
        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Overall Market Regime</span>
            <BarChart2 size={20} className="text-muted" />
          </div>
          <div className="stat-value text-success">Bullish Trending</div>
          <div className="text-sm text-muted mt-2">60% of tracked pairs are in uptrend</div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Average Funding Rate</span>
            <TrendingUp size={20} className="text-muted" />
          </div>
          <div className="stat-value text-warning">+0.0125%</div>
          <div className="text-sm text-muted mt-2">Slight long bias across market</div>
        </div>
        
        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Active Opportunities</span>
            <Eye size={20} className="text-muted" />
          </div>
          <div className="stat-value text-primary">3 Pairs</div>
          <div className="text-sm text-muted mt-2">Currently analyzing entry triggers</div>
        </div>
      </div>

      <div className="glass-panel card">
        <div className="card-header">
          <span className="card-title">Top Volume Pairs Intelligence</span>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>24h Volume</th>
                <th>Trend</th>
                <th>Market Regime</th>
                <th>AAT Score</th>
                <th>Funding Rate</th>
              </tr>
            </thead>
            <tbody>
              {mockMarketPairs.map(pair => (
                <tr key={pair.symbol}>
                  <td className="font-bold">{pair.symbol}</td>
                  <td className="mono">{pair.volume}</td>
                  <td>
                    <span className={`badge ${pair.trend === 'UP' ? 'badge-success' : pair.trend === 'DOWN' ? 'badge-danger' : 'badge-primary'}`}>
                      {pair.trend} {pair.trend === 'UP' ? <TrendingUp size={14}/> : pair.trend === 'DOWN' ? <TrendingDown size={14}/> : '-'}
                    </span>
                  </td>
                  <td>{pair.regime}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div style={{ width: '60px', height: '6px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${pair.score}%`, height: '100%', backgroundColor: pair.score > 70 ? 'var(--success)' : pair.score < 40 ? 'var(--danger)' : 'var(--warning)' }}></div>
                      </div>
                      <span className="mono text-sm">{pair.score}/100</span>
                    </div>
                  </td>
                  <td className={`mono ${pair.funding > 0.01 ? 'text-warning' : pair.funding < 0 ? 'text-danger' : 'text-success'}`}>
                    {pair.funding > 0 ? '+' : ''}{pair.funding.toFixed(4)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Market;
