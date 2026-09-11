import { lazy, Suspense } from 'react';
import { Toaster } from '@/components/ui/toaster';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClientInstance } from '@/lib/query-client';
import { BrowserRouter as Router, Route, Routes, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import UserNotRegisteredError from '@/components/UserNotRegisteredError';
import ScrollToTop from '@/components/ScrollToTop';
import ProtectedRoute from '@/components/ProtectedRoute';
import RouteLoading from '@/components/RouteLoading';
import { AppContextProvider } from '@/lib/AppContext';
import AppShell from '@/components/tupan/AppShell';

const PageNotFound = lazy(() => import('@/lib/PageNotFound'));
const Welcome = lazy(() => import('@/pages/Welcome'));
const Login = lazy(() => import('@/pages/Login'));
const Register = lazy(() => import('@/pages/Register'));
const ForgotPassword = lazy(() => import('@/pages/ForgotPassword'));
const ResetPassword = lazy(() => import('@/pages/ResetPassword'));
const Menu = lazy(() => import('@/pages/Menu'));
const Overview = lazy(() => import('@/pages/Overview'));
const MarketMap = lazy(() => import('@/pages/MarketMap'));
const Portfolio = lazy(() => import('@/pages/Portfolio'));
const Properties = lazy(() => import('@/pages/Properties'));
const PropertyDetail = lazy(() => import('@/pages/PropertyDetail'));
const Compare = lazy(() => import('@/pages/Compare'));
const VoiceAgent = lazy(() => import('@/pages/VoiceAgent'));
const AgentLog = lazy(() => import('@/pages/AgentLog'));
const DataManagement = lazy(() => import('@/pages/DataManagement'));
const Settings = lazy(() => import('@/pages/Settings'));
const ReportBuilder = lazy(() => import('@/pages/ReportBuilder'));
const TeamManagement = lazy(() => import('@/pages/TeamManagement'));
const SavedSearches = lazy(() => import('@/pages/SavedSearches'));
const MarketTrends = lazy(() => import('@/pages/MarketTrends'));

const PUBLIC_ROUTE_PATHS = new Set(["/", "/login", "/register", "/forgot-password", "/reset-password"]);
const AuthenticatedApp = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError } = useAuth();
  const location = useLocation();
  const isPublicRoute = PUBLIC_ROUTE_PATHS.has(location.pathname);

  // Sign-in, registration, and recovery must remain available even when the
  // session check is pending, unavailable, or returns the expected 401.
  if (!isPublicRoute && (isLoadingPublicSettings || isLoadingAuth)) return <RouteLoading />;

  if (!isPublicRoute && authError) {
    if (authError.type === 'user_not_registered') return <UserNotRegisteredError />;
    if (authError.type === 'auth_required') return <Navigate to="/login" replace />;
  }

  return (
    <Suspense fallback={<RouteLoading />}>
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
    </Suspense>
  );
};

export default function App() {
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
  );
}
