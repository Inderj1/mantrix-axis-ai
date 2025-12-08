/**
 * Conversation Store - Zustand state management for chat conversations
 *
 * Replaces ConversationContext.jsx and conversation state from SimpleChatInterface.jsx
 *
 * Manages:
 * - Current conversation and messages
 * - Conversation list (sidebar)
 * - Initialization state (prevents race conditions)
 * - Database selection
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiService, getAuthToken, getApiBaseUrl } from '../services/api';

// Welcome message shown at start of new conversations
const WELCOME_MESSAGE = {
  type: 'assistant',
  content: 'Hello! I can help you query your data. Try asking something like "Show me top 5 GL accounts by total amount". I\'ll maintain context throughout our conversation, so you can ask follow-up questions like "filter by amount > 1000".',
};

// Generate unique message ID
const generateMessageId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Generate temporary conversation ID (for optimistic creation)
const generateTempConversationId = () => `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export const useConversationStore = create(
  persist(
    (set, get) => ({
      // ============ State ============

      // Current user ID (set during initialization)
      userId: null,

      // Initialization state - prevents sending messages before ready
      isInitializing: true,
      isInitialized: false,

      // Current conversation
      conversationId: null,
      messages: [],

      // Conversation list (for sidebar)
      conversations: [],
      loadingConversations: false,

      // Query execution state
      isLoading: false,
      isLoadingMore: false, // For pagination load more

      // Database selection (null = let backend use enabled connector)
      selectedDatabase: null,
      multiDatabases: null,

      // Error state
      error: null,

      // Streaming query progress state
      queryProgress: {
        isStreaming: false,
        phase: null,
        progress: 0,
        message: '',
        detail: '',
        sql: null,
        streamingResults: [],
        totalRows: 0,
      },

      // ============ Initialization ============

      /**
       * Initialize the store for a user.
       * Loads conversations and sets up the current conversation.
       * Must be called before any other actions.
       */
      initialize: async (userId) => {
        const state = get();

        // Prevent re-initialization for same user
        if (state.isInitialized && state.userId === userId) {
          console.log('[ConversationStore] Already initialized for user:', userId);
          return;
        }

        // IMPORTANT: Capture temp conversation BEFORE any async operations
        // This prevents race conditions when user clicks "New chat" and navigates
        const preExistingConvId = state.conversationId;
        const hasTempConversation = preExistingConvId && preExistingConvId.startsWith('temp-');

        console.log('[ConversationStore] === INITIALIZING ===');
        console.log('[ConversationStore] userId:', userId);
        console.log('[ConversationStore] preExistingConvId:', preExistingConvId);
        console.log('[ConversationStore] hasTempConversation:', hasTempConversation);

        // If user just created a new chat (temp conversation), skip full initialization
        // Just mark as initialized and load conversations in background
        if (hasTempConversation) {
          console.log('[ConversationStore] Preserving temp conversation, skipping full init:', preExistingConvId);
          set({ isInitializing: false, isInitialized: true, userId });

          // Load conversations list in background (don't block, don't change current conversation)
          apiService.listConversations(userId, 50, 0).then(response => {
            const loadedConversations = response.data.conversations || [];
            const sortedConversations = loadedConversations.sort((a, b) => {
              const dateA = new Date(a.updated_at || a.updatedAt || 0);
              const dateB = new Date(b.updated_at || b.updatedAt || 0);
              return dateB - dateA;
            });
            set({ conversations: sortedConversations });
            console.log('[ConversationStore] Background loaded', sortedConversations.length, 'conversations');
          }).catch(err => console.error('[ConversationStore] Background load failed:', err));

          return;
        }

        console.log('[ConversationStore] Setting isInitializing=true');
        set({ isInitializing: true, userId, error: null });

        try {
          // Load conversations from backend
          console.log('[ConversationStore] Fetching conversations from backend...');
          const response = await apiService.listConversations(userId, 50, 0);
          const loadedConversations = response.data.conversations || [];
          console.log('[ConversationStore] Loaded', loadedConversations.length, 'conversations');

          // Sort by updated_at (most recent first)
          const sortedConversations = loadedConversations.sort((a, b) => {
            const dateA = new Date(a.updated_at || a.updatedAt || 0);
            const dateB = new Date(b.updated_at || b.updatedAt || 0);
            return dateB - dateA;
          });

          set({ conversations: sortedConversations });

          // Try to restore last conversation from localStorage
          const savedConversationId = localStorage.getItem(`currentConversationId_${userId}`);
          console.log('[ConversationStore] localStorage savedConversationId:', savedConversationId);

          // Check again if a temp conversation was created during the API call
          const currentConvId = get().conversationId;
          if (currentConvId && currentConvId.startsWith('temp-')) {
            console.log('[ConversationStore] Temp conversation created during init, preserving:', currentConvId);
          } else if (savedConversationId && sortedConversations.some(c =>
            (c.conversation_id || c.conversationId) === savedConversationId
          )) {
            // Load the saved conversation
            console.log('[ConversationStore] Loading saved conversation:', savedConversationId);
            await get().loadConversation(savedConversationId);
          } else if (sortedConversations.length > 0) {
            // Load most recent conversation
            const mostRecentId = sortedConversations[0].conversation_id || sortedConversations[0].conversationId;
            console.log('[ConversationStore] Loading most recent conversation:', mostRecentId);
            await get().loadConversation(mostRecentId);
          } else {
            // No conversations exist - create a new one
            console.log('[ConversationStore] No conversations found, creating new one');
            await get().createNewConversation();
          }

          console.log('[ConversationStore] === INITIALIZATION COMPLETE ===');
          console.log('[ConversationStore] Setting isInitializing=false, isInitialized=true');
          set({ isInitializing: false, isInitialized: true });

        } catch (error) {
          console.error('[ConversationStore] Initialization failed:', error);
          // Create a local conversation as fallback
          await get().createNewConversation();
          set({ isInitializing: false, isInitialized: true, error: error.message });
        }
      },

      // ============ Conversation Management ============

      /**
       * Load a specific conversation by ID
       */
      loadConversation: async (conversationId) => {
        const { userId } = get();
        console.log('[ConversationStore] loadConversation:', conversationId);

        try {
          const response = await apiService.getConversation(conversationId);
          const conversation = response.data;

          // Convert messages to UI format
          const formattedMessages = (conversation.messages || []).map(msg => ({
            id: msg.id || generateMessageId(),
            type: msg.type,
            content: msg.content,
            sql: msg.sql,
            results: msg.results,
            resultCount: msg.result_count,
            error: msg.error,
            metadata: msg.metadata,
            timestamp: new Date(msg.timestamp),
          }));

          // Skip automatic welcome message - let UI show minimal welcome section instead

          set({
            conversationId,
            messages: formattedMessages,
            error: null
          });

          // Save to localStorage
          if (userId) {
            localStorage.setItem(`currentConversationId_${userId}`, conversationId);
          }

        } catch (error) {
          console.error('ConversationStore: Failed to load conversation', error);
          set({ error: error.message });
        }
      },

      /**
       * Create a new conversation.
       * Creates locally first (optimistic), then syncs to backend on first message.
       */
      createNewConversation: async () => {
        const { userId } = get();

        // Create temporary local conversation
        const tempConvId = generateTempConversationId();
        console.log('[ConversationStore] === CREATE NEW CONVERSATION ===');
        console.log('[ConversationStore] Generated temp ID:', tempConvId);

        // Start with empty messages - UI will show minimal welcome section
        set({
          conversationId: tempConvId,
          messages: [],
          error: null,
        });

        // Save to localStorage
        if (userId) {
          localStorage.setItem(`currentConversationId_${userId}`, tempConvId);
          console.log('[ConversationStore] Saved to localStorage:', tempConvId);
        }

        return tempConvId;
      },

      /**
       * Ensure conversation exists on backend.
       * If current conversation is temporary, creates it on backend.
       * Returns the actual conversation ID.
       */
      ensureConversationExists: async (title = 'New Conversation') => {
        const { conversationId, userId, conversations } = get();
        console.log('[ConversationStore] ensureConversationExists - current ID:', conversationId);

        // If no conversation or it's temporary, create on backend
        if (!conversationId || conversationId.startsWith('temp-')) {
          console.log('[ConversationStore] Need to create on backend (temp or null)');

          try {
            const response = await apiService.createConversation(userId, title);
            const newConvId = response.data.conversation_id;
            console.log('[ConversationStore] Backend created conversation:', newConvId);

            // Add to conversations list
            const newConv = {
              conversation_id: newConvId,
              user_id: userId,
              title,
              messages: [],
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              metadata: { starred: false, message_count: 0 }
            };

            set({
              conversationId: newConvId,
              conversations: [newConv, ...conversations],
            });

            // Update localStorage
            if (userId) {
              localStorage.setItem(`currentConversationId_${userId}`, newConvId);
              console.log('[ConversationStore] Updated localStorage to:', newConvId);
            }

            return newConvId;

          } catch (error) {
            console.error('[ConversationStore] Failed to create conversation:', error);
            throw error;
          }
        }

        console.log('[ConversationStore] Using existing conversation:', conversationId);
        return conversationId;
      },

      /**
       * Delete a conversation
       */
      deleteConversation: async (convId) => {
        const { conversationId, conversations, userId } = get();

        try {
          await apiService.deleteConversation(convId);

          const updatedConversations = conversations.filter(c =>
            (c.conversation_id || c.conversationId) !== convId
          );

          set({ conversations: updatedConversations });

          // If deleted current conversation, switch to another or create new
          if (conversationId === convId) {
            if (updatedConversations.length > 0) {
              const nextId = updatedConversations[0].conversation_id || updatedConversations[0].conversationId;
              await get().loadConversation(nextId);
            } else {
              await get().createNewConversation();
            }
          }

        } catch (error) {
          console.error('ConversationStore: Failed to delete conversation', error);
          set({ error: error.message });
        }
      },

      /**
       * Clear all conversations for the current user
       */
      clearAllConversations: async () => {
        const { userId } = get();
        if (!userId) return;

        set({ loadingConversations: true });

        try {
          console.log('ConversationStore: Clearing all conversations for user', userId);
          await apiService.deleteAllConversations(userId);

          // Clear local state
          set({ conversations: [] });
          localStorage.removeItem(`currentConversationId_${userId}`);

          // Create a new conversation
          await get().createNewConversation();

          console.log('ConversationStore: Cleared all conversations');
        } catch (error) {
          console.error('ConversationStore: Failed to clear conversations', error);
          set({ error: error.message });
          // Reload to sync state
          await get().reloadConversations();
        } finally {
          set({ loadingConversations: false });
        }
      },

      /**
       * Reload conversations list from backend
       */
      reloadConversations: async () => {
        const { userId } = get();
        if (!userId) return;

        set({ loadingConversations: true });

        try {
          const response = await apiService.listConversations(userId, 50, 0);
          const loadedConversations = response.data.conversations || [];

          const sortedConversations = loadedConversations.sort((a, b) => {
            const dateA = new Date(a.updated_at || a.updatedAt || 0);
            const dateB = new Date(b.updated_at || b.updatedAt || 0);
            return dateB - dateA;
          });

          set({ conversations: sortedConversations, loadingConversations: false });

        } catch (error) {
          console.error('ConversationStore: Failed to reload conversations', error);
          set({ loadingConversations: false, error: error.message });
        }
      },

      // ============ Message Management ============

      /**
       * Add a message to the current conversation (local only)
       */
      addMessage: (message) => {
        const newMessage = {
          id: message.id || generateMessageId(),
          timestamp: message.timestamp || new Date(),
          ...message,
        };

        set(state => ({
          messages: [...state.messages, newMessage],
        }));

        return newMessage;
      },

      /**
       * Update a message by ID
       */
      updateMessage: (messageId, updates) => {
        set(state => ({
          messages: state.messages.map(msg =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          ),
        }));
      },

      /**
       * Send a query and get response
       */
      sendQuery: async (question, options = {}) => {
        const { selectedDatabase, multiDatabases } = get();
        console.log('[ConversationStore] === SEND QUERY ===');
        console.log('[ConversationStore] Question:', question.substring(0, 50));
        console.log('[ConversationStore] selectedDatabase from store:', selectedDatabase);
        console.log('[ConversationStore] options.databaseType:', options.databaseType);

        set({ isLoading: true, error: null });

        try {
          // Ensure conversation exists on backend
          const actualConversationId = await get().ensureConversationExists(
            question.substring(0, 50) + (question.length > 50 ? '...' : '')
          );
          console.log('[ConversationStore] Using conversation ID:', actualConversationId);

          // Add user message
          const userMessage = get().addMessage({
            type: 'user',
            content: question,
          });

          // Build query options
          const resolvedDatabaseType = options.databaseType || selectedDatabase;
          console.log('[ConversationStore] Resolved databaseType:', resolvedDatabaseType,
            '(from options:', options.databaseType, ', from store:', selectedDatabase, ')');

          const queryOptions = {
            conversationId: actualConversationId,
            databaseType: resolvedDatabaseType,
            ...options,
          };

          if (multiDatabases && multiDatabases.length > 0 && !options.multiDatabases) {
            queryOptions.multiDatabases = multiDatabases;
          }

          console.log('[ConversationStore] Final queryOptions:', JSON.stringify(queryOptions, null, 2));

          // Execute query
          const response = await apiService.executeQuery(question, queryOptions);
          const { data } = response;

          // Handle error response
          if (data.error) {
            const errorMessage = get().addMessage({
              type: 'assistant',
              content: data.error_details?.user_friendly_message || 'Sorry, I encountered an error processing your query.',
              error: data.error,
              errorAnalysis: data.error_analysis,
            });

            set({ isLoading: false });
            return { success: false, error: data.error, message: errorMessage };
          }

          // Add assistant response
          const assistantMessage = get().addMessage({
            type: 'assistant',
            content: data.explanation || 'Query executed successfully.',
            sql: data.sql,
            results: data.results || data.execution?.results || [],
            resultCount: data.row_count || data.execution?.row_count || 0,
            followUpSuggestions: data.follow_up_suggestions || [],
            autoCorrected: data.auto_corrected,
            correctionInfo: data.correction_info,
            emptyResultNote: data.empty_result_note,
            // Cross-connector query fields
            isCrossConnector: data.is_cross_connector || false,
            connectorQueries: data.connector_queries || null,
            joinSpec: data.join_specification || null,
            // Pagination metadata for large table queries
            pagination: data.pagination || null,
            metadata: {
              cost: data.validation?.estimated_cost_usd,
              bytesProcessed: data.validation?.total_bytes_processed,
              tablesUsed: data.tables_used,
              // Include connector info for cross-connector queries
              connectorsUsed: data.execution?.connectors_used,
              databaseTypesUsed: data.execution?.database_types_used,
              // Include database_type and connector_id for pagination "Load More" requests
              databaseType: data.database_type,
              connectorId: data.connector_id,
            },
          });

          // Update conversation in list (move to top, update timestamp)
          set(state => ({
            conversations: state.conversations.map(c => {
              const cId = c.conversation_id || c.conversationId;
              if (cId === actualConversationId) {
                return {
                  ...c,
                  updated_at: new Date().toISOString(),
                  metadata: {
                    ...c.metadata,
                    message_count: (c.metadata?.message_count || 0) + 2,
                  },
                };
              }
              return c;
            }).sort((a, b) => {
              const dateA = new Date(a.updated_at || a.updatedAt || 0);
              const dateB = new Date(b.updated_at || b.updatedAt || 0);
              return dateB - dateA;
            }),
            isLoading: false,
          }));

          return { success: true, data, message: assistantMessage };

        } catch (error) {
          console.error('ConversationStore: Query failed', error);

          const errorMessage = get().addMessage({
            type: 'assistant',
            content: 'Sorry, I encountered an error processing your query. Please try again.',
            error: error.message,
          });

          set({ isLoading: false, error: error.message });
          return { success: false, error: error.message, message: errorMessage };
        }
      },

      /**
       * Send a query with progress updates via polling.
       * Replaces SSE streaming with simpler async polling pattern.
       */
      sendQueryStreaming: async (question, options = {}) => {
        const { selectedDatabase, multiDatabases } = get();
        console.log('[ConversationStore] === SEND QUERY WITH POLLING ===');
        console.log('[ConversationStore] Question:', question.substring(0, 50));

        // Reset progress state
        set({
          isLoading: true,
          error: null,
          queryProgress: {
            isStreaming: true,
            phase: 'understanding',
            progress: 0,
            message: 'Understanding your question...',
            sql: null,
            streamingResults: [],
            totalRows: 0,
          },
        });

        try {
          // Ensure conversation exists on backend
          const actualConversationId = await get().ensureConversationExists(
            question.substring(0, 50) + (question.length > 50 ? '...' : '')
          );
          console.log('[ConversationStore] Using conversation ID:', actualConversationId);

          // Add user message
          const userMessage = get().addMessage({
            type: 'user',
            content: question,
          });

          // Build request payload
          const resolvedDatabaseType = options.databaseType || selectedDatabase;
          const payload = {
            question,
            conversationId: actualConversationId,
          };

          if (resolvedDatabaseType) {
            payload.database_type = resolvedDatabaseType;
          }
          if (multiDatabases && multiDatabases.length > 0) {
            payload.multi_databases = multiDatabases;
          }

          // Get auth token
          const token = await getAuthToken();
          const baseUrl = getApiBaseUrl();

          // Start async query processing
          const postStartTime = Date.now();
          console.log('[ConversationStore] Starting POST request at:', new Date().toISOString());
          const startResponse = await fetch(`${baseUrl}/api/v1/query?async_mode=true`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token ? `Bearer ${token}` : '',
            },
            body: JSON.stringify(payload),
          });

          if (!startResponse.ok) {
            const errorData = await startResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${startResponse.status}`);
          }

          const { execution_id } = await startResponse.json();
          const postDuration = Date.now() - postStartTime;
          console.log('[ConversationStore] POST completed in', postDuration, 'ms at:', new Date().toISOString());
          console.log('[ConversationStore] Query started with execution_id:', execution_id);
          console.log('[ConversationStore] About to enter polling loop at:', new Date().toISOString());

          // Poll for status
          const POLL_INTERVAL = 2000; // 2 seconds
          const MAX_POLL_TIME = 600000; // 10 minutes timeout
          const startTime = Date.now();
          let finalData = null;
          let isFirstPoll = true;
          let pollCount = 0;

          while (Date.now() - startTime < MAX_POLL_TIME) {
            pollCount++;
            // First poll is immediate, then every 2 seconds
            if (!isFirstPoll) {
              console.log('[ConversationStore] Waiting 2 seconds before poll #', pollCount);
              await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
            }
            isFirstPoll = false;

            console.log('[ConversationStore] Poll #', pollCount, 'starting at:', new Date().toISOString());

            const pollStart = Date.now();
            const statusResponse = await fetch(`${baseUrl}/api/v1/query/status/${execution_id}`, {
              headers: {
                'Authorization': token ? `Bearer ${token}` : '',
              },
            });

            if (!statusResponse.ok) {
              if (statusResponse.status === 404) {
                throw new Error('Query expired or not found');
              }
              throw new Error(`Status check failed: ${statusResponse.status}`);
            }

            const status = await statusResponse.json();
            const pollDuration = Date.now() - pollStart;
            console.log('[ConversationStore] Poll status:', status.status, status.progress, '% (fetch took', pollDuration, 'ms)');

            // Update progress UI
            set(state => ({
              queryProgress: {
                ...state.queryProgress,
                phase: status.phase || status.status,
                progress: status.progress,
                message: status.message,
                sql: status.sql || state.queryProgress.sql,
                isLongRunning: status.is_long_running || false,
                estimatedMinutes: status.estimated_minutes,
                largestTableRows: status.largest_table_rows,
              },
            }));

            // Check if long_running - auto-switch to background mode
            if (status.status === 'long_running' || status.is_long_running) {
              console.log('[ConversationStore] Long-running query detected - switching to background mode');
              console.log('[ConversationStore] Estimated time:', status.estimated_minutes, 'minutes');
              console.log('[ConversationStore] Largest table rows:', status.largest_table_rows?.toLocaleString());

              // Request notification permission
              if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
                Notification.requestPermission();
              }

              // Save to localStorage for background checking
              const pendingQueries = JSON.parse(localStorage.getItem('pendingQueries') || '[]');
              if (!pendingQueries.find(p => p.execution_id === execution_id)) {
                pendingQueries.push({
                  execution_id,
                  started_at: Date.now(),
                  message: status.message,
                  estimated_minutes: status.estimated_minutes,
                  largest_table_rows: status.largest_table_rows,
                  question: question,
                });
                localStorage.setItem('pendingQueries', JSON.stringify(pendingQueries));
              }

              // Update UI to background mode and stop loading
              set(state => ({
                isLoading: false, // Allow user to run other queries
                queryProgress: {
                  ...state.queryProgress,
                  phase: 'background',
                  isLongRunning: true,
                  isStreaming: false,
                  estimatedMinutes: status.estimated_minutes,
                  largestTableRows: status.largest_table_rows,
                  message: 'Query running in background. You will be notified when complete.',
                  executionId: execution_id,
                },
              }));

              // Add system message to conversation
              get().addMessage({
                role: 'assistant',
                type: 'system',
                content: `This query is scanning ~${status.largest_table_rows?.toLocaleString() || 'billions of'} rows and may take ${status.estimated_minutes || '5+'}+ minutes. It's now running in the background - you'll receive a notification when it completes. Feel free to continue asking other questions!`,
              });

              // Exit polling - background checker takes over
              return;
            }

            // Check if complete
            if (status.status === 'complete') {
              finalData = status.result;
              set(state => ({
                queryProgress: {
                  ...state.queryProgress,
                  phase: 'complete',
                  progress: 100,
                  message: 'Done!',
                  isStreaming: false,
                  isLongRunning: false,
                },
              }));

              // Show browser notification if query was long-running
              if (status.is_long_running || get().queryProgress.isLongRunning) {
                try {
                  if (Notification.permission === 'granted') {
                    new Notification('Query Complete!', {
                      body: 'Your large table query has finished executing.',
                      icon: '/favicon.ico',
                    });
                  }
                } catch (e) {
                  console.log('Could not show notification:', e);
                }
              }
              break;
            }

            // Check if error
            if (status.status === 'error') {
              throw new Error(status.error || status.message || 'Query failed');
            }
          }

          // Timeout check - extended for long-running queries
          const isLongRunning = get().queryProgress.isLongRunning;
          const effectiveTimeout = isLongRunning ? 3600000 : MAX_POLL_TIME; // 1 hour for long-running, 10 min otherwise

          if (!finalData && (Date.now() - startTime) >= effectiveTimeout) {
            if (isLongRunning) {
              // For long-running queries, don't throw error - just inform user
              set(state => ({
                queryProgress: {
                  ...state.queryProgress,
                  phase: 'background',
                  message: 'Query is still running in background. You will be notified when it completes.',
                  isStreaming: false,
                },
              }));

              // Store execution_id for later retrieval
              const pendingQueries = JSON.parse(localStorage.getItem('pendingQueries') || '[]');
              pendingQueries.push({
                executionId: execution_id,
                startTime: startTime,
                question: question,
              });
              localStorage.setItem('pendingQueries', JSON.stringify(pendingQueries));

              return; // Exit without error
            }
            throw new Error('Query timed out after 10 minutes');
          }

          // Add assistant response with final data
          const assistantMessage = get().addMessage({
            type: 'assistant',
            content: finalData.explanation || 'Query executed successfully.',
            sql: finalData.sql,
            results: finalData.results || finalData.execution?.results || [],
            resultCount: finalData.row_count || finalData.execution?.row_count || 0,
            followUpSuggestions: finalData.follow_up_suggestions || [],
            autoCorrected: finalData.auto_corrected,
            correctionInfo: finalData.correction_info,
            emptyResultNote: finalData.empty_result_note,
            isCrossConnector: finalData.is_cross_connector || false,
            connectorQueries: finalData.connector_queries || null,
            joinSpec: finalData.join_specification || null,
            // Pagination metadata for large table queries
            pagination: finalData.pagination || null,
            metadata: {
              cost: finalData.validation?.estimated_cost_usd,
              bytesProcessed: finalData.validation?.total_bytes_processed,
              tablesUsed: finalData.tables_used,
              connectorsUsed: finalData.execution?.connectors_used,
              databaseTypesUsed: finalData.execution?.database_types_used,
            },
          });

          // Update conversation in list
          set(state => ({
            conversations: state.conversations.map(c => {
              const cId = c.conversation_id || c.conversationId;
              if (cId === actualConversationId) {
                return {
                  ...c,
                  updated_at: new Date().toISOString(),
                  metadata: {
                    ...c.metadata,
                    message_count: (c.metadata?.message_count || 0) + 2,
                  },
                };
              }
              return c;
            }).sort((a, b) => {
              const dateA = new Date(a.updated_at || a.updatedAt || 0);
              const dateB = new Date(b.updated_at || b.updatedAt || 0);
              return dateB - dateA;
            }),
            isLoading: false,
            queryProgress: {
              ...state.queryProgress,
              isStreaming: false,
            },
          }));

          // Clear progress after a short delay so user can see completion
          setTimeout(() => {
            set({
              queryProgress: {
                isStreaming: false,
                phase: null,
                progress: 0,
                message: '',
                detail: '',
                sql: null,
                streamingResults: [],
                totalRows: 0,
              },
            });
          }, 1500);

          return { success: true, data: finalData, message: assistantMessage };

        } catch (error) {
          console.error('[ConversationStore] Polling query failed:', error);

          const errorMessage = get().addMessage({
            type: 'assistant',
            content: 'Sorry, I encountered an error processing your query. Please try again.',
            error: error.message,
          });

          set({
            isLoading: false,
            error: error.message,
            queryProgress: {
              isStreaming: false,
              phase: 'error',
              progress: 0,
              message: error.message,
              detail: '',
              sql: null,
              streamingResults: [],
              totalRows: 0,
            },
          });

          // Clear error progress after longer delay so user can read the error
          setTimeout(() => {
            set({
              queryProgress: {
                isStreaming: false,
                phase: null,
                progress: 0,
                message: '',
                detail: '',
                sql: null,
                streamingResults: [],
                totalRows: 0,
              },
            });
          }, 5000);

          return { success: false, error: error.message, message: errorMessage };
        }
      },

      /**
       * Reset query progress state (e.g., when cancelling)
       */
      resetQueryProgress: () => {
        set({
          queryProgress: {
            isStreaming: false,
            phase: null,
            progress: 0,
            message: '',
            detail: '',
            sql: null,
            streamingResults: [],
            totalRows: 0,
          },
        });
      },

      /**
       * Load more results for a paginated query.
       * Appends additional rows to an existing message's results.
       *
       * @param {string} messageId - ID of the message to append results to
       * @returns {Promise<{success: boolean, newRows?: number, error?: string}>}
       */
      loadMoreResults: async (messageId) => {
        const state = get();
        const { messages, selectedDatabase } = state;

        // Find the message
        const messageIndex = messages.findIndex((m) => m.id === messageId);
        if (messageIndex === -1) {
          console.error('[ConversationStore] Message not found:', messageId);
          return { success: false, error: 'Message not found' };
        }

        const message = messages[messageIndex];

        // Check if message has pagination info
        if (!message.pagination?.is_paginated) {
          console.warn('[ConversationStore] Message is not paginated');
          return { success: false, error: 'No more results to load' };
        }

        // Calculate next page
        const currentCount = message.results?.length || 0;
        const pageSize = message.pagination?.page_size || 100;
        const nextPage = Math.floor(currentCount / pageSize) + 1;

        const totalCount = message.pagination?.total_count;

        console.log('[ConversationStore] Loading more results', {
          messageId,
          currentCount,
          pageSize,
          nextPage,
          totalCount,
        });

        set({ isLoadingMore: true });

        try {
          const response = await apiService.loadMoreResults({
            sql: message.sql,
            databaseType: message.metadata?.databaseType || selectedDatabase,
            connectorId: message.metadata?.connectorId,
            page: nextPage,
            pageSize,
            totalCount,
          });

          const newResults = response.data?.results || [];
          const hasMore = response.data?.has_more ?? false;
          console.log('[ConversationStore] Loaded', newResults.length, 'more rows, hasMore:', hasMore);

          if (newResults.length === 0) {
            // No more results - update pagination to reflect that
            set((state) => ({
              isLoadingMore: false,
              messages: state.messages.map((m, idx) => {
                if (idx === messageIndex) {
                  return {
                    ...m,
                    pagination: {
                      ...m.pagination,
                      is_paginated: false, // No more pages to load
                    },
                  };
                }
                return m;
              }),
            }));
            return { success: true, newRows: 0 };
          }

          // Update the message with appended results
          set((state) => ({
            isLoadingMore: false,
            messages: state.messages.map((m, idx) => {
              if (idx === messageIndex) {
                return {
                  ...m,
                  results: [...(m.results || []), ...newResults],
                  resultCount: (m.resultCount || 0) + newResults.length,
                  pagination: {
                    ...m.pagination,
                    page: nextPage,
                    is_paginated: hasMore, // Update based on backend response
                  },
                };
              }
              return m;
            }),
          }));

          return { success: true, newRows: newResults.length };
        } catch (error) {
          console.error('[ConversationStore] Failed to load more results:', error);
          set({ isLoadingMore: false });

          // Check if it's a 404/501 (endpoint not implemented)
          if (error.response?.status === 404 || error.response?.status === 501) {
            return {
              success: false,
              error: 'Pagination endpoint not yet implemented. This feature is coming soon!',
            };
          }

          return { success: false, error: error.message || 'Failed to load more results' };
        }
      },

      // ============ Star/Favorite Management ============

      /**
       * Toggle star status for a conversation
       */
      toggleStar: async (convId) => {
        const { conversations } = get();

        const conv = conversations.find(c =>
          (c.conversation_id || c.conversationId) === convId
        );
        if (!conv) return;

        const currentStarred = conv.metadata?.starred || false;
        const newStarred = !currentStarred;

        // Optimistic update
        set(state => ({
          conversations: state.conversations.map(c => {
            const cId = c.conversation_id || c.conversationId;
            if (cId === convId) {
              return {
                ...c,
                metadata: { ...c.metadata, starred: newStarred },
              };
            }
            return c;
          }),
        }));

        try {
          await apiService.updateConversation(convId, { starred: newStarred });
        } catch (error) {
          console.error('ConversationStore: Failed to toggle star', error);
          // Revert on failure
          set(state => ({
            conversations: state.conversations.map(c => {
              const cId = c.conversation_id || c.conversationId;
              if (cId === convId) {
                return {
                  ...c,
                  metadata: { ...c.metadata, starred: currentStarred },
                };
              }
              return c;
            }),
          }));
        }
      },

      // ============ Database Selection ============

      setSelectedDatabase: (database) => {
        set({ selectedDatabase: database });
      },

      setMultiDatabases: (databases) => {
        set({ multiDatabases: databases });
      },

      // ============ Loading State ============

      setIsLoading: (isLoading) => {
        set({ isLoading });
      },

      // ============ Utility ============

      /**
       * Clear error state
       */
      clearError: () => {
        set({ error: null });
      },

      // ============ Query Preview ============

      /**
       * Preview query complexity before execution.
       * Returns estimated rows, time, and warnings for large queries.
       *
       * @param {string} question - The natural language question
       * @param {string} databaseType - Optional database type
       * @returns {Promise<{is_long_running: boolean, estimated_minutes: number, warning?: string}>}
       */
      previewQuery: async (question, databaseType) => {
        try {
          const token = await getAuthToken();
          const baseUrl = getApiBaseUrl();

          const payload = { question };
          if (databaseType) {
            payload.database_type = databaseType;
          }

          const response = await fetch(`${baseUrl}/api/v1/query/preview`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token ? `Bearer ${token}` : '',
            },
            body: JSON.stringify(payload),
          });

          if (!response.ok) {
            console.warn('[ConversationStore] Preview failed, proceeding without warning');
            return { is_long_running: false, estimated_minutes: 0 };
          }

          return response.json();
        } catch (error) {
          console.error('[ConversationStore] Preview error:', error);
          // On error, don't block - just proceed without warning
          return { is_long_running: false, estimated_minutes: 0 };
        }
      },

      // ============ Background Query Checker ============

      /**
       * Check status of pending background queries.
       * Called periodically (every 30s) and on app load.
       * Shows browser notification when queries complete.
       */
      checkPendingQueries: async () => {
        const pendingQueries = JSON.parse(localStorage.getItem('pendingQueries') || '[]');
        if (pendingQueries.length === 0) return;

        console.log('[ConversationStore] Checking', pendingQueries.length, 'pending queries');

        const token = await getAuthToken();
        const baseUrl = getApiBaseUrl();

        const stillPending = [];

        for (const query of pendingQueries) {
          try {
            const response = await fetch(`${baseUrl}/api/v1/query/status/${query.execution_id}`, {
              headers: { 'Authorization': token ? `Bearer ${token}` : '' },
            });

            if (response.ok) {
              const status = await response.json();

              if (status.status === 'complete') {
                console.log('[ConversationStore] Background query completed:', query.execution_id);
                // Show browser notification
                if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
                  new Notification('Query Complete!', {
                    body: query.question ? `"${query.question.substring(0, 50)}..." has finished.` : 'Your large table query has finished.',
                    icon: '/favicon.ico',
                  });
                }
                // Don't add to stillPending - it's done
              } else if (status.status === 'error') {
                console.log('[ConversationStore] Background query failed:', query.execution_id);
                if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
                  new Notification('Query Failed', {
                    body: status.message || 'Query execution failed.',
                    icon: '/favicon.ico',
                  });
                }
                // Don't add to stillPending - it's done (failed)
              } else {
                // Still processing - keep in pending list
                stillPending.push(query);
              }
            } else if (response.status === 404) {
              // Query expired or not found - remove from list
              console.log('[ConversationStore] Query expired:', query.execution_id);
            } else {
              // Keep in list on other errors (might be temporary)
              stillPending.push(query);
            }
          } catch (e) {
            console.warn('[ConversationStore] Failed to check query:', query.execution_id, e);
            stillPending.push(query); // Keep in list on error
          }
        }

        // Update localStorage with remaining pending queries
        localStorage.setItem('pendingQueries', JSON.stringify(stillPending));

        if (stillPending.length < pendingQueries.length) {
          console.log('[ConversationStore] Cleared', pendingQueries.length - stillPending.length, 'completed queries');
        }
      },

      /**
       * Reset store (for logout)
       */
      reset: () => {
        set({
          userId: null,
          isInitializing: true,
          isInitialized: false,
          conversationId: null,
          messages: [],
          conversations: [],
          loadingConversations: false,
          isLoading: false,
          selectedDatabase: null,  // Let backend use enabled connector
          multiDatabases: null,
          error: null,
        });
      },
    }),
    {
      name: 'conversation-store',
      // Don't persist selectedDatabase - let backend auto-detect from enabled connectors
      partialize: () => ({}),
    }
  )
);

// ============ Selector Hooks ============

export const useConversationId = () => useConversationStore(state => state.conversationId);
export const useMessages = () => useConversationStore(state => state.messages);
export const useConversations = () => useConversationStore(state => state.conversations);
export const useIsInitializing = () => useConversationStore(state => state.isInitializing);
export const useIsLoading = () => useConversationStore(state => state.isLoading);
export const useSelectedDatabase = () => useConversationStore(state => state.selectedDatabase);
export const useConversationError = () => useConversationStore(state => state.error);
export const useQueryProgress = () => useConversationStore(state => state.queryProgress);

// Derived selectors
export const useStarredConversations = () => useConversationStore(
  state => state.conversations.filter(c => c.metadata?.starred)
);

export const useCurrentConversation = () => useConversationStore(state => {
  const { conversationId, conversations } = state;
  return conversations.find(c =>
    (c.conversation_id || c.conversationId) === conversationId
  );
});
