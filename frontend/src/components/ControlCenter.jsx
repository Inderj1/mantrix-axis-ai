import React, { useState } from 'react';
import {
  Box,
  Paper,
  Tabs,
  Tab,
  Typography,
  Stack,
  Chip,
  Avatar,
  IconButton,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Monitor as MonitorIcon,
  Storage as StorageIcon,
  Settings as SettingsIcon,
  AccountCircle as PersonaIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  CloudSync as CloudSyncIcon,
  Hub as HubIcon,
} from '@mui/icons-material';

// Import the components
import SystemHealthMonitoring from './controlcenter/SystemHealthMonitoring';
import DataSourcesConnections from './controlcenter/DataSourcesConnections';
import PlatformSettings from './controlcenter/PlatformSettings';
import PipelineManagement from './controlcenter/PipelineManagement';
import UserProfileManager from './UserProfileManager';
import CommsConfig from './CommsConfig';

const ControlCenter = ({ apiHealth, onRefreshStatus }) => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);

  const tabs = [
    {
      label: 'Data Sources',
      icon: <StorageIcon />,
      component: <DataSourcesConnections />,
      status: 'healthy',
    },
    {
      label: 'System Health',
      icon: <MonitorIcon />,
      component: <SystemHealthMonitoring />,
      status: 'healthy',
    },
    {
      label: 'Pipeline',
      icon: <CloudSyncIcon />,
      component: <PipelineManagement />,
      status: 'healthy',
    },
    {
      label: 'Settings',
      icon: <SettingsIcon />,
      component: <PlatformSettings />,
      status: 'healthy',
    },
    {
      label: 'AI Persona',
      icon: <PersonaIcon />,
      component: <UserProfileManager />,
      status: 'healthy',
    },
    {
      label: 'COMMS Config',
      icon: <SettingsIcon />,
      component: <CommsConfig />,
      status: 'healthy',
    },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return theme.palette.success.main;
      case 'warning': return theme.palette.warning.main;
      case 'error': return theme.palette.error.main;
      case 'building': return theme.palette.grey[400];
      default: return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircleIcon sx={{ fontSize: 16 }} />;
      case 'warning': return <WarningIcon sx={{ fontSize: 16 }} />;
      case 'building': return <HubIcon sx={{ fontSize: 16 }} />;
      default: return null;
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar
              sx={{
                width: 64,
                height: 64,
                bgcolor: alpha('#1976d2', 0.1),
              }}
            >
              <SettingsIcon sx={{ fontSize: 36, color: '#1976d2' }} />
            </Avatar>
            <Box>
              <Typography variant="h4" fontWeight={900}>
                Control Center
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Centralized platform management and monitoring dashboard
              </Typography>
            </Box>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              icon={apiHealth?.status === 'healthy' ? <CheckCircleIcon /> : <ErrorIcon />}
              label={`API: ${apiHealth?.status || 'Unknown'}`}
              color="default"
              variant="outlined"
              disabled
              sx={{ opacity: 0.5 }}
            />
            <Chip
              size="small"
              icon={<CheckCircleIcon />}
              label="DB: Connected"
              color="default"
              variant="outlined"
              disabled
              sx={{ opacity: 0.5 }}
            />
            <IconButton color="default" onClick={onRefreshStatus} size="small" disabled sx={{ opacity: 0.5 }}>
              <RefreshIcon />
            </IconButton>
          </Stack>
        </Stack>
      </Box>

      {/* Tab Navigation */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, v) => setActiveTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': {
              minHeight: 72,
              textTransform: 'none',
              fontSize: '0.875rem',
              fontWeight: 600,
              px: 3,
            },
            '& .MuiTabs-indicator': {
              height: 3,
            },
          }}
        >
          {tabs.map((tab, index) => (
            <Tab
              key={index}
              icon={
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <Avatar
                    sx={{
                      width: 40,
                      height: 40,
                      bgcolor: alpha(getStatusColor(tab.status), 0.1),
                      color: getStatusColor(tab.status),
                    }}
                  >
                    {tab.icon}
                  </Avatar>
                  <Box sx={{ textAlign: 'left' }}>
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <Typography variant="body2" fontWeight={600}>
                        {tab.label}
                      </Typography>
                      {getStatusIcon(tab.status)}
                    </Stack>
                    <Chip
                      label={tab.badge}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        bgcolor: alpha(getStatusColor(tab.status), 0.1),
                        color: getStatusColor(tab.status),
                        fontWeight: 600,
                      }}
                    />
                  </Box>
                </Stack>
              }
              iconPosition="start"
              disabled={tab.status === 'building'}
            />
          ))}
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <Box>
        {tabs[activeTab].component}
      </Box>
    </Box>
  );
};

export default ControlCenter;