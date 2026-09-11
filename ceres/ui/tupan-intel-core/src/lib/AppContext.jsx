import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { THEMES, applyTheme } from '@/lib/themes';

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

export function AppContextProvider({ children }) {
  const navigate = useNavigate();
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [filters, setFilters] = useState({
    city: 'São Paulo',
    neighborhood: null,
    propertyType: null,
    priceMin: null,
    priceMax: null,
    heatMin: null,
    period: '90d',
  });
  const [timePeriod, setTimePeriod] = useState('90d');
  const [headerCollapsed, setHeaderCollapsed] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [agentContextItems, setAgentContextItems] = useState([]);
  const [savedInsights, setSavedInsights] = useState([]);
  const [agentPrefill, setAgentPrefill] = useState('');
  const [agentContextArrival, setAgentContextArrival] = useState(null);
  const [recentTrace, setRecentTrace] = useState(null);
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'midnight';
    const savedTheme = localStorage.getItem('ceres-theme');
    // Migrate the original default into Midnight, preserving any deliberate
    // selection of another theme.
    return !savedTheme || savedTheme === 'aqua' ? 'midnight' : savedTheme;
  });

  useEffect(() => {
    applyTheme(theme);
    try { localStorage.setItem('ceres-theme', theme); } catch { /* ignore */ }
  }, [theme]);

  const addAgentContext = useCallback((item) => {
    setAgentContextItems((prev) => (prev.find((p) => p.id === item.id) ? prev : [...prev, item]));
  }, []);

  const removeAgentContext = useCallback(
    (id) => setAgentContextItems((prev) => prev.filter((p) => p.id !== id)),
    []
  );

  const clearAgentContext = useCallback(() => setAgentContextItems([]), []);

  const addSavedInsight = useCallback((item) => {
    setSavedInsights((prev) => (prev.find((saved) => saved.id === item.id) ? prev : [...prev, item]));
  }, []);

  const removeSavedInsight = useCallback(
    (id) => setSavedInsights((prev) => prev.filter((item) => item.id !== id)),
    []
  );

  const clearSavedInsights = useCallback(() => setSavedInsights([]), []);

  const sendToAgent = useCallback(
    (contextItems = [], prefill = '', source = 'direct') => {
      setAgentContextItems((prev) => {
        const merged = [...prev];
        contextItems.forEach((item) => {
          if (!merged.find((p) => p.id === item.id)) merged.push(item);
        });
        return merged;
      });
      setAgentPrefill(prefill);
      setAgentContextArrival({ id: Date.now(), source, count: contextItems.length });
      navigate('/agent');
    },
    [navigate]
  );

  const value = {
    selectedRegion,
    setSelectedRegion,
    selectedProperty,
    setSelectedProperty,
    filters,
    setFilters,
    timePeriod,
    setTimePeriod,
    headerCollapsed,
    setHeaderCollapsed,
    navOpen,
    setNavOpen,
    agentContextItems,
    savedInsights,
    addSavedInsight,
    removeSavedInsight,
    clearSavedInsights,
    addAgentContext,
    removeAgentContext,
    clearAgentContext,
    agentPrefill,
    setAgentPrefill,
    agentContextArrival,
    recentTrace,
    setRecentTrace,
    sendToAgent,
    theme,
    setTheme,
    THEMES,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

