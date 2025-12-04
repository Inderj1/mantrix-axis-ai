import React, { useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  useTheme,
  alpha,
  Chip,
  Tooltip,
} from '@mui/material';
import {
  TableRows as RowsIcon,
  ViewColumn as ColumnsIcon,
  Timer as TimerIcon,
  Storage as TablesIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as MoneyIcon,
  Numbers as NumbersIcon,
} from '@mui/icons-material';

// Stat card component
const StatCard = ({ icon: Icon, value, label, color, tooltip }) => {
  const theme = useTheme();

  const card = (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2,
        bgcolor: alpha(color, 0.08),
        border: `1px solid ${alpha(color, 0.2)}`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0.5,
        minWidth: 100,
        transition: 'all 0.2s ease',
        '&:hover': {
          bgcolor: alpha(color, 0.12),
          transform: 'translateY(-2px)',
        },
      }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: '10px',
          bgcolor: alpha(color, 0.15),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 0.5,
        }}
      >
        <Icon sx={{ color, fontSize: 20 }} />
      </Box>
      <Typography
        variant="h6"
        sx={{
          fontWeight: 700,
          color: theme.palette.text.primary,
          fontSize: '1.25rem',
          lineHeight: 1.2,
        }}
      >
        {value}
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: theme.palette.text.secondary,
          fontSize: '0.7rem',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          fontWeight: 500,
        }}
      >
        {label}
      </Typography>
    </Paper>
  );

  return tooltip ? (
    <Tooltip title={tooltip} arrow placement="top">
      {card}
    </Tooltip>
  ) : card;
};

// Format large numbers with K, M, B suffixes
const formatNumber = (num) => {
  if (num === null || num === undefined) return '—';
  if (typeof num !== 'number') num = parseFloat(num);
  if (isNaN(num)) return '—';

  if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(1) + 'B';
  if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(1) + 'M';
  if (Math.abs(num) >= 1e3) return (num / 1e3).toFixed(1) + 'K';
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

// Format currency
const formatCurrency = (num) => {
  if (num === null || num === undefined) return '—';
  if (typeof num !== 'number') num = parseFloat(num);
  if (isNaN(num)) return '—';

  if (Math.abs(num) >= 1e9) return '$' + (num / 1e9).toFixed(1) + 'B';
  if (Math.abs(num) >= 1e6) return '$' + (num / 1e6).toFixed(1) + 'M';
  if (Math.abs(num) >= 1e3) return '$' + (num / 1e3).toFixed(1) + 'K';
  return '$' + num.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

const SummaryStatsHeader = ({
  rowCount,
  columnCount,
  executionTime,
  tablesUsed,
  results,
  fromCache,
}) => {
  const theme = useTheme();

  // Detect key metrics from results
  const detectedMetrics = useMemo(() => {
    if (!results || results.length === 0) return [];

    const metrics = [];
    const firstRow = results[0];
    const columns = Object.keys(firstRow);

    // Look for revenue/monetary columns
    const monetaryPatterns = /revenue|sales|amount|total|sum|money|cost|price|value/i;
    const countPatterns = /count|quantity|qty|num|number/i;

    columns.forEach((col) => {
      const colLower = col.toLowerCase();
      const values = results.map((r) => r[col]).filter((v) => typeof v === 'number' && !isNaN(v));

      if (values.length === 0) return;

      const sum = values.reduce((a, b) => a + b, 0);
      const avg = sum / values.length;

      if (monetaryPatterns.test(colLower)) {
        metrics.push({
          icon: MoneyIcon,
          value: formatCurrency(sum),
          label: col.replace(/_/g, ' '),
          color: '#10B981', // Green
          tooltip: `Sum of ${col}: ${sum.toLocaleString()}`,
        });
      } else if (countPatterns.test(colLower)) {
        metrics.push({
          icon: NumbersIcon,
          value: formatNumber(sum),
          label: col.replace(/_/g, ' '),
          color: '#F59E0B', // Amber
          tooltip: `Total ${col}: ${sum.toLocaleString()}`,
        });
      }
    });

    // Limit to 2 detected metrics
    return metrics.slice(0, 2);
  }, [results]);

  return (
    <Box sx={{ mb: 3 }}>
      {/* Status bar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          mb: 2,
        }}
      >
        <Chip
          size="small"
          label={fromCache ? 'From cache' : 'Query complete'}
          sx={{
            bgcolor: fromCache
              ? alpha('#F59E0B', 0.1)
              : alpha('#10B981', 0.1),
            color: fromCache ? '#F59E0B' : '#10B981',
            fontWeight: 600,
            fontSize: '0.75rem',
          }}
        />
        {executionTime && (
          <Typography variant="caption" color="text.secondary">
            Completed in {executionTime.toFixed(2)}s
          </Typography>
        )}
      </Box>

      {/* Stats cards */}
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 1.5,
        }}
      >
        <StatCard
          icon={RowsIcon}
          value={formatNumber(rowCount)}
          label="Rows"
          color="#3B82F6" // Blue
          tooltip={`${rowCount?.toLocaleString()} rows returned`}
        />
        <StatCard
          icon={ColumnsIcon}
          value={columnCount}
          label="Columns"
          color="#8B5CF6" // Purple
        />
        {tablesUsed && tablesUsed.length > 0 && (
          <StatCard
            icon={TablesIcon}
            value={tablesUsed.length}
            label="Tables"
            color="#EC4899" // Pink
            tooltip={tablesUsed.join(', ')}
          />
        )}
        {executionTime && (
          <StatCard
            icon={TimerIcon}
            value={executionTime < 1 ? `${(executionTime * 1000).toFixed(0)}ms` : `${executionTime.toFixed(1)}s`}
            label="Time"
            color="#6366F1" // Indigo
          />
        )}
        {detectedMetrics.map((metric, idx) => (
          <StatCard key={idx} {...metric} />
        ))}
      </Box>
    </Box>
  );
};

export default SummaryStatsHeader;
