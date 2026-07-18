import React from 'react';
import { ListOrdered, ArrowUpRight, ArrowDownRight } from 'lucide-react';

const mockPositions = [
  { id: '1', symbol: 'BTCUSDT', side: 'LONG', size: 0.5, entry: 64200.50, current: 64800.20, pnl: 300.85, pnlPct: 4.5, strategy: 'Trend Following', time: '2h ago' },
  { id: '2', symbol: 'ETHUSDT', side: 'SHORT', size: 5.0, entry: 3500.10, current: 3450.00, pnl: 250.50, pnlPct: 7.2, strategy: 'Momentum', time: '1h ago' },
];

const Positions = () => {
  return (
    <div className="page-container">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-gradient">Active Positions</h1>
          <p className="text-muted">Currently managing {mockPositions.length} positions</p>
        </div>
      </div>

      <div className="glass-panel">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Size</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Strategy</th>
                <th>Unrealized P&L</th>
                <th>Duration</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {mockPositions.map((pos) => (
                <tr key={pos.id}>
                  <td className="font-bold">{pos.symbol}</td>
                  <td>
                    <span className={`badge ${pos.side === 'LONG' ? 'badge-success' : 'badge-danger'}`}>
                      {pos.side} {pos.side === 'LONG' ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>}
                    </span>
                  </td>
                  <td className="mono">{pos.size}</td>
                  <td className="mono">${pos.entry.toFixed(2)}</td>
                  <td className="mono">${pos.current.toFixed(2)}</td>
                  <td><span className="badge badge-primary">{pos.strategy}</span></td>
                  <td>
                    <div className={`mono ${pos.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      {pos.pnl >= 0 ? '+' : '-'}${Math.abs(pos.pnl).toFixed(2)} ({pos.pnlPct}%)
                    </div>
                  </td>
                  <td className="text-muted">{pos.time}</td>
                  <td>
                    <button className="btn btn-outline" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>Close</button>
                  </td>
                </tr>
              ))}
              {mockPositions.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-tertiary)' }}>
                    <ListOrdered size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                    <p>No active positions at the moment.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Positions;
