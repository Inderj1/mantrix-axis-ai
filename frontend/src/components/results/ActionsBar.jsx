import React from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  FileDownload as DownloadIcon,
  ContentCopy as CopyIcon,
  AutoAwesome as InsightsIcon,
  Dashboard as DashboardIcon,
} from '@mui/icons-material';

const ActionsBar = ({
  results,
  sql,
  onExportCSV,
  onCopySQL,
  onViewAnalysis,
  onViewDetailed,
  chartDataAvailable = true,
}) => {
  const theme = useTheme();

  const handleExportCSV = () => {
    if (onExportCSV) {
      onExportCSV();
      return;
    }

    // Default CSV export logic
    if (!results || results.length === 0) return;

    const headers = Object.keys(results[0]);
    const csvContent = [
      headers.join(','),
      ...results.map((row) =>
        headers
          .map((h) => {
            const val = row[h];
            // Escape quotes and wrap in quotes if contains comma
            if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
              return `"${val.replace(/"/g, '""')}"`;
            }
            return val ?? '';
          })
          .join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `query_results_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  const handleCopySQL = () => {
    if (onCopySQL) {
      onCopySQL();
      return;
    }

    if (sql) {
      navigator.clipboard.writeText(sql);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        pt: 2,
        borderTop: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
      }}
    >
      <ButtonGroup size="small" variant="outlined">
        <Tooltip title="Export as CSV">
          <Button
            onClick={handleExportCSV}
            disabled={!results || results.length === 0}
            startIcon={<DownloadIcon />}
            sx={{
              textTransform: 'none',
              fontSize: '0.8rem',
            }}
          >
            Export CSV
          </Button>
        </Tooltip>

        {sql && (
          <Tooltip title="Copy SQL query">
            <Button
              onClick={handleCopySQL}
              startIcon={<CopyIcon />}
              sx={{
                textTransform: 'none',
                fontSize: '0.8rem',
              }}
            >
              Copy SQL
            </Button>
          </Tooltip>
        )}
      </ButtonGroup>

      <Box sx={{ flex: 1 }} />

      {onViewAnalysis && (
        <Tooltip title="Get AI-powered insights, trends, and recommendations">
          <Button
            size="small"
            variant="text"
            onClick={onViewAnalysis}
            startIcon={<InsightsIcon />}
            sx={{
              textTransform: 'none',
              fontSize: '0.8rem',
              color: theme.palette.text.secondary,
              '&:hover': {
                color: theme.palette.primary.main,
              },
            }}
          >
            AI Insights
          </Button>
        </Tooltip>
      )}

      {onViewDetailed && (
        <Tooltip
          title={
            chartDataAvailable
              ? "View as interactive dashboard with charts and metrics"
              : "Dashboard requires multiple data rows for charts. This query returned aggregate values only."
          }
        >
          <span>
            <Button
              size="small"
              variant="text"
              onClick={onViewDetailed}
              disabled={!chartDataAvailable}
              startIcon={<DashboardIcon />}
              sx={{
                textTransform: 'none',
                fontSize: '0.8rem',
                color: chartDataAvailable
                  ? theme.palette.text.secondary
                  : theme.palette.text.disabled,
                '&:hover': {
                  color: chartDataAvailable ? theme.palette.primary.main : undefined,
                },
                '&.Mui-disabled': {
                  color: theme.palette.text.disabled,
                },
              }}
            >
              Dashboard View
            </Button>
          </span>
        </Tooltip>
      )}
    </Box>
  );
};

export default ActionsBar;
