/**
 * WidgetInsightBadge - AI insight indicator for dashboard widgets
 *
 * Shows a small badge on widgets with AI-generated insights
 * Clicking opens a popover with the insight details
 */

import React, { useState } from 'react';
import {
  Badge,
  IconButton,
  Popover,
  Box,
  Typography,
  Chip,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  AutoAwesome as InsightsIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import api from '../../services/api';

const WidgetInsightBadge = ({
  widgetType,
  widgetTitle,
  metricName,
  currentData,
  historicalData,
  insight: preloadedInsight,
  onInsightGenerated
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [insight, setInsight] = useState(preloadedInsight);
  const [error, setError] = useState(null);

  const handleClick = async (event) => {
    setAnchorEl(event.currentTarget);

    // If we don't have an insight yet, fetch one
    if (!insight && !loading) {
      setLoading(true);
      setError(null);

      try {
        const response = await api.post('/api/v1/widgets/insight', {
          widget_type: widgetType,
          widget_title: widgetTitle,
          metric_name: metricName || widgetTitle,
          current_data: currentData || {},
          historical_data: historicalData
        });

        setInsight(response.data);
        if (onInsightGenerated) {
          onInsightGenerated(response.data);
        }
      } catch (err) {
        console.error('Failed to get widget insight:', err);
        setError('Unable to generate insight');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const getTrendIcon = () => {
    if (!insight?.trend) return <TrendingFlatIcon fontSize="small" />;

    switch (insight.trend.toLowerCase()) {
      case 'up':
      case 'increasing':
        return <TrendingUpIcon fontSize="small" color="success" />;
      case 'down':
      case 'decreasing':
        return <TrendingDownIcon fontSize="small" color="error" />;
      case 'anomaly':
        return <WarningIcon fontSize="small" color="warning" />;
      default:
        return <TrendingFlatIcon fontSize="small" color="action" />;
    }
  };

  const getConfidenceColor = () => {
    if (!insight?.confidence) return 'default';
    switch (insight.confidence.toLowerCase()) {
      case 'high':
        return 'success';
      case 'low':
        return 'warning';
      default:
        return 'default';
    }
  };

  const open = Boolean(anchorEl);
  const hasInsight = insight || preloadedInsight;

  return (
    <>
      <Tooltip title={hasInsight ? 'View AI insight' : 'Get AI insight'}>
        <IconButton
          size="small"
          onClick={handleClick}
          sx={{
            color: hasInsight ? 'primary.main' : 'action.disabled',
            '&:hover': {
              color: 'primary.main',
              backgroundColor: 'primary.50'
            }
          }}
        >
          <Badge
            variant="dot"
            color={hasInsight ? 'primary' : 'default'}
            invisible={!hasInsight}
          >
            <InsightsIcon fontSize="small" />
          </Badge>
        </IconButton>
      </Tooltip>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right'
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right'
        }}
        PaperProps={{
          sx: { maxWidth: 320, p: 2 }
        }}
      >
        <Box>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <InsightsIcon color="primary" fontSize="small" />
            <Typography variant="subtitle2">
              AI Insight
            </Typography>
          </Box>

          {/* Content */}
          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 2 }}>
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">
                Analyzing data...
              </Typography>
            </Box>
          ) : error ? (
            <Typography variant="body2" color="error">
              {error}
            </Typography>
          ) : insight ? (
            <>
              {/* Trend indicator */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                {getTrendIcon()}
                <Chip
                  label={insight.trend || 'stable'}
                  size="small"
                  variant="outlined"
                  sx={{ height: 22, fontSize: '0.75rem' }}
                />
                <Chip
                  label={`${insight.confidence || 'medium'} confidence`}
                  size="small"
                  color={getConfidenceColor()}
                  variant="outlined"
                  sx={{ height: 22, fontSize: '0.75rem' }}
                />
              </Box>

              {/* Insight text */}
              <Typography variant="body2" sx={{ mb: 1 }}>
                {insight.insight}
              </Typography>

              {/* Comparison if available */}
              {insight.comparison && (
                <Typography variant="caption" color="text.secondary">
                  {insight.comparison}
                </Typography>
              )}
            </>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Click to generate an AI insight for this widget
            </Typography>
          )}
        </Box>
      </Popover>
    </>
  );
};

export default WidgetInsightBadge;
