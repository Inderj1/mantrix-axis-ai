/**
 * Filter Event Bus - Cross-chart filtering via Zustand pub/sub pattern
 *
 * When user clicks a bar in Chart A:
 * 1. Chart A publishes: { dimension: "country", value: "USA" }
 * 2. All other charts subscribe and re-filter their data
 *
 * This enables Superset-like interactivity where clicking one chart
 * filters all other charts on the dashboard.
 */
import { create } from 'zustand';
import React from 'react';

export const useFilterBus = create((set, get) => ({
  // Active filters: { "country": "USA", "product": "Widget", "date_range": { start, end } }
  activeFilters: {},

  // Subscribers: widgets that react to filter changes
  subscribers: new Map(), // Map<widgetId, callback>

  // Filter history for undo/redo
  filterHistory: [],
  historyIndex: -1,

  // Publish a filter (when clicking a chart element)
  publishFilter: (dimension, value) => {
    set(state => {
      const newFilters = {
        ...state.activeFilters,
        [dimension]: value
      };

      // Add to history
      const newHistory = [
        ...state.filterHistory.slice(0, state.historyIndex + 1),
        newFilters
      ];

      return {
        activeFilters: newFilters,
        filterHistory: newHistory,
        historyIndex: newHistory.length - 1
      };
    });

    // Notify all subscribers
    get().notifySubscribers();
  },

  // Publish multiple filters at once
  publishFilters: (filters) => {
    set(state => {
      const newFilters = {
        ...state.activeFilters,
        ...filters
      };

      const newHistory = [
        ...state.filterHistory.slice(0, state.historyIndex + 1),
        newFilters
      ];

      return {
        activeFilters: newFilters,
        filterHistory: newHistory,
        historyIndex: newHistory.length - 1
      };
    });

    get().notifySubscribers();
  },

  // Clear a specific filter
  clearFilter: (dimension) => {
    set(state => {
      const { [dimension]: _, ...rest } = state.activeFilters;

      const newHistory = [
        ...state.filterHistory.slice(0, state.historyIndex + 1),
        rest
      ];

      return {
        activeFilters: rest,
        filterHistory: newHistory,
        historyIndex: newHistory.length - 1
      };
    });

    get().notifySubscribers();
  },

  // Clear all filters
  clearAllFilters: () => {
    set(state => {
      const newHistory = [
        ...state.filterHistory.slice(0, state.historyIndex + 1),
        {}
      ];

      return {
        activeFilters: {},
        filterHistory: newHistory,
        historyIndex: newHistory.length - 1
      };
    });

    get().notifySubscribers();
  },

  // Undo last filter change
  undoFilter: () => {
    set(state => {
      if (state.historyIndex <= 0) return state;

      const newIndex = state.historyIndex - 1;
      return {
        activeFilters: state.filterHistory[newIndex] || {},
        historyIndex: newIndex
      };
    });

    get().notifySubscribers();
  },

  // Redo filter change
  redoFilter: () => {
    set(state => {
      if (state.historyIndex >= state.filterHistory.length - 1) return state;

      const newIndex = state.historyIndex + 1;
      return {
        activeFilters: state.filterHistory[newIndex] || {},
        historyIndex: newIndex
      };
    });

    get().notifySubscribers();
  },

  // Subscribe a widget to filter changes
  subscribe: (widgetId, callback) => {
    set(state => {
      const newSubscribers = new Map(state.subscribers);
      newSubscribers.set(widgetId, callback);
      return { subscribers: newSubscribers };
    });

    // Return unsubscribe function
    return () => get().unsubscribe(widgetId);
  },

  // Unsubscribe when widget unmounts
  unsubscribe: (widgetId) => {
    set(state => {
      const newSubscribers = new Map(state.subscribers);
      newSubscribers.delete(widgetId);
      return { subscribers: newSubscribers };
    });
  },

  // Notify all subscribers of filter change
  notifySubscribers: () => {
    const { subscribers, activeFilters } = get();
    subscribers.forEach((callback) => {
      try {
        callback(activeFilters);
      } catch (error) {
        console.error('Filter subscriber error:', error);
      }
    });
  },

  // Check if a specific filter is active
  hasFilter: (dimension) => {
    const { activeFilters } = get();
    return dimension in activeFilters;
  },

  // Get filter value for a dimension
  getFilter: (dimension) => {
    const { activeFilters } = get();
    return activeFilters[dimension];
  },

  // Get all active filters as array of {dimension, value} pairs
  getFilterEntries: () => {
    const { activeFilters } = get();
    return Object.entries(activeFilters).map(([dimension, value]) => ({
      dimension,
      value
    }));
  },

  // Build a SQL WHERE clause from active filters
  buildWhereClause: () => {
    const { activeFilters } = get();
    const conditions = [];

    Object.entries(activeFilters).forEach(([dimension, value]) => {
      if (typeof value === 'object' && value !== null) {
        // Date range filter
        if (value.start && value.end) {
          conditions.push(`${dimension} BETWEEN '${value.start}' AND '${value.end}'`);
        } else if (value.start) {
          conditions.push(`${dimension} >= '${value.start}'`);
        } else if (value.end) {
          conditions.push(`${dimension} <= '${value.end}'`);
        }
      } else if (Array.isArray(value)) {
        // Multi-select filter
        const quoted = value.map(v => `'${v}'`).join(', ');
        conditions.push(`${dimension} IN (${quoted})`);
      } else {
        // Single value filter
        conditions.push(`${dimension} = '${value}'`);
      }
    });

    return conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  },

  // Build filter context for NLP query modification
  buildFilterContext: () => {
    const { activeFilters } = get();
    const parts = [];

    Object.entries(activeFilters).forEach(([dimension, value]) => {
      if (typeof value === 'object' && value !== null && value.start) {
        parts.push(`${dimension} from ${value.start} to ${value.end || 'now'}`);
      } else if (Array.isArray(value)) {
        parts.push(`${dimension} in [${value.join(', ')}]`);
      } else {
        parts.push(`${dimension} = "${value}"`);
      }
    });

    return parts.length > 0 ? `Filter: ${parts.join(', ')}` : '';
  },

  // Reset all state
  reset: () => {
    set({
      activeFilters: {},
      subscribers: new Map(),
      filterHistory: [],
      historyIndex: -1
    });
  }
}));

// Selector hooks for common use cases
export const useActiveFilters = () => useFilterBus(state => state.activeFilters);
export const useFilterCount = () => useFilterBus(state => Object.keys(state.activeFilters).length);
export const useCanUndo = () => useFilterBus(state => state.historyIndex > 0);
export const useCanRedo = () => useFilterBus(state => state.historyIndex < state.filterHistory.length - 1);

// Custom hook for subscribing a widget to filter changes
export const useFilterSubscription = (widgetId, callback) => {
  const subscribe = useFilterBus(state => state.subscribe);
  const unsubscribe = useFilterBus(state => state.unsubscribe);

  // Subscribe on mount, unsubscribe on unmount
  React.useEffect(() => {
    const unsub = subscribe(widgetId, callback);
    return () => unsub();
  }, [widgetId, callback, subscribe]);
};
