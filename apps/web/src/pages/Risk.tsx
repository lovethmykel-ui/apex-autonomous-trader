import React from 'react';
import { ShieldAlert, AlertTriangle, Crosshair, DollarSign } from 'lucide-react';

const Risk = () => {
  return (
    <div className="page-container">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-gradient">Risk & Treasury Controls</h1>
          <p className="text-muted">Dynamic risk sizing and capital preservation</p>
        </div>
      </div>

      <div className="grid-2 mb-6">
        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title text-danger flex items-center gap-2">
              <ShieldAlert size={18} /> Global Risk Settings
            </span>
          </div>
          <div className="flex-col gap-6 mt-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-secondary">Max Generation Drawdown Limit</span>
                <span className="text-sm font-mono text-danger">25.0%</span>
              </div>
              <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px' }}>
                <div style={{ width: '16.8%', height: '100%', backgroundColor: 'var(--danger)', borderRadius: '4px' }}></div>
              </div>
              <div className="text-xs text-muted mt-2">Current Drawdown: 4.2% / 25.0% (Agent terminates at 25%)</div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-secondary">Max Risk Per Trade</span>
                <span className="text-sm font-mono text-warning">2.0%</span>
              </div>
              <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px' }}>
                <div style={{ width: '40%', height: '100%', backgroundColor: 'var(--warning)', borderRadius: '4px' }}></div>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-secondary">Max Open Positions</span>
                <span className="text-sm font-mono text-primary">5</span>
              </div>
              <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px' }}>
                <div style={{ width: '40%', height: '100%', backgroundColor: 'var(--accent-primary)', borderRadius: '4px' }}></div>
              </div>
              <div className="text-xs text-muted mt-2">Currently utilizing 2 of 5 slots</div>
            </div>
          </div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title text-success flex items-center gap-2">
              <Crosshair size={18} /> Dynamic Position Sizing (Kelly Criterion)
            </span>
          </div>
          
          <div className="mt-4 flex-col gap-4">
            <div className="p-4" style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px', borderLeft: '4px solid var(--success)' }}>
              <h4 className="mb-2">How Kelly is applied:</h4>
              <p className="text-sm text-muted">
                The agent dynamically calculates optimal trade size using a modified half-Kelly criterion based on historical win rate (68.5%) and average win/loss ratio (1.8).
              </p>
              <div className="flex justify-between mt-4">
                <div className="text-sm">
                  <div className="text-tertiary mb-1">Win Probability</div>
                  <div className="font-mono text-success">68.5%</div>
                </div>
                <div className="text-sm text-right">
                  <div className="text-tertiary mb-1">Optimal Fraction</div>
                  <div className="font-mono text-primary">12.4%</div>
                </div>
              </div>
            </div>

            <div className="p-4" style={{ backgroundColor: 'var(--warning-bg)', borderRadius: '8px', borderLeft: '4px solid var(--warning)' }}>
              <h4 className="mb-2 text-warning flex items-center gap-2"><AlertTriangle size={16}/> Override Engaged</h4>
              <p className="text-sm text-warning">
                Kelly fraction (12.4%) exceeds global Max Risk Per Trade (2.0%). 
                Position sizes are capped at 2.0% to preserve capital.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Risk;
