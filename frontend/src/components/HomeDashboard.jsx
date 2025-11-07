import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Stack,
  Paper,
  Avatar,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  Chat as ChatIcon,
  Search as SearchIcon,
  Add as AddIcon,
  CloudUpload as UploadIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Schedule as ScheduleIcon,
  ArrowForward as ArrowIcon,
} from '@mui/icons-material';

const HomeDashboard = ({ setSelectedTab, useSapTheme }) => {
  // Quick Start actions
  const quickStartActions = [
    {
      icon: <ChatIcon />,
      label: 'Ask AI',
      description: 'Natural language queries',
      color: '#0a6ed1', // SAP Blue
      action: () => setSelectedTab('chat'),
    },
    {
      icon: <SearchIcon />,
      label: 'Search',
      description: 'Find data & insights',
      color: '#107e3e', // SAP Positive Green
      action: () => setSelectedTab('explore'),
    },
    {
      icon: <AddIcon />,
      label: 'Create',
      description: 'New dashboard',
      color: '#354a5f', // SAP Shell Header
      action: () => setSelectedTab('analyze'),
    },
    {
      icon: <UploadIcon />,
      label: 'Upload',
      description: 'Add data source',
      color: '#6a6d70', // SAP Neutral
      action: () => setSelectedTab('admin'),
    },
  ];

  // Key Metrics - System overview
  const metrics = [
    { label: 'Total Queries', value: '2,547', change: '+12%', trend: 'up', color: '#107e3e' },
    { label: 'Active Users', value: '156', change: '+8%', trend: 'up', color: '#0a6ed1' },
    { label: 'Data Sources', value: '24', change: '0', trend: 'neutral', color: '#6a6d70' },
    { label: 'AI Insights', value: '89', change: '+45%', trend: 'up', color: '#0854a0' },
  ];

  // Recent Activity
  const recentActivity = [
    { title: 'Sales Dashboard edited', user: 'You', time: '2 hours ago', icon: <AddIcon />, color: '#0a6ed1' },
    { title: 'Q4 Forecast completed', user: 'AI Agent', time: '4 hours ago', icon: <CheckIcon />, color: '#107e3e' },
    { title: 'New anomaly detected', user: 'System', time: '6 hours ago', icon: <WarningIcon />, color: '#bb0000' },
    { title: 'Data sync completed', user: 'System', time: '1 day ago', icon: <CheckIcon />, color: '#107e3e' },
  ];

  // Active Tasks
  const activeTasks = [
    { title: 'Review Q4 Sales Analysis', priority: 'High', progress: 75, dueDate: 'Today' },
    { title: 'Update Marketing Dashboard', priority: 'Medium', progress: 40, dueDate: 'Tomorrow' },
    { title: 'Prepare Executive Report', priority: 'High', progress: 25, dueDate: 'This Week' },
  ];

  return (
    <Paper elevation={1} sx={{ p: 4, borderRadius: 2, minHeight: 'calc(100vh - 180px)', bgcolor: 'background.paper' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={400} gutterBottom sx={{ color: '#32363a' }}>
          Welcome back
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </Typography>
      </Box>

      {/* Quick Start Actions */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" fontWeight={400} sx={{ mb: 2 }}>
          Quick Start
        </Typography>
        <Grid container spacing={2}>
          {quickStartActions.map((action, index) => (
            <Grid item xs={6} sm={3} key={index}>
              <Card
                sx={{
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
                onClick={action.action}
              >
                <CardContent sx={{ textAlign: 'center', py: 3 }}>
                  <Avatar
                    sx={{
                      bgcolor: `${action.color}20`,
                      color: action.color,
                      width: 56,
                      height: 56,
                      mx: 'auto',
                      mb: 1.5,
                    }}
                  >
                    {action.icon}
                  </Avatar>
                  <Typography variant="body1" fontWeight={600} gutterBottom>
                    {action.label}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {action.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Key Metrics */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" fontWeight={400} sx={{ mb: 2 }}>
          Overview
        </Typography>
        <Grid container spacing={2}>
          {metrics.map((metric, index) => (
            <Grid item xs={6} md={3} key={index}>
              <Paper sx={{ p: 2.5 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={500} sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  {metric.label}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: 0.5 }}>
                  <Typography variant="h4" fontWeight={400}>
                    {metric.value}
                  </Typography>
                  {metric.change !== '0' && (
                    <Chip
                      label={metric.change}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        bgcolor: metric.trend === 'up' ? 'rgba(16, 126, 62, 0.1)' : 'rgba(187, 0, 0, 0.1)',
                        color: metric.trend === 'up' ? '#107e3e' : '#bb0000',
                        fontWeight: 600,
                      }}
                    />
                  )}
                </Box>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>

      <Grid container spacing={3}>
        {/* Recent Activity */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={400}>
                Recent Activity
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />} onClick={() => setSelectedTab('content')}>
                View All
              </Button>
            </Box>
            <Stack spacing={2}>
              {recentActivity.map((activity, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    p: 1.5,
                    borderRadius: 1,
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Avatar sx={{ bgcolor: `${activity.color}20`, color: activity.color, width: 40, height: 40 }}>
                    {activity.icon}
                  </Avatar>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" fontWeight={500}>
                      {activity.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {activity.user} • {activity.time}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* Active Tasks */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={400}>
                Active Tasks
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />}>
                View All
              </Button>
            </Box>
            <Stack spacing={2.5}>
              {activeTasks.map((task, index) => (
                <Box key={index}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" fontWeight={500} gutterBottom>
                        {task.title}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <Chip
                          label={task.priority}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: '0.7rem',
                            bgcolor: task.priority === 'High' ? 'rgba(187, 0, 0, 0.1)' : 'rgba(223, 110, 12, 0.1)',
                            color: task.priority === 'High' ? '#bb0000' : '#df6e0c',
                            fontWeight: 600,
                          }}
                        />
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <ScheduleIcon sx={{ fontSize: 14 }} />
                          {task.dueDate}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={task.progress}
                      sx={{ flex: 1, height: 6, borderRadius: 1 }}
                    />
                    <Typography variant="caption" fontWeight={600}>
                      {task.progress}%
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default HomeDashboard;
