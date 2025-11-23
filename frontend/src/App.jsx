import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Generator from './pages/Generator';
import History from './pages/History';
import Profiles from './pages/Profiles';
import Settings from './pages/Settings';
import './index.css';

function Navigation() {
  const location = useLocation();
  const [kioskMode, setKioskMode] = useState(false);

  useEffect(() => {
    // Check for kiosk mode from localStorage
    const savedKioskMode = localStorage.getItem('kioskMode') === 'true';
    setKioskMode(savedKioskMode);
    
    if (savedKioskMode) {
      document.body.classList.add('kiosk-mode');
    }
  }, []);

  const navClasses = (path) => {
    const isActive = location.pathname === path;
    return `px-4 py-2 rounded-lg transition-colors ${
      isActive
        ? 'bg-elzar-red text-white'
        : 'text-gray-300 hover:bg-gray-700'
    }`;
  };

  if (kioskMode && location.pathname !== '/settings') {
    // Minimal navigation in kiosk mode
    return (
      <nav className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <span className="text-3xl">🌶️</span>
            <h1 className="text-2xl font-bold text-white">Elzar</h1>
          </div>
          <div className="flex space-x-2">
            <Link to="/" className={navClasses('/')}>
              BAM!
            </Link>
            <Link to="/history" className={navClasses('/history')}>
              History
            </Link>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="bg-gray-800 border-b border-gray-700 px-4 py-3">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <span className="text-3xl">🌶️</span>
          <h1 className="text-2xl font-bold text-white">Elzar</h1>
        </div>
        <div className="flex space-x-2">
          <Link to="/" className={navClasses('/')}>
            Generator
          </Link>
          <Link to="/history" className={navClasses('/history')}>
            History
          </Link>
          <Link to="/profiles" className={navClasses('/profiles')}>
            Profiles
          </Link>
          <Link to="/settings" className={navClasses('/settings')}>
            Settings
          </Link>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-white">
        <Navigation />
        <main className="container mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Generator />} />
            <Route path="/history" element={<History />} />
            <Route path="/profiles" element={<Profiles />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

