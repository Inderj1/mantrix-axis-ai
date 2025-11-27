/**
 * ShareDialog - Advanced dashboard sharing dialog
 *
 * Features:
 * - Share with users via email
 * - Permission level selection (view, edit, admin)
 * - Generate shareable links
 * - Manage existing shares
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Divider,
  Alert,
  CircularProgress,
  Tooltip,
  InputAdornment,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Snackbar
} from '@mui/material';
import {
  Close as CloseIcon,
  Share as ShareIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  Link as LinkIcon,
  ContentCopy as CopyIcon,
  Delete as DeleteIcon,
  Send as SendIcon,
  Public as PublicIcon,
  Lock as LockIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  AdminPanelSettings as AdminIcon
} from '@mui/icons-material';
import api from '../../services/api';

const PERMISSION_OPTIONS = [
  { value: 'view', label: 'Can view', icon: <ViewIcon fontSize="small" /> },
  { value: 'edit', label: 'Can edit', icon: <EditIcon fontSize="small" /> },
  { value: 'admin', label: 'Admin', icon: <AdminIcon fontSize="small" /> }
];

const ShareDialog = ({
  open,
  onClose,
  dashboardId,
  dashboardName
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Share with user state
  const [email, setEmail] = useState('');
  const [permission, setPermission] = useState('view');
  const [message, setMessage] = useState('');
  const [sendNotification, setSendNotification] = useState(true);

  // Permissions state
  const [permissions, setPermissions] = useState(null);

  // Link sharing state
  const [shareLink, setShareLink] = useState(null);
  const [linkPermission, setLinkPermission] = useState('view');
  const [isPublic, setIsPublic] = useState(false);

  useEffect(() => {
    if (open && dashboardId) {
      fetchPermissions();
    }
  }, [open, dashboardId]);

  const fetchPermissions = async () => {
    try {
      const response = await api.get(`/api/v1/dashboards/${dashboardId}/permissions`);
      setPermissions(response.data);
      setShareLink(response.data.share_url);
      setIsPublic(response.data.is_public);
    } catch (err) {
      console.error('Failed to fetch permissions:', err);
    }
  };

  const handleShare = async () => {
    if (!email) {
      setError('Please enter an email address');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.post(`/api/v1/dashboards/${dashboardId}/share`, {
        email,
        permission,
        message: message || undefined,
        send_notification: sendNotification
      });

      setSuccess(`Dashboard shared with ${email}`);
      setEmail('');
      setMessage('');
      fetchPermissions();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to share dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleRemovePermission = async (permissionId) => {
    try {
      await api.delete(`/api/v1/dashboards/${dashboardId}/permissions/${permissionId}`);
      fetchPermissions();
      setSuccess('Access removed');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove access');
    }
  };

  const handleGenerateLink = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post(`/api/v1/dashboards/${dashboardId}/share-link`, null, {
        params: { permission: linkPermission }
      });
      setShareLink(response.data.share_url);
      setSuccess('Share link generated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate link');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeLink = async () => {
    try {
      await api.delete(`/api/v1/dashboards/${dashboardId}/share-link`);
      setShareLink(null);
      setSuccess('Share link revoked');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke link');
    }
  };

  const handleCopyLink = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
      setSuccess('Link copied to clipboard');
    }
  };

  const handleTogglePublic = async () => {
    try {
      await api.put(`/api/v1/dashboards/${dashboardId}/public`, null, {
        params: { is_public: !isPublic }
      });
      setIsPublic(!isPublic);
      setSuccess(isPublic ? 'Dashboard is now private' : 'Dashboard is now public');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update public access');
    }
  };

  const getPermissionIcon = (perm) => {
    switch (perm) {
      case 'admin':
        return <AdminIcon fontSize="small" color="primary" />;
      case 'edit':
        return <EditIcon fontSize="small" color="action" />;
      default:
        return <ViewIcon fontSize="small" color="action" />;
    }
  };

  const renderShareTab = () => (
    <Box sx={{ pt: 2 }}>
      {/* Email input */}
      <TextField
        fullWidth
        label="Email address"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="colleague@company.com"
        size="small"
        sx={{ mb: 2 }}
      />

      {/* Permission select */}
      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
        <InputLabel>Permission</InputLabel>
        <Select
          value={permission}
          label="Permission"
          onChange={(e) => setPermission(e.target.value)}
        >
          {PERMISSION_OPTIONS.map((opt) => (
            <MenuItem key={opt.value} value={opt.value}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {opt.icon}
                {opt.label}
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Optional message */}
      <TextField
        fullWidth
        label="Add a message (optional)"
        multiline
        rows={2}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        size="small"
        sx={{ mb: 2 }}
      />

      {/* Send notification toggle */}
      <FormControlLabel
        control={
          <Switch
            checked={sendNotification}
            onChange={(e) => setSendNotification(e.target.checked)}
          />
        }
        label="Send email notification"
      />

      {/* Share button */}
      <Button
        fullWidth
        variant="contained"
        startIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
        onClick={handleShare}
        disabled={loading || !email}
        sx={{ mt: 2 }}
      >
        Share
      </Button>
    </Box>
  );

  const renderPeopleTab = () => (
    <Box sx={{ pt: 2 }}>
      {/* Owner */}
      {permissions?.owner_id && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Owner
          </Typography>
          <ListItem disableGutters>
            <ListItemAvatar>
              <Avatar sx={{ bgcolor: 'primary.main' }}>
                <PersonIcon />
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={permissions.owner_name || permissions.owner_id}
              secondary="Full access"
            />
          </ListItem>
        </Box>
      )}

      <Divider sx={{ my: 1 }} />

      {/* Shared with */}
      <Typography variant="caption" color="text.secondary">
        Shared with
      </Typography>

      {permissions?.permissions?.length > 0 ? (
        <List disablePadding>
          {permissions.permissions.map((perm) => (
            <ListItem key={perm.id} disableGutters>
              <ListItemAvatar>
                <Avatar>
                  {perm.type === 'group' ? <GroupIcon /> : <PersonIcon />}
                </Avatar>
              </ListItemAvatar>
              <ListItemText
                primary={perm.display_name || perm.identifier}
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {getPermissionIcon(perm.permission)}
                    <span>{perm.permission}</span>
                  </Box>
                }
              />
              <ListItemSecondaryAction>
                <IconButton
                  edge="end"
                  size="small"
                  onClick={() => handleRemovePermission(perm.id)}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          Not shared with anyone yet
        </Typography>
      )}
    </Box>
  );

  const renderLinkTab = () => (
    <Box sx={{ pt: 2 }}>
      {/* Public toggle */}
      <Box sx={{ mb: 3, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {isPublic ? <PublicIcon color="primary" /> : <LockIcon />}
            <Box>
              <Typography variant="subtitle2">
                {isPublic ? 'Public to organization' : 'Private'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {isPublic
                  ? 'Anyone in your organization can view'
                  : 'Only people with access can view'}
              </Typography>
            </Box>
          </Box>
          <Switch checked={isPublic} onChange={handleTogglePublic} />
        </Box>
      </Box>

      {/* Share link section */}
      <Typography variant="subtitle2" gutterBottom>
        Share via link
      </Typography>

      {shareLink ? (
        <>
          <TextField
            fullWidth
            value={shareLink}
            size="small"
            InputProps={{
              readOnly: true,
              endAdornment: (
                <InputAdornment position="end">
                  <Tooltip title="Copy link">
                    <IconButton onClick={handleCopyLink} edge="end">
                      <CopyIcon />
                    </IconButton>
                  </Tooltip>
                </InputAdornment>
              )
            }}
            sx={{ mb: 2 }}
          />
          <Button
            variant="outlined"
            color="error"
            size="small"
            onClick={handleRevokeLink}
          >
            Revoke link
          </Button>
        </>
      ) : (
        <>
          <FormControl fullWidth size="small" sx={{ mb: 2 }}>
            <InputLabel>Link permission</InputLabel>
            <Select
              value={linkPermission}
              label="Link permission"
              onChange={(e) => setLinkPermission(e.target.value)}
            >
              {PERMISSION_OPTIONS.slice(0, 2).map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {opt.icon}
                    {opt.label}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={20} /> : <LinkIcon />}
            onClick={handleGenerateLink}
            disabled={loading}
          >
            Generate link
          </Button>
        </>
      )}
    </Box>
  );

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ShareIcon color="primary" />
              <Typography variant="h6">Share Dashboard</Typography>
            </Box>
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {dashboardName}
          </Typography>
        </DialogTitle>

        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Tabs
            value={tabValue}
            onChange={(e, v) => setTabValue(v)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="Share" icon={<SendIcon />} iconPosition="start" />
            <Tab label="People" icon={<PersonIcon />} iconPosition="start" />
            <Tab label="Link" icon={<LinkIcon />} iconPosition="start" />
          </Tabs>

          {tabValue === 0 && renderShareTab()}
          {tabValue === 1 && renderPeopleTab()}
          {tabValue === 2 && renderLinkTab()}
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose}>Done</Button>
        </DialogActions>
      </Dialog>

      {/* Success snackbar */}
      <Snackbar
        open={!!success}
        autoHideDuration={3000}
        onClose={() => setSuccess(null)}
        message={success}
      />
    </>
  );
};

export default ShareDialog;
