import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { apiService } from '../services/api';

const ConversationContext = createContext(null);

export function ConversationProvider({ children }) {
  const { user } = useAuth();
  // Use username to match SimpleChatInterface
  const userId = user?.username || 'default';

  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [loadingConversations, setLoadingConversations] = useState(false);

  // Load conversations from backend
  const loadConversations = useCallback(async () => {
    if (!userId) return;

    setLoadingConversations(true);
    try {
      const response = await apiService.listConversations(userId, 50, 0);
      const loadedConversations = response.data.conversations || [];

      // Sort by updated_at (most recent first)
      const sortedConversations = loadedConversations.sort((a, b) => {
        const dateA = new Date(a.updated_at || a.updatedAt || 0);
        const dateB = new Date(b.updated_at || b.updatedAt || 0);
        return dateB - dateA;
      });

      setConversations(sortedConversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  }, [userId]);

  // Load conversations on mount and when userId changes
  useEffect(() => {
    if (userId) {
      loadConversations();
    }
  }, [userId, loadConversations]);

  // Create a new conversation
  const createNewConversation = useCallback(async () => {
    console.log('ConversationContext.createNewConversation called, userId:', userId);
    try {
      const response = await apiService.createConversation(userId, 'New Conversation');
      console.log('createConversation API response:', response);
      const newConvId = response.data.conversation_id;

      // Add to local state
      const newConv = {
        conversation_id: newConvId,
        user_id: userId,
        title: 'New Conversation',
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: { starred: false, message_count: 0 }
      };

      setConversations(prev => [newConv, ...prev]);
      setCurrentConversationId(newConvId);

      console.log('New conversation created:', newConvId);
      return newConvId;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      return null;
    }
  }, [userId]);

  // Toggle star status
  const toggleStar = useCallback(async (conversationId) => {
    try {
      // Find current conversation
      const conv = conversations.find(c =>
        (c.conversation_id || c.conversationId) === conversationId
      );
      if (!conv) return;

      const currentStarred = conv.metadata?.starred || false;
      const newStarred = !currentStarred;

      // Update backend
      await apiService.updateConversation(conversationId, { starred: newStarred });

      // Update local state
      setConversations(prev => prev.map(c => {
        const cId = c.conversation_id || c.conversationId;
        if (cId === conversationId) {
          return {
            ...c,
            metadata: { ...c.metadata, starred: newStarred }
          };
        }
        return c;
      }));
    } catch (error) {
      console.error('Failed to toggle star:', error);
    }
  }, [conversations]);

  // Delete a conversation
  const deleteConversation = useCallback(async (conversationId) => {
    try {
      await apiService.deleteConversation(conversationId);
      setConversations(prev => prev.filter(c =>
        (c.conversation_id || c.conversationId) !== conversationId
      ));

      if (currentConversationId === conversationId) {
        setCurrentConversationId(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  }, [currentConversationId]);

  // Update conversation in local state (for title updates, etc.)
  const updateConversationLocal = useCallback((conversationId, updates) => {
    setConversations(prev => prev.map(c => {
      const cId = c.conversation_id || c.conversationId;
      if (cId === conversationId) {
        return { ...c, ...updates };
      }
      return c;
    }));
  }, []);

  // Get starred conversations
  const starredConversations = conversations.filter(c => c.metadata?.starred);

  const value = {
    conversations,
    starredConversations,
    currentConversationId,
    loadingConversations,
    setCurrentConversationId,
    loadConversations,
    createNewConversation,
    toggleStar,
    deleteConversation,
    updateConversationLocal,
  };

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversations() {
  const context = useContext(ConversationContext);
  if (!context) {
    throw new Error('useConversations must be used within a ConversationProvider');
  }
  return context;
}

export default ConversationContext;
