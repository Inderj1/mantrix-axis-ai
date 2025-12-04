/**
 * DashboardCreationPreview - Shows preview of AI-generated dashboard before creation
 *
 * Displays when user types "Create a sales dashboard..." in chat
 * Shows widget previews with sample data and allows user to confirm or modify
 */
import React, { useState, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  Chip,
  IconButton,
  TextField,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Tooltip,
  LinearProgress,
  Divider
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  BarChart as BarChartIcon,
  ShowChart as LineChartIcon,
  PieChart as PieChartIcon,
  TableChart as TableIcon,
  Add as AddIcon,
  AutoAwesome as AIIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';

const CHART_TYPE_ICONS = {
  bar: <BarChartIcon />,
  line: <LineChartIcon />,
  pie: <PieChartIcon />,
  area: <LineChartIcon />,
  scatter: <BarChartIcon />,
  table: <TableIcon />,
  metric: <DashboardIcon />
};

const WidgetPreviewCard = ({ widget, onEdit, onRemove }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(widget.title);
  const [editedQuery, setEditedQuery] = useState(widget.query);

  const hasError = !!widget.error;
  const hasData = widget.execution_preview?.sample_data?.length > 0;

  const handleSaveEdit = () => {
    onEdit(widget.id, { title: editedTitle, query: editedQuery });
    setIsEditing(false);
  };

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        border: hasError ? '2px solid' : '1px solid',
        borderColor: hasError ? 'error.main' : 'divider'
      }}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          {hasError ? (
            <ErrorIcon color="error" sx={{ mr: 1 }} />
          ) : (
            <CheckIcon color="success" sx={{ mr: 1 }} />
          )}

          {isEditing ? (
            <TextField
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              size="small"
              fullWidth
              variant="outlined"
            />
          ) : (
            <Typography variant="subtitle1" sx={{ fontWeight: 'medium', flexGrow: 1 }} noWrap>
              {widget.title}
            </Typography>
          )}

          <Chip
            icon={CHART_TYPE_ICONS[widget.suggested_chart_type] || <BarChartIcon />}
            label={widget.suggested_chart_type || 'auto'}
            size="small"
            sx={{ ml: 1 }}
          />
        </Box>

        {/* Query */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            Query:
          </Typography>
          {isEditing ? (
            <TextField
              value={editedQuery}
              onChange={(e) => setEditedQuery(e.target.value)}
              size="small"
              fullWidth
              multiline
              rows={2}
              variant="outlined"
            />
          ) : (
            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
              "{widget.query}"
            </Typography>
          )}
        </Box>

        {/* Error Message */}
        {hasError && (
          <Alert severity="error" sx={{ mb: 1 }}>
            <Typography variant="caption">{widget.error}</Typography>
          </Alert>
        )}

        {/* Data Preview */}
        {hasData && (
          <Box>
            <Typography variant="caption" color="text.secondary">
              Preview ({widget.execution_preview.row_count} rows):
            </Typography>
            <Box
              sx={{
                maxHeight: 100,
                overflow: 'auto',
                mt: 0.5,
                p: 1,
                bgcolor: 'action.hover',
                borderRadius: 1,
                fontSize: 11
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {widget.execution_preview.columns?.slice(0, 3).map((col, i) => (
                      <th key={i} style={{ textAlign: 'left', padding: '2px 4px', fontSize: 10 }}>
                        {col.name}
                      </th>
                    ))}
                    {widget.execution_preview.columns?.length > 3 && (
                      <th style={{ fontSize: 10 }}>...</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {widget.execution_preview.sample_data?.slice(0, 3).map((row, i) => (
                    <tr key={i}>
                      {Object.values(row).slice(0, 3).map((val, j) => (
                        <td key={j} style={{ padding: '2px 4px', fontSize: 10 }}>
                          {typeof val === 'number' ? val.toLocaleString() : String(val).slice(0, 15)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Box>
          </Box>
        )}

        {/* Chart Recommendations */}
        {widget.execution_preview?.chart_recommendations?.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Recommended:
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
              {widget.execution_preview.chart_recommendations.slice(0, 3).map((ct) => (
                <Chip
                  key={ct}
                  label={ct}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: 10, height: 20 }}
                />
              ))}
            </Box>
          </Box>
        )}
      </CardContent>

      <CardActions sx={{ justifyContent: 'flex-end', pt: 0 }}>
        {isEditing ? (
          <>
            <Button size="small" onClick={() => setIsEditing(false)}>Cancel</Button>
            <Button size="small" variant="contained" onClick={handleSaveEdit}>Save</Button>
          </>
        ) : (
          <>
            <Tooltip title="Edit widget">
              <IconButton size="small" onClick={() => setIsEditing(true)}>
                <EditIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Remove widget">
              <IconButton size="small" onClick={() => onRemove(widget.id)} color="error">
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        )}
      </CardActions>
    </Card>
  );
};

const DashboardCreationPreview = ({
  open,
  onClose,
  previewData,
  originalQuery,
  onRefresh
}) => {
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [dashboardName, setDashboardName] = useState(previewData?.dashboard_name || 'New Dashboard');
  const [widgets, setWidgets] = useState(previewData?.widgets || []);
  const [error, setError] = useState(null);

  // Update state when previewData changes
  React.useEffect(() => {
    if (previewData) {
      setDashboardName(previewData.dashboard_name || 'New Dashboard');
      setWidgets(previewData.widgets || []);
    }
  }, [previewData]);

  const handleEditWidget = useCallback((widgetId, updates) => {
    setWidgets(prev => prev.map(w =>
      w.id === widgetId ? { ...w, ...updates } : w
    ));
  }, []);

  const handleRemoveWidget = useCallback((widgetId) => {
    setWidgets(prev => prev.filter(w => w.id !== widgetId));
  }, []);

  const handleCreate = async () => {
    if (!previewData?.preview_id) {
      setError('No preview available. Please try again.');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const response = await api.post('/api/v1/dashboards/confirm-creation', null, {
        params: { preview_id: previewData.preview_id }
      });

      const result = response.data;

      // Navigate to the new dashboard
      onClose();
      navigate(result.dashboard_url);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const validWidgets = widgets.filter(w => !w.error);
  const errorWidgets = widgets.filter(w => w.error);

  if (!previewData) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '60vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AIIcon color="primary" />
          <Typography variant="h6">Create Dashboard from Chat</Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {/* Original Query */}
        <Alert severity="info" sx={{ mb: 2 }} icon={<AIIcon />}>
          <Typography variant="body2">
            <strong>Your request:</strong> "{originalQuery}"
          </Typography>
        </Alert>

        {/* Dashboard Name */}
        <Box sx={{ mb: 3 }}>
          <TextField
            label="Dashboard Name"
            value={dashboardName}
            onChange={(e) => setDashboardName(e.target.value)}
            fullWidth
            size="small"
          />
          {previewData.dashboard_description && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {previewData.dashboard_description}
            </Typography>
          )}
        </Box>

        {/* Confidence Indicator */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            AI Confidence: {Math.round(previewData.confidence * 100)}%
          </Typography>
          <LinearProgress
            variant="determinate"
            value={previewData.confidence * 100}
            color={previewData.confidence > 0.7 ? 'success' : previewData.confidence > 0.4 ? 'warning' : 'error'}
            sx={{ height: 6, borderRadius: 3 }}
          />
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Widgets Grid */}
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Widgets to Create ({validWidgets.length} ready, {errorWidgets.length} with errors)
        </Typography>

        <Grid container spacing={2}>
          {widgets.map((widget) => (
            <Grid item xs={12} sm={6} key={widget.id}>
              <WidgetPreviewCard
                widget={widget}
                onEdit={handleEditWidget}
                onRemove={handleRemoveWidget}
              />
            </Grid>
          ))}
        </Grid>

        {/* Empty State */}
        {widgets.length === 0 && (
          <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'action.hover' }}>
            <Typography color="text.secondary">
              No widgets to create. Add at least one widget.
            </Typography>
          </Paper>
        )}

        {/* Global Filters */}
        {previewData.global_filters && Object.keys(previewData.global_filters).length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Global Filters:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
              {Object.entries(previewData.global_filters).map(([key, value]) => (
                <Chip key={key} label={`${key}: ${value}`} size="small" />
              ))}
            </Box>
          </Box>
        )}

        {/* Error Message */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isCreating}>
          Cancel
        </Button>
        <Button
          variant="outlined"
          onClick={onRefresh}
          disabled={isCreating}
        >
          Regenerate
        </Button>
        <Button
          variant="contained"
          onClick={handleCreate}
          disabled={isCreating || validWidgets.length === 0}
          startIcon={isCreating ? <CircularProgress size={16} /> : <DashboardIcon />}
        >
          {isCreating ? 'Creating...' : `Create Dashboard (${validWidgets.length} widgets)`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DashboardCreationPreview;
