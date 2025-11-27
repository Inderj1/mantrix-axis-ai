/**
 * Dashboard Store - Zustand state management for dashboards
 *
 * Manages:
 * - Dashboard CRUD operations
 * - Widget management
 * - Layout state
 * - Global filters
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';

// Default widget layout
const DEFAULT_LAYOUT = {
  x: 0,
  y: 0,
  w: 6,
  h: 3,
  minW: 2,
  minH: 2
};

// Generate unique widget ID
const generateWidgetId = () => Math.random().toString(36).substring(2, 10);

export const useDashboardStore = create(
  persist(
    (set, get) => ({
      // State
      dashboards: [],
      currentDashboard: null,
      isLoading: false,
      error: null,
      editMode: false,
      widgetData: {}, // Cached query results per widget: { widgetId: { data, columns, ... } }

      // Dashboard CRUD Actions
      fetchDashboards: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.get('/api/v1/dashboards/');
          set({ dashboards: response.data, isLoading: false });
          return response.data;
        } catch (error) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

      fetchDashboard: async (dashboardId) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.get(`/api/v1/dashboards/${dashboardId}`);
          set({ currentDashboard: response.data, isLoading: false });
          return response.data;
        } catch (error) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

      createDashboard: async (dashboardData) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post('/api/v1/dashboards/', dashboardData);
          const newDashboard = response.data;
          set(state => ({
            dashboards: [...state.dashboards, newDashboard],
            currentDashboard: newDashboard,
            isLoading: false
          }));
          return newDashboard;
        } catch (error) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

      updateDashboard: async (dashboardId, updates) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.put(`/api/v1/dashboards/${dashboardId}`, updates);
          const updatedDashboard = response.data;
          set(state => ({
            dashboards: state.dashboards.map(d =>
              d.id === dashboardId ? updatedDashboard : d
            ),
            currentDashboard: state.currentDashboard?.id === dashboardId
              ? updatedDashboard
              : state.currentDashboard,
            isLoading: false
          }));
          return updatedDashboard;
        } catch (error) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

      deleteDashboard: async (dashboardId) => {
        set({ isLoading: true, error: null });
        try {
          await api.delete(`/api/v1/dashboards/${dashboardId}`);
          set(state => ({
            dashboards: state.dashboards.filter(d => d.id !== dashboardId),
            currentDashboard: state.currentDashboard?.id === dashboardId
              ? null
              : state.currentDashboard,
            isLoading: false
          }));
        } catch (error) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

      // Local state management (optimistic updates)
      setCurrentDashboard: (dashboard) => {
        set({ currentDashboard: dashboard });
      },

      setEditMode: (editMode) => {
        set({ editMode });
      },

      toggleEditMode: () => {
        set(state => ({ editMode: !state.editMode }));
      },

      // Widget Management
      addWidget: (widgetConfig) => {
        const newWidget = {
          id: generateWidgetId(),
          type: 'chart',
          title: 'New Widget',
          query: '',
          chart_type: null,
          layout: { ...DEFAULT_LAYOUT },
          filters: null,
          drill_path: null,
          config: null,
          ...widgetConfig
        };

        set(state => {
          if (!state.currentDashboard) return state;

          // Calculate next available position
          const widgets = state.currentDashboard.widgets || [];
          const maxY = widgets.reduce((max, w) => Math.max(max, (w.layout?.y || 0) + (w.layout?.h || 3)), 0);
          newWidget.layout.y = maxY;

          return {
            currentDashboard: {
              ...state.currentDashboard,
              widgets: [...widgets, newWidget]
            }
          };
        });

        return newWidget;
      },

      updateWidget: (widgetId, updates) => {
        set(state => {
          if (!state.currentDashboard) return state;

          return {
            currentDashboard: {
              ...state.currentDashboard,
              widgets: state.currentDashboard.widgets.map(w =>
                w.id === widgetId ? { ...w, ...updates } : w
              )
            }
          };
        });
      },

      removeWidget: (widgetId) => {
        set(state => {
          if (!state.currentDashboard) return state;

          return {
            currentDashboard: {
              ...state.currentDashboard,
              widgets: state.currentDashboard.widgets.filter(w => w.id !== widgetId)
            },
            // Also clear cached data
            widgetData: { ...state.widgetData, [widgetId]: undefined }
          };
        });
      },

      // Layout Management
      updateLayout: (newLayout) => {
        set(state => {
          if (!state.currentDashboard) return state;

          const layoutMap = {};
          newLayout.forEach(item => {
            layoutMap[item.i] = {
              x: item.x,
              y: item.y,
              w: item.w,
              h: item.h
            };
          });

          return {
            currentDashboard: {
              ...state.currentDashboard,
              widgets: state.currentDashboard.widgets.map(w => ({
                ...w,
                layout: layoutMap[w.id] || w.layout
              }))
            }
          };
        });
      },

      // Widget Data (cached query results)
      setWidgetData: (widgetId, data) => {
        set(state => ({
          widgetData: {
            ...state.widgetData,
            [widgetId]: data
          }
        }));
      },

      clearWidgetData: (widgetId) => {
        set(state => {
          const { [widgetId]: _, ...rest } = state.widgetData;
          return { widgetData: rest };
        });
      },

      clearAllWidgetData: () => {
        set({ widgetData: {} });
      },

      // Sharing
      generateShareLink: async (dashboardId) => {
        try {
          const response = await api.post(`/api/v1/dashboards/${dashboardId}/share`);
          return response.data;
        } catch (error) {
          set({ error: error.message });
          throw error;
        }
      },

      revokeShareLink: async (dashboardId) => {
        try {
          await api.delete(`/api/v1/dashboards/${dashboardId}/share`);
        } catch (error) {
          set({ error: error.message });
          throw error;
        }
      },

      // Save current dashboard to backend
      saveDashboard: async () => {
        const { currentDashboard, updateDashboard } = get();
        if (!currentDashboard) return;

        return updateDashboard(currentDashboard.id, {
          name: currentDashboard.name,
          description: currentDashboard.description,
          widgets: currentDashboard.widgets,
          global_filters: currentDashboard.global_filters,
          is_public: currentDashboard.is_public,
          tags: currentDashboard.tags
        });
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Reset state
      reset: () => {
        set({
          dashboards: [],
          currentDashboard: null,
          isLoading: false,
          error: null,
          editMode: false,
          widgetData: {}
        });
      }
    }),
    {
      name: 'dashboard-store',
      partialize: (state) => ({
        // Only persist these fields
        dashboards: state.dashboards,
        currentDashboard: state.currentDashboard
      })
    }
  )
);

// Selector hooks for common use cases
export const useDashboards = () => useDashboardStore(state => state.dashboards);
export const useCurrentDashboard = () => useDashboardStore(state => state.currentDashboard);
export const useEditMode = () => useDashboardStore(state => state.editMode);
export const useWidgetData = (widgetId) => useDashboardStore(state => state.widgetData[widgetId]);
export const useDashboardLoading = () => useDashboardStore(state => state.isLoading);
export const useDashboardError = () => useDashboardStore(state => state.error);
