import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Chat from './pages/Chat';
import Generator from './pages/Generator';
import MealPlanner from './pages/MealPlanner';
import History from './pages/History';
import Profiles from './pages/Profiles';
import Settings from './pages/Settings';
import InventoryManager from './pages/InventoryManager';
import Ideas from './pages/Ideas';
import Nutrition from './pages/Nutrition';
import { ServiceStatusProvider, useServiceStatus } from './contexts/ServiceStatusContext';
import './index.css';

function Navigation() {
  const location = useLocation();
  const [kioskMode, setKioskMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { grocyConfigured } = useServiceStatus();

  useEffect(() => {
    // Check for kiosk mode from localStorage
    const savedKioskMode = localStorage.getItem('kioskMode') === 'true';
    setKioskMode(savedKioskMode);

    if (savedKioskMode) {
      document.body.classList.add('kiosk-mode');
    }
  }, []);

  // Close sidebar when route changes
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Close sidebar when clicking outside
  const handleOverlayClick = () => {
    setSidebarOpen(false);
  };

  // Base nav items - Inventory only shown when Grocy is configured
  const allNavItems = [
    { path: '/', label: 'Chat', icon: '💬' },
    { path: '/generator', label: 'Quick Recipe', icon: '⚡' },
    { path: '/inventory', label: 'Inventory', icon: '📦', requiresGrocy: true },
    { path: '/nutrition', label: 'Nutrition', icon: '🥗' },
    { path: '/history', label: 'History', icon: '📜' },
    { path: '/profiles', label: 'Profiles', icon: '👤' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  // Filter nav items based on Grocy configuration
  const navItems = allNavItems.filter(item => !item.requiresGrocy || grocyConfigured);

  const kioskNavItems = [
    { path: '/', label: 'Chat', icon: '💬' },
    { path: '/generator', label: 'BAM!', icon: '⚡' },
    { path: '/history', label: 'History', icon: '📜' },
  ];

  const currentNavItems = kioskMode && location.pathname !== '/settings' ? kioskNavItems : navItems;

  const isActive = (path) => location.pathname === path;

  return (
    <>
      {/* Top Navigation Bar */}
      <nav className="bg-gray-800 border-b border-gray-700 px-4 py-3 sticky top-0 z-40">
        <div className="container mx-auto flex justify-between items-center">
          {/* Hamburger Menu Button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
            aria-label="Open menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Logo */}
          <div className="flex items-center space-x-2">
            <img src="/elzar.png" alt="Elzar" className="h-8 w-8 object-contain" />
            <h1 className="text-2xl font-bold text-white">Elzar</h1>
          </div>

          {/* Spacer for centering */}
          <div className="w-10"></div>
        </div>
      </nav>

      {/* Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
          onClick={handleOverlayClick}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full w-72 bg-gray-800 border-r border-gray-700 z-50 transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center space-x-2">
            <img src="/elzar.png" alt="Elzar" className="h-8 w-8 object-contain" />
            <h2 className="text-xl font-bold text-white">Elzar</h2>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
            aria-label="Close menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Sidebar Navigation */}
        <nav className="p-4">
          <ul className="space-y-2">
            {currentNavItems.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? 'bg-elzar-red text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`}
                >
                  <span className="text-xl">{item.icon}</span>
                  <span className="font-medium">{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sidebar Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700">
          <p className="text-xs text-gray-500 text-center">
            BAM! Let's kick it up a notch!
          </p>
        </div>
      </aside>
    </>
  );
}

function AppContent() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Navigation />
      <main className="container mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/generator" element={<Generator />} />
          <Route path="/meal-planner" element={<MealPlanner />} />
          <Route path="/inventory" element={<InventoryManager />} />
          <Route path="/ideas" element={<Ideas />} />
          <Route path="/nutrition" element={<Nutrition />} />
          <Route path="/history" element={<History />} />
          <Route path="/profiles" element={<Profiles />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <ServiceStatusProvider>
        <AppContent />
      </ServiceStatusProvider>
    </Router>
  );
}

export default App;
