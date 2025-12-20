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
  LinearProgress,
  Snackbar,
  Alert,
  Slide
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  NotificationsActive as NotificationsActiveIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenIcon,
  Clear as ClearIcon,
  FiberNew as NewIcon
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

// Slide transition for snackbar
const SlideTransition = (props) => <Slide {...props} direction="up" />;

const QueryHistoryDropdown = ({ onViewResults }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [pendingQueries, setPendingQueries] = useState([]);
  const [recentQueries, setRecentQueries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0); // New completions user hasn't seen
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success', query: null });
  const [seenCompletions, setSeenCompletions] = useState(() => {
    // Load seen completions from localStorage
    try {
      return new Set(JSON.parse(localStorage.getItem('seenQueryCompletions') || '[]'));
    } catch {
      return new Set();
    }
  });
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
      if (eventType === 'queryComplete') {
        fetchHistory();
        // Show toast notification for completed queries
        const { metadata, result } = data;
        const rowCount = result?.result?.execution?.row_count || 0;
        setSnackbar({
          open: true,
          message: `Query completed: "${metadata?.question?.slice(0, 40)}${metadata?.question?.length > 40 ? '...' : ''}" returned ${rowCount.toLocaleString()} rows`,
          severity: 'success',
          query: { executionId: data.executionId, ...metadata }
        });
        // Increment unread count
        setUnreadCount(prev => prev + 1);
      } else if (eventType === 'queryError') {
        fetchHistory();
        // Show toast notification for failed queries
        const { metadata } = data;
        setSnackbar({
          open: true,
          message: `Query failed: "${metadata?.question?.slice(0, 40)}${metadata?.question?.length > 40 ? '...' : ''}"`,
          severity: 'error',
          query: { executionId: data.executionId, ...metadata }
        });
        setUnreadCount(prev => prev + 1);
      } else if (eventType === 'queryAdded' || eventType === 'queryRemoved') {
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
    // Clear unread count when opening dropdown
    setUnreadCount(0);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') return;
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const handleSnackbarClick = () => {
    if (snackbar.query && onViewResults) {
      onViewResults(snackbar.query);
    }
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const handleViewResults = (query) => {
    handleClose();
    if (onViewResults) {
      onViewResults(query);
    }
  };

  const handleCancelQuery = async (executionId) => {
    try {
      // Cancel on backend
      await apiService.cancelQuery(executionId);
      // Remove from local tracking
      backgroundQueryService.removeQuery(executionId);
      // Refresh
      fetchHistory();
    } catch (error) {
      console.error('[QueryHistoryDropdown] Failed to cancel query:', error);
      // Still remove locally even if backend fails
      backgroundQueryService.removeQuery(executionId);
      fetchHistory();
    }
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

  const totalBadgeCount = pendingCount + unreadCount;
  const hasActivity = totalBadgeCount > 0;

  return (
    <>
      <Tooltip title={hasActivity ? `${pendingCount} running, ${unreadCount} new` : "Notifications"}>
        <IconButton
          onClick={handleClick}
          size="large"
          sx={{
            color: hasActivity ? 'primary.main' : '#5f6368',
            '&:hover': {
              color: 'primary.main',
              backgroundColor: 'rgba(0, 0, 0, 0.04)',
            },
            animation: unreadCount > 0 ? 'pulse 2s infinite' : 'none',
            '@keyframes pulse': {
              '0%': { transform: 'scale(1)' },
              '50%': { transform: 'scale(1.1)' },
              '100%': { transform: 'scale(1)' },
            },
          }}
        >
          <Badge
            badgeContent={totalBadgeCount}
            color={unreadCount > 0 ? 'error' : 'primary'}
            max={9}
          >
            {hasActivity ? <NotificationsActiveIcon /> : <NotificationsIcon />}
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
              <Box sx={{ px: 2, py: 1, bgcolor: 'background.default', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  RUNNING ({pendingQueries.length})
                </Typography>
                <Button
                  size="small"
                  color="error"
                  onClick={async () => {
                    try {
                      // Clear from backend (marks as expired)
                      await apiService.clearStalePendingQueries(0); // 0 hours = clear all
                      // Clear local tracking
                      backgroundQueryService.clearAll();
                      // Refresh the list
                      fetchHistory();
                    } catch (error) {
                      console.error('[QueryHistoryDropdown] Failed to clear queries:', error);
                    }
                  }}
                  sx={{ fontSize: '0.65rem', py: 0, minWidth: 'auto' }}
                >
                  Clear All
                </Button>
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
              <NotificationsIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                No notifications yet
              </Typography>
              <Typography variant="caption" color="text.disabled">
                Background query updates will appear here
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

      {/* Toast notification for query completions */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={8000}
        onClose={handleSnackbarClose}
        TransitionComponent={SlideTransition}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbar.severity}
          variant="filled"
          sx={{
            width: '100%',
            cursor: 'pointer',
            '&:hover': { opacity: 0.9 }
          }}
          onClick={handleSnackbarClick}
          action={
            <Button color="inherit" size="small" onClick={handleSnackbarClick}>
              VIEW
            </Button>
          }
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default QueryHistoryDropdown;
