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
  Tune as TuneIcon,
} from '@mui/icons-material';

// Salesforce-style colors
const sfColors = {
  bgPage: '#f3f3f3',
  bgCard: '#ffffff',
  textPrimary: '#032D60',
  textSecondary: '#706e6b',
  accent: '#0176D3',
  accentHover: '#014486',
  border: '#e5e5e5',
  success: '#2E844A',
  warning: '#FE9339',
  error: '#C23934',
  iconBg: '#e8f4fd',
};

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
    <Box sx={{ bgcolor: sfColors.bgPage, minHeight: '100%', p: 3 }}>
      {/* Hero Header */}
      <Box sx={{
        bgcolor: sfColors.bgCard,
        borderRadius: '8px',
        p: 3,
        mb: 3,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
        border: `1px solid ${sfColors.border}`,
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Avatar
            sx={{
              width: 64,
              height: 64,
              bgcolor: sfColors.iconBg,
            }}
          >
            <TuneIcon sx={{ fontSize: 32, color: sfColors.accent }} />
          </Avatar>
          <Box>
            <Typography sx={{ fontWeight: 700, fontSize: '1.5rem', color: sfColors.textPrimary }}>
              Control Center
            </Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.95rem' }}>
              Centralized platform management and monitoring dashboard
            </Typography>
          </Box>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip
            size="small"
            icon={apiHealth?.status === 'healthy' ? <CheckCircleIcon sx={{ color: sfColors.success }} /> : <ErrorIcon sx={{ color: sfColors.error }} />}
            label={`API: ${apiHealth?.status || 'Unknown'}`}
            variant="outlined"
            sx={{ borderColor: sfColors.border }}
          />
          <Chip
            size="small"
            icon={<CheckCircleIcon sx={{ color: sfColors.success }} />}
            label="DB: Connected"
            variant="outlined"
            sx={{ borderColor: sfColors.border }}
          />
          <IconButton
            onClick={onRefreshStatus}
            size="small"
            sx={{ color: sfColors.textSecondary, '&:hover': { bgcolor: sfColors.iconBg } }}
          >
            <RefreshIcon />
          </IconButton>
        </Stack>
      </Box>

      {/* Tab Navigation */}
      <Paper sx={{
        mb: 3,
        boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
        border: `1px solid ${sfColors.border}`,
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        <Tabs
          value={activeTab}
          onChange={(e, v) => setActiveTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            bgcolor: sfColors.bgCard,
            '& .MuiTab-root': {
              minHeight: 72,
              textTransform: 'none',
              fontSize: '0.875rem',
              fontWeight: 600,
              px: 3,
              color: sfColors.textSecondary,
              '&.Mui-selected': {
                color: sfColors.accent,
              },
            },
            '& .MuiTabs-indicator': {
              height: 3,
              bgcolor: sfColors.accent,
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