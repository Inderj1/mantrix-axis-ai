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
import { apiService } from '../services/api';

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

      // Database selection (null = let backend use enabled connector)
      selectedDatabase: null,
      multiDatabases: null,

      // Error state
      error: null,

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

        console.log('[ConversationStore] === INITIALIZING ===');
        console.log('[ConversationStore] userId:', userId);
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

          if (savedConversationId && sortedConversations.some(c =>
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

          // Add welcome message if no messages
          if (formattedMessages.length === 0) {
            formattedMessages.push({
              id: generateMessageId(),
              ...WELCOME_MESSAGE,
              timestamp: new Date(),
            });
          }

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

        const welcomeMessage = {
          id: generateMessageId(),
          ...WELCOME_MESSAGE,
          timestamp: new Date(),
        };

        set({
          conversationId: tempConvId,
          messages: [welcomeMessage],
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
            metadata: {
              cost: data.validation?.estimated_cost_usd,
              bytesProcessed: data.validation?.total_bytes_processed,
              tablesUsed: data.tables_used,
              // Include connector info for cross-connector queries
              connectorsUsed: data.execution?.connectors_used,
              databaseTypesUsed: data.execution?.database_types_used,
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
