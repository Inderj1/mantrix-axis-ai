import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  Stack,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Switch,
  FormControlLabel,
  Alert,
  Tabs,
  Tab,
  Divider,
  Avatar,
  LinearProgress,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Tooltip,
  Badge,
  useTheme,
  alpha,
  CircularProgress,
  Snackbar,
  FormGroup,
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  Cloud as CloudIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  Key as KeyIcon,
  Settings as SettingsIcon,
  PlayArrow as TestIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  CloudQueue as BigQueryIcon,
  DataArray as SnowflakeIcon,
  DataObject as PostgreSQLIcon,
  Storage as RedshiftIcon,
  Insights as DatabricksIcon,
  Chat as ChatIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/api';
import DatabaseToggleCard from './DatabaseToggleCard';

// Database type configurations
const DATABASE_CONFIGS = {
  bigquery: {
    name: 'BigQuery',
    icon: <BigQueryIcon />,
    color: '#4285F4',
    fields: [
      { name: 'project_id', label: 'Project ID', required: true },
      { name: 'dataset_id', label: 'Dataset ID', required: true },
      { name: 'credentials_json', label: 'Service Account JSON', type: 'json', required: true },
    ],
  },
  snowflake: {
    name: 'Snowflake',
    icon: <SnowflakeIcon />,
    color: '#29B5E8',
    fields: [
      { name: 'account', label: 'Account', required: true },
      { name: 'warehouse', label: 'Warehouse', required: true },
      { name: 'database', label: 'Database', required: true },
      { name: 'schema', label: 'Schema', default: 'PUBLIC' },
      { name: 'username', label: 'Username', required: true },
      { name: 'password', label: 'Password', type: 'password', required: true },
      { name: 'role', label: 'Role' },
    ],
  },
  postgresql: {
    name: 'PostgreSQL',
    icon: <PostgreSQLIcon />,
    color: '#336791',
    fields: [
      { name: 'host', label: 'Host', required: true },
      { name: 'port', label: 'Port', default: 5432, type: 'number' },
      { name: 'database', label: 'Database', required: true },
      { name: 'username', label: 'Username', required: true },
      { name: 'password', label: 'Password', type: 'password', required: true },
      { name: 'ssl', label: 'Use SSL', type: 'checkbox' },
    ],
  },
  redshift: {
    name: 'Amazon Redshift',
    icon: <RedshiftIcon />,
    color: '#FF9900',
    fields: [
      { name: 'host', label: 'Cluster Endpoint', required: true },
      { name: 'port', label: 'Port', default: 5439, type: 'number' },
      { name: 'database', label: 'Database', required: true },
      { name: 'username', label: 'Username', required: true },
      { name: 'password', label: 'Password', type: 'password', required: true },
      { name: 'schema', label: 'Schema', default: 'public' },
    ],
  },
  databricks: {
    name: 'Databricks',
    icon: <DatabricksIcon />,
    color: '#FF3621',
    fields: [
      { name: 'server_hostname', label: 'Server Hostname', required: true },
      { name: 'http_path', label: 'HTTP Path', required: true },
      { name: 'catalog', label: 'Catalog', required: true },
      { name: 'schema', label: 'Schema', required: true },
      { name: 'token', label: 'Access Token', type: 'password', required: true },
    ],
  },
};

