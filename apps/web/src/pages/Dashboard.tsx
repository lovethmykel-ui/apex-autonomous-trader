import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, DollarSign, Target, Zap, Shield } from 'lucide-react';
import axios from 'axios';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const mockChartData = [
  { time: '10:00', balance: 10000 },
  { time: '11:00', balance: 10150 },
  { time: '12:00', balance: 10120 },
  { time: '13:00', balance: 10300 },
  { time: '14:00', balance: 10250 },
  { time: '15:00', balance: 10500 },
];

const Dashboard = () => {
  return (
    <div className="page-container">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-gradient">Treasury Dashboard</h1>
          <p className="text-muted">Generation G-04 Active</p>
        </div>
        <div className="flex gap-4">
          <button className="btn btn-outline"><Zap size={16} /> Run Scan</button>
          <button className="btn btn-primary"><Activity size={16} /> System Online</button>
        </div>
      </div>

      <div className="grid-4 mb-6">
        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Treasury Balance</span>
            <DollarSign size={20} className="text-muted" />
          </div>
          <div className="stat-value text-success">$10,500.00</div>
          <div className="flex items-center gap-2 mt-2">
            <TrendingUp size={16} className="text-success" />
            <span className="text-success text-sm">+5.00%</span>
            <span className="text-muted text-sm">since start</span>
          </div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Win Rate</span>
            <Target size={20} className="text-muted" />
          </div>
          <div className="stat-value text-primary">68.5%</div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-muted text-sm">45 Wins / 21 Losses</span>
          </div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Max Drawdown</span>
            <TrendingDown size={20} className="text-muted" />
          </div>
          <div className="stat-value text-warning">4.2%</div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-muted text-sm">Limit: 25.0%</span>
          </div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Status</span>
            <Shield size={20} className="text-muted" />
          </div>
          <div className="stat-value text-success">ACTIVE</div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-muted text-sm">Bot is executing trades</span>
          </div>
        </div>
      </div>

      <div className="grid-3">
        <div className="glass-panel card" style={{ gridColumn: 'span 2' }}>
          <div className="card-header">
            <span className="card-title">Equity Curve</span>
          </div>
          <div style={{ height: '300px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockChartData}>
                <defs>
                  <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="var(--text-tertiary)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-tertiary)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${val}`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Area type="monotone" dataKey="balance" stroke="var(--accent-primary)" fillOpacity={1} fill="url(#colorBalance)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel card">
          <div className="card-header">
            <span className="card-title">Recent Trades</span>
          </div>
          <div className="flex-col gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="flex justify-between items-center p-3" style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                <div>
                  <div className="font-bold">BTCUSDT</div>
                  <div className="text-xs text-success">LONG • Trend Following</div>
                </div>
                <div className="text-right">
                  <div className="text-success font-mono">+$45.20</div>
                  <div className="text-xs text-muted">2 mins ago</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
