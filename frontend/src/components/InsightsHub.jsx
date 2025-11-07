import React, { useState } from 'react';
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
  IconButton,
  Tabs,
  Tab,
  Divider,
  LinearProgress,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  TrendingUp as TrendingIcon,
  Warning as WarningIcon,
  Lightbulb as InsightIcon,
  ShowChart as ChartIcon,
  Error as AlertIcon,
  CheckCircle as CheckIcon,
  ArrowForward as ArrowIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Schedule as ScheduleIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';

const InsightsHub = ({ setSelectedTab, useSapTheme }) => {
  const [selectedCategory, setSelectedCategory] = useState(0);

  // Insight categories
  const categories = ['All Insights', 'Critical', 'Trends', 'Anomalies', 'Recommendations'];

  // Mock insights data
  const insights = [
    {
      id: 1,
      type: 'critical',
      category: 'Sales',
      title: 'Revenue Drop Detected',
      description: 'Q4 revenue declined by 15% compared to Q3. Primary driver: APAC region showing -23% decline.',
      confidence: 95,
      impact: 'High',
      timestamp: '2 hours ago',
      metrics: { affected: '$2.3M', trend: '-15%' },
      icon: <AlertIcon />,
      color: '#bb0000',
      status: 'new',
    },
    {
      id: 2,
      type: 'trend',
      category: 'Customer',
      title: 'Mobile Signup Surge',
      description: 'New user signups from mobile channels increased by 45% over the past 2 weeks.',
      confidence: 88,
      impact: 'Medium',
      timestamp: '4 hours ago',
      metrics: { growth: '+45%', users: '12.5K' },
      icon: <TrendingIcon />,
      color: '#0a6ed1',
      status: 'reviewed',
    },
    {
      id: 3,
      type: 'anomaly',
      category: 'E-commerce',
      title: 'Checkout Conversion Drop',
      description: 'Checkout conversion rate unexpectedly dropped from 12% to 8% starting yesterday.',
      confidence: 92,
      impact: 'High',
      timestamp: '6 hours ago',
      metrics: { before: '12%', after: '8%' },
      icon: <WarningIcon />,
      color: '#df6e0c',
      status: 'investigating',
    },
    {
      id: 4,
      type: 'recommendation',
      category: 'Inventory',
      title: 'Stock Reallocation Opportunity',
      description: 'AI suggests reallocating 2,400 units from Store A to Store B to reduce stockouts.',
      confidence: 82,
      impact: 'Medium',
      timestamp: '8 hours ago',
      metrics: { savings: '$45K', units: '2.4K' },
      icon: <InsightIcon />,
      color: '#107e3e',
      status: 'new',
    },
    {
      id: 5,
      type: 'trend',
      category: 'Marketing',
      title: 'Campaign Performance Excellence',
      description: 'Email campaign "Summer Sale" achieving 3.2x higher CTR than historical average.',
      confidence: 90,
      impact: 'Medium',
      timestamp: '12 hours ago',
      metrics: { ctr: '8.4%', vs_avg: '+220%' },
      icon: <TrendingIcon />,
      color: '#0a6ed1',
      status: 'reviewed',
    },
    {
      id: 6,
      type: 'critical',
      category: 'Supply Chain',
      title: 'Supplier Delay Risk',
      description: 'Supplier XYZ showing 4-day delay pattern. May impact Q1 production schedule.',
      confidence: 87,
      impact: 'High',
      timestamp: '1 day ago',
      metrics: { delay: '4 days', risk: 'High' },
      icon: <AlertIcon />,
      color: '#bb0000',
      status: 'investigating',
    },
  ];

  // Filter insights by category
  const filteredInsights = selectedCategory === 0
    ? insights
    : insights.filter(insight => {
        const categoryMap = {
          1: 'critical',
          2: 'trend',
          3: 'anomaly',
          4: 'recommendation',
        };
        return insight.type === categoryMap[selectedCategory];
      });

  // Stats cards
  const stats = [
    { label: 'Active Insights', value: '23', change: '+5', icon: <AIIcon />, color: '#667eea' },
    { label: 'Critical Alerts', value: '4', change: '+2', icon: <AlertIcon />, color: '#bb0000' },
    { label: 'Opportunities', value: '12', change: '+3', icon: <InsightIcon />, color: '#107e3e' },
    { label: 'Trends Detected', value: '8', change: '+1', icon: <TrendingIcon />, color: '#0a6ed1' },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'new': return 'primary';
      case 'investigating': return 'warning';
      case 'reviewed': return 'success';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1600, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AIIcon sx={{ fontSize: 32, color: 'primary.main' }} />
            AI Insights & Analytics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Automated insights, anomalies, trends, and recommendations powered by AI
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<FilterIcon />} size="small">
            Filters
          </Button>
          <Button variant="contained" startIcon={<RefreshIcon />} size="small">
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Stats Overview */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {stats.map((stat, index) => (
          <Grid item xs={6} md={3} key={index}>
            <Card sx={{ bgcolor: `${stat.color}10`, border: `1px solid ${stat.color}30` }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Avatar sx={{ bgcolor: stat.color, width: 48, height: 48, mx: 'auto', mb: 1 }}>
                  {stat.icon}
                </Avatar>
                <Typography variant="h4" fontWeight={600}>
                  {stat.value}
                </Typography>
                <Typography variant="body2" color="text.primary" gutterBottom>
                  {stat.label}
                </Typography>
                <Chip
                  label={stat.change}
                  size="small"
                  sx={{ fontSize: '0.7rem', height: 20, bgcolor: 'background.paper' }}
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

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

      {/* Insights Feed */}
      <Stack spacing={2}>
        {filteredInsights.map((insight) => (
          <Paper
            key={insight.id}
            sx={{
              p: 3,
              borderLeft: `4px solid ${insight.color}`,
              transition: 'all 0.2s',
              '&:hover': {
                boxShadow: 4,
                transform: 'translateX(4px)',
              },
            }}
          >
            <Box sx={{ display: 'flex', gap: 2 }}>
              {/* Icon */}
              <Avatar
                sx={{
                  bgcolor: `${insight.color}20`,
                  color: insight.color,
                  width: 56,
                  height: 56,
                }}
              >
                {insight.icon}
              </Avatar>

              {/* Content */}
              <Box sx={{ flex: 1 }}>
                {/* Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Box>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 0.5 }}>
                      <Typography variant="h6" fontWeight={600}>
                        {insight.title}
                      </Typography>
                      <Chip
                        label={insight.status.toUpperCase()}
                        size="small"
                        color={getStatusColor(insight.status)}
                        sx={{ height: 20, fontSize: '0.65rem' }}
                      />
                    </Box>
                    <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                      <Chip label={insight.category} size="small" variant="outlined" />
                      <Chip
                        label={`Impact: ${insight.impact}`}
                        size="small"
                        color={insight.impact === 'High' ? 'error' : 'default'}
                        variant="outlined"
                      />
                      <Chip
                        label={`${insight.confidence}% Confidence`}
                        size="small"
                        icon={<CheckIcon />}
                        variant="outlined"
                      />
                    </Stack>
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <ScheduleIcon sx={{ fontSize: 14 }} />
                    {insight.timestamp}
                  </Typography>
                </Box>

                {/* Description */}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {insight.description}
                </Typography>

                {/* Metrics */}
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  {Object.entries(insight.metrics).map(([key, value]) => (
                    <Paper key={key} sx={{ px: 2, py: 1, bgcolor: 'background.default' }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {key.replace('_', ' ').toUpperCase()}
                      </Typography>
                      <Typography variant="body1" fontWeight={600}>
                        {value}
                      </Typography>
                    </Paper>
                  ))}
                </Box>

                {/* Confidence Bar */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      AI Confidence
                    </Typography>
                    <Typography variant="caption" fontWeight={600}>
                      {insight.confidence}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={insight.confidence}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      bgcolor: `${insight.color}20`,
                      '& .MuiLinearProgress-bar': {
                        bgcolor: insight.color,
                      },
                    }}
                  />
                </Box>

                {/* Actions */}
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="contained"
                    size="small"
                    endIcon={<ArrowIcon />}
                    sx={{ textTransform: 'none' }}
                  >
                    Investigate
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<AnalyticsIcon />}
                    sx={{ textTransform: 'none' }}
                    onClick={() => setSelectedTab('analyze')}
                  >
                    View Details
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<ChartIcon />}
                    sx={{ textTransform: 'none' }}
                  >
                    View Trend
                  </Button>
                </Stack>
              </Box>
            </Box>
          </Paper>
        ))}
      </Stack>

      {/* Empty State (if no insights) */}
      {filteredInsights.length === 0 && (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <AIIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No insights in this category
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try selecting a different category or refresh to get new insights
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default InsightsHub;
