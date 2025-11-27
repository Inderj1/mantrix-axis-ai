/**
 * WidgetConfigDialog - Configure widget settings (query, chart type, etc.)
 */
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Tabs,
  Tab,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  BarChart as BarIcon,
  ShowChart as LineIcon,
  PieChart as PieIcon,
  ScatterPlot as ScatterIcon,
  StackedLineChart as AreaIcon,
  TableChart as TableIcon
} from '@mui/icons-material';

import { useDashboardStore } from '../../stores/dashboardStore';
import api from '../../services/api';

const CHART_TYPES = [
  { value: 'bar', label: 'Bar Chart', icon: <BarIcon /> },
  { value: 'line', label: 'Line Chart', icon: <LineIcon /> },
  { value: 'pie', label: 'Pie Chart', icon: <PieIcon /> },
  { value: 'scatter', label: 'Scatter Plot', icon: <ScatterIcon /> },
  { value: 'area', label: 'Area Chart', icon: <AreaIcon /> },
  { value: 'table', label: 'Table', icon: <TableIcon /> }
];

const WidgetConfigDialog = ({ open, widget, onClose }) => {
  const { updateWidget } = useDashboardStore();

  // Form state
  const [title, setTitle] = useState('');
  const [query, setQuery] = useState('');
  const [chartType, setChartType] = useState('bar');
  const [activeTab, setActiveTab] = useState(0);

  // Preview state
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [recommendations, setRecommendations] = useState(null);

  // Initialize form when widget changes
  useEffect(() => {
    if (widget) {
      setTitle(widget.title || '');
      setQuery(widget.query || '');
      setChartType(widget.chart_type || 'bar');
      setPreviewData(null);
      setRecommendations(null);
    }
  }, [widget]);

  // Preview query
  const handlePreview = async () => {
    if (!query.trim()) return;

    setPreviewLoading(true);
    setPreviewError(null);

    try {
      const response = await api.post('/api/v1/query', {
        question: query,
        options: { execute: true }
      });

      setPreviewData(response.data.execution?.results || []);
      setRecommendations({
        chart_recommendations: response.data.chart_recommendations,
        dimensions: response.data.dimensions,
        measures: response.data.measures
      });

      // Auto-select recommended chart type
      if (response.data.chart_recommendations?.length > 0 && !chartType) {
        setChartType(response.data.chart_recommendations[0]);
      }
    } catch (err) {
      setPreviewError(err.response?.data?.detail || err.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Save widget
  const handleSave = () => {
    if (widget) {
      updateWidget(widget.id, {
        title,
        query,
        chart_type: chartType
      });
      onClose(widget);
    }
  };

  // Cancel
  const handleCancel = () => {
    onClose(null);
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        {widget?.id ? 'Edit Widget' : 'New Widget'}
      </DialogTitle>

      <DialogContent>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 2 }}>
          <Tab label="Query" />
          <Tab label="Appearance" />
        </Tabs>

        {/* Query Tab */}
        {activeTab === 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Widget Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              fullWidth
              size="small"
            />

            <TextField
              label="Natural Language Query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              multiline
              rows={3}
              fullWidth
              placeholder="e.g., Show me revenue by country for the last 12 months"
              helperText="Describe the data you want to visualize in plain English"
            />

            <Button
              variant="outlined"
              onClick={handlePreview}
              disabled={!query.trim() || previewLoading}
            >
              {previewLoading ? <CircularProgress size={20} /> : 'Preview'}
            </Button>

            {/* Preview Error */}
            {previewError && (
              <Alert severity="error">{previewError}</Alert>
            )}

            {/* Recommendations */}
            {recommendations && (
              <Box sx={{ p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Detected:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Dimensions:</strong> {recommendations.dimensions?.join(', ') || 'None'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Measures:</strong> {recommendations.measures?.join(', ') || 'None'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Recommended charts:</strong> {recommendations.chart_recommendations?.join(', ') || 'table'}
                </Typography>
              </Box>
            )}

            {/* Preview Data */}
            {previewData && previewData.length > 0 && (
              <Box sx={{ maxHeight: 200, overflow: 'auto', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr>
                      {Object.keys(previewData[0] || {}).map(key => (
                        <th key={key} style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd', backgroundColor: '#f5f5f5' }}>
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.slice(0, 5).map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val, j) => (
                          <td key={j} style={{ padding: 8, borderBottom: '1px solid #eee' }}>
                            {typeof val === 'number' ? val.toLocaleString() : String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {previewData.length > 5 && (
                  <Typography variant="caption" sx={{ p: 1, display: 'block', textAlign: 'center' }}>
                    Showing 5 of {previewData.length} rows
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        )}

        {/* Appearance Tab */}
        {activeTab === 1 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Chart Type</InputLabel>
              <Select
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                label="Chart Type"
              >
                {CHART_TYPES.map(ct => (
                  <MenuItem key={ct.value} value={ct.value}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {ct.icon}
                      {ct.label}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Recommended charts */}
            {recommendations?.chart_recommendations && (
              <Box>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  Recommended for your data:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                  {recommendations.chart_recommendations.map(ct => {
                    const chartInfo = CHART_TYPES.find(c => c.value === ct);
                    return chartInfo ? (
                      <Button
                        key={ct}
                        size="small"
                        variant={chartType === ct ? 'contained' : 'outlined'}
                        onClick={() => setChartType(ct)}
                        startIcon={chartInfo.icon}
                      >
                        {chartInfo.label}
                      </Button>
                    ) : null;
                  })}
                </Box>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleCancel}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default WidgetConfigDialog;
