import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  Stack,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Alert,
  AlertTitle,
  Button,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  useTheme,
  alpha,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  CloudQueue as CloudIcon,
  Api as ApiIcon,
  Storage as DatabaseIcon,
  Hub as HubIcon,
  AccountTree as AccountTreeIcon,
  Notifications as NotificationsIcon,
  MoreVert as MoreVertIcon,
  Circle as CircleIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// Service icon mapping
const getServiceIcon = (serviceType) => {
  switch (serviceType) {
    case 'api': return <ApiIcon />;
    case 'database': return <CloudIcon />;
    case 'cache': return <StorageIcon />;
    case 'vectordb': return <HubIcon />;
    default: return <DatabaseIcon />;
  }
};

const SystemHealthMonitoring = () => {
  const theme = useTheme();
  const [systemHealth, setSystemHealth] = useState(null);
  const [services, setServices] = useState([]);
  const [metricsData, setMetricsData] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch system health data
  const fetchSystemHealth = async () => {
    try {
      const response = await fetch('/api/v1/control-center/system-health');
      const data = await response.json();

      if (data.success) {
        setSystemHealth(data);
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching system health:', err);
      setError('Failed to load system health data');
    } finally {
      setLoading(false);
    }
  };

  // Fetch services
  const fetchServices = async () => {
    try {
      const response = await fetch('/api/v1/control-center/services');
      const data = await response.json();

      if (data.success) {
        // Transform services to include icons
        const transformedServices = data.services.map(service => ({
          ...service,
          icon: getServiceIcon(service.type),
        }));
        setServices(transformedServices);
      }
    } catch (err) {
      console.error('Error fetching services:', err);
    }
  };

  // Fetch metrics history
  const fetchMetricsHistory = async () => {
    try {
      const response = await fetch('/api/v1/control-center/metrics-history?hours=1');
      const data = await response.json();

      if (data.success && data.history) {
        setMetricsData(data.history);
      } else if (data.message) {
        // No data available yet
        setMetricsData([]);
      }
    } catch (err) {
      console.error('Error fetching metrics history:', err);
      setMetricsData([]);
    }
  };

  // Initial load
  useEffect(() => {
    fetchSystemHealth();
    fetchServices();
    fetchMetricsHistory();
  }, []);

  // Auto-refresh data every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchSystemHealth();
      fetchServices();
      fetchMetricsHistory();
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleRefresh = () => {
    setRefreshing(true);
    Promise.all([
      fetchSystemHealth(),
      fetchServices(),
      fetchMetricsHistory()
    ]).finally(() => {
      setRefreshing(false);
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return theme.palette.success.main;
      case 'warning': return theme.palette.warning.main;
      case 'error': return theme.palette.error.main;
      default: return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircleIcon />;
      case 'warning': return <WarningIcon />;
      case 'error': return <ErrorIcon />;
      default: return <CircleIcon />;
    }
  };

  const overallHealth = {
    total: services.length,
    healthy: services.filter(s => s.status === 'healthy' || s.status === 'connected').length,
    warning: services.filter(s => s.status === 'warning').length,
    error: services.filter(s => s.status === 'error').length,
  };

  const healthData = [
    { name: 'Healthy', value: overallHealth.healthy, color: theme.palette.success.main },
    { name: 'Warning', value: overallHealth.warning, color: theme.palette.warning.main },
    { name: 'Error', value: overallHealth.error, color: theme.palette.error.main },
  ];

  if (loading) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading system health...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h5" fontWeight={600} gutterBottom>
            System Health & Monitoring
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Real-time monitoring of all platform services and resources
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Chip
            label={autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
            color={autoRefresh ? "success" : "default"}
            onClick={() => setAutoRefresh(!autoRefresh)}
            size="small"
          />
          <Button
            variant="outlined"
            startIcon={refreshing ? <CircularProgress size={16} /> : <RefreshIcon />}
            onClick={handleRefresh}
            disabled={refreshing}
            size="small"
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Overall Health Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  System Status
                </Typography>
                <CheckCircleIcon color="success" />
              </Stack>
              <Typography variant="h4" fontWeight={600}>
                {systemHealth?.health_score || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Services Operational
              </Typography>
              <LinearProgress
                variant="determinate"
                value={systemHealth?.health_score || 0}
                sx={{ mt: 2, height: 6, borderRadius: 3 }}
                color="success"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Average Uptime
                </Typography>
                <TrendingUpIcon color="primary" />
              </Stack>
              <Typography variant="h4" fontWeight={600}>
                {systemHealth?.system_metrics?.cpu?.percent || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                CPU Usage
              </Typography>
              <Stack direction="row" spacing={0.5} sx={{ mt: 2 }}>
                <Chip label={`${systemHealth?.system_metrics?.cpu?.cores || 0} cores`} size="small" />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Total Requests
                </Typography>
                <SpeedIcon color="info" />
              </Stack>
              <Typography variant="h4" fontWeight={600}>
                {systemHealth?.system_metrics?.memory?.percent || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Memory Usage
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Typography variant="body2">
                    {systemHealth?.system_metrics?.memory?.used_gb || 0}GB / {systemHealth?.system_metrics?.memory?.total_gb || 0}GB
                  </Typography>
                </Stack>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Error Rate
                </Typography>
                <ErrorIcon color="error" />
              </Stack>
              <Typography variant="h4" fontWeight={600}>
                {systemHealth?.system_metrics?.disk?.percent || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Disk Usage
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Typography variant="body2">
                    {systemHealth?.system_metrics?.disk?.used_gb || 0}GB / {systemHealth?.system_metrics?.disk?.total_gb || 0}GB
                  </Typography>
                </Stack>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Service Health Grid */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Service Health Status
        </Typography>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          {services.map((service) => (
            <Grid item xs={12} sm={6} md={4} key={service.id}>
              <Card
                sx={{
                  border: '1px solid',
                  borderColor: alpha(getStatusColor(service.status), 0.3),
                  bgcolor: alpha(getStatusColor(service.status), 0.02),
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: 2,
                  },
                }}
                onClick={() => setSelectedService(service)}
              >
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: 2,
                          bgcolor: alpha(getStatusColor(service.status), 0.1),
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: getStatusColor(service.status),
                        }}
                      >
                        {service.icon}
                      </Box>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={600}>
                          {service.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {service.endpoint || 'Local Service'}
                        </Typography>
                      </Box>
                    </Box>
                    <Tooltip title={service.status}>
                      <Box sx={{ color: getStatusColor(service.status) }}>
                        {getStatusIcon(service.status)}
                      </Box>
                    </Tooltip>
                  </Stack>

                  <Box sx={{ mt: 2 }}>
                    <Grid container spacing={1}>
                      {service.latency_ms !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Latency
                          </Typography>
                          <Typography variant="body2" fontWeight={500}>
                            {service.latency_ms}ms
                          </Typography>
                        </Grid>
                      )}
                      {service.tables !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Tables
                          </Typography>
                          <Typography variant="body2" fontWeight={500}>
                            {service.tables}
                          </Typography>
                        </Grid>
                      )}
                      {service.memory_used_mb !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Memory
                          </Typography>
                          <Typography variant="body2" fontWeight={500}>
                            {service.memory_used_mb}MB
                          </Typography>
                        </Grid>
                      )}
                      {service.connected_clients !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Clients
                          </Typography>
                          <Typography variant="body2" fontWeight={500}>
                            {service.connected_clients}
                          </Typography>
                        </Grid>
                      )}
                      {service.schemas !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Schemas
                          </Typography>
                          <Typography variant="body2" fontWeight={500}>
                            {service.schemas}
                          </Typography>
                        </Grid>
                      )}
                      {service.error && (
                        <Grid item xs={12}>
                          <Typography variant="caption" color="error.main">
                            {service.error}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </Box>

                  {service.message && (
                    <Alert severity="warning" sx={{ mt: 2, py: 0 }}>
                      <Typography variant="caption">{service.message}</Typography>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Performance Metrics */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Performance
            </Typography>
            <Box sx={{ height: 300, mt: 2 }}>
              {metricsData.length === 0 ? (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                  <Alert severity="info" sx={{ width: '100%' }}>
                    <AlertTitle>No Metrics Data Available</AlertTitle>
                    Metrics collection will begin shortly. Refresh to see updated data.
                  </Alert>
                </Box>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metricsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                    <XAxis dataKey="time" fontSize={12} />
                    <YAxis fontSize={12} />
                    <ChartTooltip />
                    <Line
                      type="monotone"
                      dataKey="cpu"
                      stroke={theme.palette.primary.main}
                      strokeWidth={2}
                      name="CPU %"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="memory"
                      stroke={theme.palette.secondary.main}
                      strokeWidth={2}
                      name="Memory %"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Request Volume & Latency
            </Typography>
            <Box sx={{ height: 300, mt: 2 }}>
              {metricsData.length === 0 ? (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                  <Alert severity="info" sx={{ width: '100%' }}>
                    <AlertTitle>No Metrics Data Available</AlertTitle>
                    Metrics collection will begin shortly. Refresh to see updated data.
                  </Alert>
                </Box>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={metricsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                    <XAxis dataKey="time" fontSize={12} />
                    <YAxis fontSize={12} />
                    <ChartTooltip />
                    <Area
                      type="monotone"
                      dataKey="requests"
                      stroke={theme.palette.success.main}
                      fill={alpha(theme.palette.success.main, 0.2)}
                      strokeWidth={2}
                      name="Requests/min"
                    />
                    <Area
                      type="monotone"
                      dataKey="latency"
                      stroke={theme.palette.warning.main}
                      fill={alpha(theme.palette.warning.main, 0.2)}
                      strokeWidth={2}
                      name="Latency (ms)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Alerts */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">
            Recent Alerts
          </Typography>
          <Button startIcon={<NotificationsIcon />} size="small">
            Configure Alerts
          </Button>
        </Stack>
        <List>
          <ListItem>
            <ListItemIcon>
              <WarningIcon color="warning" />
            </ListItemIcon>
            <ListItemText
              primary="High latency detected on Weaviate Vector DB"
              secondary="2 minutes ago - Average response time exceeded 200ms threshold"
            />
          </ListItem>
          <Divider />
          <ListItem>
            <ListItemIcon>
              <CheckCircleIcon color="success" />
            </ListItemIcon>
            <ListItemText
              primary="Redis cache memory usage normalized"
              secondary="15 minutes ago - Memory usage dropped below 80% threshold"
            />
          </ListItem>
          <Divider />
          <ListItem>
            <ListItemIcon>
              <ErrorIcon color="error" />
            </ListItemIcon>
            <ListItemText
              primary="API endpoint /api/v1/query experienced timeout"
              secondary="1 hour ago - Query execution exceeded 30 second limit"
            />
          </ListItem>
        </List>
      </Paper>
    </Box>
  );
};

export default SystemHealthMonitoring;