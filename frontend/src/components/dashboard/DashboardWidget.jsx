/**
 * DashboardWidget - Container for individual dashboard widgets
 *
 * Features:
 * - Renders chart, metric, table, or filter widgets
 * - Handles query execution and data loading
 * - Supports cross-chart filtering via click handlers
 * - Drill-down navigation with breadcrumbs
 * - Edit/delete controls in edit mode
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Paper,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Menu,
  MenuItem,
  Tooltip,
  Breadcrumbs,
  Link,
  Chip
} from '@mui/material';
import {
  DragIndicator as DragIcon,
  MoreVert as MoreIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  FilterAlt as FilterIcon,
  ArrowBack as BackIcon
} from '@mui/icons-material';

import { useDashboardStore } from '../../stores/dashboardStore';
import { useFilterBus } from '../../stores/filterEventBus';
import api from '../../services/api';

// Import visualization components
import EChartsVisualization from '../EChartsVisualization';

// Import filter components
import { DateRangeFilter, MultiSelectFilter } from './filters';

const DashboardWidget = ({
  widget,
  editMode = false,
  onEdit,
  onDelete
}) => {
  // Store hooks
  const { setWidgetData, widgetData } = useDashboardStore();
  const { publishFilter, activeFilters, subscribe, unsubscribe } = useFilterBus();

  // Local state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [chartMetadata, setChartMetadata] = useState(null);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [drillBreadcrumbs, setDrillBreadcrumbs] = useState([]);

  // Get cached data if available
  const cachedData = widgetData?.[widget.id];

  // Execute widget query
  const executeQuery = useCallback(async (query, additionalFilters = {}) => {
    if (!query) return;

    setIsLoading(true);
    setError(null);

    try {
      // Build filter context
      const filterContext = useFilterBus.getState().buildFilterContext();
      const modifiedQuery = filterContext ? `${query} (${filterContext})` : query;

      const response = await api.post('/api/v1/query', {
        question: modifiedQuery,
        options: { execute: true }
      });

      const result = response.data;

      // Store data
      setData(result.execution?.results || []);
      setChartMetadata({
        chart_recommendations: result.chart_recommendations,
        dimensions: result.dimensions,
        measures: result.measures,
        time_columns: result.time_columns,
        drill_paths: result.drill_paths,
        semantic_types: result.semantic_types,
        visualization_config: result.visualization_config
      });

      // Cache in store
      setWidgetData(widget.id, {
        data: result.execution?.results,
        columns: result.execution?.columns,
        metadata: chartMetadata
      });

    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  }, [widget.id, setWidgetData]);

  // Initial load - skip for filter/text widgets
  useEffect(() => {
    const skipQueryTypes = ['date-filter', 'multi-select-filter', 'text'];
    if (skipQueryTypes.includes(widget.type)) {
      return; // These widget types don't need data fetching
    }

    if (widget.query && !cachedData) {
      executeQuery(widget.query);
    } else if (cachedData) {
      setData(cachedData.data);
      setChartMetadata(cachedData.metadata);
    }
  }, [widget.query, widget.type, cachedData, executeQuery]);

  // Subscribe to filter changes - only for data widgets (not filter widgets)
  useEffect(() => {
    const skipQueryTypes = ['date-filter', 'multi-select-filter', 'text'];
    if (skipQueryTypes.includes(widget.type)) {
      return; // Filter widgets don't need to re-fetch on filter changes
    }

    const handleFilterChange = (filters) => {
      // Re-execute query when filters change
      if (widget.query) {
        executeQuery(widget.query);
      }
    };

    const unsub = subscribe(widget.id, handleFilterChange);
    return () => unsub();
  }, [widget.id, widget.type, widget.query, subscribe, executeQuery]);

  // Handle chart click (cross-filtering + drill-down) - ECharts event format
  const handleChartClick = useCallback((params) => {
    if (!params) return;

    const dimension = chartMetadata?.dimensions?.[0] || params.seriesName || 'value';
    // ECharts provides name for category axis values, value for numeric
    const value = params.name || params.value;

    if (dimension && value) {
      // Publish filter for cross-filtering
      publishFilter(dimension, value);

      // Always try drill-down - API will auto-detect hierarchy
      // This enables drill-down even without pre-configured paths
      handleDrillDown(dimension, value);
    }
  }, [chartMetadata, publishFilter, handleDrillDown]);

  // Available hierarchies from API
  const [availableHierarchies, setAvailableHierarchies] = useState([]);

  // Handle drill-down with auto-hierarchy detection
  const handleDrillDown = useCallback(async (dimension, value) => {
    // Add to breadcrumbs
    setDrillBreadcrumbs(prev => [...prev, { dimension, value }]);
    setIsLoading(true);

    try {
      // Call enhanced drill-down API with auto-detection
      const response = await api.post('/api/v1/dashboards/drill-down', {
        base_query: widget.query,
        drill_dimension: dimension,
        filter_value: value,
        // Let API auto-detect next dimension if not in metadata
        next_dimension: null,
        connector_id: widget.connector_id || chartMetadata?.connector_id,
        table: widget.table || chartMetadata?.table,
        measure_column: widget.measure || chartMetadata?.measures?.[0]
      });

      // Update data with drill results
      setData(response.data.data || response.data.results || []);

      // Store available hierarchies for UI hints
      if (response.data.available_hierarchies) {
        setAvailableHierarchies(response.data.available_hierarchies);
      }

      // Update chart metadata with drill info
      setChartMetadata(prev => ({
        ...prev,
        drill_paths: response.data.available_hierarchies?.map(h => h.path) || prev?.drill_paths,
        current_drill_level: response.data.next_dimension
      }));

      // Save drill state for restoration
      try {
        const { useDashboardStore } = await import('../../stores/dashboardStore');
        useDashboardStore.getState().setDrillPath(widget.id, [
          ...drillBreadcrumbs,
          { dimension, value }
        ]);
      } catch (e) {
        console.warn('Could not save drill state:', e);
      }

    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  }, [widget.query, widget.id, widget.connector_id, widget.table, widget.measure, chartMetadata, drillBreadcrumbs]);

  // Handle breadcrumb navigation
  const handleBreadcrumbClick = useCallback((index) => {
    if (index === -1) {
      // Go back to root
      setDrillBreadcrumbs([]);
      executeQuery(widget.query);
    } else {
      // Go back to specific level
      setDrillBreadcrumbs(prev => prev.slice(0, index + 1));
      // Re-execute query with filters up to that level
      executeQuery(widget.query);
    }
  }, [widget.query, executeQuery]);

  // Render chart based on type
  const renderContent = () => {
    // Filter and text widgets don't need loading/data states
    const noDataTypes = ['date-filter', 'multi-select-filter', 'text'];
    const isNoDataWidget = noDataTypes.includes(widget.type);

    if (!isNoDataWidget && isLoading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
          <CircularProgress />
        </Box>
      );
    }

    if (!isNoDataWidget && error) {
      return (
        <Box sx={{ p: 2, color: 'error.main' }}>
          <Typography variant="body2">{error}</Typography>
        </Box>
      );
    }

    if (!isNoDataWidget && (!data || data.length === 0)) {
      if (!widget.query) {
        return (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'text.secondary' }}>
            <Typography>Click edit to configure this widget</Typography>
          </Box>
        );
      }
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'text.secondary' }}>
          <Typography>No data</Typography>
        </Box>
      );
    }

    // Render based on widget type
    switch (widget.type) {
      case 'chart':
        // Map chart types for ECharts
        const chartTypeMap = {
          'bar': 'bar',
          'line': 'line',
          'pie': 'pie',
          'donut': 'donut',
          'area': 'area',
          'scatter': 'scatter',
          'horizontal_bar': 'horizontalBar',
          'heatmap': 'heatmap',
          'treemap': 'treemap',
          'funnel': 'funnel'
        };
        const chartType = widget.chart_type || chartMetadata?.chart_recommendations?.[0] || 'auto';
        const echartsType = chartTypeMap[chartType] || chartType;

        return (
          <EChartsVisualization
            data={data}
            chartType={echartsType}
            height="100%"
            showToolbox={true}
            showDataZoom={data?.length > 15}
            onChartClick={handleChartClick}
          />
        );

      case 'metric':
        // Use ECharts metric visualization for single values
        return (
          <EChartsVisualization
            data={data}
            chartType="metric"
            height="100%"
            showToolbox={false}
            showDataZoom={false}
          />
        );

      case 'table':
        return (
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {Object.keys(data[0] || {}).map(key => (
                    <th key={key} style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 100).map((row, i) => (
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
          </Box>
        );

      case 'date-filter':
        return (
          <DateRangeFilter
            dimension={widget.config?.dimension || 'date'}
            title={widget.title}
            showPresets={widget.config?.showPresets !== false}
            initialPreset={widget.config?.initialPreset}
          />
        );

      case 'multi-select-filter':
        return (
          <MultiSelectFilter
            dimension={widget.config?.dimension || 'category'}
            title={widget.title}
            values={widget.config?.values || []}
            fetchValues={widget.config?.fetchValues}
          />
        );

      case 'text':
        return (
          <Box sx={{ p: 2 }}>
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
              {widget.config?.content || 'Add text content...'}
            </Typography>
          </Box>
        );

      default:
        return <Typography>Unknown widget type: {widget.type}</Typography>;
    }
  };

  return (
    <Paper
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: editMode ? '2px dashed' : '1px solid',
        borderColor: editMode ? 'primary.main' : 'divider'
      }}
      elevation={editMode ? 3 : 1}
    >
      {/* Widget Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 1,
          py: 0.5,
          borderBottom: '1px solid',
          borderColor: 'divider',
          backgroundColor: 'background.default'
        }}
      >
        {/* Drag Handle */}
        {editMode && (
          <Tooltip title="Drag to move">
            <Box className="drag-handle" sx={{ cursor: 'grab', mr: 1, display: 'flex' }}>
              <DragIcon fontSize="small" color="action" />
            </Box>
          </Tooltip>
        )}

        {/* Title */}
        <Typography variant="subtitle2" sx={{ flexGrow: 1, fontWeight: 'medium' }} noWrap>
          {widget.title}
        </Typography>

        {/* Filter indicator */}
        {Object.keys(activeFilters).length > 0 && (
          <Chip
            icon={<FilterIcon fontSize="small" />}
            label="Filtered"
            size="small"
            color="primary"
            variant="outlined"
            sx={{ mr: 1, height: 20 }}
          />
        )}

        {/* Actions */}
        <Tooltip title="Refresh">
          <IconButton size="small" onClick={() => executeQuery(widget.query)}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>

        {editMode && (
          <>
            <Tooltip title="Edit">
              <IconButton size="small" onClick={onEdit}>
                <EditIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton size="small" onClick={onDelete} color="error">
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        )}
      </Box>

      {/* Drill-down breadcrumbs */}
      {drillBreadcrumbs.length > 0 && (
        <Box sx={{ px: 1, py: 0.5, backgroundColor: 'action.hover' }}>
          <Breadcrumbs separator=">" maxItems={4}>
            <Link
              component="button"
              variant="caption"
              onClick={() => handleBreadcrumbClick(-1)}
              sx={{ cursor: 'pointer' }}
            >
              All
            </Link>
            {drillBreadcrumbs.map((bc, idx) => (
              <Link
                key={idx}
                component="button"
                variant="caption"
                onClick={() => handleBreadcrumbClick(idx)}
                sx={{ cursor: 'pointer' }}
              >
                {bc.value}
              </Link>
            ))}
          </Breadcrumbs>
        </Box>
      )}

      {/* Widget Content */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden', p: 1 }}>
        {renderContent()}
      </Box>
    </Paper>
  );
};

export default DashboardWidget;
