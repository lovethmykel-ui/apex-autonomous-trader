import React from 'react';
import { BrainCircuit, GitBranch, Zap, Trophy } from 'lucide-react';

const mockGenerations = [
  { id: 4, status: 'ACTIVE', winRate: 68.5, trades: 66, maxDd: 4.2, pnl: 500, time: '2 days' },
  { id: 3, status: 'DEAD', winRate: 45.2, trades: 120, maxDd: 25.1, pnl: -1200, time: '14 days' },
  { id: 2, status: 'DEAD', winRate: 52.1, trades: 85, maxDd: 26.5, pnl: -800, time: '7 days' },
  { id: 1, status: 'DEAD', winRate: 38.4, trades: 42, maxDd: 30.2, pnl: -1500, time: '3 days' },
];

const mockMemories = [
  { symbol: 'SOLUSDT', score: 95, pnl: '+4.5%', lesson: 'Strong momentum continuation after EMA cross' },
  { symbol: 'DOGEUSDT', score: 20, pnl: '-2.1%', lesson: 'Fakeout on low volume' },
  { symbol: 'ETHUSDT', score: 85, pnl: '+3.2%', lesson: 'Mean reversion successful at RSI 25' },
];

const AILab = () => {
  return (
    <div className="page-container">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-gradient">Evolution & Memory Lab</h1>
          <p className="text-muted">Agent genome tracking and trade memories</p>
        </div>
      </div>

      <div className="grid-3 mb-6">
        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Generations Alive</span>
            <GitBranch size={20} className="text-muted" />
          </div>
          <div className="stat-value text-primary">04</div>
          <div className="text-sm text-muted mt-2">Current generation active for 2 days</div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Memories Formed</span>
            <BrainCircuit size={20} className="text-muted" />
          </div>
          <div className="stat-value text-success">313</div>
          <div className="text-sm text-muted mt-2">Trade lessons learned across all generations</div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Peak Win Rate</span>
            <Trophy size={20} className="text-muted" />
          </div>
          <div className="stat-value text-warning">68.5%</div>
          <div className="text-sm text-muted mt-2">Achieved by current generation (G-04)</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Evolutionary Lineage</span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Gen</th>
                  <th>Status</th>
                  <th>Win Rate</th>
                  <th>Trades</th>
                  <th>P&L</th>
                </tr>
              </thead>
              <tbody>
                {mockGenerations.map(g => (
                  <tr key={g.id}>
                    <td className="font-bold">G-{g.id.toString().padStart(2, '0')}</td>
                    <td>
                      <span className={`badge ${g.status === 'ACTIVE' ? 'badge-success' : 'badge-danger'}`}>
                        {g.status}
                      </span>
                    </td>
                    <td className="mono">{g.winRate}%</td>
                    <td className="mono">{g.trades}</td>
                    <td className={`mono ${g.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      {g.pnl >= 0 ? '+' : ''}${g.pnl}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Recent Neural Memories</span>
          </div>
          <div className="flex-col gap-4">
            {mockMemories.map((m, i) => (
              <div key={i} className="flex-col gap-2 p-4" style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                <div className="flex justify-between items-center">
                  <div className="font-bold flex items-center gap-2">
                    <Zap size={16} className={m.score > 80 ? 'text-success' : 'text-warning'} />
                    {m.symbol}
                  </div>
                  <div className={`badge ${m.pnl.startsWith('+') ? 'badge-success' : 'badge-danger'}`}>{m.pnl}</div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted">Fitness Score: <span className="text-primary font-bold">{m.score}/100</span></span>
                </div>
                <p className="text-sm text-tertiary italic mt-1">"{m.lesson}"</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AILab;
