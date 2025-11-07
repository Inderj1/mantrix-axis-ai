import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Paper,
  Avatar,
  IconButton,
  Tabs,
  Tab,
  Divider,
  Switch,
  FormControlLabel,
  TextField,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
} from '@mui/material';
import {
  AdminPanelSettings as AdminIcon,
  People as UsersIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  DataUsage as DataIcon,
  Cable as ConnectionIcon,
  Notifications as NotificationIcon,
  VpnKey as ApiKeyIcon,
  Assessment as ReportsIcon,
  CloudUpload as BackupIcon,
  Speed as PerformanceIcon,
  Shield as ShieldIcon,
  ArrowForward as ArrowIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

const AdminHub = ({ setSelectedTab, useSapTheme }) => {
  const [selectedCategory, setSelectedCategory] = useState(0);

  // Admin categories
  const categories = ['Overview', 'Users & Access', 'Data Sources', 'Settings', 'Security', 'Logs'];

  // Admin sections
  const adminSections = [
    {
      icon: <UsersIcon />,
      title: 'User Management',
      description: 'Manage users, roles, and permissions',
      color: '#0a6ed1',
      action: () => {},
      stats: { users: 145, active: 128 },
    },
    {
      icon: <ConnectionIcon />,
      title: 'Data Connections',
      description: 'Configure and manage data source connections',
      color: '#107e3e',
      action: () => {},
      stats: { total: 12, active: 10 },
    },
    {
      icon: <SecurityIcon />,
      title: 'Security & Compliance',
      description: 'Security policies, audit logs, and compliance',
      color: '#bb0000',
      action: () => {},
      stats: { policies: 8, alerts: 2 },
    },
    {
      icon: <SettingsIcon />,
      title: 'System Settings',
      description: 'Configure system-wide settings and preferences',
      color: '#df6e0c',
      action: () => {},
      stats: { configs: 45 },
    },
    {
      icon: <ApiKeyIcon />,
      title: 'API Keys & Tokens',
      description: 'Manage API keys and authentication tokens',
      color: '#354a5f',
      action: () => {},
      stats: { keys: 18, active: 15 },
    },
    {
      icon: <BackupIcon />,
      title: 'Backup & Recovery',
      description: 'Data backup, restore, and disaster recovery',
      color: '#00BCD4',
      action: () => {},
      stats: { backups: 24, last: '2h ago' },
    },
  ];

  // System health metrics
  const systemHealth = [
    { label: 'System Status', value: 'Operational', status: 'success', icon: <CheckIcon /> },
    { label: 'API Response Time', value: '145ms', status: 'success', icon: <PerformanceIcon /> },
    { label: 'Database Health', value: 'Good', status: 'success', icon: <DataIcon /> },
    { label: 'Active Users', value: '128', status: 'success', icon: <UsersIcon /> },
    { label: 'Data Sources', value: '10/12', status: 'warning', icon: <ConnectionIcon /> },
    { label: 'Security Alerts', value: '2', status: 'error', icon: <WarningIcon /> },
  ];

  // Recent activity
  const recentActivity = [
    { action: 'User added', user: 'Admin', target: 'john.doe@company.com', time: '5 min ago', type: 'user' },
    { action: 'Data source connected', user: 'Sarah Chen', target: 'PostgreSQL-Prod', time: '1 hour ago', type: 'connection' },
    { action: 'Security policy updated', user: 'Admin', target: 'Password Policy', time: '3 hours ago', type: 'security' },
    { action: 'API key created', user: 'Mike Johnson', target: 'Analytics API', time: '5 hours ago', type: 'api' },
    { action: 'Backup completed', user: 'System', target: 'Daily Backup', time: '12 hours ago', type: 'backup' },
  ];

  // Data sources
  const dataSources = [
    { name: 'PostgreSQL Production', type: 'PostgreSQL', status: 'connected', lastSync: '5 min ago', icon: <DataIcon /> },
    { name: 'MySQL Analytics', type: 'MySQL', status: 'connected', lastSync: '10 min ago', icon: <DataIcon /> },
    { name: 'Snowflake DW', type: 'Snowflake', status: 'connected', lastSync: '1 hour ago', icon: <DataIcon /> },
    { name: 'MongoDB Logs', type: 'MongoDB', status: 'error', lastSync: '2 days ago', icon: <DataIcon /> },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return '#107e3e';
      case 'warning': return '#df6e0c';
      case 'error': return '#bb0000';
      default: return '#757575';
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1600, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AdminIcon sx={{ fontSize: 32, color: 'primary.main' }} />
            Administration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            System administration, user management, and configuration
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<SettingsIcon />} size="small">
          System Settings
        </Button>
      </Box>

      {/* System Health Overview */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" fontWeight={600} sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          💚 System Health
        </Typography>
        <Grid container spacing={2}>
          {systemHealth.map((metric, index) => (
            <Grid item xs={6} md={2} key={index}>
              <Card sx={{ bgcolor: `${getStatusColor(metric.status)}10`, border: `1px solid ${getStatusColor(metric.status)}30` }}>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Avatar
                    sx={{
                      bgcolor: getStatusColor(metric.status),
                      width: 40,
                      height: 40,
                      mx: 'auto',
                      mb: 1,
                    }}
                  >
                    {metric.icon}
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    {metric.value}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {metric.label}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Category Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={selectedCategory}
          onChange={(e, newValue) => setSelectedCategory(newValue)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          {categories.map((category, index) => (
            <Tab key={index} label={category} />
          ))}
        </Tabs>
      </Paper>

      {/* Overview Tab */}
      {selectedCategory === 0 && (
        <>
          {/* Admin Sections */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              ⚙️ Administration Tools
            </Typography>
            <Grid container spacing={3}>
              {adminSections.map((section, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: 4,
                      },
                    }}
                    onClick={section.action}
                  >
                    <CardContent>
                      <Avatar
                        sx={{
                          bgcolor: `${section.color}20`,
                          color: section.color,
                          width: 56,
                          height: 56,
                          mb: 2,
                        }}
                      >
                        {section.icon}
                      </Avatar>
                      <Typography variant="h6" fontWeight={600} gutterBottom>
                        {section.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {section.description}
                      </Typography>
                      <Stack direction="row" spacing={1}>
                        {Object.entries(section.stats).map(([key, value]) => (
                          <Chip
                            key={key}
                            label={`${key}: ${value}`}
                            size="small"
                            sx={{ fontSize: '0.7rem', height: 20 }}
                          />
                        ))}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>

        </>
      )}

      {/* Users & Access Tab */}
      {selectedCategory === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            User Management
          </Typography>
          <Typography variant="body2" color="text.secondary">
            User management features coming soon...
          </Typography>
        </Paper>
      )}

      {/* Data Sources Tab */}
      {selectedCategory === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Data Source Configuration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Data source management features coming soon...
          </Typography>
        </Paper>
      )}

      {/* Settings Tab */}
      {selectedCategory === 3 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            System Settings
          </Typography>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <FormControlLabel
              control={<Switch defaultChecked />}
              label="Enable email notifications"
            />
            <FormControlLabel
              control={<Switch defaultChecked />}
              label="Auto-backup enabled"
            />
            <FormControlLabel
              control={<Switch />}
              label="Maintenance mode"
            />
            <FormControlLabel
              control={<Switch defaultChecked />}
              label="Audit logging"
            />
          </Stack>
        </Paper>
      )}

      {/* Security Tab */}
      {selectedCategory === 4 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Security & Compliance
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Security management features coming soon...
          </Typography>
        </Paper>
      )}

      {/* Logs Tab */}
      {selectedCategory === 5 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            System Logs & Audit Trail
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Log viewer coming soon...
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default AdminHub;
