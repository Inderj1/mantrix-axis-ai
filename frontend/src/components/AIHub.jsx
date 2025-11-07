import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Paper,
  Avatar,
  Button,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  Psychology as AutoMLIcon,
  TrendingUp as PredictionsIcon,
  Science as ModelsIcon,
  Warning as AnomalyIcon,
  ShowChart as ForecastIcon,
  Analytics as RootCauseIcon,
  Speed as KeyDriversIcon,
  Pattern as PatternIcon,
  ArrowForward as ArrowIcon,
} from '@mui/icons-material';

const AIHub = ({ setSelectedTab, useSapTheme }) => {
  // Core AI Tools - Only essential AI features
  const aiTools = [
    {
      icon: <AutoMLIcon />,
      title: 'AutoML',
      description: 'Train models automatically without code',
      color: '#667eea',
      count: '12 algorithms',
    },
    {
      icon: <PredictionsIcon />,
      title: 'Forecasting',
      description: 'Predict future trends and outcomes',
      color: '#00BCD4',
      count: '98.5% accuracy',
    },
    {
      icon: <AnomalyIcon />,
      title: 'Anomaly Detection',
      description: 'Real-time pattern detection',
      color: '#bb0000',
      count: '24/7 monitoring',
    },
    {
      icon: <RootCauseIcon />,
      title: 'Root Cause Analysis',
      description: 'Understand why metrics changed',
      color: '#df6e0c',
      count: 'AI-powered',
    },
    {
      icon: <KeyDriversIcon />,
      title: 'Key Drivers',
      description: 'Identify factors impacting metrics',
      color: '#107e3e',
      count: 'Multi-variable',
    },
    {
      icon: <PatternIcon />,
      title: 'Pattern Discovery',
      description: 'Find hidden correlations',
      color: '#0a6ed1',
      count: 'Unsupervised',
    },
  ];

  // ML Models
  const mlModels = [
    { name: 'Sales Forecast Model', accuracy: '98.5%', status: 'Active', lastRun: '2h ago', color: '#107e3e' },
    { name: 'Churn Prediction', accuracy: '95.2%', status: 'Active', lastRun: '4h ago', color: '#0a6ed1' },
    { name: 'Demand Planning', accuracy: '97.1%', status: 'Training', lastRun: '1d ago', color: '#df6e0c' },
  ];

  // AI Insights
  const recentInsights = [
    { title: 'Sales dropped 15% in West region', severity: 'High', time: '2h ago', color: '#bb0000' },
    { title: 'Customer retention improved by 8%', severity: 'Positive', time: '4h ago', color: '#107e3e' },
    { title: 'Inventory turnover anomaly detected', severity: 'Medium', time: '6h ago', color: '#df6e0c' },
  ];

  return (
    <Paper elevation={1} sx={{ p: 4, borderRadius: 2, minHeight: 'calc(100vh - 180px)', bgcolor: 'background.paper' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AIIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          AI Hub
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Artificial intelligence and machine learning tools
        </Typography>
      </Box>

      {/* AI Stats Overview */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" fontWeight={600} color="primary.main">5</Typography>
            <Typography variant="body2" fontWeight={500}>ML Models</Typography>
            <Typography variant="caption" color="text.secondary">2 training</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" fontWeight={600} color="primary.main">89</Typography>
            <Typography variant="body2" fontWeight={500}>AI Insights</Typography>
            <Typography variant="caption" color="text.secondary">24 new today</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" fontWeight={600} color="primary.main">156</Typography>
            <Typography variant="body2" fontWeight={500}>Predictions</Typography>
            <Typography variant="caption" color="text.secondary">This week</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" fontWeight={600} color="primary.main">98.5%</Typography>
            <Typography variant="body2" fontWeight={500}>Accuracy</Typography>
            <Typography variant="caption" color="text.secondary">Average</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* AI Tools */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
          🤖 AI Tools
        </Typography>
        <Grid container spacing={2}>
          {aiTools.map((tool, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Card
                sx={{
                  cursor: 'pointer',
                  height: '100%',
                  transition: 'all 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                    <Avatar
                      sx={{
                        bgcolor: `${tool.color}20`,
                        color: tool.color,
                        width: 48,
                        height: 48,
                      }}
                    >
                      {tool.icon}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body1" fontWeight={600} gutterBottom>
                        {tool.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {tool.description}
                      </Typography>
                      <Chip
                        label={tool.count}
                        size="small"
                        sx={{
                          bgcolor: `${tool.color}20`,
                          color: tool.color,
                          fontWeight: 600,
                          fontSize: '0.7rem',
                        }}
                      />
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      <Grid container spacing={3}>
        {/* ML Models */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                <ModelsIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                ML Models
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />}>
                View All
              </Button>
            </Box>
            <Stack spacing={2}>
              {mlModels.map((model, index) => (
                <Box
                  key={index}
                  sx={{
                    p: 2,
                    borderRadius: 1,
                    bgcolor: 'background.default',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="body2" fontWeight={600}>
                      {model.name}
                    </Typography>
                    <Chip
                      label={model.status}
                      size="small"
                      sx={{
                        bgcolor: `${model.color}20`,
                        color: model.color,
                        fontWeight: 600,
                        height: 20,
                        fontSize: '0.7rem',
                      }}
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Accuracy: {model.accuracy} • Last run: {model.lastRun}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* Recent AI Insights */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                💡 Recent Insights
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />}>
                View All
              </Button>
            </Box>
            <Stack spacing={2}>
              {recentInsights.map((insight, index) => (
                <Box
                  key={index}
                  sx={{
                    p: 2,
                    borderRadius: 1,
                    borderLeft: `4px solid ${insight.color}`,
                    bgcolor: 'background.default',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight={600}>
                      {insight.title}
                    </Typography>
                    <Chip
                      label={insight.severity}
                      size="small"
                      sx={{
                        bgcolor: `${insight.color}20`,
                        color: insight.color,
                        fontWeight: 600,
                        height: 20,
                        fontSize: '0.7rem',
                      }}
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {insight.time}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default AIHub;
