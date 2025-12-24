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
  LinearProgress,
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
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { apiService } from '../services/api';
import EChartsVisualization from './EChartsVisualization';

// Premium Loading Component with Lottie Animation and Glassmorphism
const LoadingSkeleton = ({ query }) => {
  const theme = useTheme();
  const [currentStep, setCurrentStep] = React.useState(0);
  const [progress, setProgress] = React.useState(0);

  const loadingSteps = [
    { label: 'Analyzing data structure', icon: '📊' },
    { label: 'Identifying patterns', icon: '🔍' },
    { label: 'Generating visualizations', icon: '📈' },
    { label: 'Preparing insights', icon: '💡' },
  ];

  // Progress simulation
  React.useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 95) return prev;
        return prev + Math.random() * 8;
      });
    }, 500);

    const stepInterval = setInterval(() => {
      setCurrentStep(prev => (prev + 1) % loadingSteps.length);
    }, 2500);

    return () => {
      clearInterval(progressInterval);
      clearInterval(stepInterval);
    };
  }, []);

  const isDark = theme.palette.mode === 'dark';
  const primaryBlue = '#5899DA';

  return (
    <Box
      sx={{
        minHeight: 500,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        p: 4,
        background: isDark
          ? 'linear-gradient(180deg, rgba(18,20,28,1) 0%, rgba(26,28,38,1) 100%)'
          : 'linear-gradient(180deg, rgba(248,250,254,1) 0%, rgba(238,242,250,1) 100%)',
      }}
    >
      {/* Main Loading Card with Premium Glassmorphism */}
      <Paper
        elevation={0}
        sx={{
          p: 5,
          borderRadius: 4,
          textAlign: 'center',
          maxWidth: 480,
          width: '100%',
          background: isDark
            ? 'linear-gradient(145deg, rgba(40,42,54,0.88) 0%, rgba(30,32,44,0.92) 100%)'
            : 'linear-gradient(145deg, rgba(255,255,255,0.92) 0%, rgba(248,250,252,0.88) 100%)',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'}`,
          backdropFilter: 'blur(20px) saturate(180%)',
          boxShadow: isDark
            ? '0 24px 80px rgba(0,0,0,0.5), 0 8px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.05)'
            : '0 24px 80px rgba(0,0,0,0.1), 0 8px 24px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.8)',
        }}
      >
        {/* Lottie Animation */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center', minHeight: 200 }}>
          <DotLottieReact
            src="/Loading animation blue.lottie"
            loop
            autoplay
            style={{
              width: 280,
              height: 200,
            }}
          />
        </Box>

        {/* Title with Gradient */}
        <Typography
          variant="h5"
          sx={{
            fontWeight: 700,
            mb: 1,
            fontSize: '1.5rem',
            background: `linear-gradient(135deg, ${primaryBlue} 0%, #3B82F6 100%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          Building Dashboard
        </Typography>

        {/* Current Step */}
        <Typography
          variant="body1"
          sx={{
            color: theme.palette.text.secondary,
            mb: 3,
            minHeight: 28,
            transition: 'all 0.3s ease',
            fontSize: '0.95rem',
          }}
        >
          {loadingSteps[currentStep].icon} {loadingSteps[currentStep].label}...
        </Typography>

        {/* Premium Progress Bar */}
        <Box sx={{ mb: 3 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 4,
                background: `linear-gradient(90deg, ${primaryBlue} 0%, #3B82F6 50%, ${primaryBlue} 100%)`,
                backgroundSize: '200% 100%',
                animation: 'shimmer 2s infinite linear',
              },
              '@keyframes shimmer': {
                '0%': { backgroundPosition: '100% 0' },
                '100%': { backgroundPosition: '-100% 0' },
              },
            }}
          />
          <Typography
            variant="caption"
            sx={{
              color: theme.palette.text.secondary,
              mt: 1.5,
              display: 'block',
              fontWeight: 600,
              fontSize: '0.75rem',
            }}
          >
            {Math.round(progress)}% complete
          </Typography>
        </Box>

        {/* Step Indicators with Glow */}
        <Stack
          direction="row"
          spacing={1.5}
          justifyContent="center"
          sx={{ mb: 3 }}
        >
          {loadingSteps.map((step, index) => (
            <Box
              key={index}
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                transition: 'all 0.3s ease',
                bgcolor: index === currentStep
                  ? primaryBlue
                  : index < currentStep
                    ? alpha(primaryBlue, 0.5)
                    : isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)',
                transform: index === currentStep ? 'scale(1.3)' : 'scale(1)',
                boxShadow: index === currentStep
                  ? `0 0 12px ${alpha(primaryBlue, 0.6)}, 0 0 4px ${alpha(primaryBlue, 0.4)}`
                  : 'none',
              }}
            />
          ))}
        </Stack>

        {/* Query Display with Glass Effect */}
        {query && (
          <Box
            sx={{
              p: 2,
              borderRadius: 2.5,
              bgcolor: isDark ? 'rgba(88,153,218,0.06)' : 'rgba(88,153,218,0.04)',
              border: `1px solid ${isDark ? 'rgba(88,153,218,0.15)' : 'rgba(88,153,218,0.12)'}`,
              backdropFilter: 'blur(8px)',
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: theme.palette.text.disabled,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                fontSize: '0.65rem',
                fontWeight: 600,
              }}
            >
              Your Query
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: theme.palette.text.secondary,
                mt: 0.5,
                fontStyle: 'italic',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}
            >
              "{query}"
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Subtle tip */}
      <Typography
        variant="caption"
        sx={{
          mt: 3,
          color: theme.palette.text.disabled,
          opacity: 0.7,
        }}
      >
        AI is analyzing your data and creating visualizations
      </Typography>
    </Box>
  );
};

