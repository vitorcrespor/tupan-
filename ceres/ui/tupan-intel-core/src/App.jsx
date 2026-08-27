import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import UserNotRegisteredError from '@/components/UserNotRegisteredError';
import ScrollToTop from './components/ScrollToTop';
import ProtectedRoute from '@/components/ProtectedRoute';
import { AppContextProvider } from '@/lib/AppContext';
import AppShell from '@/components/tupan/AppShell';
import Welcome from '@/pages/Welcome';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';
import Menu from '@/pages/Menu';
import Overview from '@/pages/Overview';
import MarketMap from '@/pages/MarketMap';
import Portfolio from '@/pages/Portfolio';
import Properties from '@/pages/Properties';
import PropertyDetail from '@/pages/PropertyDetail';
import Compare from '@/pages/Compare';
import VoiceAgent from '@/pages/VoiceAgent';
import AgentLog from '@/pages/AgentLog';
import DataManagement from '@/pages/DataManagement';
import Settings from '@/pages/Settings';
import ReportBuilder from '@/pages/ReportBuilder';
import TeamManagement from '@/pages/TeamManagement';
import SavedSearches from '@/pages/SavedSearches';
import MarketTrends from '@/pages/MarketTrends';

const AuthenticatedApp = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError, navigateToLogin } = useAuth();

  // Show loading spinner while checking app public settings or auth
  if (isLoadingPublicSettings || isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
      </div>
    );
  }

  // Handle authentication errors
  if (authError) {
    if (authError.type === 'user_not_registered') {
      return <UserNotRegisteredError />;
    } else if (authError.type === 'auth_required') {
      // Redirect to login automatically
      navigateToLogin();
      return null;
    }
  }

  // Render the main app
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<ProtectedRoute unauthenticatedElement={<Navigate to="/login" replace />} />}>
        <Route path="/menu" element={<Menu />} />
        <Route path="/voice" element={<VoiceAgent />} />
        <Route path="/agent" element={<VoiceAgent />} />
        <Route element={<AppShell />}>
          <Route path="/overview" element={<Overview />} />
          <Route path="/market-map" element={<MarketMap />} />
          <Route path="/market-intelligence" element={<Navigate to="/overview#market-metrics" replace />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/properties" element={<Properties />} />
          <Route path="/properties/:id" element={<PropertyDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/agent-log" element={<AgentLog />} />
          <Route path="/data" element={<DataManagement />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/report-builder" element={<ReportBuilder />} />
          <Route path="/team-management" element={<TeamManagement />} />
          <Route path="/saved-searches" element={<SavedSearches />} />
          <Route path="/market-trends" element={<MarketTrends />} />
        </Route>
      </Route>
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
};


function App() {

  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <AppContextProvider>
            <ScrollToTop />
            <AuthenticatedApp />
          </AppContextProvider>
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App