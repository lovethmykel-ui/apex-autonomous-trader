import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Positions from './pages/Positions';
import AILab from './pages/AILab';
import Market from './pages/Market';
import Risk from './pages/Risk';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/positions" element={<Positions />} />
            <Route path="/ai-lab" element={<AILab />} />
            <Route path="/market" element={<Market />} />
            <Route path="/risk" element={<Risk />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
