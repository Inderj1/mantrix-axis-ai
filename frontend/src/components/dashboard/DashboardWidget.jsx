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
// We'll use dynamic imports or conditionally render based on widget type
const PlotlyVisualization = React.lazy(() => import('../PlotlyVisualization'));

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

  // Handle chart click (cross-filtering)
  const handleChartClick = useCallback((event) => {
    if (!event.points || event.points.length === 0) return;

    const point = event.points[0];
    const dimension = chartMetadata?.dimensions?.[0] || 'value';
    const value = point.x || point.label || point.y;

    if (dimension && value) {
      publishFilter(dimension, value);
    }
  }, [chartMetadata, publishFilter]);

  // Handle drill-down
  const handleDrillDown = useCallback(async (dimension, value) => {
    if (!chartMetadata?.drill_paths?.length) return;

    const drillPath = chartMetadata.drill_paths[0];
    const currentIndex = drillPath.indexOf(dimension);

    if (currentIndex === -1 || currentIndex >= drillPath.length - 1) return;

    const nextDimension = drillPath[currentIndex + 1];

    // Add to breadcrumbs
    setDrillBreadcrumbs(prev => [...prev, { dimension, value }]);

    // Generate drill-down query
    try {
      const response = await api.post('/api/v1/dashboards/drill-down', {
        base_query: widget.query,
        drill_dimension: dimension,
        filter_value: value,
        next_dimension: nextDimension
      });

      setData(response.data.data);
    } catch (err) {
      setError(err.message);
    }
  }, [widget.query, chartMetadata]);

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
        return (
          <React.Suspense fallback={<CircularProgress />}>
            <PlotlyVisualization
              data={data}
              title={widget.title}
              chartType={widget.chart_type || chartMetadata?.chart_recommendations?.[0] || 'bar'}
              enableCrossFilter={true}
              onClick={handleChartClick}
              dimensions={chartMetadata?.dimensions}
              measures={chartMetadata?.measures}
              drillPaths={chartMetadata?.drill_paths}
              onDrillDown={handleDrillDown}
            />
          </React.Suspense>
        );

      case 'metric':
        const value = data[0]?.[Object.keys(data[0])[0]];
        const formattedValue = typeof value === 'number'
          ? value.toLocaleString()
          : value;
        return (
          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%'
          }}>
            <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
              {formattedValue}
            </Typography>
          </Box>
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
