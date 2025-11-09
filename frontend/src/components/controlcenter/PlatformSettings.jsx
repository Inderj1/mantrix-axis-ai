import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  Divider,
  Stack,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
  Schedule as ScheduleIcon,
  Settings as SettingsIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Edit as EditIcon,
} from '@mui/icons-material';

const PlatformSettings = () => {
  const theme = useTheme();
  const [settings, setSettings] = useState({
    emailNotifications: true,
    slackNotifications: false,
    autoRefresh: true,
    darkMode: false,
    dataRetention: 90,
    cacheExpiry: 24,
  });

  const [automationJobs, setAutomationJobs] = useState([
    {
      id: 1,
      name: 'Daily Data Sync',
      schedule: 'Daily at 2:00 AM',
      status: 'active',
      lastRun: '2025-10-18 02:00',
      nextRun: '2025-10-19 02:00',
    },
    {
      id: 2,
      name: 'Weekly Report Generation',
      schedule: 'Monday at 9:00 AM',
      status: 'active',
      lastRun: '2025-10-14 09:00',
      nextRun: '2025-10-21 09:00',
    },
    {
      id: 3,
      name: 'Cache Cleanup',
      schedule: 'Every 6 hours',
      status: 'paused',
      lastRun: '2025-10-18 12:00',
      nextRun: 'Paused',
    },
  ]);

  const handleSettingChange = (setting) => (event) => {
    setSettings({
      ...settings,
      [setting]: event.target.checked !== undefined ? event.target.checked : event.target.value,
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return theme.palette.success.main;
      case 'paused':
        return theme.palette.warning.main;
      case 'failed':
        return theme.palette.error.main;
      default:
        return theme.palette.grey[500];
    }
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* General Settings */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
              <SettingsIcon color="primary" />
              <Typography variant="h6">General Settings</Typography>
            </Stack>
            <Stack spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoRefresh}
                    onChange={handleSettingChange('autoRefresh')}
                  />
                }
                label="Auto-refresh dashboards"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.darkMode}
                    onChange={handleSettingChange('darkMode')}
                  />
                }
                label="Dark mode (not available for change)"
                disabled
              />
              <FormControl fullWidth size="small">
                <InputLabel>Data Retention (days)</InputLabel>
                <Select
                  value={settings.dataRetention}
                  label="Data Retention (days)"
                  onChange={handleSettingChange('dataRetention')}
                >
                  <MenuItem value={30}>30 days</MenuItem>
                  <MenuItem value={60}>60 days</MenuItem>
                  <MenuItem value={90}>90 days</MenuItem>
                  <MenuItem value={180}>180 days</MenuItem>
                  <MenuItem value={365}>1 year</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>Cache Expiry (hours)</InputLabel>
                <Select
                  value={settings.cacheExpiry}
                  label="Cache Expiry (hours)"
                  onChange={handleSettingChange('cacheExpiry')}
                >
                  <MenuItem value={1}>1 hour</MenuItem>
                  <MenuItem value={6}>6 hours</MenuItem>
                  <MenuItem value={12}>12 hours</MenuItem>
                  <MenuItem value={24}>24 hours</MenuItem>
                  <MenuItem value={48}>48 hours</MenuItem>
                </Select>
              </FormControl>
            </Stack>
          </Paper>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
              <NotificationsIcon color="primary" />
              <Typography variant="h6">Notifications</Typography>
            </Stack>
            <Stack spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.emailNotifications}
                    onChange={handleSettingChange('emailNotifications')}
                  />
                }
                label="Email notifications"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.slackNotifications}
                    onChange={handleSettingChange('slackNotifications')}
                  />
                }
                label="Slack notifications"
              />
              <TextField
                fullWidth
                size="small"
                label="Notification Email"
                defaultValue="admin@example.com"
                helperText="Receive alerts and reports"
              />
              <TextField
                fullWidth
                size="small"
                label="Slack Webhook URL"
                placeholder="https://hooks.slack.com/..."
                helperText="Optional Slack integration"
              />
            </Stack>
          </Paper>
        </Grid>

        {/* Automation Jobs */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb: 3 }}>
              <Stack direction="row" spacing={2} alignItems="center">
                <ScheduleIcon color="primary" />
                <Typography variant="h6">Automation & Scheduling</Typography>
              </Stack>
              <Button startIcon={<AddIcon />} variant="contained" size="small">
                New Job
              </Button>
            </Stack>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Job Name</TableCell>
                    <TableCell>Schedule</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Last Run</TableCell>
                    <TableCell>Next Run</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {automationJobs.map((job) => (
                    <TableRow key={job.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {job.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {job.schedule}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={job.status}
                          size="small"
                          sx={{
                            bgcolor: alpha(getStatusColor(job.status), 0.1),
                            color: getStatusColor(job.status),
                            textTransform: 'capitalize',
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {job.lastRun}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {job.nextRun}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <IconButton size="small" color="primary">
                            {job.status === 'active' ? <PauseIcon fontSize="small" /> : <PlayIcon fontSize="small" />}
                          </IconButton>
                          <IconButton size="small" color="primary">
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" color="error">
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Save Button */}
        <Grid item xs={12}>
          <Stack direction="row" spacing={2} justifyContent="flex-end">
            <Button variant="outlined">Reset to Defaults</Button>
            <Button variant="contained">Save Settings</Button>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PlatformSettings;
