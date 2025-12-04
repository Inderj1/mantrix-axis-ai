import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Alert,
  IconButton,
  Tooltip,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tabs,
  Tab,
  Skeleton,
  TextField,
  InputAdornment,
  Stack,
  Breadcrumbs,
  Link,
  CircularProgress,
  Snackbar,
  Backdrop,
  useTheme,
  alpha,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Info as InfoIcon,
  Lightbulb as LightbulbIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Close as CloseIcon,
  FileDownload as DownloadIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
  TableChart as CsvIcon,
  Dashboard as DashboardIcon,
  TableChart as TableIcon,
  AutoAwesome as InsightsIcon,
  Code as CodeIcon,
  Search as SearchIcon,
  ContentCopy as CopyIcon,
  Check as CopiedIcon,
  Schedule as TimeIcon,
  Storage as RowsIcon,
  AccessTime as UpdatedIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';
import EChartsVisualization from './EChartsVisualization';

// Loading skeleton component
const LoadingSkeleton = () => {
  const theme = useTheme();

  return (
    <Box sx={{ p: 3 }}>
      {/* Header skeleton */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Skeleton variant="circular" width={40} height={40} />
          <Box>
            <Skeleton variant="text" width={200} height={32} />
            <Skeleton variant="text" width={120} height={20} />
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Skeleton variant="rounded" width={100} height={36} />
          <Skeleton variant="rounded" width={36} height={36} />
        </Box>
      </Box>

      {/* Metrics skeleton */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[1, 2, 3, 4].map((i) => (
          <Grid item xs={6} md={3} key={i}>
            <Skeleton variant="rounded" height={100} sx={{ borderRadius: 2 }} />
          </Grid>
        ))}
      </Grid>

      {/* Tabs skeleton */}
      <Skeleton variant="rounded" width={400} height={48} sx={{ mb: 3, borderRadius: 2 }} />

      {/* Content skeleton - 60/40 split */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Skeleton variant="rounded" height={350} sx={{ borderRadius: 2, mb: 2 }} />
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Skeleton variant="rounded" height={220} sx={{ borderRadius: 2 }} />
            </Grid>
            <Grid item xs={6}>
              <Skeleton variant="rounded" height={220} sx={{ borderRadius: 2 }} />
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={12} md={5}>
          <Skeleton variant="rounded" height={580} sx={{ borderRadius: 2 }} />
        </Grid>
      </Grid>

      {/* Footer skeleton */}
      <Box sx={{ mt: 3, pt: 2, borderTop: `1px solid ${alpha(theme.palette.divider, 0.5)}` }}>
        <Skeleton variant="text" width={300} height={20} />
      </Box>
    </Box>
  );
};

// Metric card with glassmorphism effect
const MetricCard = ({ label, value, change, trend, theme }) => {
  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp sx={{ fontSize: 16, color: theme.palette.success.main }} />;
    if (trend === 'down') return <TrendingDown sx={{ fontSize: 16, color: theme.palette.error.main }} />;
    return <TrendingFlat sx={{ fontSize: 16, color: theme.palette.text.secondary }} />;
  };

  const getTrendColor = () => {
    if (trend === 'up') return theme.palette.success.main;
    if (trend === 'down') return theme.palette.error.main;
    return theme.palette.text.secondary;
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        height: '100%',
        borderRadius: 2,
        border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
        background: `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.9)} 0%, ${alpha(theme.palette.background.default, 0.7)} 100%)`,
        backdropFilter: 'blur(10px)',
        transition: 'all 0.2s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.1)}`,
        },
      }}
    >
      <Typography
        variant="overline"
        sx={{
          color: theme.palette.text.secondary,
          fontSize: '0.7rem',
          letterSpacing: '0.08em',
          fontWeight: 600,
        }}
      >
        {label}
      </Typography>
      <Typography
        variant="h4"
        sx={{
          fontWeight: 700,
          color: theme.palette.text.primary,
          my: 0.5,
          fontSize: '1.75rem',
        }}
      >
        {value}
      </Typography>
      {change && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {getTrendIcon()}
          <Typography
            variant="caption"
            sx={{
              fontWeight: 600,
              color: getTrendColor(),
            }}
          >
            {change}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

// Chart card wrapper
const ChartCard = ({ title, children, height = 300, theme }) => (
  <Paper
    elevation={0}
    sx={{
      height: '100%',
      borderRadius: 2,
      border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
      overflow: 'hidden',
    }}
  >
    <Box
      sx={{
        px: 2.5,
        py: 1.5,
        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
        bgcolor: alpha(theme.palette.background.default, 0.5),
      }}
    >
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
    </Box>
    <Box sx={{ p: 2, height }}>
      {children}
    </Box>
  </Paper>
);

// Insight card with impact color
const InsightCard = ({ insight, theme, compact = false }) => {
  const getIcon = () => {
    switch (insight.type) {
      case 'finding': return <InfoIcon sx={{ fontSize: compact ? 18 : 20 }} />;
      case 'trend': return <TrendingUp sx={{ fontSize: compact ? 18 : 20 }} />;
      case 'anomaly': return <WarningIcon sx={{ fontSize: compact ? 18 : 20 }} />;
      case 'recommendation': return <LightbulbIcon sx={{ fontSize: compact ? 18 : 20 }} />;
      default: return <InfoIcon sx={{ fontSize: compact ? 18 : 20 }} />;
    }
  };

  const getAccentColor = () => {
    switch (insight.impact) {
      case 'high': return theme.palette.error.main;
      case 'medium': return theme.palette.warning.main;
      default: return theme.palette.info.main;
    }
  };

  const accentColor = getAccentColor();

  if (compact) {
    return (
      <Box
        sx={{
          p: 1.5,
          borderRadius: 1.5,
          border: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
          borderLeft: `3px solid ${accentColor}`,
          bgcolor: alpha(accentColor, 0.04),
          mb: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
          <Box sx={{ color: accentColor, mt: 0.25 }}>{getIcon()}</Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.4 }}>
              {insight.title}
            </Typography>
          </Box>
          <Chip
            label={insight.impact}
            size="small"
            sx={{
              height: 20,
              fontSize: '0.65rem',
              fontWeight: 600,
              bgcolor: alpha(accentColor, 0.1),
              color: accentColor,
              textTransform: 'uppercase',
            }}
          />
        </Box>
      </Box>
    );
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 2,
        border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
        borderLeft: `4px solid ${accentColor}`,
        mb: 2,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 1.5 }}>
        <Box
          sx={{
            p: 1,
            borderRadius: 1.5,
            bgcolor: alpha(accentColor, 0.1),
            color: accentColor,
          }}
        >
          {getIcon()}
        </Box>
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {insight.title}
            </Typography>
            <Chip
              label={insight.impact}
              size="small"
              sx={{
                height: 22,
                fontSize: '0.7rem',
                fontWeight: 600,
                bgcolor: alpha(accentColor, 0.1),
                color: accentColor,
                textTransform: 'uppercase',
              }}
            />
          </Box>
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary, lineHeight: 1.6 }}>
            {insight.description}
          </Typography>
        </Box>
      </Box>
      {insight.actions && insight.actions.length > 0 && (
        <Box sx={{ mt: 2, pl: 6 }}>
          <Typography
            variant="overline"
            sx={{
              fontSize: '0.65rem',
              letterSpacing: '0.08em',
              color: theme.palette.text.secondary,
              fontWeight: 600,
            }}
          >
            Recommended Actions
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {insight.actions.map((action, i) => (
              <Typography
                component="li"
                variant="body2"
                key={i}
                sx={{ color: theme.palette.text.primary, py: 0.25 }}
              >
                {action}
              </Typography>
            ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

// Tab panel wrapper
const TabPanel = ({ children, value, index, ...other }) => (
  <div role="tabpanel" hidden={value !== index} {...other}>
    {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
  </div>
);

const MantraxResultsView = ({ query, sql, results, metadata, onClose }) => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formattedData, setFormattedData] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [exportAnchorEl, setExportAnchorEl] = useState(null);
  const [copiedSql, setCopiedSql] = useState(false);
  const [tableSearch, setTableSearch] = useState('');
  const [tablePage, setTablePage] = useState(0);
  const [tableRowsPerPage, setTableRowsPerPage] = useState(10);

  // Drill-down state
  const [drillBreadcrumbs, setDrillBreadcrumbs] = useState([]);
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillMessage, setDrillMessage] = useState('');
  const [originalQuery] = useState(query);
  const [currentQuery, setCurrentQuery] = useState(query);

  useEffect(() => {
    formatResults();
  }, [query, sql, results]);

  const formatResults = async (queryOverride = null) => {
    try {
      setLoading(true);
      setError(null);
      const userId = 'persona';
      const queryToUse = queryOverride || query;
      const response = await apiService.formatResultsWithMantrax(queryToUse, sql, results, metadata, userId);
      setFormattedData(response.data);
    } catch (err) {
      console.error('Failed to format results:', err);
      setError('Failed to format results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle chart click → drill down
  const handleDrillDown = useCallback(async (params, chartComponent) => {
    const dimension = chartComponent?.data?.xAxis?.key || params.seriesName || params.name;
    const value = params.name || params.value;

    if (!dimension || !value) {
      console.log('[MantraxResultsView] Drill-down: missing dimension or value', { dimension, value, params });
      return;
    }

    console.log('[MantraxResultsView] Drilling down:', { dimension, value });

    // Show feedback immediately
    const displayDimension = dimension.replace(/_/g, ' ');
    setDrillMessage(`Drilling into ${displayDimension}: ${value}...`);

    // Add to breadcrumbs
    setDrillBreadcrumbs(prev => [...prev, { dimension, value }]);
    setDrillLoading(true);

    try {
      // Build drill query by adding filter to current query
      const drillQuery = `${currentQuery} where ${dimension} = '${value}'`;
      setCurrentQuery(drillQuery);

      // Re-format with new filtered query
      const userId = 'persona';
      const response = await apiService.formatResultsWithMantrax(
        drillQuery,
        sql,
        results,
        metadata,
        userId
      );
      setFormattedData(response.data);
      setDrillMessage(`Filtered by ${displayDimension}: ${value}`);
    } catch (err) {
      console.error('Drill-down failed:', err);
      // Revert breadcrumb on error
      setDrillBreadcrumbs(prev => prev.slice(0, -1));
      setDrillMessage('Drill-down failed. Please try again.');
    } finally {
      setDrillLoading(false);
      // Auto-hide message after 3 seconds
      setTimeout(() => setDrillMessage(''), 3000);
    }
  }, [currentQuery, sql, results, metadata]);

  // Handle breadcrumb navigation (go back)
  const handleBreadcrumbClick = useCallback(async (index) => {
    setDrillLoading(true);

    try {
      if (index === -1) {
        // Go back to root
        setDrillBreadcrumbs([]);
        setCurrentQuery(originalQuery);
        await formatResults(originalQuery);
      } else {
        // Go back to specific level
        const newBreadcrumbs = drillBreadcrumbs.slice(0, index + 1);
        setDrillBreadcrumbs(newBreadcrumbs);

        // Rebuild query with only those filters
        const filters = newBreadcrumbs.map(b => `${b.dimension} = '${b.value}'`).join(' and ');
        const drillQuery = filters ? `${originalQuery} where ${filters}` : originalQuery;
        setCurrentQuery(drillQuery);

        const userId = 'persona';
        const response = await apiService.formatResultsWithMantrax(
          drillQuery,
          sql,
          results,
          metadata,
          userId
        );
        setFormattedData(response.data);
      }
    } catch (err) {
      console.error('Breadcrumb navigation failed:', err);
    } finally {
      setDrillLoading(false);
    }
  }, [originalQuery, drillBreadcrumbs, sql, results, metadata]);

  // Extract metrics from summary-card component
  const metrics = useMemo(() => {
    if (!formattedData?.components) return [];
    const summaryCard = formattedData.components.find((c) => c.type === 'summary-card');
    return summaryCard?.data?.metrics || [];
  }, [formattedData]);

  // Extract charts from chart-config components
  const charts = useMemo(() => {
    if (!formattedData?.components) return [];
    const chartComponents = formattedData.components.filter((c) => c.type === 'chart-config');
    // Debug: log chart extraction
    if (process.env.NODE_ENV === 'development') {
      console.log('[MantraxResultsView] Components:', formattedData.components.map(c => c.type));
      console.log('[MantraxResultsView] Charts found:', chartComponents.length, chartComponents);
    }
    return chartComponents;
  }, [formattedData]);

  // Extract insights from insight-cards component
  const insights = useMemo(() => {
    if (!formattedData?.components) return [];
    const insightCards = formattedData.components.find((c) => c.type === 'insight-cards');
    return insightCards?.data?.insights || [];
  }, [formattedData]);

  // Extract data table from data-table component
  const dataTable = useMemo(() => {
    if (!formattedData?.components) return null;
    return formattedData.components.find((c) => c.type === 'data-table');
  }, [formattedData]);

  // Filter table data based on search
  const filteredTableData = useMemo(() => {
    if (!dataTable?.data?.data) return [];
    if (!tableSearch) return dataTable.data.data;
    const searchLower = tableSearch.toLowerCase();
    return dataTable.data.data.filter((row) =>
      Object.values(row).some((val) =>
        String(val).toLowerCase().includes(searchLower)
      )
    );
  }, [dataTable, tableSearch]);

  // Parse numeric values for charts
  const parseNumericValue = (value) => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
      const cleaned = value.replace(/[$,]/g, '').trim();
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? value : parsed;
    }
    return value;
  };

  // Sanitize chart data
  const sanitizeChartData = (data, yAxisKey) => {
    if (!Array.isArray(data)) return [];
    return data.map((item) => {
      const sanitized = { ...item };
      Object.keys(sanitized).forEach((key) => {
        if (key === yAxisKey || typeof sanitized[key] === 'string') {
          sanitized[key] = parseNumericValue(sanitized[key]);
        }
      });
      return sanitized;
    });
  };

  // Format cell values
  const formatCellValue = (value, type) => {
    if (value === null || value === undefined) return '—';
    switch (type) {
      case 'currency':
        return `$${parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
      case 'percentage':
        return `${(parseFloat(value) * 100).toFixed(2)}%`;
      case 'number':
        return parseFloat(value).toLocaleString('en-US');
      case 'date':
        return new Date(value).toLocaleDateString();
      default:
        return String(value);
    }
  };

  // Export handlers
  const handleExportClick = (event) => setExportAnchorEl(event.currentTarget);
  const handleExportClose = () => setExportAnchorEl(null);

  const handleExportCSV = () => {
    if (!results || results.length === 0) return;
    const headers = Object.keys(results[0]);
    const csvContent = [
      headers.join(','),
      ...results.map((row) =>
        headers.map((h) => {
          const val = row[h];
          if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
            return `"${val.replace(/"/g, '""')}"`;
          }
          return val ?? '';
        }).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `dashboard_export_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    handleExportClose();
  };

  const handleCopySQL = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopiedSql(true);
      setTimeout(() => setCopiedSql(false), 2000);
    } catch (err) {
      console.error('Failed to copy SQL:', err);
    }
  };

  // Smart chart type override - analyzes data and suggests better chart when LLM chooses poorly
  const getSmartChartType = (llmType, chartData, xAxis, yAxis) => {
    if (!Array.isArray(chartData) || chartData.length === 0) return llmType;

    const keys = Object.keys(chartData[0] || {});
    const numericKeys = keys.filter(k => typeof chartData[0][k] === 'number');
    const stringKeys = keys.filter(k => typeof chartData[0][k] === 'string');

    // Override rules when LLM chose 'bar' but data suggests otherwise
    if (llmType === 'bar') {
      // Single row → metric (NEVER bar for single values)
      if (chartData.length === 1) {
        if (numericKeys.length === 1) return 'metric';
        return 'gauge';
      }

      // Time series → line
      const timePatterns = ['date', 'time', 'month', 'year', 'quarter', 'week', 'period'];
      const hasTimeKey = keys.some(k => timePatterns.some(p => k.toLowerCase().includes(p)));
      if (hasTimeKey) return 'line';

      // Matrix/cross-tab detection (2 categorical + 1 numeric) → heatmap
      if (stringKeys.length >= 2 && numericKeys.length >= 1 && chartData.length >= 4) {
        const col1Values = new Set(chartData.map(row => row[stringKeys[0]]));
        const col2Values = new Set(chartData.map(row => row[stringKeys[1]]));
        // If it looks like a cross-tab (unique combinations)
        if (col1Values.size >= 2 && col2Values.size >= 2 && col1Values.size * col2Values.size >= chartData.length * 0.5) {
          console.log('[MantraxResultsView] Smart override: bar → heatmap (detected matrix data)');
          return 'heatmap';
        }
      }

      // Small dataset (≤6 rows) → pie
      if (chartData.length <= 6 && stringKeys.length >= 1 && numericKeys.length >= 1) {
        console.log('[MantraxResultsView] Smart override: bar → pie (small categorical)');
        return 'pie';
      }

      // Long labels → horizontalBar
      if (stringKeys.length > 0) {
        const labelKey = stringKeys[0];
        const avgLen = chartData.reduce((sum, row) => sum + String(row[labelKey] || '').length, 0) / chartData.length;
        if (avgLen > 20) {
          console.log('[MantraxResultsView] Smart override: bar → horizontalBar (long labels)');
          return 'horizontalBar';
        }
      }
    }

    return llmType;
  };

  // Render chart based on type using ECharts
  const renderChart = (component) => {
    const { type, title, data, xAxis, yAxis } = component.data || {};

    // DEBUG: Log what chart type the LLM chose
    console.log('[MantraxResultsView] LLM chart type:', type, '| title:', title);

    // Parse data if it's a string
    let chartData = typeof data === 'string' ? JSON.parse(data) : data;

    // Filter out multi-DB internal columns
    if (Array.isArray(chartData)) {
      chartData = chartData.map(row => {
        const { _source_connector, _row_id, ...rest } = row;
        return rest;
      });
      // Sanitize numeric values
      chartData = sanitizeChartData(chartData, yAxis?.key);
    }

    // Apply smart override if LLM chose suboptimally
    const smartType = getSmartChartType(type, chartData, xAxis, yAxis);
    if (smartType !== type) {
      console.log('[MantraxResultsView] Chart type overridden:', type, '→', smartType);
    }

    // Map chart types (some APIs use different names)
    const chartTypeMap = {
      // Comparison
      'bar': 'bar',
      'horizontal_bar': 'horizontalBar',
      'horizontalBar': 'horizontalBar',
      'pictorialBar': 'pictorialBar',
      'pictorial_bar': 'pictorialBar',
      // Time series
      'line': 'line',
      'area': 'area',
      'themeRiver': 'themeRiver',
      'theme_river': 'themeRiver',
      'calendar': 'calendar',
      // Part-to-whole
      'pie': 'pie',
      'donut': 'donut',
      'treemap': 'treemap',
      'sunburst': 'sunburst',
      // Distribution
      'scatter': 'scatter',
      'heatmap': 'heatmap',
      'boxplot': 'boxplot',
      'box_plot': 'boxplot',
      // Flow & process
      'funnel': 'funnel',
      'sankey': 'sankey',
      'graph': 'graph',
      'network': 'graph',
      // KPI
      'gauge': 'gauge',
      'metric': 'metric',
      // Multi-dimensional
      'radar': 'radar',
      'parallel': 'parallel',
      // Financial
      'candlestick': 'candlestick',
      'candle_stick': 'candlestick',
    };

    const echartsType = chartTypeMap[smartType] || 'auto';

    return (
      <ChartCard title={title} theme={theme}>
        <EChartsVisualization
          data={chartData}
          chartType={echartsType}
          height={280}
          xKey={xAxis?.key}
          yKey={yAxis?.key}
          showToolbox={true}
          showDataZoom={Array.isArray(chartData) && chartData.length > 10}
          onChartClick={(params) => handleDrillDown(params, component)}
        />
      </ChartCard>
    );
  };

  // Overview Tab Content
  const OverviewPanel = () => (
    <Grid container spacing={3}>
      {/* Charts - Left Side (60%) */}
      <Grid item xs={12} md={7}>
        {/* Drill-down Breadcrumbs */}
        {drillBreadcrumbs.length > 0 && (
          <Box
            sx={{
              mb: 2,
              p: 1.5,
              borderRadius: 2,
              bgcolor: alpha(theme.palette.primary.main, 0.05),
              border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Breadcrumbs separator="›" sx={{ flex: 1 }}>
              <Link
                component="button"
                variant="body2"
                onClick={() => handleBreadcrumbClick(-1)}
                underline="hover"
                sx={{
                  cursor: 'pointer',
                  color: theme.palette.primary.main,
                  fontWeight: 500,
                }}
              >
                All Data
              </Link>
              {drillBreadcrumbs.map((bc, idx) => (
                <Link
                  key={idx}
                  component="button"
                  variant="body2"
                  onClick={() => handleBreadcrumbClick(idx)}
                  underline="hover"
                  sx={{
                    cursor: 'pointer',
                    color: idx === drillBreadcrumbs.length - 1
                      ? theme.palette.text.primary
                      : theme.palette.primary.main,
                    fontWeight: idx === drillBreadcrumbs.length - 1 ? 600 : 500,
                  }}
                >
                  {bc.value}
                </Link>
              ))}
            </Breadcrumbs>
            {drillLoading && <CircularProgress size={16} />}
          </Box>
        )}

        {charts.length > 0 ? (
          <>
            {/* Primary Chart */}
            {charts[0] && (
              <Box sx={{ mb: 2, height: 350 }}>
                {renderChart(charts[0])}
              </Box>
            )}
            {/* Secondary Charts */}
            <Grid container spacing={2}>
              {charts.slice(1, 3).map((chart, idx) => (
                <Grid item xs={12} sm={6} key={idx}>
                  <Box sx={{ height: 220 }}>
                    {renderChart(chart)}
                  </Box>
                </Grid>
              ))}
            </Grid>
          </>
        ) : (
          <Paper
            elevation={0}
            sx={{
              height: 350,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 2,
              border: `1px dashed ${alpha(theme.palette.divider, 0.5)}`,
              bgcolor: alpha(theme.palette.background.default, 0.5),
            }}
          >
            <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
              <Typography variant="body2">
                No chart visualizations available for this query.
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.7 }}>
                Try a query that returns multiple rows of data.
              </Typography>
            </Box>
          </Paper>
        )}
      </Grid>

      {/* Insights Sidebar - Right Side (40%) */}
      <Grid item xs={12} md={5}>
        <Paper
          elevation={0}
          sx={{
            height: '100%',
            borderRadius: 2,
            border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              px: 2.5,
              py: 1.5,
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
              bgcolor: alpha(theme.palette.primary.main, 0.04),
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <InsightsIcon sx={{ fontSize: 18, color: theme.palette.primary.main }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              Key Insights
            </Typography>
            <Chip
              label={insights.length}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                fontWeight: 600,
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                color: theme.palette.primary.main,
              }}
            />
          </Box>
          <Box
            sx={{
              p: 2,
              maxHeight: 520,
              overflow: 'auto',
              '&::-webkit-scrollbar': { width: 6 },
              '&::-webkit-scrollbar-thumb': {
                bgcolor: alpha(theme.palette.text.secondary, 0.2),
                borderRadius: 3,
              },
            }}
          >
            {insights.length > 0 ? (
              insights.map((insight, idx) => (
                <InsightCard key={idx} insight={insight} theme={theme} compact />
              ))
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                No insights available
              </Typography>
            )}
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );

  // Data Tab Content
  const DataPanel = () => {
    if (!dataTable) {
      return (
        <Alert severity="info" sx={{ borderRadius: 2 }}>
          No tabular data available for this query.
        </Alert>
      );
    }

    const { columns, data } = dataTable.data;
    const paginatedData = filteredTableData.slice(
      tablePage * tableRowsPerPage,
      tablePage * tableRowsPerPage + tableRowsPerPage
    );

    return (
      <Paper
        elevation={0}
        sx={{
          borderRadius: 2,
          border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
          overflow: 'hidden',
        }}
      >
        {/* Search Bar */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}` }}>
          <TextField
            size="small"
            placeholder="Search data..."
            value={tableSearch}
            onChange={(e) => {
              setTableSearch(e.target.value);
              setTablePage(0);
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: theme.palette.text.secondary, fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
            sx={{ width: 300 }}
          />
        </Box>

        {/* Table */}
        <TableContainer sx={{ maxHeight: 440 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                {columns.map((col) => (
                  <TableCell
                    key={col.key}
                    align={col.align || 'left'}
                    sx={{
                      fontWeight: 600,
                      bgcolor: alpha(theme.palette.primary.main, 0.05),
                      borderBottom: `2px solid ${theme.palette.primary.main}`,
                    }}
                  >
                    {col.label}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedData.map((row, index) => (
                <TableRow
                  key={index}
                  hover
                  sx={{
                    '&:nth-of-type(even)': {
                      bgcolor: alpha(theme.palette.action.hover, 0.3),
                    },
                  }}
                >
                  {columns.map((col) => (
                    <TableCell key={col.key} align={col.align || 'left'}>
                      {formatCellValue(row[col.key], col.type)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        <TablePagination
          component="div"
          count={filteredTableData.length}
          page={tablePage}
          onPageChange={(e, newPage) => setTablePage(newPage)}
          rowsPerPage={tableRowsPerPage}
          onRowsPerPageChange={(e) => {
            setTableRowsPerPage(parseInt(e.target.value, 10));
            setTablePage(0);
          }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Paper>
    );
  };

  // Insights Tab Content
  const InsightsPanel = () => (
    <Box>
      {insights.length > 0 ? (
        insights.map((insight, idx) => (
          <InsightCard key={idx} insight={insight} theme={theme} />
        ))
      ) : (
        <Alert severity="info" sx={{ borderRadius: 2 }}>
          No insights available for this query.
        </Alert>
      )}
    </Box>
  );

  // Query Details Tab Content
  const QueryDetailsPanel = () => (
    <Grid container spacing={3}>
      {/* Original Query */}
      <Grid item xs={12}>
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            borderRadius: 2,
            border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
          }}
        >
          <Typography
            variant="overline"
            sx={{
              color: theme.palette.text.secondary,
              letterSpacing: '0.08em',
              fontWeight: 600,
              fontSize: '0.7rem',
            }}
          >
            Original Question
          </Typography>
          <Typography variant="body1" sx={{ mt: 1, fontStyle: 'italic' }}>
            "{query}"
          </Typography>
        </Paper>
      </Grid>

      {/* SQL Query */}
      <Grid item xs={12}>
        <Paper
          elevation={0}
          sx={{
            borderRadius: 2,
            border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              px: 2.5,
              py: 1.5,
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
              bgcolor: alpha(theme.palette.background.default, 0.5),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CodeIcon sx={{ fontSize: 18, color: theme.palette.text.secondary }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Generated SQL
              </Typography>
            </Box>
            <Tooltip title={copiedSql ? 'Copied!' : 'Copy SQL'}>
              <IconButton size="small" onClick={handleCopySQL}>
                {copiedSql ? (
                  <CopiedIcon sx={{ fontSize: 18, color: theme.palette.success.main }} />
                ) : (
                  <CopyIcon sx={{ fontSize: 18, color: theme.palette.text.disabled }} />
                )}
              </IconButton>
            </Tooltip>
          </Box>
          <Box
            sx={{
              p: 2.5,
              bgcolor: alpha(theme.palette.grey[900], 0.03),
              overflow: 'auto',
              maxHeight: 400,
              '&::-webkit-scrollbar': { width: 6, height: 6 },
              '&::-webkit-scrollbar-thumb': {
                bgcolor: alpha(theme.palette.text.secondary, 0.2),
                borderRadius: 3,
              },
            }}
          >
            <Typography
              component="pre"
              sx={{
                fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Fira Code", monospace',
                fontSize: '0.85rem',
                lineHeight: 1.6,
                color: theme.palette.text.primary,
                m: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {sql}
            </Typography>
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );

  // Loading state
  if (loading) {
    return <LoadingSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ borderRadius: 2 }}>
          {error}
        </Alert>
      </Box>
    );
  }

  // Empty state
  if (!formattedData) {
    return null;
  }

  return (
    <Box sx={{ p: 3, position: 'relative' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: '12px',
              bgcolor: theme.palette.primary.main,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <DashboardIcon sx={{ color: 'white', fontSize: 22 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Dashboard View
            </Typography>
            <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
              Interactive analysis of your query results
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExportClick}
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            Export
          </Button>
          <Menu
            anchorEl={exportAnchorEl}
            open={Boolean(exportAnchorEl)}
            onClose={handleExportClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          >
            <MenuItem onClick={handleExportCSV}>
              <ListItemIcon>
                <CsvIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as CSV</ListItemText>
            </MenuItem>
            <MenuItem onClick={handleExportClose} disabled>
              <ListItemIcon>
                <PdfIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as PDF</ListItemText>
            </MenuItem>
            <MenuItem onClick={handleExportClose} disabled>
              <ListItemIcon>
                <ImageIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as PNG</ListItemText>
            </MenuItem>
          </Menu>
          <Tooltip title="Close">
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Summary */}
      {formattedData.summary && (
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 3,
            borderRadius: 2,
            borderLeft: `4px solid ${theme.palette.primary.main}`,
            border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
            borderLeftWidth: 4,
            bgcolor: alpha(theme.palette.primary.main, 0.02),
          }}
        >
          <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
            {formattedData.summary}
          </Typography>
        </Paper>
      )}

      {/* Metrics Cards */}
      {metrics.length > 0 && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {metrics.slice(0, 4).map((metric, index) => (
            <Grid item xs={6} md={3} key={index}>
              <MetricCard
                label={metric.label}
                value={metric.value}
                change={metric.change}
                trend={metric.trend}
                theme={theme}
              />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}` }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 500,
              fontSize: '0.9rem',
              minHeight: 48,
            },
          }}
        >
          <Tab
            icon={<DashboardIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Overview"
          />
          <Tab
            icon={<TableIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Data"
          />
          <Tab
            icon={<InsightsIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Insights"
          />
          <Tab
            icon={<CodeIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Query Details"
          />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <TabPanel value={activeTab} index={0}>
        <OverviewPanel />
      </TabPanel>
      <TabPanel value={activeTab} index={1}>
        <DataPanel />
      </TabPanel>
      <TabPanel value={activeTab} index={2}>
        <InsightsPanel />
      </TabPanel>
      <TabPanel value={activeTab} index={3}>
        <QueryDetailsPanel />
      </TabPanel>

      {/* Footer */}
      <Box
        sx={{
          mt: 3,
          pt: 2,
          borderTop: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
          display: 'flex',
          alignItems: 'center',
          gap: 3,
        }}
      >
        {metadata?.timing?.total_seconds && (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <TimeIcon sx={{ fontSize: 16, color: theme.palette.text.disabled }} />
            <Typography variant="caption" color="text.secondary">
              Query: {metadata.timing.total_seconds.toFixed(2)}s
            </Typography>
          </Stack>
        )}
        {results?.length && (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <RowsIcon sx={{ fontSize: 16, color: theme.palette.text.disabled }} />
            <Typography variant="caption" color="text.secondary">
              {results.length.toLocaleString()} rows
            </Typography>
          </Stack>
        )}
        <Stack direction="row" spacing={0.5} alignItems="center">
          <UpdatedIcon sx={{ fontSize: 16, color: theme.palette.text.disabled }} />
          <Typography variant="caption" color="text.secondary">
            Updated: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Typography>
        </Stack>
      </Box>

      {/* Drill-down loading backdrop */}
      <Backdrop
        sx={{
          color: '#fff',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          position: 'absolute',
          borderRadius: 3,
        }}
        open={drillLoading}
      >
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress color="inherit" size={40} />
          <Typography sx={{ mt: 2 }}>{drillMessage || 'Loading...'}</Typography>
        </Box>
      </Backdrop>

      {/* Drill-down feedback snackbar */}
      <Snackbar
        open={!!drillMessage && !drillLoading}
        message={drillMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        sx={{
          '& .MuiSnackbarContent-root': {
            bgcolor: theme.palette.primary.main,
          }
        }}
      />
    </Box>
  );
};

export default MantraxResultsView;