// Premium Metric card with glassmorphism effect and trend accent
const MetricCard = ({ label, value, change, trend, theme }) => {
  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp sx={{ fontSize: 18, color: '#10B981' }} />;
    if (trend === 'down') return <TrendingDown sx={{ fontSize: 18, color: '#EF4444' }} />;
    return <TrendingFlat sx={{ fontSize: 18, color: theme.palette.text.disabled }} />;
  };

  const getTrendColor = () => {
    if (trend === 'up') return '#10B981';
    if (trend === 'down') return '#EF4444';
    return theme.palette.text.disabled;
  };

  const getAccentColor = () => {
    if (trend === 'up') return '#10B981';
    if (trend === 'down') return '#EF4444';
    return '#5899DA';
  };

  const isDark = theme.palette.mode === 'dark';

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        height: '100%',
        borderRadius: 3,
        position: 'relative',
        overflow: 'hidden',
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
        background: isDark
          ? 'linear-gradient(145deg, rgba(40,42,54,0.85) 0%, rgba(30,32,44,0.9) 100%)'
          : 'linear-gradient(145deg, rgba(255,255,255,0.92) 0%, rgba(248,250,252,0.88) 100%)',
        backdropFilter: 'blur(16px) saturate(180%)',
        transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: isDark
            ? '0 12px 32px rgba(0, 0, 0, 0.4), 0 4px 12px rgba(0, 0, 0, 0.3)'
            : '0 12px 32px rgba(0, 0, 0, 0.1), 0 4px 12px rgba(0, 0, 0, 0.05)',
          border: `1px solid ${alpha(getAccentColor(), 0.3)}`,
        },
        // Left accent stripe
        '&::before': {
          content: '""',
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: 4,
          background: `linear-gradient(180deg, ${getAccentColor()} 0%, ${alpha(getAccentColor(), 0.6)} 100%)`,
          borderRadius: '4px 0 0 4px',
        },
      }}
    >
      <Typography
        variant="overline"
        sx={{
          color: theme.palette.text.secondary,
          fontSize: '0.68rem',
          letterSpacing: '0.1em',
          fontWeight: 600,
          textTransform: 'uppercase',
          display: 'block',
          mb: 0.5,
        }}
      >
        {label}
      </Typography>
      <Typography
        sx={{
          fontWeight: 700,
          color: theme.palette.text.primary,
          my: 0.75,
          fontSize: '1.85rem',
          lineHeight: 1.2,
          fontFamily: 'Inter, system-ui, sans-serif',
          background: `linear-gradient(135deg, ${theme.palette.text.primary} 0%, ${alpha(theme.palette.text.primary, 0.8)} 100%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
        }}
      >
        {value}
      </Typography>
      {change && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
            mt: 1,
            p: 0.75,
            borderRadius: 1.5,
            bgcolor: alpha(getTrendColor(), 0.08),
            width: 'fit-content',
          }}
        >
          {getTrendIcon()}
          <Typography
            variant="caption"
            sx={{
              fontWeight: 700,
              color: getTrendColor(),
              fontSize: '0.75rem',
            }}
          >
            {change}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

// Premium Chart card wrapper with gradient header
const ChartCard = ({ title, children, height = 300, theme }) => {
  const isDark = theme.palette.mode === 'dark';

  return (
    <Paper
      elevation={0}
      sx={{
        height: '100%',
        borderRadius: 3,
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}`,
        overflow: 'hidden',
        background: isDark
          ? 'linear-gradient(180deg, rgba(40,42,54,0.8) 0%, rgba(35,37,49,0.85) 100%)'
          : 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(250,251,254,0.9) 100%)',
        backdropFilter: 'blur(12px)',
        transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
        '&:hover': {
          boxShadow: isDark
            ? '0 8px 24px rgba(0, 0, 0, 0.35)'
            : '0 8px 24px rgba(0, 0, 0, 0.08)',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}`,
        },
      }}
    >
      <Box
        sx={{
          px: 2.5,
          py: 1.75,
          borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}`,
          background: isDark
            ? 'linear-gradient(135deg, rgba(88,153,218,0.08) 0%, rgba(88,153,218,0.02) 100%)'
            : 'linear-gradient(135deg, rgba(88,153,218,0.06) 0%, rgba(88,153,218,0.01) 100%)',
        }}
      >
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            fontSize: '0.875rem',
            color: theme.palette.text.primary,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          {title}
        </Typography>
      </Box>
      <Box sx={{ p: 2.5, height }}>
        {children}
      </Box>
    </Paper>
  );
};

