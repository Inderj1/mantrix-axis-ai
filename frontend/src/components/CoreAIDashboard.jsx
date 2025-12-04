import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  IconButton,
  Chip,
  LinearProgress,
  Alert,
  AlertTitle,
  Button,
  Divider,
  Stack,
  Tooltip,
  Badge,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  Avatar,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Autocomplete,
  TablePagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Input,
  InputAdornment,
  GlobalStyles,
} from '@mui/material';
import {
  Speed as SpeedIcon,
  TrendingUp as TrendingUpIcon,
  Inventory as InventoryIcon,
  AttachMoney as MoneyIcon,
  LocalShipping as ShippingIcon,
  AccountBalance as AccountBalanceIcon,
  Security as SecurityIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Analytics as AnalyticsIcon,
  ArrowForward as ArrowForwardIcon,
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  Assignment as AssignmentIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Lightbulb as LightbulbIcon,
  Verified as VerifiedIcon,
  Close as CloseIcon,
  LocationOn as LocationIcon,
  TrendingDown as TrendingDownIcon,
  Schedule as ScheduleIcon,
  BarChart as BarChartIcon,
  ShowChart as ShowChartIcon,
  Category as CategoryIcon,
  Business as BusinessIcon,
  AttachMoney as AttachMoneyIcon,
  Group as GroupIcon,
  Build as BuildIcon,
  ThumbUp as ThumbUpIcon,
  PieChart as PieChartIcon,
  People as PeopleIcon,
  ShoppingCart as ShoppingCartIcon,
  Error as ErrorIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer, 
  Legend, 
  ComposedChart, 
  Scatter,
  RadialBarChart,
  RadialBar,
} from 'recharts';
import { apiService } from '../services/api';

// Theme colors
const COLORS = {
  primary: '#1976d2',
  secondary: '#dc004e',
  success: '#4caf50',
  warning: '#ff9800',
  error: '#f44336',
  info: '#2196f3',
  revenue: '#4caf50',
  segmentColors: {
    'Champions': '#1976d2',
    'Loyal Customers': '#2e7d32',
    'Potential Loyalists': '#0288d1',
    'New Customers': '#7b1fa2',
    'Promising': '#f57c00',
    'Need Attention': '#fbc02d',
    'About to Sleep': '#f9a825',
    'At Risk': '#e65100',
    'Lost': '#c62828',
    'Hibernating': '#424242',
  }
};

// Alias for compatibility
const chartColors = COLORS;

