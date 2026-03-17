import React, { createContext, useContext, useState, useEffect } from 'react';
import { getServiceStatus } from '../api';

const ServiceStatusContext = createContext({
  grocyConfigured: false,
  llmConfigured: false,
  visionConfigured: false,
  notificationsConfigured: false,
  loading: true,
  error: null,
  refresh: () => {},
});

export function ServiceStatusProvider({ children }) {
  const [status, setStatus] = useState({
    grocyConfigured: false,
    llmConfigured: false,
    visionConfigured: false,
    notificationsConfigured: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getServiceStatus();
      setStatus({
        grocyConfigured: data.grocy_configured,
        llmConfigured: data.llm_configured,
        visionConfigured: data.vision_configured,
        notificationsConfigured: data.notifications_configured,
      });
    } catch (err) {
      console.error('Failed to fetch service status:', err);
      setError(err.message || 'Failed to fetch service status');
      // Default to false if we can't fetch status
      setStatus({
        grocyConfigured: false,
        llmConfigured: false,
        visionConfigured: false,
        notificationsConfigured: false,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const value = {
    ...status,
    loading,
    error,
    refresh: fetchStatus,
  };

  return (
    <ServiceStatusContext.Provider value={value}>
      {children}
    </ServiceStatusContext.Provider>
  );
}

export function useServiceStatus() {
  const context = useContext(ServiceStatusContext);
  if (!context) {
    throw new Error('useServiceStatus must be used within a ServiceStatusProvider');
  }
  return context;
}

export default ServiceStatusContext;
