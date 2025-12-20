/**
 * Background Query Service
 *
 * Manages background query tracking, polling, and browser notifications
 * for long-running queries that the user wants to run in the background.
 */

import { apiService } from './api';

const STORAGE_KEY = 'backgroundQueries';
const POLL_INTERVAL = 5000; // 5 seconds for background queries (less aggressive)
const STALE_QUERY_THRESHOLD = 24 * 60 * 60 * 1000; // 24 hours - queries older than this are considered stale
const MAX_POLL_ERRORS = 3; // After this many consecutive errors, mark query as failed

class BackgroundQueryService {
  constructor() {
    this.pendingQueries = new Map(); // execution_id -> query metadata
    this.pollIntervals = new Map(); // execution_id -> interval ID
    this.eventListeners = new Set(); // Callbacks to notify on events
    this.notificationPermission = 'default';

    this.loadFromStorage();
    this.requestNotificationPermission();
  }

  /**
   * Request browser notification permission
   */
  async requestNotificationPermission() {
    if (!('Notification' in window)) {
      console.warn('Browser does not support notifications');
      return false;
    }

    if (Notification.permission === 'granted') {
      this.notificationPermission = 'granted';
      return true;
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      this.notificationPermission = permission;
      return permission === 'granted';
    }

    this.notificationPermission = 'denied';
    return false;
  }

  /**
   * Load pending queries from localStorage
   * Filters out stale queries (older than 24 hours)
   */
  loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const queries = JSON.parse(stored);
        const now = Date.now();
        let restoredCount = 0;
        let staleCount = 0;

        Object.entries(queries).forEach(([executionId, metadata]) => {
          // Only restore running queries that aren't stale
          if (metadata.status === 'running') {
            const queryAge = now - (metadata.startTime || 0);
            if (queryAge > STALE_QUERY_THRESHOLD) {
              // Query is stale (older than 24h), skip it
              staleCount++;
              console.log(`[BackgroundQueryService] Skipping stale query: ${executionId} (${Math.round(queryAge / 3600000)}h old)`);
            } else {
              metadata.pollErrors = 0; // Reset error count
              this.pendingQueries.set(executionId, metadata);
              this.startPolling(executionId);
              restoredCount++;
            }
          }
        });

        // Save cleaned storage (without stale queries)
        if (staleCount > 0) {
          this.saveToStorage();
        }

