import { useState, useCallback } from 'react';

/**
 * Custom hook for managing confirmation dialogs
 * Replaces native window.confirm() with MUI Dialog
 *
 * Usage:
 * const { confirmDialog, showConfirmDialog, ConfirmDialogComponent } = useConfirmDialog();
 *
 * // To show dialog:
 * showConfirmDialog({
 *   title: 'Delete Item',
 *   message: 'Are you sure?',
 *   severity: 'error', // 'warning' | 'error' | 'info'
 *   onConfirm: () => { ... }
 * });
 *
 * // In JSX:
 * <ConfirmDialogComponent />
 */
export const useConfirmDialog = () => {
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    severity: 'warning',
    onConfirm: null,
  });

  const showConfirmDialog = useCallback(({ title, message, severity = 'warning', onConfirm }) => {
    setConfirmDialog({
      open: true,
      title,
      message,
      severity,
      onConfirm,
    });
  }, []);

  const closeConfirmDialog = useCallback(() => {
    setConfirmDialog(prev => ({ ...prev, open: false }));
  }, []);

  const handleConfirm = useCallback(async () => {
    if (confirmDialog.onConfirm) {
      await confirmDialog.onConfirm();
    }
    closeConfirmDialog();
  }, [confirmDialog.onConfirm, closeConfirmDialog]);

  return {
    confirmDialog,
    showConfirmDialog,
    closeConfirmDialog,
    handleConfirm,
  };
};

export default useConfirmDialog;
