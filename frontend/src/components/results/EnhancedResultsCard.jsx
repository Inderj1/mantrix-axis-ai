import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  useTheme,
  alpha,
} from '@mui/material';
import {
  TableChart as TableIcon,
  BarChart as ChartIcon,
} from '@mui/icons-material';
import { DataGrid } from '@mui/x-data-grid';

import SummaryStatsHeader from './SummaryStatsHeader';
import ActionsBar from './ActionsBar';

// Helper to format cell values
const formatCellValue = (value, columnName) => {
  if (value === null || value === undefined) return '—';

  const colLower = columnName?.toLowerCase() || '';

  // Currency formatting
  if (colLower.includes('revenue') || colLower.includes('sales') ||
      colLower.includes('amount') || colLower.includes('price') ||
      colLower.includes('cost') || colLower.includes('total')) {
    if (typeof value === 'number') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }).format(value);
    }
  }

  // Percentage formatting
  if (colLower.includes('percent') || colLower.includes('rate') ||
      colLower.includes('margin') || colLower.includes('ratio')) {
    if (typeof value === 'number') {
      return `${(value * (value < 1 ? 100 : 1)).toFixed(1)}%`;
    }
  }

  // Number formatting
  if (typeof value === 'number') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  // Date formatting
  if (value instanceof Date || (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value))) {
    try {
      const date = new Date(value);
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString();
      }
    } catch {
      // Ignore date parsing errors
    }
  }

  return String(value);
};

// Generate columns from data
const generateColumns = (results, theme) => {
  if (!results || results.length === 0) return [];

  const firstRow = results[0];
  return Object.keys(firstRow).map((key, index) => ({
    field: key,
    headerName: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    flex: 1,
    minWidth: 120,
    sortable: true,
    renderCell: (params) => (
      <Box
        sx={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          width: '100%',
        }}
        title={String(params.value ?? '')}
      >
        {formatCellValue(params.value, key)}
      </Box>
    ),
    headerClassName: 'enhanced-header',
  }));
};

const EnhancedResultsCard = ({
  message,
  onViewAnalysis,
  onViewDetailed,
  showChart,
  chartComponent,
}) => {
  const theme = useTheme();
  const [viewMode, setViewMode] = useState('table');
  const [pageSize, setPageSize] = useState(10);

  const {
    sql,
    results,
    resultCount,
    metadata,
  } = message || {};

  // Generate table columns
  const columns = useMemo(
    () => generateColumns(results, theme),
    [results, theme]
  );

  // Prepare rows with IDs
  const rows = useMemo(() => {
    if (!results) return [];
    return results.map((row, idx) => ({
      id: idx,
      ...row,
    }));
  }, [results]);

  const hasResults = results && results.length > 0;

  // Charts require multiple data rows - single row results are aggregate values only
  const chartDataAvailable = useMemo(() => {
    if (!results || !Array.isArray(results)) return false;
    return results.length > 1;
  }, [results]);

  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: 3,
        border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
        overflow: 'hidden',
        bgcolor: theme.palette.background.paper,
      }}
    >
      <Box sx={{ p: 3 }}>
        {/* Summary Stats */}
        <SummaryStatsHeader
          rowCount={resultCount || results?.length || 0}
          columnCount={results?.[0] ? Object.keys(results[0]).length : 0}
          executionTime={metadata?.timing?.total_seconds}
          tablesUsed={metadata?.tablesUsed}
          results={results}
          fromCache={metadata?.fromCache}
        />

        {/* Results Section */}
        {hasResults && (
          <Box>
            {/* Section Header with View Toggle */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                mb: 2,
              }}
            >
              <Typography
                variant="subtitle1"
                sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}
              >
                <TableIcon sx={{ fontSize: 20, color: theme.palette.primary.main }} />
                Results
              </Typography>

              {showChart && chartComponent && (
                <ToggleButtonGroup
                  value={viewMode}
                  exclusive
                  onChange={(e, val) => val && setViewMode(val)}
                  size="small"
                >
                  <ToggleButton value="table" sx={{ px: 2, py: 0.5 }}>
                    <TableIcon sx={{ fontSize: 18, mr: 0.5 }} />
                    Table
                  </ToggleButton>
                  <ToggleButton value="chart" sx={{ px: 2, py: 0.5 }}>
                    <ChartIcon sx={{ fontSize: 18, mr: 0.5 }} />
                    Chart
                  </ToggleButton>
                </ToggleButtonGroup>
              )}
            </Box>

            {/* Table or Chart */}
            {viewMode === 'table' ? (
              <Box
                sx={{
                  height: Math.min(400, rows.length * 52 + 110),
                  width: '100%',
                  '& .enhanced-header': {
                    bgcolor: alpha(theme.palette.primary.main, 0.05),
                    fontWeight: 600,
                    fontSize: '0.85rem',
                  },
                  '& .MuiDataGrid-root': {
                    border: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
                    borderRadius: 2,
                    fontSize: '0.875rem',
                  },
                  '& .MuiDataGrid-cell': {
                    borderColor: alpha(theme.palette.divider, 0.3),
                  },
                  '& .MuiDataGrid-row:nth-of-type(even)': {
                    bgcolor: alpha(theme.palette.action.hover, 0.3),
                  },
                  '& .MuiDataGrid-row:hover': {
                    bgcolor: alpha(theme.palette.primary.main, 0.05),
                  },
                  '& .MuiDataGrid-footerContainer': {
                    borderTop: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
                  },
                }}
              >
                <DataGrid
                  rows={rows}
                  columns={columns}
                  pageSize={pageSize}
                  onPageSizeChange={setPageSize}
                  rowsPerPageOptions={[10, 25, 50, 100]}
                  disableSelectionOnClick
                  density="compact"
                  getRowId={(row) => row.id}
                />
              </Box>
            ) : (
              chartComponent
            )}
          </Box>
        )}

        {/* Actions Bar */}
        <ActionsBar
          results={results}
          sql={sql}
          onViewAnalysis={onViewAnalysis}
          onViewDetailed={onViewDetailed}
          chartDataAvailable={chartDataAvailable}
        />
      </Box>
    </Paper>
  );
};

export default EnhancedResultsCard;
