import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, Paper, Typography, CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import { premiumTheme } from './themes/premiumTheme';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { useConversationStore } from './stores/conversationStore';
// ConversationContext replaced by Zustand store (stores/conversationStore.js)
import Layout from './components/Layout';

/**
 * AppInitializer - Eagerly initializes the conversation store when user is authenticated.
 * This prevents the 4-5 second delay when clicking "New Chat" because the store
 * is already initialized by the time the user navigates to /chat.
 */
const AppInitializer = ({ children }) => {
  const { user, loading: authLoading } = useAuth();
  const initialize = useConversationStore(state => state.initialize);
  const isInitialized = useConversationStore(state => state.isInitialized);

  useEffect(() => {
    // Initialize conversation store as soon as user is authenticated
    if (user?.userId && !authLoading && !isInitialized) {
      console.log('[AppInitializer] Eagerly initializing conversation store for user:', user.userId);
      initialize(user.userId);
    }
  }, [user?.userId, authLoading, isInitialized, initialize]);

  return children;
};
import QueryPage from './pages/QueryPage-simple';
import SimpleChatInterface from './components/SimpleChatInterface';
import AdminSettings from './pages/AdminSettings';
import HomePage from './pages/HomePage';
import UserProfileManager from './components/UserProfileManager';
import CommsConfig from './components/CommsConfig';
import ControlCenter from './components/ControlCenter';
import DatabaseConfigPage from './pages/DatabaseConfigPage';
import DashboardPage from './pages/DashboardPage';
import ProtectedRoute from './components/ProtectedRoute';

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
        </ThemeProvider>
      </AppInitializer>
    </AuthProvider>
  );
}

export default App;