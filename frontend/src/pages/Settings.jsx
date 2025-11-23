import React, { useState, useEffect } from 'react';
import { getConfig, testGrocyConnection, testLLMConnection } from '../api';

function Settings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [kioskMode, setKioskMode] = useState(false);
  
  // Test results
  const [grocyTestResult, setGrocyTestResult] = useState(null);
  const [llmTestResult, setLlmTestResult] = useState(null);
  const [testingGrocy, setTestingGrocy] = useState(false);
  const [testingLLM, setTestingLLM] = useState(false);

  useEffect(() => {
    loadConfig();
    
    // Load kiosk mode preference
    const savedKioskMode = localStorage.getItem('kioskMode') === 'true';
    setKioskMode(savedKioskMode);
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await getConfig();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load config:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKioskModeToggle = () => {
    const newValue = !kioskMode;
    setKioskMode(newValue);
    localStorage.setItem('kioskMode', newValue.toString());
    
    if (newValue) {
      document.body.classList.add('kiosk-mode');
    } else {
      document.body.classList.remove('kiosk-mode');
    }
  };

  const handleTestGrocy = async () => {
    setTestingGrocy(true);
    setGrocyTestResult(null);
    
    try {
      const result = await testGrocyConnection();
      setGrocyTestResult({ success: true, ...result });
    } catch (err) {
      setGrocyTestResult({
        success: false,
        message: err.response?.data?.detail || 'Connection failed'
      });
    } finally {
      setTestingGrocy(false);
    }
  };

  const handleTestLLM = async () => {
    setTestingLLM(true);
    setLlmTestResult(null);
    
    try {
      const result = await testLLMConnection();
      setLlmTestResult({ success: true, ...result });
    } catch (err) {
      setLlmTestResult({
        success: false,
        message: err.response?.data?.detail || 'Connection failed'
      });
    } finally {
      setTestingLLM(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <div className="text-center py-12 text-gray-400">
            Loading settings...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h1 className="text-3xl font-bold flex items-center">
          <span className="text-3xl mr-2">⚙️</span>
          Settings
        </h1>
        <p className="text-gray-400 mt-2">
          Configure Elzar and test your connections
        </p>
      </div>

      {/* Kiosk Mode */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4">Display Settings</h2>
        
        <div className="flex items-center justify-between py-3 border-b border-gray-700">
          <div className="flex-1">
            <h3 className="font-semibold">Kiosk Mode</h3>
            <p className="text-sm text-gray-400">
              Optimized for Raspberry Pi 7" touchscreen (800x480)
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={kioskMode}
              onChange={handleKioskModeToggle}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-elzar-red rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-elzar-red"></div>
          </label>
        </div>
        
        {kioskMode && (
          <div className="mt-4 bg-yellow-900 border border-yellow-700 rounded-lg p-4 text-yellow-200">
            <p className="text-sm">
              🌶️ Kiosk mode enabled! The interface is now optimized for touchscreens with larger buttons and simplified navigation.
            </p>
          </div>
        )}
      </div>

      {/* Current Configuration */}
      {config && (
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-2xl font-bold mb-4">Current Configuration</h2>
          
          <div className="space-y-4">
            <div className="bg-gray-700 rounded-lg p-4">
              <h3 className="font-semibold mb-2">Grocy Instance</h3>
              <p className="text-sm text-gray-300 font-mono break-all">
                {config.grocy_url}
              </p>
            </div>

            <div className="bg-gray-700 rounded-lg p-4">
              <h3 className="font-semibold mb-2">LLM Configuration</h3>
              <p className="text-sm text-gray-300">
                <span className="text-gray-400">API URL:</span> <span className="font-mono">{config.llm_api_url}</span>
              </p>
              <p className="text-sm text-gray-300 mt-1">
                <span className="text-gray-400">Model:</span> <span className="font-mono">{config.llm_model}</span>
              </p>
            </div>

            <div className="bg-gray-700 rounded-lg p-4">
              <h3 className="font-semibold mb-2">Recipe History</h3>
              <p className="text-sm text-gray-300">
                Maximum recipes stored: <span className="font-mono">{config.max_recipe_history}</span>
              </p>
            </div>

            <div className="bg-gray-700 rounded-lg p-4">
              <h3 className="font-semibold mb-2">Notifications</h3>
              <p className="text-sm text-gray-300">
                Status: {config.notification_configured ? (
                  <span className="text-green-400">✓ Configured</span>
                ) : (
                  <span className="text-yellow-400">⚠ Not configured</span>
                )}
              </p>
            </div>
          </div>

          <div className="mt-4 bg-blue-900 border border-blue-700 rounded-lg p-4 text-blue-200">
            <p className="text-sm">
              💡 To change these settings, edit the <code className="bg-blue-800 px-2 py-1 rounded">.env</code> file in the backend directory and restart the server.
            </p>
          </div>
        </div>
      )}

      {/* Connection Tests */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4">Connection Tests</h2>
        
        <div className="space-y-4">
          {/* Grocy Test */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold">Grocy API</h3>
              <button
                onClick={handleTestGrocy}
                disabled={testingGrocy}
                className="bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                {testingGrocy ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
            
            {grocyTestResult && (
              <div className={`mt-3 p-3 rounded ${
                grocyTestResult.success
                  ? 'bg-green-900 border border-green-700 text-green-200'
                  : 'bg-red-900 border border-red-700 text-red-200'
              }`}>
                <p className="font-semibold">
                  {grocyTestResult.success ? '✓ Success' : '✗ Failed'}
                </p>
                <p className="text-sm mt-1">{grocyTestResult.message}</p>
                {grocyTestResult.items_count !== undefined && (
                  <p className="text-sm mt-1">
                    Found {grocyTestResult.items_count} items in inventory
                  </p>
                )}
              </div>
            )}
          </div>

          {/* LLM Test */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold">LLM API</h3>
              <button
                onClick={handleTestLLM}
                disabled={testingLLM}
                className="bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                {testingLLM ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
            
            {llmTestResult && (
              <div className={`mt-3 p-3 rounded ${
                llmTestResult.success
                  ? 'bg-green-900 border border-green-700 text-green-200'
                  : 'bg-red-900 border border-red-700 text-red-200'
              }`}>
                <p className="font-semibold">
                  {llmTestResult.success ? '✓ Success' : '✗ Failed'}
                </p>
                <p className="text-sm mt-1">{llmTestResult.message}</p>
                {llmTestResult.response_length && (
                  <p className="text-sm mt-1">
                    Generated test recipe ({llmTestResult.response_length} characters)
                  </p>
                )}
              </div>
            )}
            
            <div className="mt-3 bg-yellow-900 border border-yellow-700 rounded p-3 text-yellow-200">
              <p className="text-xs">
                ⚠️ Note: This test sends a real API request and may cost a small amount depending on your LLM provider.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4">About Elzar</h2>
        
        <div className="text-gray-300 space-y-3">
          <p>
            <span className="text-3xl">🌶️</span> <strong>Elzar</strong> - The Grocy Recipe Generator
          </p>
          <p>
            Version 1.0.0
          </p>
          <p className="text-sm">
            BAM! Generate amazing recipes from your Grocy inventory using AI. Elzar helps you reduce food waste, accommodate dietary restrictions, and discover new meals based on what you already have.
          </p>
          <div className="pt-4 border-t border-gray-700">
            <p className="text-sm text-gray-400">
              Built with FastAPI, React, and powered by your choice of LLM.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;

