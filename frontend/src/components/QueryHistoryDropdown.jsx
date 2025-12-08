/**
 * QueryHistoryDropdown - Top navigation dropdown for background query tracking
 *
 * Features:
 * - Badge showing count of pending queries
 * - Dropdown menu with query list
 * - Pending queries with spinner and progress
 * - Completed queries with checkmark
 * - Failed queries with error icon
 * - Click to view results
 * - Relative timestamps
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Box,
  Typography,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Button,
  Tooltip,
  LinearProgress
} from '@mui/material';
import {
  History as HistoryIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import { backgroundQueryService } from '../services/backgroundQueryService';
import { apiService } from '../services/api';

// Format relative time
const formatRelativeTime = (timestamp) => {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (seconds < 60) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return new Date(timestamp).toLocaleDateString();
};

// Format execution time
const formatDuration = (seconds) => {
  if (!seconds) return '';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
};

const QueryHistoryDropdown = ({ onViewResults }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [pendingQueries, setPendingQueries] = useState([]);
  const [recentQueries, setRecentQueries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const open = Boolean(anchorEl);

  // Fetch query history
  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      const [pendingResponse, historyResponse] = await Promise.all([
        apiService.getPendingQueries(),
        apiService.getQueryHistory({ limit: 10 })
      ]);

      // Get pending from both service and API
      const servicePending = backgroundQueryService.getPendingQueries();
      const apiPending = pendingResponse.data?.queries || [];

      // Merge and deduplicate
      const pendingMap = new Map();
      [...servicePending, ...apiPending].forEach(q => {
        const id = q.executionId || q.execution_id;
        if (!pendingMap.has(id)) {
          pendingMap.set(id, {
            executionId: id,
            question: q.question,
            sql: q.sql,
            status: 'running',
            startTime: q.startTime || new Date(q.started_at).getTime(),
            progress: q.progress || 0,
            phase: q.phase || 'processing'
          });
        }
      });
      setPendingQueries(Array.from(pendingMap.values()));
      setPendingCount(pendingMap.size);

      // Recent completed/failed queries
      const completed = (historyResponse.data?.queries || [])
        .filter(q => q.status !== 'running')
        .map(q => ({
          executionId: q.execution_id,
          question: q.question,
          sql: q.sql,
          status: q.status,
          startTime: new Date(q.started_at).getTime(),
          endTime: q.completed_at ? new Date(q.completed_at).getTime() : null,
          executionTime: q.execution_time_seconds,
          rowCount: q.result_summary?.row_count || 0,
          error: q.error
        }));
      setRecentQueries(completed.slice(0, 5));
    } catch (error) {
      console.error('[QueryHistoryDropdown] Failed to fetch history:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Listen for background query events
  useEffect(() => {
    const unsubscribe = backgroundQueryService.addEventListener((eventType, data) => {
      if (eventType === 'queryComplete' || eventType === 'queryError' ||
          eventType === 'queryAdded' || eventType === 'queryRemoved') {
        fetchHistory();
      } else if (eventType === 'queryProgress') {
        // Update progress for specific query
        setPendingQueries(prev =>
          prev.map(q =>
            q.executionId === data.executionId
              ? { ...q, progress: data.status.progress, phase: data.status.phase }
              : q
          )
        );
      }
    });

    // Sync with server on mount
    backgroundQueryService.syncWithServer();
    fetchHistory();

    return unsubscribe;
  }, [fetchHistory]);

  // Refresh count periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setPendingCount(backgroundQueryService.getPendingCount());
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
    fetchHistory();
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleViewResults = (query) => {
    handleClose();
    if (onViewResults) {
      onViewResults(query);
    }
  };

  const handleCancelQuery = (executionId) => {
    backgroundQueryService.removeQuery(executionId);
    fetchHistory();
  };

  const renderQueryItem = (query, isRecent = false) => {
    const isPending = query.status === 'running';
    const isError = query.status === 'error';
    const isComplete = query.status === 'complete';

    return (
      <ListItem
        key={query.executionId}
        sx={{
          py: 1.5,
          px: 2,
          borderRadius: 1,
          mb: 0.5,
          bgcolor: isPending ? 'action.hover' : 'transparent',
          '&:hover': { bgcolor: 'action.hover' }
        }}
        secondaryAction={
          isPending ? (
            <Tooltip title="Cancel">
              <IconButton size="small" onClick={() => handleCancelQuery(query.executionId)}>
                <ClearIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          ) : isComplete ? (
            <Tooltip title="View Results">
              <IconButton size="small" onClick={() => handleViewResults(query)}>
                <OpenIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          ) : null
        }
      >
        <ListItemIcon sx={{ minWidth: 36 }}>
          {isPending && <CircularProgress size={20} />}
          {isComplete && <CompleteIcon color="success" />}
          {isError && <ErrorIcon color="error" />}
        </ListItemIcon>
        <ListItemText
          primary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: 200
                }}
              >
                {query.question}
              </Typography>
            </Box>
          }
          secondary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                {formatRelativeTime(query.startTime)}
              </Typography>
              {isPending && query.progress > 0 && (
                <Chip
                  label={`${query.progress}%`}
                  size="small"
                  sx={{ height: 18, fontSize: '0.65rem' }}
                />
              )}
              {isComplete && query.rowCount > 0 && (
                <Chip
                  label={`${query.rowCount.toLocaleString()} rows`}
                  size="small"
                  color="success"
                  sx={{ height: 18, fontSize: '0.65rem' }}
                />
              )}
              {isComplete && query.executionTime && (
                <Typography variant="caption" color="text.secondary">
                  {formatDuration(query.executionTime)}
                </Typography>
              )}
              {isError && (
                <Chip
                  label="Failed"
                  size="small"
                  color="error"
                  sx={{ height: 18, fontSize: '0.65rem' }}
                />
              )}
            </Box>
          }
        />
      </ListItem>
    );
  };

  return (
    <>
      <Tooltip title="Query History">
        <IconButton
          onClick={handleClick}
          size="large"
          sx={{
            color: pendingCount > 0 ? 'primary.main' : 'inherit'
          }}
        >
          <Badge
            badgeContent={pendingCount}
            color="primary"
            max={9}
          >
            <HistoryIcon />
          </Badge>
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        PaperProps={{
          sx: {
            width: 380,
            maxHeight: 500,
            overflow: 'hidden'
          }
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Query History
          </Typography>
          <IconButton size="small" onClick={fetchHistory} disabled={loading}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Box>

        <Divider />

        {loading && <LinearProgress sx={{ position: 'absolute', top: 48, left: 0, right: 0 }} />}

        <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
          {/* Pending Queries */}
          {pendingQueries.length > 0 && (
            <>
              <Box sx={{ px: 2, py: 1, bgcolor: 'background.default' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  RUNNING ({pendingQueries.length})
                </Typography>
              </Box>
              <List dense sx={{ py: 0 }}>
                {pendingQueries.map(q => renderQueryItem(q, false))}
              </List>
            </>
          )}

          {/* Recent Queries */}
          {recentQueries.length > 0 && (
            <>
              <Box sx={{ px: 2, py: 1, bgcolor: 'background.default' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  RECENT
                </Typography>
              </Box>
              <List dense sx={{ py: 0 }}>
                {recentQueries.map(q => renderQueryItem(q, true))}
              </List>
            </>
          )}

          {/* Empty State */}
          {!loading && pendingQueries.length === 0 && recentQueries.length === 0 && (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <HistoryIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                No query history yet
              </Typography>
              <Typography variant="caption" color="text.disabled">
                Long-running queries will appear here
              </Typography>
            </Box>
          )}
        </Box>

        <Divider />

        <Box sx={{ p: 1, display: 'flex', justifyContent: 'center' }}>
          <Button
            size="small"
            color="primary"
            onClick={() => {
              handleClose();
              // Navigate to full history page if available
            }}
          >
            View All History
          </Button>
        </Box>
      </Menu>
    </>
  );
};

export default QueryHistoryDropdown;
