import React, { useEffect, lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, Paper, Typography, CssBaseline, CircularProgress } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import { premiumTheme } from './themes/premiumTheme';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { useConversationStore } from './stores/conversationStore';
// ConversationContext replaced by Zustand store (stores/conversationStore.js)
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Route loading fallback
const RouteLoadingFallback = () => (
  <Box sx={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: 'background.default'
  }}>
    <CircularProgress />
  </Box>
);

// Lazy load page components for code splitting
const QueryPage = lazy(() => import('./pages/QueryPage-simple'));
const SimpleChatInterface = lazy(() => import('./components/SimpleChatInterface'));
const AdminSettings = lazy(() => import('./pages/AdminSettings'));
const HomePage = lazy(() => import('./pages/HomePage'));
const UserProfileManager = lazy(() => import('./components/UserProfileManager'));
const CommsConfig = lazy(() => import('./components/CommsConfig'));
const ControlCenter = lazy(() => import('./components/ControlCenter'));
const DatabaseConfigPage = lazy(() => import('./pages/DatabaseConfigPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));

/**
 * AppInitializer - Eagerly initializes the conversation store when user is authenticated.
 * This prevents the 4-5 second delay when clicking "New Chat" because the store
 * is already initialized by the time the user navigates to /chat.
 *
 * Also starts the background query checker to poll for completed queries.
 */
const AppInitializer = ({ children }) => {
  const { user, loading: authLoading } = useAuth();
  const initialize = useConversationStore(state => state.initialize);
  const isInitialized = useConversationStore(state => state.isInitialized);
  const checkPendingQueries = useConversationStore(state => state.checkPendingQueries);

  useEffect(() => {
    // Initialize conversation store as soon as user is authenticated
    if (user?.userId && !authLoading && !isInitialized) {
      console.log('[AppInitializer] Eagerly initializing conversation store for user:', user.userId);
      initialize(user.userId);
    }
  }, [user?.userId, authLoading, isInitialized, initialize]);

  // Background query checker - polls for completed queries every 30 seconds
  useEffect(() => {
    if (!user?.userId || authLoading) return;

    // Check immediately on mount
    const pendingQueries = JSON.parse(localStorage.getItem('pendingQueries') || '[]');
    if (pendingQueries.length > 0) {
      console.log('[AppInitializer] Found', pendingQueries.length, 'pending background queries, checking status...');
      checkPendingQueries();
    }

    // Set up interval to check every 30 seconds
    const interval = setInterval(() => {
      const pending = JSON.parse(localStorage.getItem('pendingQueries') || '[]');
      if (pending.length > 0) {
        console.log('[AppInitializer] Checking', pending.length, 'pending background queries...');
        checkPendingQueries();
      }
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [user?.userId, authLoading, checkPendingQueries]);

  return children;
};

// Temporary simple pages
const HistoryPage = () => (
  <Paper sx={{ p: 3 }}>
    <Typography variant="h4">History Page</Typography>
    <Typography>Query history will be shown here</Typography>
  </Paper>
);

const SchemaPage = () => (
  <Paper sx={{ p: 3 }}>
    <Typography variant="h4">Schema Page</Typography>
    <Typography>Database schema will be shown here</Typography>
  </Paper>
);

const HealthPage = () => (
  <Paper sx={{ p: 3 }}>
    <Typography variant="h4">Health Page</Typography>
    <Typography>System health will be shown here</Typography>
  </Paper>
);

function App() {
  console.log('App component rendering');
  console.log('Environment:', import.meta.env);

  return (
    <AuthProvider>
      <AppInitializer>
        <ThemeProvider theme={premiumTheme}>
          <CssBaseline />
          <Suspense fallback={<RouteLoadingFallback />}>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<HomePage />} />

        {/* Default protected route */}
        <Route
          path="/home"
          element={
            <ProtectedRoute routePath="/home">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <Navigate to="/chat" replace />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat"
          element={
            <ProtectedRoute routePath="/chat" requireAuth={false}>
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <SimpleChatInterface />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/query"
          element={
            <ProtectedRoute routePath="/query">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <QueryPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute routePath="/history">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <HistoryPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/schema"
          element={
            <ProtectedRoute routePath="/schema">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <SchemaPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/control-center"
          element={
            <ProtectedRoute routePath="/control-center">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <ControlCenter />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute routePath="/profile">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <UserProfileManager />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <ProtectedRoute routePath="/admin/settings">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <AdminSettings />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/database-config"
          element={
            <ProtectedRoute routePath="/database-config">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <DatabaseConfigPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/comms/config"
          element={
            <ProtectedRoute routePath="/comms/config">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <CommsConfig />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        {/* Dashboard Routes */}
        <Route
          path="/dashboards"
          element={
            <ProtectedRoute routePath="/dashboards">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <DashboardPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/:id"
          element={
            <ProtectedRoute routePath="/dashboards">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <DashboardPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        {/* Shared Dashboard (public, no auth required) */}
        <Route
          path="/dashboards/shared/:token"
          element={
            <Box sx={{ minHeight: '100vh' }}>
              <DashboardPage />
            </Box>
          }
        />
            </Routes>
          </Suspense>
        </ThemeProvider>
      </AppInitializer>
    </AuthProvider>
  );
}

export default App;