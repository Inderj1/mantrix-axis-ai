import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

/**
 * Reusable Confirmation Dialog Component
 *
 * Props:
 * - open: boolean - Whether dialog is open
 * - title: string - Dialog title
 * - message: string - Dialog message/content
 * - severity: 'warning' | 'error' | 'info' - Determines icon and button color
 * - onConfirm: () => void - Called when user confirms
 * - onCancel: () => void - Called when user cancels
 * - confirmText: string - Text for confirm button (default: 'Confirm')
 * - cancelText: string - Text for cancel button (default: 'Cancel')
 */
const ConfirmDialog = ({
  open,
  title,
  message,
  severity = 'warning',
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
}) => {
  const getIcon = () => {
    switch (severity) {
      case 'error':
        return <ErrorIcon />;
      case 'info':
        return <InfoIcon />;
      case 'warning':
      default:
        return <WarningIcon />;
    }
  };

  const getColor = () => {
    switch (severity) {
      case 'error':
        return 'error.main';
      case 'info':
        return 'info.main';
      case 'warning':
      default:
        return 'warning.main';
    }
  };

  const getButtonColor = () => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'info':
        return 'primary';
      case 'warning':
      default:
        return 'warning';
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onCancel}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          color: getColor(),
        }}
      >
        {getIcon()}
        {title}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {message}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>
          {cancelText}
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color={getButtonColor()}
          autoFocus
        >
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConfirmDialog;