        console.log(`[BackgroundQueryService] Restored ${restoredCount} pending queries, removed ${staleCount} stale queries`);
      }
    } catch (error) {
      console.error('[BackgroundQueryService] Failed to load from storage:', error);
      // Clear corrupted storage
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  /**
   * Save pending queries to localStorage
   */
  saveToStorage() {
    try {
      const queries = Object.fromEntries(this.pendingQueries);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));
    } catch (error) {
      console.error('[BackgroundQueryService] Failed to save to storage:', error);
    }
  }

  /**
   * Add a query to background tracking
   * @param {string} executionId - Unique execution ID
   * @param {string} question - Original question text
   * @param {string} sql - Generated SQL (optional)
   * @param {object} notificationPreferences - { browser: true, email: false }
   */
  trackQuery(executionId, question, sql = '', notificationPreferences = { browser: true, email: false }) {
    const metadata = {
      executionId,
      question,
      sql,
      status: 'running',
      startTime: Date.now(),
      notificationPreferences
    };

    this.pendingQueries.set(executionId, metadata);
    this.saveToStorage();
    this.startPolling(executionId);
    this.emitEvent('queryAdded', { executionId, metadata });

    console.log(`[BackgroundQueryService] Tracking query: ${executionId}`);
    return metadata;
  }

  /**
   * Start polling for a query's completion
   */
  startPolling(executionId) {
    if (this.pollIntervals.has(executionId)) {
      return; // Already polling
    }

    const pollFn = async () => {
      const metadata = this.pendingQueries.get(executionId);
      if (!metadata) {
        this.stopPolling(executionId);
        return;
      }

      try {
        const status = await apiService.getQueryStatus(executionId);

        // Reset error count on successful poll
        metadata.pollErrors = 0;

        if (status.status === 'complete') {
          this.onQueryComplete(executionId, status);
        } else if (status.status === 'error') {
          this.onQueryError(executionId, status);
        } else {
          // Update progress
          metadata.progress = status.progress;
          metadata.message = status.message;
          metadata.phase = status.phase;
          this.pendingQueries.set(executionId, metadata);
          this.emitEvent('queryProgress', { executionId, status });
        }
      } catch (error) {
        console.error(`[BackgroundQueryService] Poll error for ${executionId}:`, error);

        // Track consecutive errors
        metadata.pollErrors = (metadata.pollErrors || 0) + 1;

        if (error.response?.status === 404) {
          // Query not found on backend - mark as expired/failed
          console.log(`[BackgroundQueryService] Query ${executionId} not found on server, removing`);
          this.onQueryError(executionId, { error: 'Query expired or not found on server' });
        } else if (metadata.pollErrors >= MAX_POLL_ERRORS) {
          // Too many consecutive errors - mark as failed
          console.log(`[BackgroundQueryService] Query ${executionId} failed after ${MAX_POLL_ERRORS} poll errors`);
          this.onQueryError(executionId, { error: 'Lost connection to query - please try again' });
        }
        // Otherwise continue polling (transient error)
      }
    };

    // Poll immediately, then at intervals
    pollFn();
    const intervalId = setInterval(pollFn, POLL_INTERVAL);
    this.pollIntervals.set(executionId, intervalId);
  }

  /**
   * Stop polling for a query
   */
  stopPolling(executionId) {
    const intervalId = this.pollIntervals.get(executionId);
    if (intervalId) {
      clearInterval(intervalId);
      this.pollIntervals.delete(executionId);
    }
  }

  /**
   * Handle query completion
   */
  onQueryComplete(executionId, result) {
    const metadata = this.pendingQueries.get(executionId);
    if (!metadata) return;

    this.stopPolling(executionId);

    // Update status
    metadata.status = 'complete';
    metadata.endTime = Date.now();
    metadata.result = result;
    metadata.executionTime = (metadata.endTime - metadata.startTime) / 1000;

    // Remove from pending, add to completed cache briefly for UI
    this.pendingQueries.delete(executionId);
    this.saveToStorage();

    // Send browser notification
    if (metadata.notificationPreferences?.browser && this.notificationPermission === 'granted') {
      this.showNotification(
        'Query Complete',
        {
          body: `"${metadata.question.slice(0, 50)}${metadata.question.length > 50 ? '...' : ''}" returned ${result.result?.execution?.row_count || 0} rows`,
          tag: executionId,
          icon: '/logo.png',
          requireInteraction: true
        }
      );
    }

    // Emit event for UI updates
    this.emitEvent('queryComplete', { executionId, metadata, result });

    // Mark notification as sent via API
    this.markNotificationSent(executionId, 'browser');

    console.log(`[BackgroundQueryService] Query complete: ${executionId}, took ${metadata.executionTime.toFixed(1)}s`);
  }

  /**
   * Handle query error
   */
  onQueryError(executionId, status) {
    const metadata = this.pendingQueries.get(executionId);
    if (!metadata) return;

    this.stopPolling(executionId);

    // Update status
    metadata.status = 'error';
    metadata.endTime = Date.now();
    metadata.error = status.error || 'Query failed';
    metadata.executionTime = (metadata.endTime - metadata.startTime) / 1000;

    this.pendingQueries.delete(executionId);
    this.saveToStorage();

    // Send browser notification for errors too
    if (metadata.notificationPreferences?.browser && this.notificationPermission === 'granted') {
      this.showNotification(
        'Query Failed',
        {
          body: `"${metadata.question.slice(0, 50)}${metadata.question.length > 50 ? '...' : ''}" encountered an error`,
          tag: executionId,
          icon: '/logo.png'
        }
      );
    }

    // Emit event
    this.emitEvent('queryError', { executionId, metadata, error: status.error });

    console.log(`[BackgroundQueryService] Query error: ${executionId}, error: ${metadata.error}`);
  }

  /**
   * Show a browser notification
   */
  showNotification(title, options) {
    if (!('Notification' in window) || Notification.permission !== 'granted') {
      return null;
    }

    try {
      const notification = new Notification(title, options);

      notification.onclick = () => {
        window.focus();
        notification.close();
        // Emit click event for UI to handle (e.g., scroll to results)
        this.emitEvent('notificationClicked', { executionId: options.tag });
      };

      return notification;
    } catch (error) {
      console.error('[BackgroundQueryService] Failed to show notification:', error);
      return null;
    }
  }

  /**
   * Mark a notification as sent via API
   */
  async markNotificationSent(executionId, type) {
    try {
      await apiService.markQueryNotificationSent(executionId, type);
    } catch (error) {
      console.warn('[BackgroundQueryService] Failed to mark notification sent:', error);
    }
  }

  /**
   * Add event listener
   * @param {function} callback - Called with (eventType, data)
   */
  addEventListener(callback) {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  /**
   * Emit event to all listeners
   */
  emitEvent(eventType, data) {
    this.eventListeners.forEach(callback => {
      try {
        callback(eventType, data);
      } catch (error) {
        console.error('[BackgroundQueryService] Event listener error:', error);
      }
    });

    // Also dispatch DOM event for components that prefer that
    window.dispatchEvent(new CustomEvent(`backgroundQuery:${eventType}`, { detail: data }));
  }

  /**
   * Get count of pending queries (for badge)
   */
  getPendingCount() {
    return this.pendingQueries.size;
  }

  /**
   * Get all pending queries
   */
  getPendingQueries() {
    return Array.from(this.pendingQueries.values());
  }

  /**
   * Check if a query is being tracked
   */
  isTracking(executionId) {
    return this.pendingQueries.has(executionId);
  }

  /**
   * Remove a query from tracking (cancel)
   */
  removeQuery(executionId) {
    this.stopPolling(executionId);
    this.pendingQueries.delete(executionId);
    this.saveToStorage();
    this.emitEvent('queryRemoved', { executionId });
  }

  /**
   * Clear all tracked queries
   */
  clearAll() {
    this.pollIntervals.forEach((_, executionId) => this.stopPolling(executionId));
    this.pendingQueries.clear();
    this.saveToStorage();
    this.emitEvent('cleared', {});
  }

  /**
   * Sync with server - fetch latest pending queries
   */
  async syncWithServer() {
    try {
      const response = await apiService.getPendingQueries();
      const serverQueries = response.queries || [];

      // Add any server queries we're not tracking
      serverQueries.forEach(query => {
        if (!this.pendingQueries.has(query.execution_id)) {
          this.pendingQueries.set(query.execution_id, {
            executionId: query.execution_id,
            question: query.question,
            sql: query.sql,
            status: 'running',
            startTime: new Date(query.started_at).getTime(),
            notificationPreferences: query.notification_preferences || { browser: true, email: false }
          });
          this.startPolling(query.execution_id);
        }
      });

      this.saveToStorage();
      return serverQueries;
    } catch (error) {
      console.error('[BackgroundQueryService] Failed to sync with server:', error);
      return [];
    }
  }
}

// Export singleton instance
export const backgroundQueryService = new BackgroundQueryService();

// Export class for testing
export { BackgroundQueryService };
