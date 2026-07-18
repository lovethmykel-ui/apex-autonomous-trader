import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ListOrdered, BrainCircuit, ShieldAlert, Activity, Settings, TerminalSquare } from 'lucide-react';
import './Sidebar.css';

const Sidebar = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-container">
          <TerminalSquare className="logo-icon" size={28} />
          <div className="logo-text">
            <span className="logo-title text-gradient">APEX</span>
            <span className="logo-subtitle">AUTONOMOUS TRADER</span>
          </div>
        </div>
      </div>
      
      <div className="nav-group">
        <div className="nav-label">Core Systems</div>
        <nav className="nav-menu">
          <NavLink to="/" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={20} />
            <span>Treasury & Dashboard</span>
          </NavLink>
          <NavLink to="/positions" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <ListOrdered size={20} />
            <span>Active Positions</span>
          </NavLink>
        </nav>
      </div>

      <div className="nav-group">
        <div className="nav-label">Intelligence</div>
        <nav className="nav-menu">
          <NavLink to="/ai-lab" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <BrainCircuit size={20} />
            <span>Evolution & Memory</span>
          </NavLink>
          <NavLink to="/market" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <Activity size={20} />
            <span>Market Radar</span>
          </NavLink>
          <NavLink to="/risk" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <ShieldAlert size={20} />
            <span>Risk Calculator</span>
          </NavLink>
        </nav>
      </div>
      
      <div className="sidebar-footer">
        <div className="system-status pulse-active">
          <span className="status-text">System Live</span>
          <span className="status-mode badge badge-primary">PAPER MODE</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
