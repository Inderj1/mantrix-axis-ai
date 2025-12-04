/**
 * Chat Message Styles
 * Premium styling for chat interface messages
 */

import { neutral, primary, semantic } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { buttonGradients } from '../effects/gradients';

// User message (right-aligned, primary gradient)
export const userMessage = {
  ml: 'auto',
  maxWidth: '70%',
  background: buttonGradients.primary,
  borderRadius: '16px 16px 4px 16px',
  boxShadow: shadowTokens.colored.primaryLight,
  color: '#FFFFFF',
  px: 2.5,
  py: 1.5,
  transition: 'all 0.2s ease',
  '&:hover': {
    boxShadow: shadowTokens.colored.primary,
    transform: 'translateY(-1px)',
  },
};

// Assistant message (left-aligned, neutral card)
export const assistantMessage = {
  mr: 'auto',
  maxWidth: '85%',
  bgcolor: 'background.paper',
  border: `1px solid ${neutral[300]}`,
  borderRadius: '16px 16px 16px 4px',
  boxShadow: shadowTokens.standard.sm,
  px: 2.5,
  py: 2,
  transition: 'all 0.2s ease',
  '&:hover': {
    boxShadow: shadowTokens.standard.md,
  },
};

// System/info message (centered, subtle)
export const systemMessage = {
  mx: 'auto',
  maxWidth: '90%',
  bgcolor: `${primary[50]}`,
  border: `1px solid ${primary[100]}`,
  borderRadius: 3,
  px: 2,
  py: 1.5,
  textAlign: 'center',
};

// Error message (left-aligned, error styling)
export const errorMessage = {
  mr: 'auto',
  maxWidth: '85%',
  bgcolor: semantic.error.light,
  border: `1px solid rgba(187, 0, 0, 0.2)`,
  borderRadius: '16px 16px 16px 4px',
  px: 2.5,
  py: 2,
};

// Loading/thinking message
export const loadingMessage = {
  mr: 'auto',
  maxWidth: '60%',
  bgcolor: neutral[50],
  border: `1px solid ${neutral[200]}`,
  borderRadius: '16px 16px 16px 4px',
  px: 2.5,
  py: 1.5,
  display: 'flex',
  alignItems: 'center',
  gap: 1.5,
};

// Timestamp styles
export const timestampUser = {
  display: 'block',
  mt: 1.5,
  color: 'rgba(255, 255, 255, 0.7)',
  fontSize: '0.75rem',
  fontWeight: 300,
};

export const timestampAssistant = {
  display: 'block',
  mt: 1.5,
  color: neutral[500],
  fontSize: '0.75rem',
  fontStyle: 'italic',
};

// Message container
export const messageContainer = {
  mb: 2,
};

// SQL code block inside messages
export const sqlCodeBlock = {
  bgcolor: neutral[900],
  color: '#FFFFFF',
  fontFamily: 'monospace',
  fontSize: '0.875rem',
  p: 2,
  borderRadius: 2,
  overflow: 'auto',
  maxHeight: 300,
  '& pre': {
    margin: 0,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
};

// Results summary card
export const resultsSummary = {
  bgcolor: semantic.success.light,
  border: `1px solid rgba(16, 126, 62, 0.2)`,
  borderRadius: 2,
  p: 2,
  mb: 2,
};

// Chat input area
export const chatInputContainer = {
  p: 2,
  borderRadius: 0,
  borderTop: `1px solid ${neutral[300]}`,
  bgcolor: '#FFFFFF',
};

export const chatInput = {
  '& .MuiOutlinedInput-root': {
    borderRadius: 3,
    bgcolor: '#FFFFFF',
    '&.Mui-focused': {
      boxShadow: shadowTokens.focus.primary,
    },
  },
};

// Send button
export const sendButton = {
  borderRadius: 2,
  px: 3,
  minWidth: 100,
  background: buttonGradients.primary,
  '&:hover': {
    background: buttonGradients.primaryHover,
    boxShadow: shadowTokens.colored.primary,
  },
};

// Export all chat styles
export const chatMessageStyles = {
  user: userMessage,
  assistant: assistantMessage,
  system: systemMessage,
  error: errorMessage,
  loading: loadingMessage,
  timestampUser,
  timestampAssistant,
  container: messageContainer,
  sqlCodeBlock,
  resultsSummary,
  inputContainer: chatInputContainer,
  input: chatInput,
  sendButton,
};

export default chatMessageStyles;
