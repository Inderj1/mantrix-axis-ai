import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, Paper, Typography } from '@mui/material';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import QueryPage from './pages/QueryPage-simple';
import SimpleChatInterface from './components/SimpleChatInterface';
import ProcessMiningPage from './pages/ProcessMiningPage';
import WhatIfAnalysisPage from './pages/WhatIfAnalysis';
import AdminSettings from './pages/AdminSettings';
import HomePage from './pages/HomePage';
import UserProfileManager from './components/UserProfileManager';
import CommsConfig from './components/CommsConfig';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './components/Auth/LoginPage';

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
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />

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
            <ProtectedRoute routePath="/chat">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <SimpleChatInterface />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/process-mining"
          element={
            <ProtectedRoute routePath="/process-mining">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <ProcessMiningPage />
                </Layout>
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/whatif-analysis"
          element={
            <ProtectedRoute routePath="/whatif-analysis">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <WhatIfAnalysisPage />
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
          path="/health"
          element={
            <ProtectedRoute routePath="/health">
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Layout>
                  <HealthPage />
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
      </Routes>
    </AuthProvider>
  );
}

export default App;