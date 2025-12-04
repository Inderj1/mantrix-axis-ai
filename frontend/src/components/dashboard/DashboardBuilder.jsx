/**
 * DashboardBuilder - Main dashboard grid layout component
 *
 * Features:
 * - Drag-and-drop widget placement (react-grid-layout)
 * - Edit mode toggle for layout changes
 * - Auto-save on layout change
 * - Responsive grid layout
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import GridLayout from 'react-grid-layout';
import {
  Box,
  Paper,
  IconButton,
  Tooltip,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Snackbar,
  Alert
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Share as ShareIcon,
  Add as AddIcon,
  BarChart as BarChartIcon,
  ShowChart as LineChartIcon,
  PieChart as PieChartIcon,
  TableChart as TableIcon,
  TextFields as TextIcon,
  FilterAlt as FilterIcon,
  CalendarMonth as CalendarIcon,
  Download as DownloadIcon
} from '@mui/icons-material';

import { useDashboardStore } from '../../stores/dashboardStore';
import { useFilterBus } from '../../stores/filterEventBus';
import DashboardWidget from './DashboardWidget';
import DashboardHeader from './DashboardHeader';
import ActiveFilterPills from './ActiveFilterPills';
import WidgetConfigDialog from './WidgetConfigDialog';
import ExportMenu from './ExportMenu';

import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

// Widget type icons for SpeedDial
const WIDGET_TYPES = [
  { type: 'chart', icon: <BarChartIcon />, label: 'Chart', needsQuery: true },
  { type: 'metric', icon: <TextIcon />, label: 'Metric Card', needsQuery: true },
  { type: 'table', icon: <TableIcon />, label: 'Table', needsQuery: true },
  { type: 'date-filter', icon: <CalendarIcon />, label: 'Date Filter', needsQuery: false },
  { type: 'multi-select-filter', icon: <FilterIcon />, label: 'Select Filter', needsQuery: false }
];

const DashboardBuilder = ({ dashboardId, readonly = false }) => {
  const dashboardRef = useRef(null);

  // Store state
  const {
    currentDashboard,
    editMode,
    isLoading,
    error,
    fetchDashboard,
    setEditMode,
    updateLayout,
    addWidget,
    removeWidget,
    saveDashboard,
    generateShareLink,
    clearError,
    restoreState,
    saveState
  } = useDashboardStore();

  const { activeFilters, clearAllFilters } = useFilterBus();

  // Local state
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [configDialogWidget, setConfigDialogWidget] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [exportMenuAnchor, setExportMenuAnchor] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [stateRestored, setStateRestored] = useState(false);

  // Load dashboard on mount
  useEffect(() => {
    if (dashboardId) {
      fetchDashboard(dashboardId);
    }
  }, [dashboardId, fetchDashboard]);

  // Restore state from Redis after dashboard loads
  useEffect(() => {
    const restoreFromRedis = async () => {
      if (currentDashboard?.id && !stateRestored) {
        try {
          const restored = await restoreState(currentDashboard.id);
          if (restored) {
            console.log('Dashboard state restored from Redis');
            setSnackbar({
              open: true,
              message: 'Filters restored from previous session',
              severity: 'info'
            });
          }
          setStateRestored(true);
        } catch (e) {
          console.warn('Could not restore state:', e);
          setStateRestored(true);
        }
      }
    };

    restoreFromRedis();
  }, [currentDashboard?.id, stateRestored, restoreState]);

  // Auto-save state to Redis when filters change
  useEffect(() => {
    if (currentDashboard?.id && stateRestored && Object.keys(activeFilters).length > 0) {
      // Debounce the save
      const timer = setTimeout(() => {
        saveState(currentDashboard.id);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [activeFilters, currentDashboard?.id, stateRestored, saveState]);

  // Convert widgets to grid layout format
  const layout = currentDashboard?.widgets?.map(widget => ({
    i: widget.id,
    x: widget.layout?.x || 0,
    y: widget.layout?.y || 0,
    w: widget.layout?.w || 6,
    h: widget.layout?.h || 3,
    minW: widget.layout?.minW || 2,
    minH: widget.layout?.minH || 2
  })) || [];

  // Handle layout change
  const handleLayoutChange = useCallback((newLayout) => {
    if (editMode && !readonly) {
      updateLayout(newLayout);
      setIsDirty(true);
    }
  }, [editMode, readonly, updateLayout]);

  // Handle adding a new widget
  const handleAddWidget = useCallback((type) => {
    const widgetType = WIDGET_TYPES.find(wt => wt.type === type);
    const isFilterWidget = type.includes('filter');

    // Create widget config based on type
    const widgetConfig = {
      type,
      title: widgetType?.label || type,
      chart_type: type === 'chart' ? 'bar' : null,
      // Filter widgets have smaller default layout
      layout: isFilterWidget ? {
        w: 3,
        h: 2,
        minW: 2,
        minH: 2
      } : undefined,
      // Filter widget specific config
      config: isFilterWidget ? {
        dimension: type === 'date-filter' ? 'date' : 'category'
      } : undefined
    };

    const newWidget = addWidget(widgetConfig);

    // Only open config dialog for widgets that need a query
    if (widgetType?.needsQuery) {
      setConfigDialogWidget(newWidget);
      setConfigDialogOpen(true);
    }

    setIsDirty(true);
  }, [addWidget]);

  // Handle widget edit
  const handleEditWidget = useCallback((widget) => {
    setConfigDialogWidget(widget);
    setConfigDialogOpen(true);
  }, []);

  // Handle widget delete
  const handleDeleteWidget = useCallback((widgetId) => {
    removeWidget(widgetId);
    setIsDirty(true);
    setSnackbar({ open: true, message: 'Widget removed', severity: 'info' });
  }, [removeWidget]);

  // Handle save
  const handleSave = useCallback(async () => {
    try {
      await saveDashboard();
      setIsDirty(false);
      setSnackbar({ open: true, message: 'Dashboard saved', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to save dashboard', severity: 'error' });
    }
  }, [saveDashboard]);

  // Handle share
  const handleShare = useCallback(async () => {
    try {
      const result = await generateShareLink(currentDashboard.id);
      const shareUrl = `${window.location.origin}${result.share_url}`;
      navigator.clipboard.writeText(shareUrl);
      setSnackbar({
        open: true,
        message: 'Share link copied to clipboard!',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to generate share link', severity: 'error' });
    }
  }, [currentDashboard?.id, generateShareLink]);

  // Handle export menu
  const handleExportClick = (event) => {
    setExportMenuAnchor(event.currentTarget);
  };

  // Toggle edit mode
  const handleToggleEdit = useCallback(() => {
    if (editMode && isDirty) {
      // Auto-save when exiting edit mode
      handleSave();
    }
    setEditMode(!editMode);
  }, [editMode, isDirty, handleSave, setEditMode]);

  // Close config dialog
  const handleConfigDialogClose = useCallback((savedWidget) => {
    setConfigDialogOpen(false);
    setConfigDialogWidget(null);
    if (savedWidget) {
      setIsDirty(true);
    }
  }, []);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        Loading dashboard...
      </Box>
    );
  }

  if (!currentDashboard) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        Dashboard not found
      </Box>
    );
  }

  return (
    <Box ref={dashboardRef} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Dashboard Header */}
      <DashboardHeader
        dashboard={currentDashboard}
        editMode={editMode}
        isDirty={isDirty}
        readonly={readonly}
        onToggleEdit={handleToggleEdit}
        onSave={handleSave}
        onShare={handleShare}
        onExport={handleExportClick}
      />

      {/* Active Filter Pills */}
      {Object.keys(activeFilters).length > 0 && (
        <Box sx={{ px: 2, py: 1 }}>
          <ActiveFilterPills />
        </Box>
      )}

      {/* Grid Layout */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
        <GridLayout
          className="dashboard-grid"
          layout={layout}
          cols={12}
          rowHeight={100}
          width={1200}
          isDraggable={editMode && !readonly}
          isResizable={editMode && !readonly}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".drag-handle"
          compactType="vertical"
          preventCollision={false}
        >
          {currentDashboard.widgets?.map(widget => (
            <div key={widget.id}>
              <DashboardWidget
                widget={widget}
                editMode={editMode && !readonly}
                onEdit={() => handleEditWidget(widget)}
                onDelete={() => handleDeleteWidget(widget.id)}
              />
            </div>
          ))}
        </GridLayout>

        {/* Empty state */}
        {(!currentDashboard.widgets || currentDashboard.widgets.length === 0) && (
          <Paper
            sx={{
              p: 4,
              textAlign: 'center',
              color: 'text.secondary',
              backgroundColor: 'background.default'
            }}
          >
            <Box sx={{ mb: 2 }}>
              {editMode ? (
                <>Click the + button to add your first widget</>
              ) : (
                <>This dashboard is empty. Enable edit mode to add widgets.</>
              )}
            </Box>
          </Paper>
        )}
      </Box>

      {/* Add Widget SpeedDial (visible in edit mode) */}
      {editMode && !readonly && (
        <SpeedDial
          ariaLabel="Add widget"
          sx={{ position: 'fixed', bottom: 24, right: 24 }}
          icon={<SpeedDialIcon />}
        >
          {WIDGET_TYPES.map((wt) => (
            <SpeedDialAction
              key={wt.type}
              icon={wt.icon}
              tooltipTitle={wt.label}
              onClick={() => handleAddWidget(wt.type)}
            />
          ))}
        </SpeedDial>
      )}

      {/* Widget Config Dialog */}
      <WidgetConfigDialog
        open={configDialogOpen}
        widget={configDialogWidget}
        onClose={handleConfigDialogClose}
      />

      {/* Export Menu */}
      <ExportMenu
        anchorEl={exportMenuAnchor}
        onClose={() => setExportMenuAnchor(null)}
        dashboardRef={dashboardRef}
        dashboard={currentDashboard}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DashboardBuilder;
