import React, { useState, useEffect } from 'react';
import {
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Stack,
  IconButton,
  Tooltip,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Switch,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  CloudQueue as CloudIcon,
  Computer as LocalIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';

const DATABASE_CONFIGS = {
  bigquery: {
    label: 'BigQuery',
    icon: '☁️',
    color: '#4285F4',
    description: 'Google BigQuery data warehouse',
    requiresAuth: true,
  },
  snowflake: {
    label: 'Snowflake',
    icon: '❄️',
    color: '#29B5E8',
    description: 'Snowflake cloud data platform',
    requiresAuth: true,
  },
  postgresql: {
    label: 'PostgreSQL',
    icon: '🐘',
    color: '#336791',
    description: 'PostgreSQL relational database',
    requiresAuth: true,
  },
  redshift: {
    label: 'Redshift',
    icon: '🔴',
    color: '#FF9900',
    description: 'Amazon Redshift data warehouse',
    requiresAuth: true,
  },
  databricks: {
    label: 'Databricks',
    icon: '🧱',
    color: '#FF3621',
    description: 'Databricks lakehouse platform',
    requiresAuth: true,
  },
};

const DatabaseSelector = ({
  value,
  onChange,
  onMultiSelect,
  disabled = false,
  showMultiSelect = true,
  showAddNew = true,
  size = 'medium'
}) => {
  const [selectedDatabase, setSelectedDatabase] = useState(value || 'bigquery');
  const [availableDatabases, setAvailableDatabases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [multiSelectEnabled, setMultiSelectEnabled] = useState(false);
  const [selectedDatabases, setSelectedDatabases] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState({});

  useEffect(() => {
    loadAvailableDatabases();
    checkConnectionStatus();
  }, []);

  const loadAvailableDatabases = async () => {
    setLoading(true);
    try {
      // Load only chat-enabled databases
      const response = await apiService.getChatEnabledDatabases();
      if (response.data) {
        const enabledDatabases = response.data.connectors || [];

        // Map to simple format for the selector
        const databases = enabledDatabases.map(db => ({
          type: db.connector_type,
          name: db.name,
          enabled: true
        }));

        setAvailableDatabases(databases);

        // Show alert if no databases are enabled
        if (databases.length === 0) {
          setConnectionStatus({});
        }
      }
    } catch (error) {
      console.error('Error loading databases:', error);
      // Fall back to empty list if API fails
      setAvailableDatabases([]);
    } finally {
      setLoading(false);
    }
  };

  const checkConnectionStatus = async () => {
    try {
      const response = await apiService.checkConnectorStatus();
      if (response.data) {
        setConnectionStatus(response.data.status || {});
      }
    } catch (error) {
      console.error('Error checking connection status:', error);
    }
  };

  const handleDatabaseChange = (event) => {
    const newValue = event.target.value;
    setSelectedDatabase(newValue);
    if (onChange) {
      onChange(newValue);
    }
  };

  const handleMultiSelectToggle = () => {
    const newValue = !multiSelectEnabled;
    setMultiSelectEnabled(newValue);

    if (newValue) {
      // Enable multi-select, add current database to selection
      setSelectedDatabases([selectedDatabase]);
      if (onMultiSelect) {
        onMultiSelect([selectedDatabase]);
      }
    } else {
      // Disable multi-select, clear multi-selection
      setSelectedDatabases([]);
      if (onMultiSelect) {
        onMultiSelect(null);
      }
    }
  };

  const handleMultiDatabaseToggle = (database) => {
    let newSelection = [...selectedDatabases];

    if (newSelection.includes(database)) {
      newSelection = newSelection.filter(db => db !== database);
    } else {
      newSelection.push(database);
    }

    setSelectedDatabases(newSelection);
    if (onMultiSelect) {
      onMultiSelect(newSelection.length > 0 ? newSelection : null);
    }
  };

  const handleAddNewDatabase = () => {
    setConfigDialogOpen(true);
  };

  const handleTestConnection = async (database) => {
    try {
      const response = await apiService.testConnection(database);
      if (response.data.success) {
        setConnectionStatus(prev => ({
          ...prev,
          [database]: 'connected'
        }));
      } else {
        setConnectionStatus(prev => ({
          ...prev,
          [database]: 'error'
        }));
      }
    } catch (error) {
      setConnectionStatus(prev => ({
        ...prev,
        [database]: 'error'
      }));
    }
  };

  const getStatusIcon = (database) => {
    const status = connectionStatus[database];
    if (status === 'connected') {
      return <CheckIcon fontSize="small" sx={{ color: 'success.main' }} />;
    } else if (status === 'error') {
      return <CloseIcon fontSize="small" sx={{ color: 'error.main' }} />;
    }
    return null;
  };

  return (
    <>
      {/* Show alert if no databases are enabled */}
      {availableDatabases.length === 0 && !loading && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => window.location.href = '/control-center'}
            >
              Go to Control Center
            </Button>
          }
        >
          No databases are enabled for chat. Enable databases in the Control Center.
        </Alert>
      )}

      <Stack direction="row" spacing={1} alignItems="center">
        {!multiSelectEnabled ? (
          <FormControl
            size={size}
            disabled={disabled || loading}
            sx={{ minWidth: 150 }}
          >
            <InputLabel>Database</InputLabel>
            <Select
              value={selectedDatabase}
              onChange={handleDatabaseChange}
              label="Database"
              startAdornment={
                DATABASE_CONFIGS[selectedDatabase] && (
                  <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
                    <Typography fontSize="small">
                      {DATABASE_CONFIGS[selectedDatabase].icon}
                    </Typography>
                  </Box>
                )
              }
              endAdornment={getStatusIcon(selectedDatabase)}
            >
              {Object.keys(DATABASE_CONFIGS).map((db) => (
                <MenuItem key={db} value={db}>
                  <Stack direction="row" spacing={1} alignItems="center" width="100%">
                    <Typography>{DATABASE_CONFIGS[db].icon}</Typography>
                    <Typography>{DATABASE_CONFIGS[db].label}</Typography>
                  </Stack>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        ) : (
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              Selected Databases:
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap">
              {selectedDatabases.length === 0 ? (
                <Typography variant="body2" color="text.disabled">
                  No databases selected
                </Typography>
              ) : (
                selectedDatabases.map(db => (
                  <Chip
                    key={db}
                    label={`${DATABASE_CONFIGS[db]?.icon} ${DATABASE_CONFIGS[db]?.label}`}
                    size="small"
                    onDelete={() => handleMultiDatabaseToggle(db)}
                    color="primary"
                    variant="outlined"
                  />
                ))
              )}
            </Stack>
          </Box>
        )}

        {showMultiSelect && (
          <Tooltip title={multiSelectEnabled ? "Disable multi-database query" : "Enable multi-database query"}>
            <IconButton
              size="small"
              onClick={handleMultiSelectToggle}
              color={multiSelectEnabled ? "primary" : "default"}
            >
              <DatabaseIcon />
            </IconButton>
          </Tooltip>
        )}

        {showAddNew && (
          <Tooltip title="Configure databases">
            <IconButton
              size="small"
              onClick={handleAddNewDatabase}
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        )}

        <Tooltip title="Refresh connections">
          <IconButton
            size="small"
            onClick={() => {
              loadAvailableDatabases();
              checkConnectionStatus();
            }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={20} /> : <RefreshIcon />}
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Multi-Database Selection Dialog */}
      <Dialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Database Configuration</Typography>
            <IconButton onClick={() => setConfigDialogOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent>
          {multiSelectEnabled && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Multi-database query mode enabled. Select databases to include in cross-database queries.
            </Alert>
          )}
          <List>
            {Object.entries(DATABASE_CONFIGS).map(([key, config]) => (
              <ListItem key={key}>
                <ListItemIcon>
                  <Typography fontSize="large">{config.icon}</Typography>
                </ListItemIcon>
                <ListItemText
                  primary={config.label}
                  secondary={config.description}
                />
                <ListItemSecondaryAction>
                  <Stack direction="row" spacing={1} alignItems="center">
                    {getStatusIcon(key)}
                    {multiSelectEnabled ? (
                      <Switch
                        checked={selectedDatabases.includes(key)}
                        onChange={() => handleMultiDatabaseToggle(key)}
                        disabled={connectionStatus[key] === 'error'}
                      />
                    ) : (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleTestConnection(key)}
                        disabled={loading}
                      >
                        Test
                      </Button>
                    )}
                  </Stack>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>
            Close
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              // Navigate to full database configuration page
              window.location.href = '/settings/databases';
            }}
          >
            Add New Database
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default DatabaseSelector;