const CoreAIDashboard = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSegment, setSelectedSegment] = useState(null);
  
  // Real data states
  const [dashboardData, setDashboardData] = useState(null);
  const [segmentData, setSegmentData] = useState(null);
  const [revenueData, setRevenueData] = useState(null);
  const [retentionData, setRetentionData] = useState(null);
  const [productData, setProductData] = useState(null);
  const [insights, setInsights] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  
  // Customer 360 states
  const [customerSearchTerm, setCustomerSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerData, setCustomerData] = useState(null);
  const [cohortRetentionData, setCohortRetentionData] = useState(null);
  const [cohortRevenueData, setCohortRevenueData] = useState(null);
  const [cohortExplanationOpen, setCohortExplanationOpen] = useState(false);
  const [cohortInsights, setCohortInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  
  // Product Performance states
  const [productMetrics, setProductMetrics] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productSegmentData, setProductSegmentData] = useState(null);
  const [productTrendData, setProductTrendData] = useState(null);
  const [productMatrixData, setProductMatrixData] = useState(null);
  const [productDetailOpen, setProductDetailOpen] = useState(false);
  
  // Financial Analytics states
  const [financialSummary, setFinancialSummary] = useState(null);
  const [financialTrends, setFinancialTrends] = useState(null);
  const [profitabilityData, setProfitabilityData] = useState(null);
  
  // Data Tables states
  const [selectedTable, setSelectedTable] = useState('customer-master');
  const [tableData, setTableData] = useState(null);
  const [tablePagination, setTablePagination] = useState({ page: 0, rowsPerPage: 100 });
  const [tableFilters, setTableFilters] = useState({});
  const [tableLoading, setTableLoading] = useState(false);

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  // Fetch all dashboard data
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [
        dashboardResponse,
        segmentResponse,
        revenueResponse,
        retentionResponse,
        productResponse,
        insightsResponse
      ] = await Promise.all([
        apiService.getAnalyticsDashboard(),
        apiService.getCustomerSegments(),
        apiService.getRevenueTrends(),
        apiService.getRetentionAnalytics(),
        apiService.getProductAnalytics(),
        apiService.getAIInsights()
      ]);

      setDashboardData(dashboardResponse.data.data);
      setSegmentData(segmentResponse.data.data);
      setRevenueData(revenueResponse.data.data);
      setRetentionData(retentionResponse.data.data);
      setProductData(productResponse.data.data);
      setInsights(insightsResponse.data.data);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchDashboardData, 60000);
    return () => clearInterval(interval);
  }, []);
  
  // Load table data when pagination or filters change
  useEffect(() => {
    if (activeTab === 6 && selectedTable) {
      loadTableData(selectedTable, tableFilters);
    }
  }, [tablePagination, activeTab]);

  // Load data when tab changes
  useEffect(() => {
    const loadTabData = async () => {
      switch (activeTab) {
        case 1: // Customer 360
          if (!segmentData || !revenueData || !cohortRetentionData) {
            setLoading(true);
            try {
              const [segmentResponse, revenueResponse, cohortRetentionResponse, cohortRevenueResponse] = await Promise.all([
                !segmentData ? apiService.getCustomerSegments() : Promise.resolve(null),
                !revenueData ? apiService.getRevenueTrends() : Promise.resolve(null),
                !cohortRetentionData ? apiService.getCohortRetentionTable() : Promise.resolve(null),
                !cohortRevenueData ? apiService.getCohortRevenueTable() : Promise.resolve(null)
              ]);
              
              if (segmentResponse && segmentResponse.data.success) {
                setSegmentData(segmentResponse.data.data);
              }
              if (revenueResponse && revenueResponse.data.success) {
                setRevenueData(revenueResponse.data.data);
              }
              if (cohortRetentionResponse && cohortRetentionResponse.data.success) {
                setCohortRetentionData(cohortRetentionResponse.data.data);
              }
              if (cohortRevenueResponse && cohortRevenueResponse.data.success) {
                setCohortRevenueData(cohortRevenueResponse.data.data);
              }
            } catch (error) {
              console.error('Failed to load customer data:', error);
            } finally {
              setLoading(false);
            }
          }
          break;
        case 2: // Product Performance
          if (!productMetrics) {
            await loadProductMetrics();
          }
          break;
        case 3: // Financial Analytics
          if (!financialSummary) {
            await loadFinancialData();
          }
          break;
        case 6: // Data Tables
          if (!tableData || selectedTable) {
            await loadTableData(selectedTable);
          }
          break;
      }
    };
    
    loadTabData();
  }, [activeTab]);
  
  // Customer 360 Functions
  const searchCustomers = async (searchTerm) => {
    if (!searchTerm || searchTerm.length < 2) {
      setSearchResults([]);
      return;
    }
    
    try {
      const response = await apiService.searchCustomers(searchTerm);
      if (response.data.success) {
        setSearchResults(response.data.data.customers);
      }
    } catch (error) {
      console.error('Failed to search customers:', error);
    }
  };
  
  const loadCustomerData = async (customerId) => {
    try {
      setLoading(true);
      const response = await apiService.getCustomer360(customerId);
      if (response.data.success) {
        setCustomerData(response.data.data);
        setSelectedCustomer(customerId);
      }
    } catch (error) {
      console.error('Failed to load customer data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Product Performance Functions
  const loadProductMetrics = async () => {
    try {
      setLoading(true);
      const [metricsResponse, matrixResponse] = await Promise.all([
        apiService.getProductMetrics(),
        apiService.getProductCustomerMatrixTable({ top_products: 20 })
      ]);
      
      if (metricsResponse.data.success) {
        setProductMetrics(metricsResponse.data.data);
      }
      if (matrixResponse.data.success) {
        setProductMatrixData(matrixResponse.data.data);
      }
    } catch (error) {
      console.error('Failed to load product metrics:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const loadProductDetails = async (productId) => {
    try {
      setLoading(true);
      const [segmentResponse, trendResponse] = await Promise.all([
        apiService.getProductBySegment(productId),
        apiService.getProductTrends(productId)
      ]);
      
      if (segmentResponse.data.success) {
        setProductSegmentData(segmentResponse.data.data);
      }
      if (trendResponse.data.success) {
        setProductTrendData(trendResponse.data.data);
      }
      setSelectedProduct(productId);
      setProductDetailOpen(true); // Open the dialog
    } catch (error) {
      console.error('Failed to load product details:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Financial Analytics Functions
  const loadFinancialData = async () => {
    try {
      setLoading(true);
      const [summaryResponse, trendsResponse, profitResponse] = await Promise.all([
        apiService.getFinancialSummary(),
        apiService.getFinancialTrends(),
        apiService.getProfitabilityAnalysis()
      ]);
      
      if (summaryResponse.data.success) {
        setFinancialSummary(summaryResponse.data.data);
      }
      if (trendsResponse.data.success) {
        setFinancialTrends(trendsResponse.data.data);
      }
      if (profitResponse.data.success) {
        setProfitabilityData(profitResponse.data.data);
      }
    } catch (error) {
      console.error('Failed to load financial data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Cohort Insights Function
  const loadCohortInsights = async () => {
    try {
      setLoadingInsights(true);
      setCohortInsights(null); // Clear previous insights
      
      const response = await apiService.getCohortInsights();
      
      if (response.data.success) {
        setCohortInsights(response.data.data);
      }
    } catch (error) {
      console.error('Failed to load cohort insights:', error);
      setError('Failed to generate insights. Please try again.');
    } finally {
      setLoadingInsights(false);
    }
  };
  
  // Data Tables Functions
  const loadTableData = async (tableName, filters = {}) => {
    try {
      setTableLoading(true);
      let response;
      const params = {
        offset: tablePagination.page * tablePagination.rowsPerPage,
        limit: tablePagination.rowsPerPage,
        ...filters
      };
      
      switch (tableName) {
        case 'customer-master':
          response = await apiService.getCustomerMasterTable(params);
          break;
        case 'transactions':
          response = await apiService.getTransactionTable(params);
          break;
        case 'segmentation-performance':
          response = await apiService.getSegmentationPerformanceTable();
          break;
        case 'cohort-retention':
          response = await apiService.getCohortRetentionTable();
          break;
        case 'cohort-revenue':
          response = await apiService.getCohortRevenueTable();
          break;
        case 'time-series':
          response = await apiService.getTimeSeriesPerformanceTable(filters.segment);
          break;
        case 'product-matrix':
          response = await apiService.getProductCustomerMatrixTable(params);
          break;
        default:
          throw new Error('Unknown table');
      }
      
      if (response.data.success) {
        setTableData(response.data.data);
      }
    } catch (error) {
      console.error('Failed to load table data:', error);
      setError(`Failed to load ${tableName} data`);
    } finally {
      setTableLoading(false);
    }
  };
  
  const handleTableChange = (newTable) => {
    setSelectedTable(newTable);
    setTablePagination({ page: 0, rowsPerPage: 100 });
    setTableFilters({});
    loadTableData(newTable);
  };
  
  const handlePageChange = (event, newPage) => {
    setTablePagination({ ...tablePagination, page: newPage });
  };
  
  const handleRowsPerPageChange = (event) => {
    setTablePagination({ page: 0, rowsPerPage: parseInt(event.target.value, 10) });
  };

  // Calculate KPI cards data
  const generateProductTrendData = () => {
    if (!productMetrics) return [];
    
    // Generate mock trend data for top products
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    return months.map(month => {
      const dataPoint = { month };
      productMetrics.products.slice(0, 5).forEach(product => {
        // Generate realistic trend data based on current revenue
        const baseValue = parseFloat(product.total_revenue) / 12;
        const variation = (Math.random() - 0.5) * 0.3; // ±15% variation
        dataPoint[product.product] = Math.round(baseValue * (1 + variation));
      });
      return dataPoint;
    });
  };

  const getKPIData = () => {
    if (!dashboardData) return [];

    const metrics = dashboardData.summary_metrics || {};
    const segments = dashboardData.segments || [];
    const championsData = segments.find(s => s.segment === 'Champions') || {};

    return [
      {
        title: 'Total Customers',
        value: metrics.total_customers?.toLocaleString() || '0',
        change: `${metrics.monthly_growth_rate || 0}%`,
        icon: <PeopleIcon />,
        color: COLORS.primary,
        trend: metrics.monthly_growth_rate > 0 ? 'up' : 'down'
      },
      {
        title: 'Total Revenue',
        value: `$${(metrics.total_revenue / 1000000).toFixed(2)}M`,
        change: `${metrics.monthly_growth_rate || 0}%`,
        icon: <MoneyIcon />,
        color: COLORS.success,
        trend: metrics.monthly_growth_rate > 0 ? 'up' : 'down'
      },
      {
        title: 'Champions Revenue',
        value: `${metrics.champions_revenue_percentage || 0}%`,
        subtitle: `$${(championsData.total_revenue / 1000000).toFixed(2)}M`,
        icon: <VerifiedIcon />,
        color: COLORS.info,
        trend: 'stable'
      },
      {
        title: 'At Risk Customers',
        value: metrics.at_risk_customers?.toLocaleString() || '0',
        change: 'Require attention',
        icon: <WarningIcon />,
        color: COLORS.warning,
        trend: 'warning'
      }
    ];
  };

  // Render KPI Card
  const renderKPICard = (kpi) => (
    <Card sx={{ height: '100%', position: 'relative', overflow: 'visible' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="caption">
              {kpi.title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ mb: 1 }}>
              {kpi.value}
            </Typography>
            {kpi.subtitle && (
              <Typography variant="body2" color="textSecondary">
                {kpi.subtitle}
              </Typography>
            )}
            <Box display="flex" alignItems="center" mt={1}>
              {kpi.trend === 'up' && <TrendingUpIcon sx={{ color: COLORS.success, mr: 0.5, fontSize: 16 }} />}
              {kpi.trend === 'down' && <TrendingDownIcon sx={{ color: COLORS.error, mr: 0.5, fontSize: 16 }} />}
              {kpi.trend === 'warning' && <WarningIcon sx={{ color: COLORS.warning, mr: 0.5, fontSize: 16 }} />}
              <Typography 
                variant="caption" 
                sx={{ 
                  color: kpi.trend === 'up' ? COLORS.success : 
                         kpi.trend === 'down' ? COLORS.error : 
                         kpi.trend === 'warning' ? COLORS.warning : 'textSecondary' 
                }}
              >
                {kpi.change}
              </Typography>
            </Box>
          </Box>
          <Avatar sx={{ bgcolor: kpi.color, width: 48, height: 48 }}>
            {kpi.icon}
          </Avatar>
        </Box>
      </CardContent>
    </Card>
  );

  // Render segment distribution pie chart
  const renderSegmentChart = () => {
    if (!dashboardData?.segments) return null;

    const data = dashboardData.segments.map(segment => ({
      name: segment.segment,
      value: segment.customer_count,
      revenue: segment.total_revenue,
      percentage: segment.percentage
    }));

    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({name, percentage}) => `${name}: ${percentage}%`}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS.segmentColors[entry.name] || COLORS.primary} />
            ))}
          </Pie>
          <RechartsTooltip 
            formatter={(value, name) => [
              `${value.toLocaleString()} customers`,
              name
            ]}
          />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  // Render revenue trends chart
  const renderRevenueTrends = () => {
    if (!revenueData?.time_series) return null;

    const data = revenueData.time_series.map(item => ({
      month: item.month,
      revenue: item.total_revenue,
      ...item.segments
    }));

    return (
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis tickFormatter={(value) => `$${(value/1000).toFixed(0)}K`} />
          <RechartsTooltip 
            formatter={(value) => `$${value.toLocaleString()}`}
          />
          <Legend />
          {Object.keys(COLORS.segmentColors).map((segment) => (
            data[0]?.[segment] !== undefined && (
              <Area
                key={segment}
                type="monotone"
                dataKey={segment}
                stackId="1"
                stroke={COLORS.segmentColors[segment]}
                fill={COLORS.segmentColors[segment]}
              />
            )
          ))}
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  // Render top customers table
  const renderTopCustomers = () => {
    if (!dashboardData?.top_customers) return null;

    return (
      <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell>Customer</TableCell>
              <TableCell>Segment</TableCell>
              <TableCell align="right">Revenue</TableCell>
              <TableCell align="right">Orders</TableCell>
              <TableCell align="right">Recency</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dashboardData.top_customers.map((customer, index) => (
              <TableRow key={index} hover>
                <TableCell>{customer.customer}</TableCell>
                <TableCell>
                  <Chip 
                    label={customer.segment} 
                    size="small"
                    sx={{ 
                      bgcolor: COLORS.segmentColors[customer.segment], 
                      color: 'white' 
                    }}
                  />
                </TableCell>
                <TableCell align="right">${customer.revenue.toLocaleString()}</TableCell>
                <TableCell align="right">{customer.frequency}</TableCell>
                <TableCell align="right">{customer.recency}d</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Render AI insights
  const renderInsights = () => {
    if (!insights?.insights) return null;

    return (
      <Stack spacing={2}>
        {insights.insights.map((insight, index) => (
          <Alert 
            key={index} 
            severity={insight.type}
            action={
              <Button size="small" onClick={() => handleInsightAction(insight)}>
                Take Action
              </Button>
            }
          >
            <AlertTitle>{insight.title}</AlertTitle>
            {insight.description}
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Recommended Action: {insight.action}
            </Typography>
          </Alert>
        ))}
      </Stack>
    );
  };

  const handleInsightAction = (insight) => {
    // Show confirmation dialog for all actions
    setConfirmDialog({
      open: true,
      title: 'Confirm Action',
      message: `Execute action: ${insight.action}?`,
      onConfirm: () => {
        console.log('Executing action:', insight);
        // TODO: Implement actual action execution
        setConfirmDialog({ open: false, title: '', message: '', onConfirm: null });
      },
    });
  };

  if (loading && !dashboardData) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  // Performance Insights Tab Component
  const PerformanceInsightsTab = () => {
    const [performanceInsights, setPerformanceInsights] = useState(null);
    const [loadingInsights, setLoadingInsights] = useState(false);
    const [followUpQuestion, setFollowUpQuestion] = useState('');
    const [conversations, setConversations] = useState([]);
    
    const loadPerformanceInsights = async () => {
      try {
        setLoadingInsights(true);
        const response = await apiService.getPerformanceInsights();
        if (response.data.success) {
          setPerformanceInsights(response.data.data);
        }
      } catch (error) {
        console.error('Failed to load performance insights:', error);
        setError('Failed to load performance insights');
      } finally {
        setLoadingInsights(false);
      }
    };
    
    const handleFollowUpQuestion = async () => {
      if (!followUpQuestion.trim()) return;
      
      try {
        const response = await apiService.askFollowUpQuestion(
          followUpQuestion,
          performanceInsights
        );
        
        if (response.data.success) {
          setConversations([...conversations, response.data.data]);
          setFollowUpQuestion('');
        }
      } catch (error) {
        console.error('Failed to get answer:', error);
      }
    };
    
    useEffect(() => {
      loadPerformanceInsights();
    }, []);
    
    if (loadingInsights) {
      return (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      );
    }
    
    if (!performanceInsights) {
      return (
        <Box textAlign="center" p={4}>
          <Button variant="contained" onClick={loadPerformanceInsights}>
            Generate Performance Insights
          </Button>
        </Box>
      );
    }
    
    return (
      <Grid container spacing={3}>
        {/* Executive Summary */}
        <Grid item xs={12}>
          <Card sx={{ bgcolor: 'primary.main', color: 'primary.contrastText' }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                {performanceInsights.insights.executive_summary?.headline}
              </Typography>
              <Typography variant="body1" paragraph>
                {performanceInsights.insights.executive_summary?.key_message}
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Typography variant="subtitle1">Business Health Score:</Typography>
                <Chip 
                  label={performanceInsights.insights.executive_summary?.business_health_score || 'N/A'} 
                  sx={{ bgcolor: 'white', color: 'primary.main', fontWeight: 'bold' }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Performance Highlights */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>Performance Highlights</Typography>
          <Grid container spacing={2}>
            {performanceInsights.insights.performance_highlights?.map((highlight, index) => (
              <Grid item xs={12} md={6} lg={3} key={index}>
                <Card variant="outlined">
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="subtitle2" color="textSecondary">
                        {highlight.metric}
                      </Typography>
                      {highlight.trend === 'up' ? <TrendingUpIcon color="success" /> :
                       highlight.trend === 'down' ? <TrendingDownIcon color="error" /> :
                       <ShowChartIcon color="action" />}
                    </Box>
                    <Typography variant="h4" gutterBottom>
                      {highlight.value}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {highlight.insight}
                    </Typography>
                    {highlight.action_required && (
                      <Chip label="Action Required" color="warning" size="small" sx={{ mt: 1 }} />
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>
        
        {/* Financial Insights */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Financial Insights</Typography>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="textSecondary">
                    Profitability Trend
                  </Typography>
                  <Chip 
                    label={performanceInsights.insights.financial_insights?.profitability_trend || 'Unknown'}
                    color={
                      performanceInsights.insights.financial_insights?.profitability_trend === 'improving' ? 'success' :
                      performanceInsights.insights.financial_insights?.profitability_trend === 'declining' ? 'error' : 'default'
                    }
                  />
                </Box>
                <Typography variant="body2">
                  {performanceInsights.insights.financial_insights?.margin_analysis}
                </Typography>
                {performanceInsights.insights.financial_insights?.cost_optimization_opportunities?.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>Cost Optimization Opportunities:</Typography>
                    <List dense>
                      {performanceInsights.insights.financial_insights.cost_optimization_opportunities.map((opp, idx) => (
                        <ListItem key={idx}>
                          <ListItemText primary={opp} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Strategic Priorities */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Strategic Priorities</Typography>
              <Stack spacing={2}>
                {performanceInsights.insights.strategic_priorities?.map((priority, index) => (
                  <Box key={index} sx={{ borderLeft: 3, borderColor: 'primary.main', pl: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      {priority.priority}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" paragraph>
                      {priority.rationale}
                    </Typography>
                    <Box display="flex" gap={2}>
                      <Chip label={`Impact: ${priority.expected_impact}`} size="small" />
                      <Chip label={priority.timeline} size="small" variant="outlined" />
                    </Box>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Interactive Q&A */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Ask Follow-up Questions</Typography>
              <Box display="flex" gap={2} mb={3}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="Ask a specific question about these insights..."
                  value={followUpQuestion}
                  onChange={(e) => setFollowUpQuestion(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleFollowUpQuestion()}
                />
                <Button 
                  variant="contained" 
                  onClick={handleFollowUpQuestion}
                  disabled={!followUpQuestion.trim()}
                >
                  Ask
                </Button>
              </Box>
              
              {/* Conversation History */}
              {conversations.map((conv, index) => (
                <Box key={index} sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    Q: {conv.question}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    {conv.response.answer}
                  </Typography>
                  {conv.response.supporting_data?.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      {conv.response.supporting_data.map((data, idx) => (
                        <Chip 
                          key={idx}
                          label={`${data.metric}: ${data.value}`}
                          size="small"
                          sx={{ mr: 1, mb: 1 }}
                        />
                      ))}
                    </Box>
                  )}
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };
  
  // Recommendations Tab Component
  const RecommendationsTab = () => {
    const [recommendations, setRecommendations] = useState(null);
    const [loadingRecs, setLoadingRecs] = useState(false);
    const [selectedFocusArea, setSelectedFocusArea] = useState('');
    const [followUpQuestion, setFollowUpQuestion] = useState('');
    const [conversations, setConversations] = useState([]);
    
    const focusAreas = [
      'Revenue Growth',
      'Cost Optimization',
      'Customer Retention',
      'Operational Excellence',
      'Market Expansion',
      'Product Strategy'
    ];
    
    const loadRecommendations = async (focusArea = null) => {
      try {
        setLoadingRecs(true);
        const response = await apiService.getRecommendations(focusArea);
        if (response.data.success) {
          setRecommendations(response.data.data);
        }
      } catch (error) {
        console.error('Failed to load recommendations:', error);
        setError('Failed to load recommendations');
      } finally {
        setLoadingRecs(false);
      }
    };
    
    const handleFollowUpQuestion = async () => {
      if (!followUpQuestion.trim()) return;
      
      try {
        const response = await apiService.askFollowUpQuestion(
          followUpQuestion,
          recommendations
        );
        
        if (response.data.success) {
          setConversations([...conversations, response.data.data]);
          setFollowUpQuestion('');
        }
      } catch (error) {
        console.error('Failed to get answer:', error);
      }
    };
    
    useEffect(() => {
      loadRecommendations();
    }, []);
    
    if (loadingRecs) {
      return (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      );
    }
    
    if (!recommendations) {
      return (
        <Box textAlign="center" p={4}>
          <Button variant="contained" onClick={() => loadRecommendations()}>
            Generate Recommendations
          </Button>
        </Box>
      );
    }
    
    return (
      <Grid container spacing={3}>
        {/* Focus Area Selector */}
        <Grid item xs={12}>
          <Box display="flex" gap={2} alignItems="center" mb={2}>
            <Typography variant="subtitle1">Focus Area:</Typography>
            {focusAreas.map((area) => (
              <Chip
                key={area}
                label={area}
                onClick={() => {
                  setSelectedFocusArea(area);
                  loadRecommendations(area);
                }}
                color={selectedFocusArea === area ? 'primary' : 'default'}
                variant={selectedFocusArea === area ? 'filled' : 'outlined'}
              />
            ))}
          </Box>
        </Grid>
        
        {/* Strategic Recommendations */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>Strategic Recommendations</Typography>
          <Grid container spacing={2}>
            {recommendations.recommendations.strategic_recommendations?.map((rec, index) => (
              <Grid item xs={12} key={index}>
                <Card variant="outlined">
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          {rec.title}
                        </Typography>
                        <Chip 
                          label={rec.category} 
                          size="small" 
                          color="primary"
                          sx={{ mr: 1 }}
                        />
                        <Chip 
                          label={`Priority: ${rec.priority}`}
                          size="small"
                          color={
                            rec.priority === 'Critical' ? 'error' :
                            rec.priority === 'High' ? 'warning' : 'default'
                          }
                        />
                      </Box>
                    </Box>
                    
                    <Typography variant="body2" paragraph>
                      {rec.description}
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={4}>
                        <Box sx={{ bgcolor: 'success.light', p: 2, borderRadius: 1 }}>
                          <Typography variant="subtitle2" gutterBottom>Expected Impact</Typography>
                          <Typography variant="body2">
                            <strong>{rec.expected_impact?.metric}:</strong> {rec.expected_impact?.improvement}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            Timeframe: {rec.expected_impact?.timeframe}
                          </Typography>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={4}>
                        <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1 }}>
                          <Typography variant="subtitle2" gutterBottom>Implementation Steps</Typography>
                          <List dense>
                            {rec.implementation_steps?.slice(0, 3).map((step, idx) => (
                              <ListItem key={idx}>
                                <ListItemText 
                                  primary={step}
                                  primaryTypographyProps={{ variant: 'caption' }}
                                />
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={4}>
                        <Box sx={{ bgcolor: 'warning.light', p: 2, borderRadius: 1 }}>
                          <Typography variant="subtitle2" gutterBottom>Success Metrics</Typography>
                          {rec.success_metrics?.map((metric, idx) => (
                            <Chip 
                              key={idx}
                              label={metric}
                              size="small"
                              sx={{ mr: 0.5, mb: 0.5 }}
                            />
                          ))}
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>
        
        {/* Quick Wins */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <ThumbUpIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Quick Wins
              </Typography>
              <List>
                {recommendations.recommendations.quick_wins?.map((win, index) => (
                  <ListItem key={index} sx={{ borderBottom: '1px solid #eee' }}>
                    <ListItemText
                      primary={win.action}
                      secondary={
                        <Box>
                          <Typography variant="caption" display="block">
                            Impact: {win.impact}
                          </Typography>
                          <Box display="flex" gap={1} mt={0.5}>
                            <Chip label={`Effort: ${win.effort}`} size="small" />
                            <Chip label={win.timeline} size="small" variant="outlined" />
                          </Box>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Next 30 Days Action Plan */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <ScheduleIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Next 30 Days
              </Typography>
              
              <Box mb={2}>
                <Typography variant="subtitle2" gutterBottom>Immediate Actions</Typography>
                <Stack spacing={1}>
                  {recommendations.recommendations.next_30_days?.immediate_actions?.map((action, idx) => (
                    <Box key={idx} display="flex" alignItems="center" gap={1}>
                      <CheckCircleIcon fontSize="small" color="success" />
                      <Typography variant="body2">{action}</Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
              
              <Box mb={2}>
                <Typography variant="subtitle2" gutterBottom>Key Decisions</Typography>
                <Stack spacing={1}>
                  {recommendations.recommendations.next_30_days?.key_decisions?.map((decision, idx) => (
                    <Alert key={idx} severity="info" icon={<InfoIcon />}>
                      {decision}
                    </Alert>
                  ))}
                </Stack>
              </Box>
              
              <Box>
                <Typography variant="subtitle2" gutterBottom>Metrics to Watch</Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {recommendations.recommendations.next_30_days?.metrics_to_watch?.map((metric, idx) => (
                    <Chip 
                      key={idx}
                      label={metric}
                      icon={<TimelineIcon />}
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Interactive Q&A */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Ask About These Recommendations</Typography>
              <Box display="flex" gap={2} mb={3}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="Ask for clarification or additional details about any recommendation..."
                  value={followUpQuestion}
                  onChange={(e) => setFollowUpQuestion(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleFollowUpQuestion()}
                />
                <Button 
                  variant="contained" 
                  onClick={handleFollowUpQuestion}
                  disabled={!followUpQuestion.trim()}
                >
                  Ask
                </Button>
              </Box>
              
              {/* Conversation History */}
              {conversations.map((conv, index) => (
                <Box key={index} sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    Q: {conv.question}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    {conv.response.answer}
                  </Typography>
                  {conv.response.recommendations?.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="textSecondary">
                        Additional recommendations:
                      </Typography>
                      <List dense>
                        {conv.response.recommendations.map((rec, idx) => (
                          <ListItem key={idx}>
                            <ListItemText primary={rec} primaryTypographyProps={{ variant: 'caption' }} />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  if (error) {
    return (
      <Alert severity="error">
        <AlertTitle>Error Loading Dashboard</AlertTitle>
        {error}
        <Button onClick={fetchDashboardData} sx={{ mt: 2 }}>
          Retry
        </Button>
      </Alert>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Global Styles for animations */}
      <GlobalStyles
        styles={{
          '@keyframes pulse': {
            '0%': {
              opacity: 1,
              transform: 'scale(1)',
            },
            '50%': {
              opacity: 0.5,
              transform: 'scale(1.1)',
            },
            '100%': {
              opacity: 1,
              transform: 'scale(1)',
            },
          },
        }}
      />
      
      {/* Modern Header Section - Light Theme */}
      <Box sx={{ 
        background: '#ffffff',
        borderRadius: 2,
        p: 3,
        mb: 3,
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        border: '1px solid #e5e7eb'
      }}>
        {/* Header Content */}
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={3}>
          <Box>
            <Typography 
              variant="h4" 
              component="h1" 
              sx={{ 
                color: '#111827',
                fontWeight: 700,
                letterSpacing: '-0.025em',
                mb: 0.5
              }}
            >
              Margen.AI | Financial Transaction Assistant
            </Typography>
            <Typography 
              variant="body1" 
              sx={{ 
                color: '#6b7280',
                fontSize: '1rem'
              }}
            >
              Real-time insights from your customer data
            </Typography>
          </Box>
          <Box display="flex" gap={2} alignItems="center">
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1,
              background: '#f3f4f6',
              borderRadius: 2,
              px: 2,
              py: 0.75,
              border: '1px solid #e5e7eb'
            }}>
              <Box sx={{ 
                width: 8, 
                height: 8, 
                borderRadius: '50%', 
                background: '#10b981',
                animation: 'pulse 2s infinite'
              }} />
              <Typography sx={{ color: '#374151', fontSize: '0.875rem', fontWeight: 500 }}>
                Live
              </Typography>
              <Typography sx={{ color: '#6b7280', fontSize: '0.875rem' }}>
                {lastUpdate.toLocaleTimeString()}
              </Typography>
            </Box>
            <IconButton 
              onClick={fetchDashboardData} 
              disabled={loading}
              sx={{ 
                color: '#374151',
                background: '#f3f4f6',
                border: '1px solid #e5e7eb',
                '&:hover': {
                  background: '#e5e7eb'
                }
              }}
            >
              <RefreshIcon />
            </IconButton>
          </Box>
        </Box>

        {/* KPI Cards - Modern Light Style */}
        <Grid container spacing={2}>
          {getKPIData().map((kpi, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Box sx={{
                background: '#f9fafb',
                borderRadius: 1.5,
                p: 2,
                border: '1px solid #e5e7eb',
                transition: 'all 0.2s ease',
                '&:hover': {
                  borderColor: '#d1d5db',
                  boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
                }
              }}>
                <Typography sx={{ 
                  color: '#6b7280', 
                  fontSize: '0.75rem',
                  mb: 0.5,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  {kpi.title}
                </Typography>
                <Typography sx={{ 
                  color: '#111827', 
                  fontSize: '1.875rem',
                  fontWeight: 700,
                  lineHeight: 1.2,
                  mb: 0.5
                }}>
                  {kpi.value}
                </Typography>
                {kpi.subtitle && (
                  <Typography sx={{ 
                    color: '#4b5563', 
                    fontSize: '0.875rem',
                    mb: 0.5
                  }}>
                    {kpi.subtitle}
                  </Typography>
                )}
                <Box display="flex" alignItems="center" gap={0.5}>
                  {kpi.trend === 'up' && (
                    <TrendingUpIcon sx={{ color: '#10b981', fontSize: 16 }} />
                  )}
                  {kpi.trend === 'down' && (
                    <TrendingDownIcon sx={{ color: '#ef4444', fontSize: 16 }} />
                  )}
                  {kpi.trend === 'warning' && (
                    <WarningIcon sx={{ color: '#f59e0b', fontSize: 16 }} />
                  )}
                  <Typography sx={{ 
                    color: kpi.trend === 'up' ? '#10b981' : 
                           kpi.trend === 'down' ? '#ef4444' : 
                           kpi.trend === 'warning' ? '#f59e0b' : '#6b7280',
                    fontSize: '0.875rem',
                    fontWeight: 500
                  }}>
                    {kpi.change}
                  </Typography>
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Main Content Tabs - Modern Light Style */}
      <Paper sx={{ 
        width: '100%',
        background: '#ffffff',
        borderRadius: 2,
        overflow: 'hidden',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
      }}>
        <Box sx={{
          borderBottom: '1px solid #e5e7eb',
          background: '#f9fafb'
        }}>
          <Tabs 
            value={activeTab} 
            onChange={(e, newValue) => setActiveTab(newValue)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              '& .MuiTabs-indicator': {
                backgroundColor: '#3b82f6',
                height: 3
              },
              '& .MuiTab-root': {
                color: '#6b7280',
                textTransform: 'none',
                fontSize: '0.875rem',
                fontWeight: 500,
                minHeight: 48,
                px: 2.5,
                '&:hover': {
                  color: '#374151',
                  background: 'rgba(0, 0, 0, 0.02)'
                },
                '&.Mui-selected': {
                  color: '#1f2937',
                  fontWeight: 600
                }
              },
              '& .MuiSvgIcon-root': {
                fontSize: '1.125rem',
                marginRight: 0.75
              }
            }}
          >
            <Tab label="Operations Overview" icon={<SpeedIcon />} iconPosition="start" />
            <Tab label="Customer 360°" icon={<PeopleIcon />} iconPosition="start" />
            <Tab label="Product Performance" icon={<InventoryIcon />} iconPosition="start" />
            <Tab label="Financial Analytics" icon={<AccountBalanceIcon />} iconPosition="start" />
            <Tab label="Recommendations" icon={<LightbulbIcon />} iconPosition="start" />
            <Tab label="Performance Insights" icon={<AssessmentIcon />} iconPosition="start" />
            <Tab label="Data Tables" icon={<BarChartIcon />} iconPosition="start" />
          </Tabs>
        </Box>

        <Box sx={{ p: 3 }}>
          {/* Operations Overview Tab */}
          {activeTab === 0 && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Customer Segment Distribution
                    </Typography>
                    {renderSegmentChart()}
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Revenue Trends by Segment
                    </Typography>
                    {renderRevenueTrends()}
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Top Customers
                    </Typography>
                    {renderTopCustomers()}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* Customer 360° Tab */}
          {activeTab === 1 && (
            <Grid container spacing={3}>
              {/* Customer Analytics Overview */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Customer Analytics Overview
                </Typography>
              </Grid>
              
              {/* Customer Segment Trends */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Customer Segment Evolution
                    </Typography>
                    {revenueData && revenueData.time_series && (
                      <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={revenueData.time_series.map(item => ({
                          month: item.month,
                          ...item.segments
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="month" />
                          <YAxis />
                          <Tooltip formatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                          <Legend />
                          {revenueData.time_series.length > 0 && Object.keys(revenueData.time_series[0].segments).map((segment) => (
                            <Area
                              key={segment}
                              type="monotone"
                              dataKey={segment}
                              stackId="1"
                              stroke={chartColors.segmentColors[segment] || '#666'}
                              fill={chartColors.segmentColors[segment] || '#666'}
                              name={segment}
                            />
                          ))}
                        </AreaChart>
                      </ResponsiveContainer>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              {/* Customer Lifetime Value Distribution */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Customer Lifetime Value Distribution
                    </Typography>
                    {segmentData && (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={segmentData.segments}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="segment" angle={-45} textAnchor="end" height={80} />
                          <YAxis />
                          <Tooltip formatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                          <Bar dataKey="avg_revenue" fill={chartColors.primary} name="Avg Revenue">
                            {segmentData.segments.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={chartColors.segmentColors[entry.segment] || '#666'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              {/* Top Customers by Segment - Clickable for drill down */}
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Top Customers by Segment (Click to drill down)
                    </Typography>
                    {dashboardData && (
                      <TableContainer sx={{ maxHeight: 400 }}>
                        <Table stickyHeader size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Customer ID</TableCell>
                              <TableCell>Segment</TableCell>
                              <TableCell align="right">Revenue</TableCell>
                              <TableCell align="right">Orders</TableCell>
                              <TableCell align="right">Recency</TableCell>
                              <TableCell align="right">CLV</TableCell>
                              <TableCell>ABC Class</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {dashboardData.top_customers.map((customer) => (
                              <TableRow 
                                key={customer.customer}
                                hover
                                onClick={() => loadCustomerData(customer.customer)}
                                sx={{ cursor: 'pointer' }}
                              >
                                <TableCell>{customer.customer}</TableCell>
                                <TableCell>
                                  <Chip 
                                    label={customer.segment}
                                    size="small"
                                    sx={{ 
                                      bgcolor: chartColors.segmentColors[customer.segment] || '#666',
                                      color: 'white'
                                    }}
                                  />
                                </TableCell>
                                <TableCell align="right">${(parseFloat(customer.revenue) / 1000).toFixed(0)}k</TableCell>
                                <TableCell align="right">{customer.frequency}</TableCell>
                                <TableCell align="right">{customer.recency} days</TableCell>
                                <TableCell align="right">${(parseFloat(customer.revenue) / 1000).toFixed(0)}k</TableCell>
                                <TableCell>{customer.abc_class}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              {/* Cohort Retention Analysis */}
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6">
                        Cohort Retention Analysis
                      </Typography>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<LightbulbIcon />}
                        onClick={loadCohortInsights}
                        disabled={loadingInsights}
                      >
                        {loadingInsights ? 'Analyzing...' : 'Get AI Insights'}
                      </Button>
                    </Box>
                    
                    {/* Cohort Summary Cards */}
                    {cohortRetentionData && cohortRetentionData.records && (
                      <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={12} md={3}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="subtitle2" color="textSecondary">
                                Latest Cohort Size
                              </Typography>
                              <Typography variant="h4">
                                {cohortRetentionData.records[cohortRetentionData.records.length - 1]?.size || 0}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                New customers this month
                              </Typography>
                            </CardContent>
                          </Card>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="subtitle2" color="textSecondary">
                                Average 3-Month Retention
                              </Typography>
                              <Typography variant="h4">
                                {(() => {
                                  const validRetentions = cohortRetentionData.records
                                    .filter(c => c.retention.month_3)
                                    .map(c => c.retention.month_3 * 100);
                                  return validRetentions.length > 0 
                                    ? (validRetentions.reduce((a, b) => a + b, 0) / validRetentions.length).toFixed(0) 
                                    : 0;
                                })()}%
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                Across all cohorts
                              </Typography>
                            </CardContent>
                          </Card>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="subtitle2" color="textSecondary">
                                Best Performing Cohort
                              </Typography>
                              <Typography variant="h5">
                                {(() => {
                                  const bestCohort = cohortRetentionData.records
                                    .filter(c => c.retention.month_3)
                                    .sort((a, b) => (b.retention.month_3 || 0) - (a.retention.month_3 || 0))[0];
                                  return bestCohort ? bestCohort.cohort : 'N/A';
                                })()}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                Highest 3-month retention
                              </Typography>
                            </CardContent>
                          </Card>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="subtitle2" color="textSecondary">
                                Retention Trend
                              </Typography>
                              <Typography variant="h4" color={
                                (() => {
                                  const recent = cohortRetentionData.records.slice(-3);
                                  const older = cohortRetentionData.records.slice(-6, -3);
                                  const recentAvg = recent.reduce((sum, c) => sum + (c.retention.month_1 || 0), 0) / recent.length;
                                  const olderAvg = older.reduce((sum, c) => sum + (c.retention.month_1 || 0), 0) / older.length;
                                  return recentAvg > olderAvg ? 'success.main' : 'error.main';
                                })()
                              }>
                                {(() => {
                                  const recent = cohortRetentionData.records.slice(-3);
                                  const older = cohortRetentionData.records.slice(-6, -3);
                                  const recentAvg = recent.reduce((sum, c) => sum + (c.retention.month_1 || 0), 0) / recent.length;
                                  const olderAvg = older.reduce((sum, c) => sum + (c.retention.month_1 || 0), 0) / older.length;
                                  return recentAvg > olderAvg ? '↑' : '↓';
                                })()}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                vs previous 3 months
                              </Typography>
                            </CardContent>
                          </Card>
                        </Grid>
                      </Grid>
                    )}
                    
                    {cohortRetentionData && cohortRetentionData.records && (
                      <Box sx={{ overflowX: 'auto' }}>
                        <Box sx={{ minWidth: 1200, mb: 2 }}>
                          {/* Retention Heatmap */}
                          <Box sx={{ mb: 4 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Customer Retention by Cohort (%)
                            </Typography>
                            <Grid container spacing={0.5}>
                              {/* Header row */}
                              <Grid item xs={2}>
                                <Box sx={{ p: 1, fontWeight: 'bold' }}>Cohort</Box>
                              </Grid>
                              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => (
                                <Grid item xs={0.75} key={`header-${month}`}>
                                  <Box sx={{ p: 1, textAlign: 'center', fontSize: '0.875rem' }}>
                                    M{month}
                                  </Box>
                                </Grid>
                              ))}
                              
                              {/* Data rows */}
                              {cohortRetentionData.records.map((cohort) => (
                                <React.Fragment key={cohort.cohort}>
                                  <Grid item xs={2}>
                                    <Box sx={{ p: 1, fontWeight: 'medium' }}>
                                      {cohort.cohort} ({cohort.size})
                                    </Box>
                                  </Grid>
                                  {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => {
                                    const retention = cohort.retention[`month_${month}`];
                                    const hasValue = retention !== undefined && retention !== null;
                                    const retentionPct = hasValue ? retention * 100 : 0;
                                    const opacity = hasValue ? Math.max(0.2, retentionPct / 100) : 0;
                                    
                                    return (
                                      <Grid item xs={0.75} key={`${cohort.cohort}-${month}`}>
                                        <Box
                                          sx={{
                                            p: 1,
                                            textAlign: 'center',
                                            backgroundColor: hasValue ? `rgba(33, 150, 243, ${opacity})` : '#f5f5f5',
                                            color: hasValue && retentionPct > 50 ? 'white' : 'inherit',
                                            fontSize: '0.75rem',
                                            fontWeight: hasValue ? 'medium' : 'normal',
                                            borderRadius: 0.5,
                                          }}
                                        >
                                          {hasValue ? `${retentionPct.toFixed(0)}%` : '-'}
                                        </Box>
                                      </Grid>
                                    );
                                  })}
                                </React.Fragment>
                              ))}
                            </Grid>
                          </Box>
                          
                          {/* Cohort Revenue Evolution */}
                          {cohortRevenueData && cohortRevenueData.records && (
                            <Box>
                              <Typography variant="subtitle2" gutterBottom>
                                Average Revenue per Customer by Cohort Evolution
                              </Typography>
                              <ResponsiveContainer width="100%" height={300}>
                                <LineChart>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis 
                                    dataKey="month"
                                    type="category"
                                    allowDuplicatedCategory={false}
                                    domain={[0, 11]}
                                    ticks={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
                                    tickFormatter={(value) => `M${value}`}
                                  />
                                  <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                                  <RechartsTooltip 
                                    formatter={(value) => `$${value.toFixed(2)}`}
                                    labelFormatter={(label) => `Month ${label}`}
                                  />
                                  <Legend />
                                  {cohortRevenueData.records.slice(0, 5).map((cohort, index) => {
                                    const data = Object.entries(cohort.revenue_evolution)
                                      .map(([key, value]) => ({
                                        month: parseInt(key.replace('month_', '')),
                                        value: value
                                      }))
                                      .sort((a, b) => a.month - b.month);
                                    
                                    return (
                                      <Line
                                        key={cohort.cohort}
                                        type="monotone"
                                        data={data}
                                        dataKey="value"
                                        name={cohort.cohort}
                                        stroke={[
                                          COLORS.primary,
                                          COLORS.secondary,
                                          COLORS.success,
                                          COLORS.warning,
                                          COLORS.info
                                        ][index % 5]}
                                        strokeWidth={2}
                                        dot={{ r: 3 }}
                                      />
                                    );
                                  })}
                                </LineChart>
                              </ResponsiveContainer>
                            </Box>
                          )}
                        </Box>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              {/* Customer Detail Modal/Drawer - shown when a customer is selected */}
              {customerData && (
                <Dialog
                  open={Boolean(customerData)}
                  onClose={() => setCustomerData(null)}
                  maxWidth="lg"
                  fullWidth
                >
                  <DialogTitle>
                    Customer Details: {customerData.customer.customer}
                    <IconButton
                      onClick={() => setCustomerData(null)}
                      sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                      <CloseIcon />
                    </IconButton>
                  </DialogTitle>
                  <DialogContent>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={4}>
                        <Card>
                          <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Customer Profile
                        </Typography>
                        <Stack spacing={2}>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">Customer ID</Typography>
                            <Typography variant="h5">{customerData.customer.customer}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">RFM Segment</Typography>
                            <Chip 
                              label={customerData.customer.rfm_segment}
                              color="primary"
                              sx={{ 
                                bgcolor: chartColors.segmentColors[customerData.customer.rfm_segment] || '#666',
                                color: 'white'
                              }}
                            />
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">ABC Class</Typography>
                            <Typography>{customerData.customer.abc_combined}</Typography>
                          </Box>
                          <Divider />
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">Lifetime Revenue</Typography>
                            <Typography variant="h6">${customerData.customer.formatted_revenue}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">Total Orders</Typography>
                            <Typography variant="h6">{customerData.customer.frequency}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">Days Since Last Order</Typography>
                            <Typography variant="h6">{customerData.customer.recency}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">Average Order Value</Typography>
                            <Typography variant="h6">${customerData.customer.avg_order_value}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="textSecondary">Margin %</Typography>
                            <Typography variant="h6">{customerData.customer.formatted_margin_pct}%</Typography>
                          </Box>
                        </Stack>
                          </CardContent>
                        </Card>
                      </Grid>
                  
                  {/* Product Preferences */}
                  <Grid item xs={12} md={4}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Top Products Purchased
                        </Typography>
                        <ResponsiveContainer width="100%" height={300}>
                          <BarChart data={customerData.product_preferences.slice(0, 10)}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="product" angle={-45} textAnchor="end" height={80} />
                            <YAxis />
                            <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                            <Bar dataKey="total_revenue" fill={chartColors.primary} />
                          </BarChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  {/* Purchase History Chart */}
                  <Grid item xs={12} md={4}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Purchase History Trend
                        </Typography>
                        <ResponsiveContainer width="100%" height={300}>
                          <LineChart 
                            data={customerData.purchase_history.reduce((acc, order) => {
                              const month = order.year_month;
                              const existing = acc.find(item => item.month === month);
                              if (existing) {
                                existing.revenue += order.revenue;
                                existing.orders += 1;
                              } else {
                                acc.push({ month, revenue: order.revenue, orders: 1 });
                              }
                              return acc;
                            }, []).reverse()}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis />
                            <Tooltip />
                            <Line type="monotone" dataKey="revenue" stroke={chartColors.primary} />
                          </LineChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  {/* Recent Orders Table */}
                  <Grid item xs={12}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Recent Orders
                        </Typography>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Order Number</TableCell>
                                <TableCell>Date</TableCell>
                                <TableCell>Product</TableCell>
                                <TableCell align="right">Quantity</TableCell>
                                <TableCell align="right">Revenue</TableCell>
                                <TableCell align="right">Margin</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {customerData.purchase_history.slice(0, 10).map((order) => (
                                <TableRow key={order.order_number}>
                                  <TableCell>{order.order_number}</TableCell>
                                  <TableCell>{new Date(order.posting_date).toLocaleDateString()}</TableCell>
                                  <TableCell>{order.product}</TableCell>
                                  <TableCell align="right">{order.quantity}</TableCell>
                                  <TableCell align="right">${order.revenue}</TableCell>
                                  <TableCell align="right">${order.margin}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </DialogContent>
            </Dialog>
          )}
          
          {/* Cohort AI Insights Dialog */}
          {cohortInsights && (
            <Dialog
              open={Boolean(cohortInsights)}
              onClose={() => setCohortInsights(null)}
              maxWidth="lg"
              fullWidth
            >
              <DialogTitle>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LightbulbIcon color="primary" />
                  <Typography variant="h6">AI-Powered Cohort Analysis Insights</Typography>
                </Box>
                <IconButton
                  onClick={() => setCohortInsights(null)}
                  sx={{ position: 'absolute', right: 8, top: 8 }}
                >
                  <CloseIcon />
                </IconButton>
              </DialogTitle>
              <DialogContent>
                <Stack spacing={3}>
                  {/* Executive Summary */}
                  <Card variant="outlined" sx={{ bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AssessmentIcon /> Executive Summary
                      </Typography>
                      <Typography variant="body1">
                        {cohortInsights.insights.executive_summary}
                      </Typography>
                    </CardContent>
                  </Card>
                  
                  {/* Key Findings */}
                  <Box>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TrendingUpIcon /> Key Findings
                    </Typography>
                    <Grid container spacing={2}>
                      {cohortInsights.insights.key_findings?.map((finding, index) => (
                        <Grid item xs={12} md={6} key={index}>
                          <Card variant="outlined">
                            <CardContent>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                <Chip 
                                  label={finding.impact} 
                                  size="small"
                                  color={
                                    finding.impact === 'high' ? 'error' : 
                                    finding.impact === 'medium' ? 'warning' : 'success'
                                  }
                                />
                                {finding.metric && (
                                  <Typography variant="h6" color="primary">
                                    {finding.metric}
                                  </Typography>
                                )}
                              </Box>
                              <Typography variant="body2">
                                {finding.finding}
                              </Typography>
                            </CardContent>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                  
                  {/* Retention & Revenue Analysis */}
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <GroupIcon /> Retention Analysis
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" color="textSecondary">Overall Health</Typography>
                            <Chip 
                              label={cohortInsights.insights.retention_analysis?.overall_health || 'Unknown'}
                              color={
                                cohortInsights.insights.retention_analysis?.overall_health === 'strong' ? 'success' :
                                cohortInsights.insights.retention_analysis?.overall_health === 'moderate' ? 'warning' : 'error'
                              }
                            />
                          </Box>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" color="textSecondary">Trend</Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {cohortInsights.insights.retention_analysis?.trend === 'improving' ? <TrendingUpIcon color="success" /> :
                               cohortInsights.insights.retention_analysis?.trend === 'declining' ? <TrendingDownIcon color="error" /> :
                               <ShowChartIcon color="action" />}
                              <Typography variant="body1">
                                {cohortInsights.insights.retention_analysis?.trend || 'Unknown'}
                              </Typography>
                            </Box>
                          </Box>
                          <Typography variant="body2" color="textSecondary">
                            {cohortInsights.insights.retention_analysis?.details}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <AttachMoneyIcon /> Revenue Analysis
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" color="textSecondary">Revenue Trend</Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {cohortInsights.insights.revenue_analysis?.trend === 'growing' ? <TrendingUpIcon color="success" /> :
                               cohortInsights.insights.revenue_analysis?.trend === 'declining' ? <TrendingDownIcon color="error" /> :
                               <ShowChartIcon color="action" />}
                              <Typography variant="body1">
                                {cohortInsights.insights.revenue_analysis?.trend || 'Unknown'}
                              </Typography>
                            </Box>
                          </Box>
                          <Typography variant="body2" paragraph>
                            {cohortInsights.insights.revenue_analysis?.key_insight}
                          </Typography>
                          {cohortInsights.insights.revenue_analysis?.ltv_projection && (
                            <Alert severity="info" icon={<InfoIcon />}>
                              <AlertTitle>LTV Projection</AlertTitle>
                              {cohortInsights.insights.revenue_analysis.ltv_projection}
                            </Alert>
                          )}
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                  
                  {/* Risk Factors */}
                  {cohortInsights.insights.risk_factors?.length > 0 && (
                    <Box>
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <WarningIcon color="warning" /> Risk Factors
                      </Typography>
                      <Grid container spacing={2}>
                        {cohortInsights.insights.risk_factors.map((risk, index) => (
                          <Grid item xs={12} key={index}>
                            <Alert 
                              severity={
                                risk.severity === 'high' ? 'error' :
                                risk.severity === 'medium' ? 'warning' : 'info'
                              }
                            >
                              <AlertTitle>{risk.risk}</AlertTitle>
                              {risk.affected_cohorts?.length > 0 && (
                                <Typography variant="caption" display="block">
                                  Affected cohorts: {risk.affected_cohorts.join(', ')}
                                </Typography>
                              )}
                            </Alert>
                          </Grid>
                        ))}
                      </Grid>
                    </Box>
                  )}
                  
                  {/* Recommendations */}
                  {cohortInsights.insights.recommendations?.length > 0 && (
                    <Box>
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CheckCircleIcon color="success" /> Recommendations
                      </Typography>
                      <TableContainer component={Paper} variant="outlined">
                        <Table>
                          <TableHead>
                            <TableRow>
                              <TableCell>Action</TableCell>
                              <TableCell>Priority</TableCell>
                              <TableCell>Expected Impact</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {cohortInsights.insights.recommendations.map((rec, index) => (
                              <TableRow key={index}>
                                <TableCell>{rec.action}</TableCell>
                                <TableCell>
                                  <Chip 
                                    label={rec.priority} 
                                    size="small"
                                    color={
                                      rec.priority === 'high' ? 'error' :
                                      rec.priority === 'medium' ? 'warning' : 'default'
                                    }
                                  />
                                </TableCell>
                                <TableCell>{rec.expected_impact}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  )}
                  
                  {/* Notable Cohorts */}
                  {cohortInsights.insights.notable_cohorts && (
                    <Box>
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TimelineIcon /> Notable Cohorts
                      </Typography>
                      <Grid container spacing={2}>
                        {cohortInsights.insights.notable_cohorts.best_performing && (
                          <Grid item xs={12} md={4}>
                            <Card sx={{ bgcolor: 'success.light' }}>
                              <CardContent>
                                <Typography variant="subtitle1" gutterBottom>
                                  <ThumbUpIcon /> Best Performing
                                </Typography>
                                <Typography variant="h6">
                                  {cohortInsights.insights.notable_cohorts.best_performing.cohort}
                                </Typography>
                                <Typography variant="body2">
                                  {cohortInsights.insights.notable_cohorts.best_performing.reason}
                                </Typography>
                              </CardContent>
                            </Card>
                          </Grid>
                        )}
                        {cohortInsights.insights.notable_cohorts.worst_performing && (
                          <Grid item xs={12} md={4}>
                            <Card sx={{ bgcolor: 'error.light' }}>
                              <CardContent>
                                <Typography variant="subtitle1" gutterBottom>
                                  <ErrorIcon /> Needs Attention
                                </Typography>
                                <Typography variant="h6">
                                  {cohortInsights.insights.notable_cohorts.worst_performing.cohort}
                                </Typography>
                                <Typography variant="body2">
                                  {cohortInsights.insights.notable_cohorts.worst_performing.reason}
                                </Typography>
                              </CardContent>
                            </Card>
                          </Grid>
                        )}
                        {cohortInsights.insights.notable_cohorts.most_improved && (
                          <Grid item xs={12} md={4}>
                            <Card sx={{ bgcolor: 'info.light' }}>
                              <CardContent>
                                <Typography variant="subtitle1" gutterBottom>
                                  <TrendingUpIcon /> Most Improved
                                </Typography>
                                <Typography variant="h6">
                                  {cohortInsights.insights.notable_cohorts.most_improved.cohort}
                                </Typography>
                                <Typography variant="body2">
                                  {cohortInsights.insights.notable_cohorts.most_improved.reason}
                                </Typography>
                              </CardContent>
                            </Card>
                          </Grid>
                        )}
                      </Grid>
                    </Box>
                  )}
                  
                  {/* Generated Timestamp */}
                  <Box sx={{ textAlign: 'center', mt: 2 }}>
                    <Typography variant="caption" color="textSecondary">
                      Analysis generated at: {cohortInsights.generated_at} | 
                      Analyzed {cohortInsights.cohort_count} cohorts from {cohortInsights.date_range}
                    </Typography>
                  </Box>
                </Stack>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setCohortInsights(null)}>Close</Button>
              </DialogActions>
            </Dialog>
          )}
        </Grid>
      )}

      {/* Product Performance Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
              {loading ? (
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                </Grid>
              ) : productMetrics ? (
                <>
                  {/* Product Performance Overview */}
                  <Grid item xs={12}>
                    <Typography variant="h5" gutterBottom>
                      Product Performance Trends
                    </Typography>
                  </Grid>

                  {/* Summary Cards */}
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Total Products
                        </Typography>
                        <Typography variant="h4">
                          {productMetrics.summary.total_products}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Total Revenue
                        </Typography>
                        <Typography variant="h4">
                          ${(parseFloat(productMetrics.summary.total_revenue) / 1000000).toFixed(1)}M
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Total Margin
                        </Typography>
                        <Typography variant="h4">
                          ${(parseFloat(productMetrics.summary.total_margin) / 1000000).toFixed(1)}M
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Avg Margin %
                        </Typography>
                        <Typography variant="h4">
                          {productMetrics.summary.avg_margin_percent}%
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  {/* Product Revenue Trends */}
                  <Grid item xs={12} md={8}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Top 10 Products Revenue Trend
                        </Typography>
                        <ResponsiveContainer width="100%" height={400}>
                          <LineChart data={generateProductTrendData()}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            {productMetrics.products.slice(0, 5).map((product, index) => (
                              <Line 
                                key={product.product}
                                type="monotone" 
                                dataKey={product.product} 
                                stroke={[
                                  chartColors.primary,
                                  chartColors.revenue,
                                  chartColors.secondary,
                                  '#ff7300',
                                  '#00bcd4'
                                ][index]}
                                strokeWidth={2}
                              />
                            ))}
                          </LineChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  {/* Product Category Performance */}
                  <Grid item xs={12} md={4}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Product Margin Distribution
                        </Typography>
                        <ResponsiveContainer width="100%" height={300}>
                          <PieChart>
                            <Pie
                              data={[
                                { name: 'High Margin (>30%)', value: productMetrics.products.filter(p => p.margin_percent > 30).length },
                                { name: 'Medium Margin (15-30%)', value: productMetrics.products.filter(p => p.margin_percent >= 15 && p.margin_percent <= 30).length },
                                { name: 'Low Margin (<15%)', value: productMetrics.products.filter(p => p.margin_percent < 15).length }
                              ]}
                              cx="50%"
                              cy="50%"
                              outerRadius={80}
                              fill="#8884d8"
                              dataKey="value"
                            >
                              {[
                                { name: 'High Margin (>30%)', value: productMetrics.products.filter(p => p.margin_percent > 30).length },
                                { name: 'Medium Margin (15-30%)', value: productMetrics.products.filter(p => p.margin_percent >= 15 && p.margin_percent <= 30).length },
                                { name: 'Low Margin (<15%)', value: productMetrics.products.filter(p => p.margin_percent < 15).length }
                              ].map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={[chartColors.primary, chartColors.revenue, chartColors.secondary][index]} />
                              ))}
                            </Pie>
                            <Tooltip />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                  </Grid>

                  {/* Top Products Table with Drill-down */}
                  <Grid item xs={12}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Top Products by Revenue
                        </Typography>
                        <Typography variant="body2" color="textSecondary" gutterBottom>
                          Click on any product to view detailed analytics
                        </Typography>
                        <TableContainer sx={{ maxHeight: 400 }}>
                          <Table stickyHeader size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Product</TableCell>
                                <TableCell align="right">Customers</TableCell>
                                <TableCell align="right">Orders</TableCell>
                                <TableCell align="right">Revenue</TableCell>
                                <TableCell align="right">Margin</TableCell>
                                <TableCell align="right">Margin %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {productMetrics.products.slice(0, 20).map((product) => (
                                <TableRow 
                                  key={product.product}
                                  hover
                                  onClick={() => loadProductDetails(product.product)}
                                  sx={{ cursor: 'pointer' }}
                                >
                                  <TableCell>{product.product}</TableCell>
                                  <TableCell align="right">{product.customer_count}</TableCell>
                                  <TableCell align="right">{product.order_count}</TableCell>
                                  <TableCell align="right">${parseFloat(product.total_revenue).toFixed(0)}</TableCell>
                                  <TableCell align="right">${parseFloat(product.total_margin).toFixed(0)}</TableCell>
                                  <TableCell align="right">{product.margin_percent}%</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  {/* Product-Customer Matrix Heatmap */}
                  {productMatrixData && productMatrixData.matrix && (
                    <Grid item xs={12}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Product-Customer Segment Matrix
                          </Typography>
                          <Typography variant="body2" color="textSecondary" gutterBottom>
                            Revenue distribution across products and customer segments
                          </Typography>
                          
                          <Box sx={{ overflowX: 'auto' }}>
                            <Box sx={{ minWidth: 800 }}>
                              {/* Matrix Headers */}
                              <Grid container spacing={0.5}>
                                <Grid item xs={3}>
                                  <Box sx={{ p: 1, fontWeight: 'bold' }}>Product</Box>
                                </Grid>
                                {productMatrixData.segments.map(segment => (
                                  <Grid item xs={9 / productMatrixData.segments.length} key={segment}>
                                    <Box sx={{ 
                                      p: 1, 
                                      textAlign: 'center', 
                                      fontSize: '0.75rem',
                                      fontWeight: 'bold',
                                      backgroundColor: COLORS.segmentColors[segment] || '#666',
                                      color: 'white',
                                      borderRadius: '4px 4px 0 0'
                                    }}>
                                      {segment}
                                    </Box>
                                  </Grid>
                                ))}
                              </Grid>
                              
                              {/* Matrix Data */}
                              {Object.entries(productMatrixData.matrix).slice(0, 15).map(([product, segmentData]) => {
                                const maxRevenue = Math.max(
                                  ...Object.values(segmentData).map(d => d.revenue || 0)
                                );
                                
                                return (
                                  <Grid container spacing={0.5} key={product}>
                                    <Grid item xs={3}>
                                      <Box sx={{ 
                                        p: 1, 
                                        fontSize: '0.75rem',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}>
                                        {product}
                                      </Box>
                                    </Grid>
                                    {productMatrixData.segments.map(segment => {
                                      const cellData = segmentData[segment] || { revenue: 0, customers: 0 };
                                      const intensity = maxRevenue > 0 ? cellData.revenue / maxRevenue : 0;
                                      const backgroundColor = cellData.revenue > 0 
                                        ? `rgba(76, 175, 80, ${Math.max(0.1, intensity)})`
                                        : '#f5f5f5';
                                      
                                      return (
                                        <Grid item xs={9 / productMatrixData.segments.length} key={segment}>
                                          <Tooltip
                                            title={
                                              <Box>
                                                <Typography variant="caption" display="block">
                                                  {product} - {segment}
                                                </Typography>
                                                <Typography variant="caption" display="block">
                                                  Revenue: ${cellData.revenue.toFixed(0)}
                                                </Typography>
                                                <Typography variant="caption" display="block">
                                                  Customers: {cellData.customers}
                                                </Typography>
                                                <Typography variant="caption" display="block">
                                                  Margin: {cellData.margin_percent?.toFixed(1)}%
                                                </Typography>
                                              </Box>
                                            }
                                            arrow
                                          >
                                            <Box sx={{
                                              p: 1,
                                              textAlign: 'center',
                                              backgroundColor,
                                              color: intensity > 0.6 ? 'white' : 'inherit',
                                              fontSize: '0.7rem',
                                              fontWeight: cellData.revenue > 0 ? 'medium' : 'normal',
                                              borderRadius: 0.5,
                                              cursor: 'pointer',
                                              transition: 'all 0.2s',
                                              '&:hover': {
                                                transform: 'scale(1.05)',
                                                boxShadow: 1
                                              }
                                            }}>
                                              {cellData.revenue > 0 
                                                ? `$${(cellData.revenue / 1000).toFixed(0)}k`
                                                : '-'
                                              }
                                            </Box>
                                          </Tooltip>
                                        </Grid>
                                      );
                                    })}
                                  </Grid>
                                );
                              })}
                              
                              {/* Legend */}
                              <Box sx={{ mt: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Typography variant="caption">Revenue Intensity:</Typography>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Box sx={{ width: 20, height: 20, backgroundColor: '#f5f5f5', border: '1px solid #ddd' }} />
                                  <Typography variant="caption">No Sales</Typography>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Box sx={{ width: 20, height: 20, backgroundColor: 'rgba(76, 175, 80, 0.3)' }} />
                                  <Typography variant="caption">Low</Typography>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Box sx={{ width: 20, height: 20, backgroundColor: 'rgba(76, 175, 80, 0.6)' }} />
                                  <Typography variant="caption">Medium</Typography>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Box sx={{ width: 20, height: 20, backgroundColor: 'rgba(76, 175, 80, 1)' }} />
                                  <Typography variant="caption">High</Typography>
                                </Box>
                              </Box>
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                </>
              ) : null}
              
              {/* Product Detail Modal - shown when a product is selected from the table */}
              {productDetailOpen && selectedProduct && (
                <Dialog
                  open={productDetailOpen}
                  onClose={() => {
                    setProductDetailOpen(false);
                    setSelectedProduct(null);
                    setProductSegmentData(null);
                    setProductTrendData(null);
                  }}
                  maxWidth="lg"
                  fullWidth
                >
                  <DialogTitle>
                    Product Details: {selectedProduct}
                    <IconButton
                      onClick={() => {
                        setProductDetailOpen(false);
                        setSelectedProduct(null);
                        setProductSegmentData(null);
                        setProductTrendData(null);
                      }}
                      sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                      <CloseIcon />
                    </IconButton>
                  </DialogTitle>
                  <DialogContent>
                    <Grid container spacing={3}>
                      {/* Product Overview Card */}
                      <Grid item xs={12} md={4}>
                        <Card>
                          <CardContent>
                            <Typography variant="h6" gutterBottom>
                              Product Overview
                            </Typography>
                            <Stack spacing={2}>
                              <Box>
                                <Typography variant="subtitle2" color="textSecondary">Product ID</Typography>
                                <Typography variant="h5">{selectedProduct}</Typography>
                              </Box>
                              {productMetrics && (() => {
                                const product = productMetrics.products.find(p => p.product === selectedProduct);
                                if (!product) return null;
                                return (
                                  <>
                                    <Divider />
                                    <Box>
                                      <Typography variant="subtitle2" color="textSecondary">Total Revenue</Typography>
                                      <Typography variant="h6">${parseFloat(product.total_revenue).toFixed(0)}</Typography>
                                    </Box>
                                    <Box>
                                      <Typography variant="subtitle2" color="textSecondary">Total Margin</Typography>
                                      <Typography variant="h6">${parseFloat(product.total_margin).toFixed(0)}</Typography>
                                    </Box>
                                    <Box>
                                      <Typography variant="subtitle2" color="textSecondary">Margin %</Typography>
                                      <Typography variant="h6">{product.margin_percent}%</Typography>
                                    </Box>
                                    <Box>
                                      <Typography variant="subtitle2" color="textSecondary">Total Customers</Typography>
                                      <Typography variant="h6">{product.customer_count}</Typography>
                                    </Box>
                                    <Box>
                                      <Typography variant="subtitle2" color="textSecondary">Total Orders</Typography>
                                      <Typography variant="h6">{product.order_count}</Typography>
                                    </Box>
                                    <Box>
                                      <Typography variant="subtitle2" color="textSecondary">Avg Order Value</Typography>
                                      <Typography variant="h6">${parseFloat(product.avg_order_value).toFixed(2)}</Typography>
                                    </Box>
                                  </>
                                );
                              })()}
                            </Stack>
                          </CardContent>
                        </Card>
                      </Grid>
                      
                      {/* Performance by Customer Segment */}
                      {productSegmentData && (
                        <Grid item xs={12} md={4}>
                          <Card>
                            <CardContent>
                              <Typography variant="h6" gutterBottom>
                                Revenue by Customer Segment
                              </Typography>
                              <ResponsiveContainer width="100%" height={300}>
                                <PieChart>
                                  <Pie
                                    data={productSegmentData.segments}
                                    dataKey="revenue"
                                    nameKey="segment"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={80}
                                    label={(entry) => `${entry.segment}: $${(entry.revenue / 1000).toFixed(0)}k`}
                                  >
                                    {productSegmentData.segments.map((segment, index) => (
                                      <Cell key={segment.segment} fill={chartColors.segmentColors[segment.segment] || '#666'} />
                                    ))}
                                  </Pie>
                                  <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                                </PieChart>
                              </ResponsiveContainer>
                              <Box mt={2}>
                                <Typography variant="subtitle2" color="textSecondary">
                                  Total Customers: {productSegmentData.total_customers}
                                </Typography>
                                <Typography variant="subtitle2" color="textSecondary">
                                  Total Revenue: ${(productSegmentData.total_revenue / 1000).toFixed(0)}k
                                </Typography>
                              </Box>
                            </CardContent>
                          </Card>
                        </Grid>
                      )}
                      
                      {/* Sales Trend */}
                      {productTrendData && (
                        <Grid item xs={12} md={4}>
                          <Card>
                            <CardContent>
                              <Typography variant="h6" gutterBottom>
                                Sales Trend ({productTrendData.months} months)
                              </Typography>
                              <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={productTrendData.trends}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey="year_month" />
                                  <YAxis />
                                  <Tooltip formatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                                  <Legend />
                                  <Line 
                                    type="monotone" 
                                    dataKey="revenue" 
                                    stroke={chartColors.primary} 
                                    name="Revenue"
                                    strokeWidth={2}
                                  />
                                  <Line 
                                    type="monotone" 
                                    dataKey="margin" 
                                    stroke={chartColors.success} 
                                    name="Margin"
                                    strokeWidth={2}
                                  />
                                </LineChart>
                              </ResponsiveContainer>
                            </CardContent>
                          </Card>
                        </Grid>
                      )}
                      
                      {/* Segment Performance Details Table */}
                      {productSegmentData && (
                        <Grid item xs={12}>
                          <Card>
                            <CardContent>
                              <Typography variant="h6" gutterBottom>
                                Performance by Segment Details
                              </Typography>
                              <TableContainer>
                                <Table size="small">
                                  <TableHead>
                                    <TableRow>
                                      <TableCell>Segment</TableCell>
                                      <TableCell align="right">Customers</TableCell>
                                      <TableCell align="right">Revenue</TableCell>
                                      <TableCell align="right">Margin</TableCell>
                                      <TableCell align="right">Contribution %</TableCell>
                                    </TableRow>
                                  </TableHead>
                                  <TableBody>
                                    {productSegmentData.segments.map((segment) => (
                                      <TableRow key={segment.segment}>
                                        <TableCell>
                                          <Chip 
                                            label={segment.segment}
                                            size="small"
                                            sx={{ 
                                              bgcolor: chartColors.segmentColors[segment.segment] || '#666',
                                              color: 'white'
                                            }}
                                          />
                                        </TableCell>
                                        <TableCell align="right">{segment.customer_count}</TableCell>
                                        <TableCell align="right">${parseFloat(segment.revenue).toFixed(0)}</TableCell>
                                        <TableCell align="right">${parseFloat(segment.margin).toFixed(0)}</TableCell>
                                        <TableCell align="right">{parseFloat(segment.contribution_pct).toFixed(1)}%</TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </TableContainer>
                            </CardContent>
                          </Card>
                        </Grid>
                      )}
                      
                      {/* Recent Trends Summary */}
                      {productTrendData && productTrendData.trends.length > 0 && (
                        <Grid item xs={12}>
                          <Card>
                            <CardContent>
                              <Typography variant="h6" gutterBottom>
                                Recent Performance Summary
                              </Typography>
                              <Grid container spacing={2}>
                                {(() => {
                                  const latestMonth = productTrendData.trends[productTrendData.trends.length - 1];
                                  const previousMonth = productTrendData.trends[productTrendData.trends.length - 2];
                                  const revenueChange = previousMonth 
                                    ? ((latestMonth.revenue - previousMonth.revenue) / previousMonth.revenue * 100).toFixed(1)
                                    : 0;
                                  const marginChange = previousMonth
                                    ? ((latestMonth.margin - previousMonth.margin) / previousMonth.margin * 100).toFixed(1)
                                    : 0;
                                  
                                  return (
                                    <>
                                      <Grid item xs={12} md={3}>
                                        <Box>
                                          <Typography variant="subtitle2" color="textSecondary">
                                            Latest Month Revenue
                                          </Typography>
                                          <Typography variant="h6">
                                            ${(latestMonth.revenue / 1000).toFixed(0)}k
                                          </Typography>
                                          <Typography 
                                            variant="body2" 
                                            color={revenueChange >= 0 ? 'success.main' : 'error.main'}
                                          >
                                            {revenueChange >= 0 ? '+' : ''}{revenueChange}% vs prev month
                                          </Typography>
                                        </Box>
                                      </Grid>
                                      <Grid item xs={12} md={3}>
                                        <Box>
                                          <Typography variant="subtitle2" color="textSecondary">
                                            Latest Month Margin
                                          </Typography>
                                          <Typography variant="h6">
                                            ${(latestMonth.margin / 1000).toFixed(0)}k
                                          </Typography>
                                          <Typography 
                                            variant="body2" 
                                            color={marginChange >= 0 ? 'success.main' : 'error.main'}
                                          >
                                            {marginChange >= 0 ? '+' : ''}{marginChange}% vs prev month
                                          </Typography>
                                        </Box>
                                      </Grid>
                                      <Grid item xs={12} md={3}>
                                        <Box>
                                          <Typography variant="subtitle2" color="textSecondary">
                                            Latest Month Customers
                                          </Typography>
                                          <Typography variant="h6">
                                            {latestMonth.customers}
                                          </Typography>
                                        </Box>
                                      </Grid>
                                      <Grid item xs={12} md={3}>
                                        <Box>
                                          <Typography variant="subtitle2" color="textSecondary">
                                            Latest Month Quantity
                                          </Typography>
                                          <Typography variant="h6">
                                            {latestMonth.quantity}
                                          </Typography>
                                        </Box>
                                      </Grid>
                                    </>
                                  );
                                })()}
                              </Grid>
                            </CardContent>
                          </Card>
                        </Grid>
                      )}
                    </Grid>
                  </DialogContent>
                </Dialog>
              )}
            </Grid>
          )}

          {/* Financial Analytics Tab */}
          {activeTab === 3 && (
            <Grid container spacing={3}>
              {loading ? (
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                </Grid>
              ) : financialSummary ? (
                <>
                  {/* Financial Trends Overview */}
                  <Grid item xs={12}>
                    <Typography variant="h5" gutterBottom>
                      Financial Performance Trends
                    </Typography>
                  </Grid>
                  {/* Financial KPI Cards */}
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Total Revenue
                        </Typography>
                        <Typography variant="h4">
                          ${(financialSummary.total_revenue / 1000000).toFixed(1)}M
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Total Margin
                        </Typography>
                        <Typography variant="h4">
                          ${(financialSummary.total_margin / 1000000).toFixed(1)}M
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Total COGS
                        </Typography>
                        <Typography variant="h4">
                          ${(financialSummary.total_cogs / 1000000).toFixed(1)}M
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          Overall Margin %
                        </Typography>
                        <Typography variant="h4">
                          {financialSummary.overall_margin_pct}%
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  {/* Revenue & Margin Trends */}
                  {financialTrends && (
                    <Grid item xs={12} md={8}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Revenue & Margin Trends
                          </Typography>
                          <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={financialTrends.trends}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="year_month" />
                              <YAxis yAxisId="left" />
                              <YAxis yAxisId="right" orientation="right" />
                              <Tooltip formatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                              <Legend />
                              <Line 
                                yAxisId="left"
                                type="monotone" 
                                dataKey="revenue" 
                                stroke={chartColors.primary} 
                                name="Revenue"
                              />
                              <Line 
                                yAxisId="left"
                                type="monotone" 
                                dataKey="margin" 
                                stroke={chartColors.success} 
                                name="Margin"
                              />
                              <Line 
                                yAxisId="left"
                                type="monotone" 
                                dataKey="cogs" 
                                stroke={chartColors.warning} 
                                name="COGS"
                              />
                              <Line 
                                yAxisId="right"
                                type="monotone" 
                                dataKey="margin_pct" 
                                stroke={chartColors.secondary} 
                                name="Margin %"
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                  
                  {/* Profitability by Segment */}
                  {profitabilityData && (
                    <Grid item xs={12} md={4}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Profitability by Segment
                          </Typography>
                          <ResponsiveContainer width="100%" height={400}>
                            <BarChart 
                              data={profitabilityData.segments}
                              layout="horizontal"
                            >
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis type="number" />
                              <YAxis dataKey="segment" type="category" width={100} />
                              <Tooltip formatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                              <Bar dataKey="profit" fill={chartColors.success}>
                                {profitabilityData.segments.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={chartColors.segmentColors[entry.segment] || '#666'} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                  
                  {/* Segment Performance Table */}
                  {profitabilityData && (
                    <Grid item xs={12}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Segment Financial Performance
                          </Typography>
                          <TableContainer>
                            <Table>
                              <TableHead>
                                <TableRow>
                                  <TableCell>Segment</TableCell>
                                  <TableCell align="right">Customers</TableCell>
                                  <TableCell align="right">Revenue</TableCell>
                                  <TableCell align="right">Profit</TableCell>
                                  <TableCell align="right">Avg Margin %</TableCell>
                                  <TableCell align="right">Revenue Share %</TableCell>
                                  <TableCell align="right">Profit Share %</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {profitabilityData.segments.map((segment) => (
                                  <TableRow key={segment.segment}>
                                    <TableCell>
                                      <Chip 
                                        label={segment.segment}
                                        size="small"
                                        sx={{ 
                                          bgcolor: chartColors.segmentColors[segment.segment] || '#666',
                                          color: 'white'
                                        }}
                                      />
                                    </TableCell>
                                    <TableCell align="right">{segment.customer_count}</TableCell>
                                    <TableCell align="right">${(segment.revenue / 1000).toFixed(0)}k</TableCell>
                                    <TableCell align="right">${(segment.profit / 1000).toFixed(0)}k</TableCell>
                                    <TableCell align="right">{segment.avg_margin_pct}%</TableCell>
                                    <TableCell align="right">{segment.revenue_share}%</TableCell>
                                    <TableCell align="right">{segment.profit_share}%</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                  
                  {/* Month over Month Growth */}
                  {financialTrends && financialTrends.trends.length > 1 && (
                    <Grid item xs={12}>
                      <Card>
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Month-over-Month Growth
                          </Typography>
                          <ResponsiveContainer width="100%" height={300}>
                            <BarChart 
                              data={financialTrends.trends.slice(1).map((month, index) => {
                                const prevMonth = financialTrends.trends[index];
                                return {
                                  month: month.year_month,
                                  revenue_growth: ((month.revenue - prevMonth.revenue) / prevMonth.revenue * 100).toFixed(1),
                                  margin_growth: ((month.margin - prevMonth.margin) / prevMonth.margin * 100).toFixed(1),
                                };
                              })}
                            >
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="month" />
                              <YAxis />
                              <Tooltip formatter={(value) => `${value}%`} />
                              <Legend />
                              <Bar dataKey="revenue_growth" fill={chartColors.primary} name="Revenue Growth %" />
                              <Bar dataKey="margin_growth" fill={chartColors.success} name="Margin Growth %" />
                            </BarChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                </>
              ) : null}
            </Grid>
          )}

          {/* Recommendations Tab */}
          {activeTab === 4 && (
            <RecommendationsTab />
          )}

          {/* Performance Insights Tab */}
          {activeTab === 5 && (
            <PerformanceInsightsTab />
          )}
          
          {/* Data Tables Tab */}
          {activeTab === 6 && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                  <Typography variant="h5" gutterBottom>
                    Analytics Data Tables
                  </Typography>
                  <FormControl sx={{ minWidth: 300 }}>
                    <InputLabel id="table-select-label">Select Table</InputLabel>
                    <Select
                      labelId="table-select-label"
                      value={selectedTable}
                      onChange={(e) => handleTableChange(e.target.value)}
                      label="Select Table"
                    >
                      <MenuItem value="customer-master">Customer Master Analysis</MenuItem>
                      <MenuItem value="transactions">Transaction Data</MenuItem>
                      <MenuItem value="segmentation-performance">Segmentation Performance</MenuItem>
                      <MenuItem value="cohort-retention">Cohort Retention</MenuItem>
                      <MenuItem value="cohort-revenue">Cohort Revenue</MenuItem>
                      <MenuItem value="time-series">Time Series Performance</MenuItem>
                      <MenuItem value="product-matrix">Product-Customer Matrix</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                
                {/* Table Filters */}
                {selectedTable === 'customer-master' && (
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        label="Search Customer ID"
                        value={tableFilters.search || ''}
                        onChange={(e) => setTableFilters({...tableFilters, search: e.target.value})}
                        InputProps={{
                          endAdornment: (
                            <InputAdornment position="end">
                              <IconButton onClick={() => loadTableData(selectedTable, tableFilters)}>
                                <SearchIcon />
                              </IconButton>
                            </InputAdornment>
                          ),
                        }}
                      />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth>
                        <InputLabel>RFM Segment</InputLabel>
                        <Select
                          value={tableFilters.segment || ''}
                          onChange={(e) => setTableFilters({...tableFilters, segment: e.target.value})}
                          label="RFM Segment"
                        >
                          <MenuItem value="">All</MenuItem>
                          <MenuItem value="Champions">Champions</MenuItem>
                          <MenuItem value="Loyal Customers">Loyal Customers</MenuItem>
                          <MenuItem value="Potential Loyalists">Potential Loyalists</MenuItem>
                          <MenuItem value="New Customers">New Customers</MenuItem>
                          <MenuItem value="Promising">Promising</MenuItem>
                          <MenuItem value="Need Attention">Need Attention</MenuItem>
                          <MenuItem value="About to Sleep">About to Sleep</MenuItem>
                          <MenuItem value="At Risk">At Risk</MenuItem>
                          <MenuItem value="Lost">Lost</MenuItem>
                          <MenuItem value="Hibernating">Hibernating</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth>
                        <InputLabel>ABC Class</InputLabel>
                        <Select
                          value={tableFilters.abc_class || ''}
                          onChange={(e) => setTableFilters({...tableFilters, abc_class: e.target.value})}
                          label="ABC Class"
                        >
                          <MenuItem value="">All</MenuItem>
                          <MenuItem value="A+A">A+A</MenuItem>
                          <MenuItem value="A+B">A+B</MenuItem>
                          <MenuItem value="A+C">A+C</MenuItem>
                          <MenuItem value="B+A">B+A</MenuItem>
                          <MenuItem value="B+B">B+B</MenuItem>
                          <MenuItem value="B+C">B+C</MenuItem>
                          <MenuItem value="C+A">C+A</MenuItem>
                          <MenuItem value="C+B">C+B</MenuItem>
                          <MenuItem value="C+C">C+C</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                  </Grid>
                )}
                
                {/* Transaction Table Filters */}
                {selectedTable === 'transactions' && (
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={3}>
                      <TextField
                        fullWidth
                        label="Customer ID"
                        value={tableFilters.customer_id || ''}
                        onChange={(e) => setTableFilters({...tableFilters, customer_id: e.target.value})}
                      />
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <TextField
                        fullWidth
                        label="Product"
                        value={tableFilters.product || ''}
                        onChange={(e) => setTableFilters({...tableFilters, product: e.target.value})}
                      />
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <TextField
                        fullWidth
                        label="Start Date"
                        type="date"
                        value={tableFilters.start_date || ''}
                        onChange={(e) => setTableFilters({...tableFilters, start_date: e.target.value})}
                        InputLabelProps={{ shrink: true }}
                      />
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <TextField
                        fullWidth
                        label="End Date"
                        type="date"
                        value={tableFilters.end_date || ''}
                        onChange={(e) => setTableFilters({...tableFilters, end_date: e.target.value})}
                        InputLabelProps={{ shrink: true }}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <Button 
                        variant="contained" 
                        onClick={() => loadTableData(selectedTable, tableFilters)}
                        startIcon={<SearchIcon />}
                      >
                        Search Transactions
                      </Button>
                    </Grid>
                  </Grid>
                )}
                
                {/* Data Table Display */}
                <Card>
                  <CardContent>
                    {tableLoading ? (
                      <Box display="flex" justifyContent="center" p={4}>
                        <CircularProgress />
                      </Box>
                    ) : tableData ? (
                      <>
                        {/* Render different table structures based on selected table */}
                        {selectedTable === 'customer-master' && tableData.records && (
                          <>
                            <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                              Click on any row to view detailed customer information
                            </Typography>
                            <TableContainer sx={{ maxHeight: 600 }}>
                              <Table stickyHeader size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell>Customer ID</TableCell>
                                    <TableCell>RFM Segment</TableCell>
                                    <TableCell>ABC Class</TableCell>
                                    <TableCell align="right">Revenue</TableCell>
                                    <TableCell align="right">Frequency</TableCell>
                                    <TableCell align="right">Recency</TableCell>
                                    <TableCell align="right">Profitability</TableCell>
                                    <TableCell align="right">Margin %</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {tableData.records.map((row) => (
                                    <TableRow 
                                      key={row.customer} 
                                      hover
                                      onClick={() => {
                                        setActiveTab(1); // Switch to Customer 360 tab
                                        loadCustomerData(row.customer);
                                      }}
                                      sx={{ cursor: 'pointer' }}
                                    >
                                      <TableCell>{row.customer}</TableCell>
                                      <TableCell>
                                        <Chip 
                                          label={row.rfm_segment}
                                          size="small"
                                          sx={{ 
                                            bgcolor: COLORS.segmentColors[row.rfm_segment] || '#666',
                                            color: 'white'
                                          }}
                                        />
                                      </TableCell>
                                      <TableCell>{row.abc_combined}</TableCell>
                                      <TableCell align="right">${parseFloat(row.monetary).toFixed(0)}</TableCell>
                                      <TableCell align="right">{row.frequency}</TableCell>
                                      <TableCell align="right">{row.recency}</TableCell>
                                      <TableCell align="right">${parseFloat(row.profitability).toFixed(0)}</TableCell>
                                      <TableCell align="right">{parseFloat(row.margin_percentage).toFixed(1)}%</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                            <TablePagination
                              component="div"
                              count={tableData.total}
                              page={tablePagination.page}
                              onPageChange={handlePageChange}
                              rowsPerPage={tablePagination.rowsPerPage}
                              onRowsPerPageChange={handleRowsPerPageChange}
                              rowsPerPageOptions={[50, 100, 250, 500]}
                            />
                          </>
                        )}
                        
                        {selectedTable === 'segmentation-performance' && tableData.records && (
                          <TableContainer>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Segment</TableCell>
                                  <TableCell align="right">Customers</TableCell>
                                  <TableCell align="right">Total Revenue</TableCell>
                                  <TableCell align="right">Revenue/Customer</TableCell>
                                  <TableCell align="right">Total Profit</TableCell>
                                  <TableCell align="right">Profit/Customer</TableCell>
                                  <TableCell align="right">Avg Margin %</TableCell>
                                  <TableCell align="center">Actions</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {tableData.records.map((row) => (
                                  <TableRow key={row.segment} hover>
                                    <TableCell>
                                      <Chip 
                                        label={row.segment}
                                        size="small"
                                        sx={{ 
                                          bgcolor: COLORS.segmentColors[row.segment] || '#666',
                                          color: 'white'
                                        }}
                                      />
                                    </TableCell>
                                    <TableCell align="right">{row.customer_count}</TableCell>
                                    <TableCell align="right">${parseFloat(row.total_revenue).toFixed(0)}</TableCell>
                                    <TableCell align="right">${parseFloat(row.revenue_per_customer).toFixed(0)}</TableCell>
                                    <TableCell align="right">${parseFloat(row.total_profit).toFixed(0)}</TableCell>
                                    <TableCell align="right">${parseFloat(row.profit_per_customer).toFixed(0)}</TableCell>
                                    <TableCell align="right">{parseFloat(row.avg_margin_percent).toFixed(1)}%</TableCell>
                                    <TableCell align="center">
                                      <Button
                                        size="small"
                                        onClick={() => {
                                          setSelectedTable('customer-master');
                                          setTableFilters({ segment: row.segment });
                                          loadTableData('customer-master', { segment: row.segment });
                                        }}
                                      >
                                        View Customers
                                      </Button>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        )}
                        
                        {selectedTable === 'cohort-retention' && tableData.records && (
                          <TableContainer>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Cohort</TableCell>
                                  <TableCell align="right">Size</TableCell>
                                  {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => (
                                    <TableCell key={month} align="right">Month {month}</TableCell>
                                  ))}
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {tableData.records.map((row) => (
                                  <TableRow key={row.cohort}>
                                    <TableCell>{row.cohort}</TableCell>
                                    <TableCell align="right">{row.size}</TableCell>
                                    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => (
                                      <TableCell key={month} align="right">
                                        {row.retention[`month_${month}`] ? 
                                          `${(row.retention[`month_${month}`] * 100).toFixed(1)}%` : 
                                          '-'
                                        }
                                      </TableCell>
                                    ))}
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        )}
                        
                        {/* Cohort Revenue Table */}
                        {selectedTable === 'cohort-revenue' && tableData.records && (
                          <TableContainer>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Cohort</TableCell>
                                  {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => (
                                    <TableCell key={month} align="right">Month {month}</TableCell>
                                  ))}
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {tableData.records.map((row) => (
                                  <TableRow key={row.cohort}>
                                    <TableCell>{row.cohort}</TableCell>
                                    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => (
                                      <TableCell key={month} align="right">
                                        {row.revenue_evolution[`month_${month}`] ? 
                                          `$${parseFloat(row.revenue_evolution[`month_${month}`]).toFixed(0)}` : 
                                          '-'
                                        }
                                      </TableCell>
                                    ))}
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        )}
                        
                        {/* Time Series Performance Table */}
                        {selectedTable === 'time-series' && tableData.records && (
                          <TableContainer>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Month</TableCell>
                                  <TableCell>Segment</TableCell>
                                  <TableCell align="right">Customers</TableCell>
                                  <TableCell align="right">Revenue</TableCell>
                                  <TableCell align="right">COGS</TableCell>
                                  <TableCell align="right">Margin</TableCell>
                                  <TableCell align="right">Margin %</TableCell>
                                  <TableCell align="right">Orders</TableCell>
                                  <TableCell align="right">AOV</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {tableData.records.map((row, index) => (
                                  <TableRow key={index}>
                                    <TableCell>{row.year_month}</TableCell>
                                    <TableCell>
                                      <Chip 
                                        label={row.segment}
                                        size="small"
                                        sx={{ 
                                          bgcolor: COLORS.segmentColors[row.segment] || '#666',
                                          color: 'white'
                                        }}
                                      />
                                    </TableCell>
                                    <TableCell align="right">{row.customer_count}</TableCell>
                                    <TableCell align="right">${parseFloat(row.revenue).toFixed(0)}</TableCell>
                                    <TableCell align="right">${parseFloat(row.cogs).toFixed(0)}</TableCell>
                                    <TableCell align="right">${parseFloat(row.margin).toFixed(0)}</TableCell>
                                    <TableCell align="right">{parseFloat(row.margin_percentage).toFixed(1)}%</TableCell>
                                    <TableCell align="right">{row.order_count}</TableCell>
                                    <TableCell align="right">${parseFloat(row.avg_order_value).toFixed(0)}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        )}
                        
                        {/* Product-Customer Matrix Table */}
                        {selectedTable === 'product-matrix' && tableData.raw_data && (
                          <>
                            <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                              Click on any row to view detailed product performance
                            </Typography>
                            <TableContainer>
                              <Table size="small">
                                <TableHead>
                                <TableRow>
                                  <TableCell>Product</TableCell>
                                  <TableCell>Segment</TableCell>
                                  <TableCell align="right">Revenue</TableCell>
                                  <TableCell align="right">Orders</TableCell>
                                  <TableCell align="right">Customers</TableCell>
                                  <TableCell align="right">AOV</TableCell>
                                  <TableCell align="right">Margin</TableCell>
                                  <TableCell align="right">Margin %</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {tableData.raw_data.map((row, index) => (
                                  <TableRow 
                                    key={index}
                                    hover
                                    onClick={() => {
                                      setActiveTab(2); // Switch to Product Performance tab
                                      loadProductDetails(row.product);
                                    }}
                                    sx={{ cursor: 'pointer' }}
                                  >
                                    <TableCell>{row.product}</TableCell>
                                    <TableCell>
                                      <Chip 
                                        label={row.segment}
                                        size="small"
                                        sx={{ 
                                          bgcolor: COLORS.segmentColors[row.segment] || '#666',
                                          color: 'white'
                                        }}
                                      />
                                    </TableCell>
                                    <TableCell align="right">${parseFloat(row.revenue).toFixed(0)}</TableCell>
                                    <TableCell align="right">{row.orders}</TableCell>
                                    <TableCell align="right">{row.customers}</TableCell>
                                    <TableCell align="right">${parseFloat(row.avg_order_value).toFixed(0)}</TableCell>
                                    <TableCell align="right">${parseFloat(row.margin).toFixed(0)}</TableCell>
                                    <TableCell align="right">{parseFloat(row.margin_percent).toFixed(1)}%</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                          </>
                        )}
                        
                        {/* Transaction Data Table */}
                        {selectedTable === 'transactions' && tableData.records && (
                          <>
                            <TableContainer sx={{ maxHeight: 600 }}>
                              <Table stickyHeader size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell>Order Number</TableCell>
                                    <TableCell>Date</TableCell>
                                    <TableCell>Customer</TableCell>
                                    <TableCell>Product</TableCell>
                                    <TableCell align="right">Quantity</TableCell>
                                    <TableCell align="right">Revenue</TableCell>
                                    <TableCell align="right">COGS</TableCell>
                                    <TableCell align="right">Margin</TableCell>
                                    <TableCell>RFM Segment</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {tableData.records.map((row) => (
                                    <TableRow key={`${row.order_number}-${row.product}`} hover>
                                      <TableCell>{row.order_number}</TableCell>
                                      <TableCell>{new Date(row.posting_date).toLocaleDateString()}</TableCell>
                                      <TableCell>{row.customer}</TableCell>
                                      <TableCell>{row.product}</TableCell>
                                      <TableCell align="right">{row.quantity}</TableCell>
                                      <TableCell align="right">${parseFloat(row.revenue).toFixed(0)}</TableCell>
                                      <TableCell align="right">${parseFloat(row.cogs).toFixed(0)}</TableCell>
                                      <TableCell align="right">${parseFloat(row.margin).toFixed(0)}</TableCell>
                                      <TableCell>
                                        <Chip 
                                          label={row.rfm_segment}
                                          size="small"
                                          sx={{ 
                                            bgcolor: COLORS.segmentColors[row.rfm_segment] || '#666',
                                            color: 'white'
                                          }}
                                        />
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                            <TablePagination
                              component="div"
                              count={tableData.total}
                              page={tablePagination.page}
                              onPageChange={handlePageChange}
                              rowsPerPage={tablePagination.rowsPerPage}
                              onRowsPerPageChange={handleRowsPerPageChange}
                              rowsPerPageOptions={[50, 100, 250, 500]}
                            />
                          </>
                        )}
                        
                      </>
                    ) : (
                      <Typography variant="body1" color="textSecondary" align="center">
                        Select filters and click search to view data
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </Box>
      </Paper>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, title: '', message: '', onConfirm: null })}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">
          <Box display="flex" alignItems="center" gap={1}>
            <WarningIcon color="warning" />
            {confirmDialog.title}
          </Box>
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog({ open: false, title: '', message: '', onConfirm: null })}
            color="inherit"
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDialog.onConfirm}
            variant="contained"
            color="primary"
            autoFocus
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CoreAIDashboard;