// Premium Insight card with impact-based gradient backgrounds
const InsightCard = ({ insight, theme, compact = false }) => {
  const isDark = theme.palette.mode === 'dark';

  const getIcon = () => {
    switch (insight.type) {
      case 'finding': return <InfoIcon sx={{ fontSize: compact ? 18 : 22 }} />;
      case 'trend': return <TrendingUp sx={{ fontSize: compact ? 18 : 22 }} />;
      case 'anomaly': return <WarningIcon sx={{ fontSize: compact ? 18 : 22 }} />;
      case 'recommendation': return <LightbulbIcon sx={{ fontSize: compact ? 18 : 22 }} />;
      default: return <InfoIcon sx={{ fontSize: compact ? 18 : 22 }} />;
    }
  };

  const getAccentColors = () => {
    switch (insight.impact) {
      case 'high': return { main: '#EF4444', light: '#FCA5A5', gradient: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' };
      case 'medium': return { main: '#F59E0B', light: '#FCD34D', gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)' };
      default: return { main: '#5899DA', light: '#93C5FD', gradient: 'linear-gradient(135deg, #5899DA 0%, #3B82F6 100%)' };
    }
  };

  const colors = getAccentColors();

  if (compact) {
    return (
      <Box
        sx={{
          p: 1.75,
          borderRadius: 2,
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}`,
          borderLeft: `4px solid ${colors.main}`,
          background: isDark
            ? `linear-gradient(135deg, ${alpha(colors.main, 0.08)} 0%, ${alpha(colors.main, 0.02)} 100%)`
            : `linear-gradient(135deg, ${alpha(colors.main, 0.06)} 0%, ${alpha(colors.main, 0.01)} 100%)`,
          mb: 1.5,
          transition: 'all 0.2s ease',
          '&:hover': {
            background: isDark
              ? `linear-gradient(135deg, ${alpha(colors.main, 0.12)} 0%, ${alpha(colors.main, 0.04)} 100%)`
              : `linear-gradient(135deg, ${alpha(colors.main, 0.1)} 0%, ${alpha(colors.main, 0.03)} 100%)`,
            transform: 'translateX(2px)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.25 }}>
          <Box sx={{ color: colors.main, mt: 0.25, display: 'flex' }}>{getIcon()}</Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant="body2"
              sx={{
                fontWeight: 600,
                lineHeight: 1.4,
                fontSize: '0.85rem',
                color: theme.palette.text.primary,
              }}
            >
              {insight.title}
            </Typography>
          </Box>
          <Chip
            label={insight.impact}
            size="small"
            sx={{
              height: 22,
              fontSize: '0.6rem',
              fontWeight: 700,
              background: insight.impact === 'high' ? colors.gradient : alpha(colors.main, 0.12),
              color: insight.impact === 'high' ? '#fff' : colors.main,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              border: 'none',
              flexShrink: 0,
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
        borderRadius: 3,
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}`,
        borderLeft: `4px solid ${colors.main}`,
        mb: 2,
        background: isDark
          ? `linear-gradient(145deg, ${alpha(colors.main, 0.06)} 0%, rgba(30,32,44,0.9) 100%)`
          : `linear-gradient(145deg, ${alpha(colors.main, 0.04)} 0%, rgba(255,255,255,0.95) 100%)`,
        transition: 'all 0.25s ease',
        '&:hover': {
          boxShadow: `0 4px 20px ${alpha(colors.main, 0.15)}`,
          transform: 'translateX(4px)',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 1.5 }}>
        <Box
          sx={{
            p: 1.25,
            borderRadius: 2,
            background: `linear-gradient(135deg, ${alpha(colors.main, 0.15)} 0%, ${alpha(colors.main, 0.08)} 100%)`,
            color: colors.main,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {getIcon()}
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.75, flexWrap: 'wrap' }}>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 600,
                fontSize: '0.95rem',
                color: theme.palette.text.primary,
              }}
            >
              {insight.title}
            </Typography>
            <Chip
              label={insight.impact}
              size="small"
              sx={{
                height: 24,
                fontSize: '0.65rem',
                fontWeight: 700,
                background: insight.impact === 'high' ? colors.gradient : alpha(colors.main, 0.12),
                color: insight.impact === 'high' ? '#fff' : colors.main,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                border: 'none',
              }}
            />
          </Box>
          <Typography
            variant="body2"
            sx={{
              color: theme.palette.text.secondary,
              lineHeight: 1.65,
              fontSize: '0.875rem',
            }}
          >
            {insight.description}
          </Typography>
        </Box>
      </Box>
      {insight.actions && insight.actions.length > 0 && (
        <Box
          sx={{
            mt: 2,
            ml: 6.5,
            p: 1.5,
            borderRadius: 2,
            bgcolor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
          }}
        >
          <Typography
            variant="overline"
            sx={{
              fontSize: '0.65rem',
              letterSpacing: '0.1em',
              color: theme.palette.text.secondary,
              fontWeight: 700,
              display: 'block',
              mb: 1,
            }}
          >
            Recommended Actions
          </Typography>
          <Box component="ol" sx={{ m: 0, pl: 2.5 }}>
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

const MantraxResultsView = ({ query, sql, results, metadata, onClose, preComputedData = null }) => {
  const theme = useTheme();
  // If we have pre-computed data, start with loading=false
  const [loading, setLoading] = useState(!preComputedData);
  const [error, setError] = useState(null);
  // Use pre-computed data if available
  const [formattedData, setFormattedData] = useState(preComputedData);
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
  // Current results state for drill-down (starts with initial results)
  const [currentResults, setCurrentResults] = useState(results);
  const [currentSql, setCurrentSql] = useState(sql);

  useEffect(() => {
    // Skip API call if we have pre-computed data
    if (preComputedData) {
      console.log('[MantraxResultsView] Using pre-computed data, skipping API call');
      setFormattedData(preComputedData);
      setLoading(false);
      return;
    }
    formatResults();
  }, [query, sql, results, preComputedData]);

  const formatResults = async (queryOverride = null, resultsOverride = null, sqlOverride = null) => {
    try {
      setLoading(true);
      setError(null);
      const userId = 'persona';
      const queryToUse = queryOverride || query;
      const resultsToUse = resultsOverride || currentResults;
      const sqlToUse = sqlOverride || currentSql;
      const response = await apiService.formatResultsWithMantrax(queryToUse, sqlToUse, resultsToUse, metadata, userId);
      setFormattedData(response.data);
    } catch (err) {
      console.error('Failed to format results:', err);
      setError('Failed to format results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle chart click → drill down with real data filtering
  const handleDrillDown = useCallback(async (params, chartComponent) => {
    const dimension = chartComponent?.data?.xAxis?.key || params.seriesName || params.name;
    const value = params.name || params.value;

    if (!dimension || !value) {
      console.log('[MantraxResultsView] Drill-down: missing dimension or value', { dimension, value, params });
      return;
    }

    console.log('[MantraxResultsView] Drilling down:', { dimension, value, metadata });

    // Show feedback immediately
    const displayDimension = dimension.replace(/_/g, ' ');
    setDrillMessage(`Drilling into ${displayDimension}: ${value}...`);

    // Add to breadcrumbs
    const newBreadcrumbs = [...drillBreadcrumbs, { dimension, value }];
    setDrillBreadcrumbs(newBreadcrumbs);
    setDrillLoading(true);

    try {
      // Build all filters from breadcrumbs
      const filters = newBreadcrumbs.map(bc => ({
        dimension: bc.dimension,
        value: bc.value,
        operator: '='
      }));

      // Check if we have connector queries for cross-database drill-down
      const connectorQueries = metadata?.connectorQueries;
      const hasMultiDb = connectorQueries && connectorQueries.length > 1;

      let drillResponse;

      if (hasMultiDb) {
        // Multi-database drill-down - call backend API
        console.log('[MantraxResultsView] Multi-DB drill-down with', connectorQueries.length, 'connectors');
        drillResponse = await apiService.executeDrillDown({
          connectorQueries: connectorQueries,
          filters: filters,
          joinSpecification: metadata?.joinSpecification
        });
      } else if (sql && metadata?.databaseType) {
        // Single-database drill-down
        console.log('[MantraxResultsView] Single-DB drill-down');
        drillResponse = await apiService.executeDrillDown({
          sql: sql,
          databaseType: metadata.databaseType,
          connectorId: metadata.connectorId,
          filters: filters
        });
      } else {
        // Fallback: client-side filtering (no re-execution)
        console.log('[MantraxResultsView] Client-side filter fallback');
        const filteredResults = currentResults.filter(row => {
          return filters.every(f => {
            const rowValue = row[f.dimension];
            if (rowValue === undefined) return true; // Column not in row
            return String(rowValue) === String(f.value);
          });
        });

        // Update current results and re-format
        setCurrentResults(filteredResults);
        const drillQuery = `${originalQuery} (filtered: ${filters.map(f => `${f.dimension}=${f.value}`).join(', ')})`;
        setCurrentQuery(drillQuery);

        await formatResults(drillQuery, filteredResults, currentSql);
        setDrillMessage(`Filtered by ${displayDimension}: ${value} (${filteredResults.length} rows)`);
        return;
      }

      // Handle API response
      if (drillResponse?.data?.success) {
        const newResults = drillResponse.data.results;
        const modifiedQueries = drillResponse.data.modified_queries;

        // Update state with filtered results
        setCurrentResults(newResults);

        // Update SQL display with modified queries
        if (modifiedQueries && Object.keys(modifiedQueries).length > 0) {
          const combinedSql = Object.entries(modifiedQueries)
            .map(([connId, query]) => `-- ${connId}\n${query}`)
            .join('\n\n');
          setCurrentSql(combinedSql);
        }

        const drillQuery = `${originalQuery} (filtered: ${filters.map(f => `${f.dimension}=${f.value}`).join(', ')})`;
        setCurrentQuery(drillQuery);

        // Re-format with new results
        await formatResults(drillQuery, newResults, currentSql);
        setDrillMessage(`Filtered by ${displayDimension}: ${value} (${newResults.length} rows)`);
      } else {
        throw new Error(drillResponse?.data?.error || 'Drill-down failed');
      }
    } catch (err) {
      console.error('Drill-down failed:', err);
      // Revert breadcrumb on error
      setDrillBreadcrumbs(prev => prev.slice(0, -1));
      setDrillMessage(`Drill-down failed: ${err.message}`);
    } finally {
      setDrillLoading(false);
      // Auto-hide message after 3 seconds
      setTimeout(() => setDrillMessage(''), 3000);
    }
  }, [drillBreadcrumbs, currentResults, currentSql, sql, metadata, originalQuery]);

  // Handle breadcrumb navigation (go back)
  const handleBreadcrumbClick = useCallback(async (index) => {
    setDrillLoading(true);

    try {
      if (index === -1) {
        // Go back to root - reset to original data
        setDrillBreadcrumbs([]);
        setCurrentQuery(originalQuery);
        setCurrentResults(results);
        setCurrentSql(sql);
        await formatResults(originalQuery, results, sql);
      } else {
        // Go back to specific level
        const newBreadcrumbs = drillBreadcrumbs.slice(0, index + 1);
        setDrillBreadcrumbs(newBreadcrumbs);

        // Build filters from remaining breadcrumbs
        const filters = newBreadcrumbs.map(bc => ({
          dimension: bc.dimension,
          value: bc.value,
          operator: '='
        }));

        // Check if we have connector queries for cross-database drill-down
        const connectorQueries = metadata?.connectorQueries;
        const hasMultiDb = connectorQueries && connectorQueries.length > 1;

        let drillResponse;

        if (hasMultiDb) {
          // Multi-database drill-down
          drillResponse = await apiService.executeDrillDown({
            connectorQueries: connectorQueries,
            filters: filters,
            joinSpecification: metadata?.joinSpecification
          });
        } else if (sql && metadata?.databaseType) {
          // Single-database drill-down
          drillResponse = await apiService.executeDrillDown({
            sql: sql,
            databaseType: metadata.databaseType,
            connectorId: metadata.connectorId,
            filters: filters
          });
        } else {
          // Fallback: client-side filtering
          const filteredResults = results.filter(row => {
            return filters.every(f => {
              const rowValue = row[f.dimension];
              if (rowValue === undefined) return true;
              return String(rowValue) === String(f.value);
            });
          });

          setCurrentResults(filteredResults);
          const drillQuery = `${originalQuery} (filtered: ${filters.map(f => `${f.dimension}=${f.value}`).join(', ')})`;
          setCurrentQuery(drillQuery);
          await formatResults(drillQuery, filteredResults, sql);
          return;
        }

        // Handle API response
        if (drillResponse?.data?.success) {
          const newResults = drillResponse.data.results;
          setCurrentResults(newResults);

          const drillQuery = `${originalQuery} (filtered: ${filters.map(f => `${f.dimension}=${f.value}`).join(', ')})`;
          setCurrentQuery(drillQuery);
          await formatResults(drillQuery, newResults, currentSql);
        }
      }
    } catch (err) {
      console.error('Breadcrumb navigation failed:', err);
    } finally {
      setDrillLoading(false);
    }
  }, [originalQuery, drillBreadcrumbs, sql, results, metadata, currentSql]);

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
    if (!currentResults || currentResults.length === 0) return;
    const headers = Object.keys(currentResults[0]);
    const csvContent = [
      headers.join(','),
      ...currentResults.map((row) =>
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

  // Helper to check if a value is numeric (number or numeric string)
  const isNumericValue = (value) => {
    if (typeof value === 'number') return true;
    if (typeof value === 'string') {
      const cleaned = value.replace(/[$,]/g, '').trim();
      return !isNaN(parseFloat(cleaned)) && isFinite(cleaned);
    }
    return false;
  };

  // Helper to detect ID/key columns that should be treated as categorical even if numeric
  // These are surrogate keys, foreign keys, etc. - NOT metric values to aggregate
  const isIdColumn = (columnName) => {
    const idPatterns = [
      /_sk$/i,           // Surrogate key (data warehouse pattern)
      /_id$/i,           // ID suffix
      /_key$/i,          // Key suffix
      /^id$/i,           // Just "id"
      /_pk$/i,           // Primary key
      /_fk$/i,           // Foreign key
      /_code$/i,         // Code columns (often categorical)
      /customer_?id/i,   // Common patterns
      /product_?id/i,
      /store_?id/i,
      /item_?id/i,
      /order_?id/i,
      /ticket_?number/i,
      /hdemo_?sk/i,      // Household demo surrogate key
      /cdemo_?sk/i,      // Customer demo surrogate key
      /addr_?sk/i,       // Address surrogate key
      /promo_?sk/i,      // Promotion surrogate key
    ];
    return idPatterns.some(pattern => pattern.test(columnName));
  };

  // Helper to detect metric/value columns (actual numbers to aggregate/visualize)
  const isMetricColumn = (columnName, value) => {
    if (!isNumericValue(value)) return false;
    if (isIdColumn(columnName)) return false;

    // Common metric patterns
    const metricPatterns = [
      /price/i, /cost/i, /amount/i, /total/i, /sum/i,
      /revenue/i, /sales/i, /profit/i, /margin/i,
      /quantity/i, /qty/i, /count/i, /num/i,
      /rate/i, /percent/i, /ratio/i, /avg/i,
      /weight/i, /size/i, /length/i, /width/i, /height/i
    ];
    return metricPatterns.some(pattern => pattern.test(columnName));
  };

  // Smart chart type override - analyzes data and suggests better chart when LLM chooses poorly
  const getSmartChartType = (llmType, chartData, xAxis, yAxis) => {
    if (!Array.isArray(chartData) || chartData.length === 0) return llmType;

    const firstRow = chartData[0] || {};
    const keys = Object.keys(firstRow);

    // Enhanced type detection - separates IDs from actual metrics
    const idKeys = keys.filter(k => isIdColumn(k) && isNumericValue(firstRow[k]));
    const metricKeys = keys.filter(k => isMetricColumn(k, firstRow[k]));
    const stringKeys = keys.filter(k => typeof firstRow[k] === 'string' && !isNumericValue(firstRow[k]));
    const numericKeys = keys.filter(k => isNumericValue(firstRow[k]) && !isIdColumn(k));

    // Treat ID columns as categorical for chart selection purposes
    const categoricalKeys = [...stringKeys, ...idKeys];
    const rowCount = chartData.length;

    // Determine what can be used as values for visualization
    // Priority: metricKeys > numericKeys > idKeys (last resort - use ID as count/value)
    const hasValueColumn = metricKeys.length >= 1 || numericKeys.length >= 1 || idKeys.length >= 1;

    // DEBUG: Log what data the smart override sees
    console.log('[SmartOverride] Analyzing:', {
      llmType,
      rowCount,
      keys,
      idKeys,
      metricKeys,
      numericKeys,
      stringKeys,
      categoricalKeys,
      hasValueColumn,
      xAxis: xAxis?.key,
      yAxis: yAxis?.key,
      sample: firstRow
    });

    // Override rules when LLM chose 'bar' but data suggests otherwise
    if (llmType === 'bar') {
      // Rule 1: Single row → metric (NEVER bar for single values)
      if (rowCount === 1) {
        console.log('[SmartOverride] Override: bar → metric (single row)');
        if (metricKeys.length === 1 || numericKeys.length === 1) return 'metric';
        return 'gauge';
      }

      // Rule 2: Time series → line
      const timePatterns = ['date', 'time', 'month', 'year', 'quarter', 'week', 'period', 'day'];
      const hasTimeKey = keys.some(k => timePatterns.some(p => k.toLowerCase().includes(p)));
      if (hasTimeKey && rowCount > 2) {
        console.log('[SmartOverride] Override: bar → line (time series detected)');
        return 'line';
      }

      // Rule 3: Small categorical dataset (2-6 rows) → pie
      // Use categoricalKeys (strings + ID columns) for detection
      // hasValueColumn includes idKeys as fallback when no metrics exist
      if (rowCount >= 2 && rowCount <= 6 && categoricalKeys.length >= 1 && hasValueColumn) {
        console.log('[SmartOverride] Override: bar → pie (small categorical, ' + rowCount + ' rows, categorical keys: ' + categoricalKeys.join(', ') + ')');
        return 'pie';
      }

      // Rule 4: Medium categorical (7-12 rows) → donut (more modern look)
      if (rowCount >= 7 && rowCount <= 12 && categoricalKeys.length >= 1 && hasValueColumn) {
        console.log('[SmartOverride] Override: bar → donut (medium categorical, ' + rowCount + ' rows)');
        return 'donut';
      }

      // Rule 5: Matrix/cross-tab detection (2 categorical + 1 numeric) → heatmap
      if (categoricalKeys.length >= 2 && hasValueColumn && rowCount >= 4) {
        const col1Values = new Set(chartData.map(row => row[categoricalKeys[0]]));
        const col2Values = new Set(chartData.map(row => row[categoricalKeys[1]]));
        // If it looks like a cross-tab (unique combinations)
        if (col1Values.size >= 2 && col2Values.size >= 2 && col1Values.size * col2Values.size >= rowCount * 0.5) {
          console.log('[SmartOverride] Override: bar → heatmap (detected matrix data)');
          return 'heatmap';
        }
      }

      // Rule 6: Long labels → horizontalBar
      if (categoricalKeys.length > 0 && hasValueColumn) {
        const labelKey = xAxis?.key || categoricalKeys[0];
        const avgLen = chartData.reduce((sum, row) => sum + String(row[labelKey] || '').length, 0) / rowCount;
        if (avgLen > 20) {
          console.log('[SmartOverride] Override: bar → horizontalBar (long labels, avg ' + avgLen.toFixed(1) + ' chars)');
          return 'horizontalBar';
        }
      }

      // Rule 7: Many rows with ID columns → treemap for hierarchical view
      if (rowCount > 12 && idKeys.length > 0 && hasValueColumn) {
        console.log('[SmartOverride] Override: bar → treemap (many rows with IDs, ' + rowCount + ' rows)');
        return 'treemap';
      }

      // Rule 8: All numeric but mostly IDs → horizontal bar for better readability
      if (idKeys.length >= keys.length / 2 && hasValueColumn) {
        console.log('[SmartOverride] Override: bar → horizontalBar (mostly ID columns)');
        return 'horizontalBar';
      }

      // Rule 9: String category with ID values (no metrics) - common for dimension tables
      // With 10 rows and a string category, donut is better than bar
      if (rowCount >= 7 && rowCount <= 15 && stringKeys.length >= 1 && idKeys.length >= 1 && metricKeys.length === 0 && numericKeys.length === 0) {
        console.log('[SmartOverride] Override: bar → donut (categorical with ID values, no metrics)');
        return 'donut';
      }
    }

    // Keep bar if none of the override rules matched
    console.log('[SmartOverride] Keeping original type:', llmType);
    return llmType;
  };

  // Valid chart types that ECharts supports
  const validChartTypes = new Set([
    'bar', 'horizontalBar', 'pictorialBar', 'line', 'area', 'themeRiver', 'calendar',
    'pie', 'donut', 'treemap', 'sunburst', 'scatter', 'heatmap', 'boxplot',
    'funnel', 'sankey', 'graph', 'gauge', 'metric', 'radar', 'parallel', 'candlestick'
  ]);

  // Render chart based on type using ECharts
  const renderChart = (component) => {
    const { type: llmType, title, data, xAxis, yAxis, backend_recommended_type } = component.data || {};

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

    // CHART TYPE PRIORITY:
    // 1. Backend recommendation (from ColumnMetadataService - most reliable)
    // 2. Smart override (frontend data analysis)
    // 3. LLM choice (fallback)
    let finalType;

    if (backend_recommended_type && validChartTypes.has(backend_recommended_type)) {
      // Use backend recommendation - it's based on deterministic data analysis
      finalType = backend_recommended_type;
      console.log('[Chart] Using BACKEND recommendation:', finalType, '| LLM wanted:', llmType);
    } else {
      // Fall back to smart override logic
      finalType = getSmartChartType(llmType, chartData, xAxis, yAxis);
      if (finalType !== llmType) {
        console.log('[Chart] Smart override:', llmType, '→', finalType);
      } else {
        console.log('[Chart] Using LLM choice:', llmType);
      }
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

    const echartsType = chartTypeMap[finalType] || 'auto';

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
    return <LoadingSkeleton query={query} />;
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
        {currentResults?.length > 0 && (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <RowsIcon sx={{ fontSize: 16, color: theme.palette.text.disabled }} />
            <Typography variant="caption" color="text.secondary">
              {currentResults.length.toLocaleString()} rows
              {drillBreadcrumbs.length > 0 && ` (filtered from ${results.length.toLocaleString()})`}
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
