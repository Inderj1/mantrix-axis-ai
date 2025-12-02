/**
 * MultiQueryAccordion Component
 *
 * Displays multiple SQL queries from cross-connector queries in a stacked accordion view.
 * Supports per-query editing, re-execution, and join specification editing.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
  IconButton,
  Box,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  CircularProgress,
  Tooltip,
  Snackbar,
  Alert
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CloseIcon from '@mui/icons-material/Close';
import AceEditor from 'react-ace';
import 'ace-builds/src-noconflict/mode-sql';
import 'ace-builds/src-noconflict/theme-monokai';
import 'ace-builds/src-noconflict/theme-github';

import { apiService } from '../services/api';

// Database brand colors for visual identification
const DATABASE_COLORS = {
  bigquery: '#4285F4',      // Google Blue
  snowflake: '#29B5E8',     // Snowflake Blue
  postgresql: '#336791',    // PostgreSQL Blue
  redshift: '#8C4FFF',      // AWS Purple
  databricks: '#FF3621',    // Databricks Red
  mysql: '#00758F',         // MySQL Blue
  sqlserver: '#CC2927'      // SQL Server Red
};

// Human-readable database names
const DATABASE_NAMES = {
  bigquery: 'BigQuery',
  snowflake: 'Snowflake',
  postgresql: 'PostgreSQL',
  redshift: 'Redshift',
  databricks: 'Databricks',
  mysql: 'MySQL',
  sqlserver: 'SQL Server'
};

export default function MultiQueryAccordion({
  connectorQueries,
  joinSpec,
  initialResults,
  onResultsUpdate,
  editorTheme = 'monokai',
  sessionId  // Session ID for secure backend re-join
}) {
  // Panel expansion state - all expanded by default
  const [expandedPanels, setExpandedPanels] = useState(
    Object.keys(connectorQueries || {})
  );

  // Per-connector state
  const [editedQueries, setEditedQueries] = useState({});
  const [isEditing, setIsEditing] = useState({});
  const [isExecuting, setIsExecuting] = useState({});
  const [queryResults, setQueryResults] = useState({});
  const [queryErrors, setQueryErrors] = useState({});

  // Join specification state
  const [editedJoinSpec, setEditedJoinSpec] = useState(null);
  const [isJoinExpanded, setIsJoinExpanded] = useState(false);

  // UI feedback
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Initialize results cache from props
  useEffect(() => {
    if (initialResults && Object.keys(initialResults).length > 0) {
      setQueryResults(initialResults);
    }
  }, [initialResults]);

  // Handle accordion panel toggle
  const handlePanelChange = (panel) => (event, isExpanded) => {
    setExpandedPanels(prev =>
      isExpanded
        ? [...prev, panel]
        : prev.filter(p => p !== panel)
    );
  };

  // Copy SQL to clipboard
  const handleCopy = useCallback(async (sql, connectorId) => {
    try {
      await navigator.clipboard.writeText(sql);
      setSnackbar({
        open: true,
        message: `SQL copied for ${connectorId}`,
        severity: 'success'
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: 'Failed to copy to clipboard',
        severity: 'error'
      });
    }
  }, []);

  // Toggle edit mode for a connector
  const handleToggleEdit = useCallback((connectorId) => {
    setIsEditing(prev => ({
      ...prev,
      [connectorId]: !prev[connectorId]
    }));
    // Initialize edited query if entering edit mode
    if (!isEditing[connectorId] && connectorQueries[connectorId]) {
      setEditedQueries(prev => ({
        ...prev,
        [connectorId]: connectorQueries[connectorId].sql
      }));
    }
  }, [connectorQueries, isEditing]);

  // Cancel edit mode
  const handleCancelEdit = useCallback((connectorId) => {
    setIsEditing(prev => ({ ...prev, [connectorId]: false }));
    setEditedQueries(prev => {
      const updated = { ...prev };
      delete updated[connectorId];
      return updated;
    });
    setQueryErrors(prev => {
      const updated = { ...prev };
      delete updated[connectorId];
      return updated;
    });
  }, []);

  // Execute single connector query and re-join via backend
  const handleRunSingleQuery = useCallback(async (connectorId) => {
    const queryData = connectorQueries[connectorId];
    const sql = editedQueries[connectorId] || queryData.sql;

    setIsExecuting(prev => ({ ...prev, [connectorId]: true }));
    setQueryErrors(prev => {
      const updated = { ...prev };
      delete updated[connectorId];
      return updated;
    });

    try {
      // Use secure backend re-join if session ID is available
      if (sessionId) {
        const joinSpecToUse = editedJoinSpec || joinSpec;
        const response = await apiService.rejoinCrossConnectorResults({
          session_id: sessionId,
          edited_connector_id: connectorId,
          edited_sql: sql,
          join_specification: joinSpecToUse ? {
            type: joinSpecToUse.type,
            condition: joinSpecToUse.condition,
            left_key: joinSpecToUse.left_key,
            right_key: joinSpecToUse.right_key
          } : undefined
        });

        if (response.data?.success) {
          // Update results from backend re-join
          onResultsUpdate?.(response.data.results);

          setSnackbar({
            open: true,
            message: `Query executed and re-joined (${response.data.row_count} rows, strategy: ${response.data.join_strategy})`,
            severity: 'success'
          });
        } else {
          throw new Error(response.data?.error || 'Re-join failed');
        }
      } else {
        // Fallback: execute single query without re-join (legacy mode)
        const response = await apiService.executeSingleConnectorQuery({
          connector_id: connectorId,
          sql: sql,
          database_type: queryData.database_type
        });

        // Cache the new results locally
        const newResults = {
          ...queryResults,
          [connectorId]: response.data?.results || []
        };
        setQueryResults(newResults);

        setSnackbar({
          open: true,
          message: `Query executed (${response.data?.results?.length || 0} rows). Note: Re-join requires session ID.`,
          severity: 'warning'
        });
      }

      // Exit edit mode on success
      setIsEditing(prev => ({ ...prev, [connectorId]: false }));

    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Query execution failed';
      setQueryErrors(prev => ({
        ...prev,
        [connectorId]: errorMessage
      }));
      setSnackbar({
        open: true,
        message: `Execution failed: ${errorMessage}`,
        severity: 'error'
      });
    } finally {
      setIsExecuting(prev => ({ ...prev, [connectorId]: false }));
    }
  }, [connectorQueries, editedQueries, queryResults, joinSpec, editedJoinSpec, onResultsUpdate, sessionId]);

  // Re-join results with updated join specification (via backend)
  const handleReJoin = useCallback(async () => {
    if (!sessionId) {
      setSnackbar({
        open: true,
        message: 'Cannot re-join: session ID required for secure backend re-join',
        severity: 'warning'
      });
      return;
    }

    const joinSpecToUse = editedJoinSpec || joinSpec;

    try {
      setIsExecuting(prev => {
        const updated = { ...prev };
        Object.keys(connectorQueries).forEach(id => { updated[id] = true; });
        return updated;
      });

      const response = await apiService.rejoinCrossConnectorResults({
        session_id: sessionId,
        // No edited_connector_id or edited_sql - just re-join with new spec
        join_specification: joinSpecToUse ? {
          type: joinSpecToUse.type,
          condition: joinSpecToUse.condition,
          left_key: joinSpecToUse.left_key,
          right_key: joinSpecToUse.right_key
        } : undefined
      });

      if (response.data?.success) {
        onResultsUpdate?.(response.data.results);
        setSnackbar({
          open: true,
          message: `Re-joined ${response.data.row_count} rows (strategy: ${response.data.join_strategy})`,
          severity: 'success'
        });
      } else {
        throw new Error(response.data?.error || 'Re-join failed');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Re-join failed';
      setSnackbar({
        open: true,
        message: `Re-join failed: ${errorMessage}`,
        severity: 'error'
      });
    } finally {
      setIsExecuting(prev => {
        const updated = { ...prev };
        Object.keys(connectorQueries).forEach(id => { updated[id] = false; });
        return updated;
      });
    }
  }, [connectorQueries, joinSpec, editedJoinSpec, onResultsUpdate, sessionId]);

  // Close snackbar
  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  if (!connectorQueries || Object.keys(connectorQueries).length === 0) {
    return null;
  }

  const hasJoinSpecChanges = editedJoinSpec && (
    editedJoinSpec.type !== joinSpec?.type ||
    editedJoinSpec.condition !== joinSpec?.condition
  );

  return (
    <Box sx={{ mt: 2 }}>
      {/* Query Accordions */}
      {Object.entries(connectorQueries).map(([connectorId, queryData]) => {
        const dbType = queryData.database_type?.toLowerCase();
        const dbColor = DATABASE_COLORS[dbType] || '#757575';
        const dbName = DATABASE_NAMES[dbType] || queryData.database_type;
        const currentSql = editedQueries[connectorId] || queryData.sql;
        const hasEdits = editedQueries[connectorId] && editedQueries[connectorId] !== queryData.sql;
        const error = queryErrors[connectorId];

        return (
          <Accordion
            key={connectorId}
            expanded={expandedPanels.includes(connectorId)}
            onChange={handlePanelChange(connectorId)}
            sx={{
              mb: 1,
              bgcolor: 'grey.900',
              '&:before': { display: 'none' },
              border: error ? '1px solid #f44336' : 'none'
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ color: 'grey.400' }} />}
              sx={{ minHeight: 48 }}
            >
              <Chip
                label={dbName}
                size="small"
                sx={{
                  bgcolor: dbColor,
                  color: 'white',
                  fontWeight: 600,
                  mr: 2
                }}
              />
              <Typography variant="subtitle2" sx={{ color: 'grey.300', flexGrow: 1 }}>
                {connectorId}
              </Typography>
              {queryData.tables_used && (
                <Typography variant="caption" sx={{ color: 'grey.500', mr: 2 }}>
                  {queryData.tables_used.join(', ')}
                </Typography>
              )}
              {isExecuting[connectorId] && (
                <CircularProgress size={16} sx={{ mr: 1 }} />
              )}
              {hasEdits && (
                <Chip label="Modified" size="small" color="warning" sx={{ mr: 1 }} />
              )}
            </AccordionSummary>

            <AccordionDetails sx={{ p: 0 }}>
              <Box sx={{ position: 'relative' }}>
                <AceEditor
                  mode="sql"
                  theme={editorTheme}
                  value={currentSql}
                  readOnly={!isEditing[connectorId]}
                  onChange={(newSql) => setEditedQueries(prev => ({
                    ...prev,
                    [connectorId]: newSql
                  }))}
                  width="100%"
                  maxLines={25}
                  minLines={4}
                  showPrintMargin={false}
                  fontSize={13}
                  setOptions={{
                    showLineNumbers: true,
                    tabSize: 2
                  }}
                  style={{
                    borderRadius: 0,
                    opacity: isEditing[connectorId] ? 1 : 0.9
                  }}
                />

                {/* Action buttons */}
                <Box
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    display: 'flex',
                    gap: 0.5,
                    bgcolor: 'rgba(0,0,0,0.5)',
                    borderRadius: 1,
                    p: 0.5
                  }}
                >
                  <Tooltip title="Copy SQL">
                    <IconButton
                      size="small"
                      onClick={() => handleCopy(currentSql, connectorId)}
                      sx={{ color: 'grey.300' }}
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>

                  {isEditing[connectorId] ? (
                    <>
                      <Tooltip title="Cancel">
                        <IconButton
                          size="small"
                          onClick={() => handleCancelEdit(connectorId)}
                          sx={{ color: 'grey.300' }}
                        >
                          <CloseIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Run Query">
                        <IconButton
                          size="small"
                          onClick={() => handleRunSingleQuery(connectorId)}
                          disabled={isExecuting[connectorId]}
                          sx={{ color: '#4caf50' }}
                        >
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </>
                  ) : (
                    <Tooltip title="Edit SQL">
                      <IconButton
                        size="small"
                        onClick={() => handleToggleEdit(connectorId)}
                        sx={{ color: 'grey.300' }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </Box>

              {/* Error display */}
              {error && (
                <Alert severity="error" sx={{ m: 1, borderRadius: 1 }}>
                  {error}
                </Alert>
              )}

              {/* Run button when editing */}
              {isEditing[connectorId] && (
                <Box sx={{ p: 1, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleCancelEdit(connectorId)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={isExecuting[connectorId] ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                    onClick={() => handleRunSingleQuery(connectorId)}
                    disabled={isExecuting[connectorId]}
                    color="success"
                  >
                    Run This Query
                  </Button>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        );
      })}

      {/* Join Specification Accordion */}
      {joinSpec && (
        <Accordion
          expanded={isJoinExpanded}
          onChange={(e, expanded) => setIsJoinExpanded(expanded)}
          sx={{
            bgcolor: 'grey.800',
            '&:before': { display: 'none' }
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'grey.400' }} />}>
            <Chip
              label="JOIN"
              size="small"
              color="warning"
              sx={{ mr: 2 }}
            />
            <Typography variant="subtitle2" sx={{ color: 'grey.300' }}>
              {(editedJoinSpec?.type || joinSpec.type)} Join
            </Typography>
            {hasJoinSpecChanges && (
              <Chip label="Modified" size="small" color="info" sx={{ ml: 2 }} />
            )}
          </AccordionSummary>

          <AccordionDetails>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel sx={{ color: 'grey.400' }}>Join Type</InputLabel>
                  <Select
                    value={editedJoinSpec?.type || joinSpec.type}
                    label="Join Type"
                    onChange={(e) => setEditedJoinSpec(prev => ({
                      ...(prev || joinSpec),
                      type: e.target.value
                    }))}
                    sx={{ color: 'grey.200' }}
                  >
                    <MenuItem value="INNER">INNER</MenuItem>
                    <MenuItem value="LEFT">LEFT</MenuItem>
                    <MenuItem value="RIGHT">RIGHT</MenuItem>
                    <MenuItem value="FULL">FULL OUTER</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Join Condition"
                  value={editedJoinSpec?.condition || joinSpec.condition}
                  onChange={(e) => setEditedJoinSpec(prev => ({
                    ...(prev || joinSpec),
                    condition: e.target.value
                  }))}
                  fullWidth
                  size="small"
                  sx={{
                    '& .MuiInputBase-input': { color: 'grey.200', fontFamily: 'monospace' },
                    '& .MuiInputLabel-root': { color: 'grey.400' }
                  }}
                />
              </Box>

              {hasJoinSpecChanges && (
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setEditedJoinSpec(null)}
                  >
                    Reset
                  </Button>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={handleReJoin}
                    color="primary"
                  >
                    Re-Join Results
                  </Button>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
