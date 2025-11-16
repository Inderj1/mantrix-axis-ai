import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  Stack,
  Chip,
  IconButton,
  Button,
  LinearProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  useTheme,
  alpha,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Speed as SpeedIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  PlayArrow as PlayIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CloudSync as CloudSyncIcon,
  TableChart as TableChartIcon,
  AccountTree as GraphIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import axios from 'axios';

const PipelineManagement = () => {
  const theme = useTheme();
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);
  const [incrementalMode, setIncrementalMode] = useState(true);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);

  useEffect(() => {
    loadPipelineData();
    const interval = setInterval(loadPipelineData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadPipelineData = async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        axios.get('/api/v1/pipeline/status'),
        axios.get('/api/v1/pipeline/history?limit=10'),
      ]);
      setStatus(statusRes.data);
      setHistory(historyRes.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load pipeline data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const executePipeline = async () => {
    setExecuting(true);
    setError(null);
    try {
      const response = await axios.post('/api/v1/pipeline/execute', {
        incremental: incrementalMode,
        table_names: null,
      });
      await loadPipelineData();
      setSelectedRun(response.data);
      setDetailsDialog(true);
    } catch (err) {
      console.error('Failed to execute pipeline:', err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setExecuting(false);
    }
  };

  const viewRunDetails = (run) => {
    setSelectedRun(run);
    setDetailsDialog(true);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return theme.palette.success.main;
      case 'failed':
        return theme.palette.error.main;
      case 'running':
        return theme.palette.info.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon sx={{ color: theme.palette.success.main }} />;
      case 'failed':
        return <ErrorIcon sx={{ color: theme.palette.error.main }} />;
      case 'running':
        return <CircularProgress size={20} />;
      default:
        return <InfoIcon sx={{ color: theme.palette.grey[500] }} />;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box mb={3}>
        <Typography variant="h5" gutterBottom fontWeight={600}>
          Build-Time Pipeline Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Manage schema extraction, RDF building, and vector indexing pipeline
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Status Cards */}
      <Grid container spacing={3} mb={3}>
        {/* Pipeline Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2} mb={2}>
                <CloudSyncIcon sx={{ fontSize: 40, color: theme.palette.primary.main }} />
                <Box>
                  <Typography variant="h6">Pipeline Status</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Current state and execution
                  </Typography>
                </Box>
              </Stack>
              <Divider sx={{ my: 2 }} />
              {status?.last_run ? (
                <Stack spacing={2}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="text.secondary">
                      Last Run
                    </Typography>
                    <Chip
                      label={status.last_run.status}
                      size="small"
                      icon={getStatusIcon(status.last_run.status)}
                      sx={{
                        bgcolor: alpha(getStatusColor(status.last_run.status), 0.1),
                        color: getStatusColor(status.last_run.status),
                      }}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Run ID
                    </Typography>
                    <Typography variant="body2" fontFamily="monospace">
                      {status.last_run.run_id}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Duration
                    </Typography>
                    <Typography variant="body2">
                      {formatDuration(status.last_run.duration_seconds)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Tables Processed
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {status.last_run.tables_processed}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Changes Detected
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {status.last_run.changes_detected}
                    </Typography>
                  </Box>
                  {status.last_run.errors?.length > 0 && (
                    <Alert severity="warning" size="small">
                      {status.last_run.errors.length} error(s) encountered
                    </Alert>
                  )}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary" align="center" py={2}>
                  No pipeline runs yet
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Schedule Info */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2} mb={2}>
                <ScheduleIcon sx={{ fontSize: 40, color: theme.palette.info.main }} />
                <Box>
                  <Typography variant="h6">Schedule</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Automated execution schedule
                  </Typography>
                </Box>
              </Stack>
              <Divider sx={{ my: 2 }} />
              <Stack spacing={2}>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    Next Scheduled Run
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {formatDateTime(status?.next_scheduled_run)}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    Frequency
                  </Typography>
                  <Chip label="Daily at 2:00 AM" size="small" color="info" />
                </Box>
                <Divider />
                <FormControlLabel
                  control={
                    <Switch
                      checked={incrementalMode}
                      onChange={(e) => setIncrementalMode(e.target.checked)}
                      color="primary"
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2">Incremental Mode</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {incrementalMode
                          ? 'Only process changed tables'
                          : 'Full refresh of all tables'}
                      </Typography>
                    </Box>
                  }
                />
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={executing ? <CircularProgress size={20} /> : <PlayIcon />}
                  onClick={executePipeline}
                  disabled={executing}
                  size="large"
                >
                  {executing ? 'Executing Pipeline...' : 'Execute Pipeline Now'}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Pipeline History */}
      <Card>
        <CardContent>
          <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="h6">Pipeline Execution History</Typography>
            <IconButton onClick={loadPipelineData} size="small">
              <RefreshIcon />
            </IconButton>
          </Stack>
          <Divider sx={{ mb: 2 }} />
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Run ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Start Time</TableCell>
                  <TableCell align="right">Duration</TableCell>
                  <TableCell align="right">Tables</TableCell>
                  <TableCell align="right">Changes</TableCell>
                  <TableCell align="right">Errors</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No pipeline runs found
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  history.map((run) => (
                    <TableRow
                      key={run.run_id}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => viewRunDetails(run)}
                    >
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {run.run_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={run.status}
                          size="small"
                          icon={getStatusIcon(run.status)}
                          sx={{
                            bgcolor: alpha(getStatusColor(run.status), 0.1),
                            color: getStatusColor(run.status),
                          }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">
                          {formatDateTime(run.start_time)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">
                          {formatDuration(run.duration_seconds)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={600}>
                          {run.tables_processed}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={600}>
                          {run.changes_detected}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {run.errors?.length > 0 ? (
                          <Chip
                            label={run.errors.length}
                            size="small"
                            color="warning"
                          />
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            0
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              viewRunDetails(run);
                            }}
                          >
                            <InfoIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Run Details Dialog */}
      <Dialog
        open={detailsDialog}
        onClose={() => setDetailsDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Pipeline Run Details
          {selectedRun && (
            <Typography variant="body2" color="text.secondary" fontFamily="monospace">
              {selectedRun.run_id}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedRun && (
            <Stack spacing={3}>
              {/* Overview */}
              <Box>
                <Typography variant="subtitle2" gutterBottom color="text.secondary">
                  Overview
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
                      <Typography variant="caption" color="text.secondary">
                        Status
                      </Typography>
                      <Typography variant="h6">
                        {selectedRun.status}
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.success.main, 0.05) }}>
                      <Typography variant="caption" color="text.secondary">
                        Duration
                      </Typography>
                      <Typography variant="h6">
                        {formatDuration(selectedRun.duration_seconds)}
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.info.main, 0.05) }}>
                      <Typography variant="caption" color="text.secondary">
                        Tables Processed
                      </Typography>
                      <Typography variant="h6">
                        {selectedRun.tables_processed}
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.warning.main, 0.05) }}>
                      <Typography variant="caption" color="text.secondary">
                        Changes Detected
                      </Typography>
                      <Typography variant="h6">
                        {selectedRun.changes_detected}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>

              {/* Phase Stats */}
              {selectedRun.phase_stats && Object.keys(selectedRun.phase_stats).length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom color="text.secondary">
                    Phase Statistics
                  </Typography>
                  <Stack spacing={1}>
                    {Object.entries(selectedRun.phase_stats).map(([phase, stats]) => (
                      <Paper key={phase} sx={{ p: 2 }}>
                        <Typography variant="body2" fontWeight={600} gutterBottom>
                          {phase.replace(/_/g, ' ').toUpperCase()}
                        </Typography>
                        <Grid container spacing={2}>
                          {Object.entries(stats).map(([key, value]) => (
                            <Grid item xs={4} key={key}>
                              <Typography variant="caption" color="text.secondary">
                                {key}
                              </Typography>
                              <Typography variant="body2">
                                {typeof value === 'number' ? value.toLocaleString() : value}
                              </Typography>
                            </Grid>
                          ))}
                        </Grid>
                      </Paper>
                    ))}
                  </Stack>
                </Box>
              )}

              {/* Errors */}
              {selectedRun.errors?.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom color="text.secondary">
                    Errors ({selectedRun.errors.length})
                  </Typography>
                  <List>
                    {selectedRun.errors.map((error, idx) => (
                      <ListItem key={idx}>
                        <ListItemText
                          primary={error}
                          primaryTypographyProps={{
                            variant: 'body2',
                            color: 'error',
                            fontFamily: 'monospace',
                          }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PipelineManagement;
