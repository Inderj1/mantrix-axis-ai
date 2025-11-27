import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Box,
  Stack,
  Avatar,
  Typography,
  Chip,
  Grid,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Circle as CircleIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/api';

const DatabaseToggleCard = ({ database, onToggle, enabledCount, maxAllowed }) => {
  const theme = useTheme();
  const [toggling, setToggling] = useState(false);

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return theme.palette.success.main;
      case 'error':
      case 'disconnected': return theme.palette.error.main;
      case 'warning': return theme.palette.warning.main;
      default: return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return <CheckCircleIcon />;
      case 'warning': return <WarningIcon />;
      case 'error':
      case 'disconnected': return <ErrorIcon />;
      default: return <CircleIcon />;
    }
  };

  const handleToggle = async (event) => {
    const newValue = event.target.checked;
    setToggling(true);

    try {
      await apiService.toggleChatDatabase(database.id, newValue);
      if (onToggle) {
        await onToggle();
      }
    } catch (error) {
      console.error('Error toggling database:', error);
    } finally {
      setToggling(false);
    }
  };

  const isDisabledForToggleOn = database.status !== 'connected' ||
    (!database.enabled_for_chat && enabledCount >= maxAllowed);

  return (
    <Card sx={{ height: '100%', position: 'relative' }}>
      {/* Green glow effect for enabled databases */}
      {database.enabled_for_chat && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 4,
            bgcolor: theme.palette.success.main,
            borderRadius: '4px 4px 0 0',
          }}
        />
      )}

      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar
              sx={{
                bgcolor: alpha(getStatusColor(database.status), 0.1),
                color: getStatusColor(database.status),
              }}
            >
              {database.icon}
            </Avatar>
            <Box>
              <Typography variant="h6" fontWeight={500}>
                {database.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {database.host}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {database.database}
              </Typography>
            </Box>
          </Box>
          <Chip
            size="small"
            icon={getStatusIcon(database.status)}
            label={database.status}
            sx={{
              bgcolor: alpha(getStatusColor(database.status), 0.1),
              color: getStatusColor(database.status),
              fontWeight: 500,
            }}
          />
        </Stack>

        {/* Database Info */}
        <Box sx={{ mt: 3 }}>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">
                Tables
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {database.tables || 0}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">
                Size
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {database.size || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">
                Last Sync
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {database.lastSync || 'Never'}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">
                Type
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {database.type}
              </Typography>
            </Grid>
          </Grid>
        </Box>

        {/* Chat Toggle Section */}
        <Box
          sx={{
            mt: 3,
            p: 2,
            bgcolor: database.enabled_for_chat
              ? alpha(theme.palette.success.main, 0.1)
              : alpha(theme.palette.grey[500], 0.1),
            borderRadius: 1,
            border: `1px solid ${
              database.enabled_for_chat
                ? alpha(theme.palette.success.main, 0.3)
                : 'transparent'
            }`,
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <ChatIcon
                sx={{
                  fontSize: 20,
                  color: database.enabled_for_chat
                    ? theme.palette.success.main
                    : theme.palette.text.disabled,
                }}
              />
              <Typography
                variant="body2"
                fontWeight={database.enabled_for_chat ? 600 : 400}
                color={database.enabled_for_chat ? 'success.main' : 'text.secondary'}
              >
                {database.enabled_for_chat ? 'Active for Chat' : 'Inactive for Chat'}
              </Typography>
            </Stack>

            <Tooltip
              title={
                isDisabledForToggleOn && !database.enabled_for_chat
                  ? `Maximum ${maxAllowed} databases can be active. Disable another database first.`
                  : database.status !== 'connected'
                  ? 'Database must be connected to enable for chat'
                  : ''
              }
            >
              <span>
                <Switch
                  checked={database.enabled_for_chat || false}
                  onChange={handleToggle}
                  disabled={toggling || isDisabledForToggleOn}
                  color="success"
                  size="small"
                />
              </span>
            </Tooltip>
          </Stack>

          {!database.enabled_for_chat && enabledCount >= maxAllowed && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mt: 1, display: 'block' }}
            >
              Maximum {maxAllowed} databases can be active
            </Typography>
          )}

          {toggling && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
              <CircularProgress size={16} />
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default DatabaseToggleCard;