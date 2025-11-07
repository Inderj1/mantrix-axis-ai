import React, { useState } from 'react';
import {
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  Zoom,
  Tooltip,
  Avatar,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import SimpleChatInterface from './SimpleChatInterface';

const AIAssistantButton = () => {
  const [open, setOpen] = useState(false);

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  return (
    <>
      {/* MANTRIX AI Floating Button */}
      <Tooltip title="Ask MANTRIX - Your AI Analytics Assistant" placement="left">
        <Zoom in={true}>
          <Fab
            color="primary"
            aria-label="mantrix ai assistant"
            onClick={handleOpen}
            sx={{
              position: 'fixed',
              bottom: 24,
              right: 24,
              width: 72,
              height: 72,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              boxShadow: '0 8px 20px rgba(102, 126, 234, 0.5)',
              '&:hover': {
                background: 'linear-gradient(135deg, #764ba2 0%, #667eea 100%)',
                boxShadow: '0 12px 28px rgba(102, 126, 234, 0.7)',
                transform: 'scale(1.08)',
              },
              transition: 'all 0.3s ease',
              animation: 'pulse-glow 2.5s infinite',
              '@keyframes pulse-glow': {
                '0%, 100%': {
                  boxShadow: '0 8px 20px rgba(102, 126, 234, 0.5)',
                },
                '50%': {
                  boxShadow: '0 12px 32px rgba(102, 126, 234, 0.8)',
                },
              },
            }}
          >
            <Box sx={{ textAlign: 'center' }}>
              <AIIcon sx={{ fontSize: 36 }} />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 700, display: 'block', mt: -0.5 }}>
                MANTRIX
              </Typography>
            </Box>
          </Fab>
        </Zoom>
      </Tooltip>

      {/* AI Assistant Dialog */}
      <Dialog
        open={open}
        onClose={handleClose}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            height: '80vh',
            maxHeight: 700,
            borderRadius: 3,
          },
        }}
      >
        <DialogTitle
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            pb: 1,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar sx={{ bgcolor: 'rgba(255, 255, 255, 0.2)', width: 40, height: 40 }}>
              <AIIcon />
            </Avatar>
            <Box>
              <Typography variant="h6" fontWeight={700}>
                MANTRIX
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.9 }}>
                Your AI Analytics Assistant
              </Typography>
            </Box>
          </Box>
          <IconButton
            onClick={handleClose}
            size="small"
            sx={{
              color: 'white',
              '&:hover': {
                bgcolor: 'rgba(255, 255, 255, 0.1)',
              },
            }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent
          sx={{
            p: 0,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <SimpleChatInterface />
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AIAssistantButton;