const DataSourcesConnections = () => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState(null);
  const [formData, setFormData] = useState({});
  const [testingConnection, setTestingConnection] = useState(false);
  const [showPassword, setShowPassword] = useState({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [maxChatDatabases, setMaxChatDatabases] = useState(2);
  const [enabledCount, setEnabledCount] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [connectorToDelete, setConnectorToDelete] = useState(null);

  // Fetch connectors on mount
  useEffect(() => {
    fetchConnectors();
    fetchSettings();
  }, []);

  const fetchConnectors = async () => {
    setLoading(true);
    try {
      const response = await apiService.getConnectors();
      if (response.data) {
        // Transform API data to include UI properties
        const enrichedConnectors = response.data.connectors.map(conn => ({
          ...conn,
          icon: DATABASE_CONFIGS[conn.connector_type]?.icon || <DatabaseIcon />,
          host: conn.config?.host || conn.config?.server_hostname || conn.config?.account || 'N/A',
          database: conn.config?.database || conn.config?.dataset_id || conn.config?.catalog || 'N/A',
          tables: conn.metadata?.table_count || 0,
          size: conn.metadata?.total_size || 'Unknown',
          lastSync: conn.metadata?.last_sync
            ? new Date(conn.metadata.last_sync).toLocaleString()
            : 'Never',
        }));

        setConnectors(enrichedConnectors);

        // Count enabled databases
        const enabled = enrichedConnectors.filter(c => c.enabled_for_chat).length;
        setEnabledCount(enabled);
      }
    } catch (error) {
      console.error('Error fetching connectors:', error);
      showSnackbar('Failed to fetch database connectors', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await apiService.getControlCenterSettings();
      if (response.data?.settings) {
        setMaxChatDatabases(response.data.settings.max_chat_databases || 2);
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleAddConnector = () => {
    setSelectedConnector(null);
    setFormData({ connector_type: 'bigquery' });
    setDialogOpen(true);
  };

  const handleEditConnector = (connector) => {
    setSelectedConnector(connector);
    setFormData({
      name: connector.name,
      connector_type: connector.connector_type,
      ...connector.config,
    });
    setDialogOpen(true);
  };

  const handleDeleteConnector = (connector) => {
    setConnectorToDelete(connector);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!connectorToDelete) return;

    try {
      await apiService.deleteConnector(connectorToDelete.id);
      showSnackbar('Connector deleted successfully', 'success');
      fetchConnectors();
    } catch (error) {
      console.error('Error deleting connector:', error);
      showSnackbar('Failed to delete connector', 'error');
    } finally {
      setDeleteDialogOpen(false);
      setConnectorToDelete(null);
    }
  };

  const handleSaveConnector = async () => {
    try {
      const { name, connector_type, ...config } = formData;

      const payload = {
        name,
        connector_type,
        config,
      };

      if (selectedConnector) {
        // Update existing connector
        await apiService.updateConnector(selectedConnector.id, payload);
        showSnackbar('Connector updated successfully', 'success');
      } else {
        // Create new connector
        await apiService.createConnector(payload);
        showSnackbar('Connector created successfully', 'success');
      }

      setDialogOpen(false);
      fetchConnectors();
    } catch (error) {
      console.error('Error saving connector:', error);
      showSnackbar('Failed to save connector', 'error');
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    try {
      const { name, connector_type, ...config } = formData;

      const response = await apiService.testConnector({
        connector_type,
        config,
      });

      if (response.data?.success) {
        showSnackbar('Connection test successful!', 'success');
      } else {
        showSnackbar(response.data?.error || 'Connection test failed', 'error');
      }
    } catch (error) {
      console.error('Error testing connection:', error);
      showSnackbar('Connection test failed', 'error');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleFormChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleToggleChat = async () => {
    // Refresh connectors after toggle
    await fetchConnectors();
  };

  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const renderConnectorForm = () => {
    const dbType = formData.connector_type || 'bigquery';
    const config = DATABASE_CONFIGS[dbType];

    if (!config) return null;

    return (
      <Stack spacing={3} sx={{ mt: 2 }}>
        <TextField
          fullWidth
          label="Connector Name"
          value={formData.name || ''}
          onChange={(e) => handleFormChange('name', e.target.value)}
          required
        />

        <FormControl fullWidth>
          <InputLabel>Database Type</InputLabel>
          <Select
            value={dbType}
            label="Database Type"
            onChange={(e) => handleFormChange('connector_type', e.target.value)}
            disabled={!!selectedConnector}
          >
            {Object.entries(DATABASE_CONFIGS).map(([type, conf]) => (
              <MenuItem key={type} value={type}>
                <Stack direction="row" spacing={1} alignItems="center">
                  {conf.icon}
                  <span>{conf.name}</span>
                </Stack>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Divider />

        {config.fields.map((field) => {
          if (field.type === 'checkbox') {
            return (
              <FormControlLabel
                key={field.name}
                control={
                  <Switch
                    checked={formData[field.name] || false}
                    onChange={(e) => handleFormChange(field.name, e.target.checked)}
                  />
                }
                label={field.label}
              />
            );
          }

          if (field.type === 'json') {
            return (
              <TextField
                key={field.name}
                fullWidth
                label={field.label}
                value={formData[field.name] || ''}
                onChange={(e) => handleFormChange(field.name, e.target.value)}
                required={field.required}
                multiline
                rows={4}
                placeholder="Paste JSON here..."
                helperText="Paste the service account JSON credentials"
              />
            );
          }

          return (
            <TextField
              key={field.name}
              fullWidth
              label={field.label}
              value={formData[field.name] || field.default || ''}
              onChange={(e) => handleFormChange(field.name, e.target.value)}
              required={field.required}
              type={field.type === 'password' ?
                (showPassword[field.name] ? 'text' : 'password') :
                (field.type || 'text')
              }
              InputProps={field.type === 'password' ? {
                endAdornment: (
                  <IconButton
                    onClick={() => setShowPassword(prev => ({
                      ...prev,
                      [field.name]: !prev[field.name]
                    }))}
                    edge="end"
                    size="small"
                  >
                    {showPassword[field.name] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                ),
              } : undefined}
            />
          );
        })}
      </Stack>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5" fontWeight={600} gutterBottom>
              Database Connections
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage database connectors and control which databases are available for chat queries
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchConnectors}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddConnector}
            >
              Add Database
            </Button>
          </Stack>
        </Stack>
      </Box>

      {/* Info Alert */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Stack spacing={1}>
          <Typography variant="body2">
            <strong>Chat Database Limit:</strong> Maximum {maxChatDatabases} databases can be enabled for chat at once.
            Currently {enabledCount} of {maxChatDatabases} enabled.
          </Typography>
          <LinearProgress
            variant="determinate"
            value={(enabledCount / maxChatDatabases) * 100}
            sx={{ height: 6, borderRadius: 3 }}
          />
        </Stack>
      </Alert>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab
            label={
              <Stack direction="row" spacing={1} alignItems="center">
                <ChatIcon />
                <span>Chat Enabled ({enabledCount})</span>
              </Stack>
            }
          />
          <Tab
            label={
              <Stack direction="row" spacing={1} alignItems="center">
                <DatabaseIcon />
                <span>All Databases ({connectors.length})</span>
              </Stack>
            }
          />
        </Tabs>
      </Paper>

      {/* Database Cards */}
      <Grid container spacing={3}>
        {activeTab === 0 ? (
          // Show only chat-enabled databases
          connectors
            .filter(conn => conn.enabled_for_chat)
            .map((connector) => (
              <Grid item xs={12} md={6} lg={4} key={connector.id}>
                <DatabaseToggleCard
                  database={connector}
                  onToggle={handleToggleChat}
                  enabledCount={enabledCount}
                  maxAllowed={maxChatDatabases}
                />
                <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    startIcon={<EditIcon />}
                    onClick={() => handleEditConnector(connector)}
                  >
                    Edit
                  </Button>
                  <Button
                    size="small"
                    startIcon={<DeleteIcon />}
                    onClick={() => handleDeleteConnector(connector)}
                    color="error"
                  >
                    Remove
                  </Button>
                </Box>
              </Grid>
            ))
        ) : (
          // Show all databases
          connectors.map((connector) => (
            <Grid item xs={12} md={6} lg={4} key={connector.id}>
              <DatabaseToggleCard
                database={connector}
                onToggle={handleToggleChat}
                enabledCount={enabledCount}
                maxAllowed={maxChatDatabases}
              />
              <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                <Button
                  size="small"
                  startIcon={<EditIcon />}
                  onClick={() => handleEditConnector(connector)}
                >
                  Edit
                </Button>
                <Button
                  size="small"
                  startIcon={<DeleteIcon />}
                  onClick={() => handleDeleteConnector(connector)}
                  color="error"
                >
                  Remove
                </Button>
              </Box>
            </Grid>
          ))
        )}

        {connectors.length === 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <DatabaseIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                No Database Connectors
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Add your first database connector to start querying data
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleAddConnector}
              >
                Add Database
              </Button>
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* Add/Edit Connector Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {selectedConnector ? 'Edit Database Connector' : 'Add Database Connector'}
        </DialogTitle>
        <DialogContent>
          {renderConnectorForm()}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="outlined"
            startIcon={<TestIcon />}
            onClick={handleTestConnection}
            disabled={testingConnection}
          >
            {testingConnection ? 'Testing...' : 'Test Connection'}
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveConnector}
            disabled={!formData.name}
          >
            {selectedConnector ? 'Save Changes' : 'Add Connector'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the connector "{connectorToDelete?.name}"?
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
};

export default DataSourcesConnections;