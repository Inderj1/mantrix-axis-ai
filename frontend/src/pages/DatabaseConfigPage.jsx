import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Grid,
  Button,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Chip,
  Stack,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormHelperText,
  Switch,
  FormControlLabel,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Tooltip,
  Badge,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add as AddIcon,
  Storage as DatabaseIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  PlayArrow as TestIcon,
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Speed as PerformanceIcon,
  Refresh as RefreshIcon,
  CloudQueue as CloudIcon,
  Computer as LocalIcon,
  VpnKey as KeyIcon,
  ContentCopy as CopyIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';

const DATABASE_TYPES = {
  bigquery: {
    label: 'Google BigQuery',
    icon: '☁️',
    color: '#4285F4',
    category: 'Cloud Data Warehouse',
    supportsOAuth: true,
    fields: [
      { name: 'project_id', label: 'Project ID', required: true, type: 'text', placeholder: 'my-gcp-project' },
      { name: 'dataset', label: 'Dataset', required: true, type: 'text', placeholder: 'my_dataset' },
      { name: 'location', label: 'Location', required: false, type: 'text', default: 'US' },
      {
        name: 'auth_method',
        label: 'Authentication Method',
        required: true,
        type: 'select',
        default: 'service_account',
        options: [
          { value: 'service_account', label: 'Service Account JSON (upload key file)' },
          { value: 'workload_identity', label: 'Workload Identity Federation (keyless)' },
          { value: 'oauth', label: 'Connect with Google Account' },
        ],
      },
      // Service Account fields (shown when auth_method === 'service_account')
      {
        name: 'credentials_json',
        label: 'Service Account JSON',
        required: false,
        type: 'file',
        showWhen: { auth_method: 'service_account' },
      },
      // Workload Identity Federation fields (shown when auth_method === 'workload_identity')
      {
        name: 'wif_provider_resource_name',
        label: 'WIF Provider Resource Name',
        required: false,
        type: 'text',
        placeholder: 'projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID',
        showWhen: { auth_method: 'workload_identity' },
        helpText: 'Full resource name of the Workload Identity Pool provider in your GCP project',
      },
      {
        name: 'wif_service_account_email',
        label: 'Service Account to Impersonate',
        required: false,
        type: 'text',
        placeholder: 'mantrix-access@project-id.iam.gserviceaccount.com',
        showWhen: { auth_method: 'workload_identity' },
        helpText: 'GCP service account that Mantrix will impersonate via WIF',
      },
    ],
  },
  snowflake: {
    label: 'Snowflake',
    icon: '❄️',
    color: '#29B5E8',
    category: 'Cloud Data Warehouse',
    fields: [
      { name: 'account', label: 'Account', required: true, type: 'text' },
      { name: 'user', label: 'Username', required: true, type: 'text' },
      { name: 'password', label: 'Password', required: true, type: 'password' },
      { name: 'warehouse', label: 'Warehouse', required: true, type: 'text' },
      { name: 'database', label: 'Database', required: true, type: 'text' },
      { name: 'schema', label: 'Schema', required: false, type: 'text', default: 'PUBLIC' },
      { name: 'role', label: 'Role', required: false, type: 'text' },
    ],
  },
  postgresql: {
    label: 'PostgreSQL',
    icon: '🐘',
    color: '#336791',
    category: 'Relational Database',
    fields: [
      { name: 'host', label: 'Host', required: true, type: 'text' },
      { name: 'port', label: 'Port', required: true, type: 'number', default: 5432 },
      { name: 'database', label: 'Database', required: true, type: 'text' },
      { name: 'username', label: 'Username', required: true, type: 'text' },
      { name: 'password', label: 'Password', required: true, type: 'password' },
      { name: 'ssl', label: 'Use SSL', required: false, type: 'boolean', default: false },
    ],
  },
  redshift: {
    label: 'Amazon Redshift',
    icon: '🔴',
    color: '#FF9900',
    category: 'Cloud Data Warehouse',
    fields: [
      { name: 'host', label: 'Cluster Endpoint', required: true, type: 'text' },
      { name: 'port', label: 'Port', required: true, type: 'number', default: 5439 },
      { name: 'database', label: 'Database', required: true, type: 'text' },
      { name: 'user', label: 'Username', required: true, type: 'text' },
      { name: 'password', label: 'Password', required: true, type: 'password' },
      { name: 'ssl', label: 'Use SSL', required: false, type: 'boolean', default: true },
    ],
  },
  databricks: {
    label: 'Databricks',
    icon: '🧱',
    color: '#FF3621',
    category: 'Lakehouse Platform',
    fields: [
      { name: 'server_hostname', label: 'Server Hostname', required: true, type: 'text' },
      { name: 'http_path', label: 'HTTP Path', required: true, type: 'text' },
      { name: 'access_token', label: 'Access Token', required: true, type: 'password' },
      { name: 'catalog', label: 'Catalog', required: false, type: 'text', default: 'hive_metastore' },
      { name: 'schema', label: 'Schema', required: false, type: 'text', default: 'default' },
    ],
  },
};

const DatabaseConfigPage = () => {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [testResults, setTestResults] = useState({});
  const [showPasswords, setShowPasswords] = useState({});

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    type: '',
    config: {},
  });
  const [formErrors, setFormErrors] = useState({});

  useEffect(() => {
    loadConnectors();
  }, []);

  const loadConnectors = async () => {
    setLoading(true);
    try {
      const response = await apiService.listConnectors();
      if (response.data) {
        setConnectors(response.data.connectors || []);
        // Test all connections
        for (const connector of response.data.connectors || []) {
          testConnection(connector.id);
        }
      }
    } catch (error) {
      console.error('Error loading connectors:', error);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (connectorId) => {
    try {
      const response = await apiService.testExistingConnector(connectorId);
      setTestResults(prev => ({
        ...prev,
        [connectorId]: response.data.success ? 'connected' : 'error',
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [connectorId]: 'error',
      }));
    }
  };

  const handleAddConnector = () => {
    setEditMode(false);
    setSelectedConnector(null);
    setFormData({
      name: '',
      type: '',
      config: {},
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleEditConnector = (connector) => {
    setEditMode(true);
    setSelectedConnector(connector);
    setFormData({
      name: connector.name,
      type: connector.type,
      config: connector.config || {},
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleDeleteConnector = async (connectorId) => {
    if (window.confirm('Are you sure you want to delete this connector?')) {
      try {
        await apiService.deleteConnector(connectorId);
        loadConnectors();
      } catch (error) {
        console.error('Error deleting connector:', error);
      }
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.name) {
      errors.name = 'Name is required';
    }

    if (!formData.type) {
      errors.type = 'Database type is required';
    }

    if (formData.type) {
      const dbConfig = DATABASE_TYPES[formData.type];
      if (dbConfig) {
        dbConfig.fields.forEach(field => {
          if (field.required && !formData.config[field.name]) {
            errors[field.name] = `${field.label} is required`;
          }
        });
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveConnector = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      if (editMode) {
        await apiService.updateConnector(selectedConnector.id, formData);
      } else {
        await apiService.createConnector(formData.type, formData.name, formData.config);
      }
      setDialogOpen(false);
      loadConnectors();
    } catch (error) {
      console.error('Error saving connector:', error);
      setFormErrors({ submit: error.response?.data?.detail || 'Error saving connector' });
    }
  };

  const handleTestNewConnection = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      const response = await apiService.testConnector(formData.type, formData.config);
      if (response.data.success) {
        alert('Connection successful!');
      } else {
        alert(`Connection failed: ${response.data.error}`);
      }
    } catch (error) {
      alert(`Connection failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFormData(prev => ({
      ...prev,
      config: {
        ...prev.config,
        [fieldName]: value,
      },
    }));

    // Clear error for this field
    if (formErrors[fieldName]) {
      setFormErrors(prev => ({
        ...prev,
        [fieldName]: undefined,
      }));
    }
  };

  const getStatusIcon = (connectorId) => {
    const status = testResults[connectorId];
    if (status === 'connected') {
      return <CheckCircleIcon sx={{ color: 'success.main' }} />;
    } else if (status === 'error') {
      return <ErrorIcon sx={{ color: 'error.main' }} />;
    }
    return <WarningIcon sx={{ color: 'warning.main' }} />;
  };

  // Check if a field should be shown based on showWhen condition
  const shouldShowField = (field) => {
    if (!field.showWhen) return true;
    const [conditionField, conditionValue] = Object.entries(field.showWhen)[0];
    return formData.config[conditionField] === conditionValue;
  };

  // Handle OAuth flow for BigQuery
  const handleOAuthConnect = async () => {
    try {
      const response = await apiService.initiateBigQueryOAuth();
      if (response.data.authorization_url) {
        // Store state for later validation
        sessionStorage.setItem('oauth_state', response.data.state);
        // Open OAuth popup
        const popup = window.open(
          response.data.authorization_url,
          'google-oauth',
          'width=500,height=600,scrollbars=yes'
        );

        // Listen for OAuth callback message
        const handleMessage = async (event) => {
          if (event.origin !== window.location.origin) return;
          if (event.data.type === 'oauth_success') {
            window.removeEventListener('message', handleMessage);
            const storedState = sessionStorage.getItem('oauth_state');
            if (event.data.state !== storedState) {
              alert('OAuth state mismatch. Please try again.');
              return;
            }
            // Complete the OAuth flow
            try {
              const completeResponse = await apiService.completeBigQueryOAuth({
                code: event.data.code,
                state: event.data.state,
                project_id: formData.config.project_id,
                dataset: formData.config.dataset,
                name: formData.name,
                location: formData.config.location || 'US',
              });
              if (completeResponse.data) {
                alert('BigQuery connection created successfully!');
                setDialogOpen(false);
                loadConnectors();
              }
            } catch (error) {
              alert(`Failed to complete OAuth: ${error.response?.data?.detail || error.message}`);
            }
          } else if (event.data.type === 'oauth_error') {
            window.removeEventListener('message', handleMessage);
            alert(`OAuth failed: ${event.data.error}`);
          }
        };
        window.addEventListener('message', handleMessage);
      }
    } catch (error) {
      alert(`Failed to initiate OAuth: ${error.response?.data?.detail || error.message}`);
    }
  };

  const renderConfigForm = () => {
    if (!formData.type) return null;

    const dbConfig = DATABASE_TYPES[formData.type];
    if (!dbConfig) return null;

    // Check if OAuth is selected for BigQuery
    const isOAuthSelected = formData.type === 'bigquery' && formData.config.auth_method === 'oauth';

    return (
      <Grid container spacing={2} sx={{ mt: 1 }}>
        {dbConfig.fields.map((field) => {
          // Check showWhen condition
          if (!shouldShowField(field)) return null;

          return (
            <Grid item xs={12} key={field.name}>
              {field.type === 'select' ? (
                <FormControl fullWidth required={field.required} error={!!formErrors[field.name]}>
                  <InputLabel>{field.label}</InputLabel>
                  <Select
                    value={formData.config[field.name] || field.default || ''}
                    onChange={(e) => handleFieldChange(field.name, e.target.value)}
                    label={field.label}
                  >
                    {field.options.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                  {formErrors[field.name] && (
                    <FormHelperText>{formErrors[field.name]}</FormHelperText>
                  )}
                </FormControl>
              ) : field.type === 'boolean' ? (
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.config[field.name] || field.default || false}
                      onChange={(e) => handleFieldChange(field.name, e.target.checked)}
                    />
                  }
                  label={field.label}
                />
              ) : field.type === 'password' ? (
                <TextField
                  fullWidth
                  type={showPasswords[field.name] ? 'text' : 'password'}
                  label={field.label}
                  value={formData.config[field.name] || ''}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  required={field.required}
                  error={!!formErrors[field.name]}
                  helperText={formErrors[field.name] || field.helpText}
                  InputProps={{
                    endAdornment: (
                      <IconButton
                        onClick={() => setShowPasswords(prev => ({
                          ...prev,
                          [field.name]: !prev[field.name],
                        }))}
                        edge="end"
                      >
                        {showPasswords[field.name] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    ),
                  }}
                />
              ) : field.type === 'file' ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {field.label}
                  </Typography>
                  <Button
                    variant="outlined"
                    component="label"
                    fullWidth
                  >
                    Upload {field.label}
                    <input
                      type="file"
                      hidden
                      accept=".json"
                      onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onload = (event) => {
                            handleFieldChange(field.name, event.target.result);
                          };
                          reader.readAsText(file);
                        }
                      }}
                    />
                  </Button>
                  {formData.config[field.name] && (
                    <Chip
                      label="File uploaded"
                      size="small"
                      color="success"
                      sx={{ mt: 1 }}
                    />
                  )}
                </Box>
              ) : (
                <TextField
                  fullWidth
                  type={field.type === 'number' ? 'number' : 'text'}
                  label={field.label}
                  value={formData.config[field.name] || field.default || ''}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  required={field.required}
                  error={!!formErrors[field.name]}
                  helperText={formErrors[field.name] || field.helpText}
                  placeholder={field.placeholder}
                />
              )}
            </Grid>
          );
        })}

        {/* OAuth Connect Button for BigQuery */}
        {isOAuthSelected && (
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mb: 2 }}>
              Click the button below to authenticate with your Google account.
              You'll be redirected to Google to grant BigQuery access.
            </Alert>
            <Button
              variant="contained"
              color="primary"
              fullWidth
              onClick={handleOAuthConnect}
              disabled={!formData.name || !formData.config.project_id || !formData.config.dataset}
              startIcon={<CloudIcon />}
              sx={{ py: 1.5 }}
            >
              Connect with Google
            </Button>
          </Grid>
        )}

        {/* WIF Setup Instructions */}
        {formData.type === 'bigquery' && formData.config.auth_method === 'workload_identity' && (
          <Grid item xs={12}>
            <Alert severity="info">
              <Typography variant="subtitle2" gutterBottom>Workload Identity Federation Setup</Typography>
              <Typography variant="body2">
                To use WIF, you need to create a Workload Identity Pool in your GCP project
                that trusts Mantrix's AWS identity. Contact your GCP administrator or see the
                documentation for setup instructions.
              </Typography>
            </Alert>
          </Grid>
        )}
      </Grid>
    );
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Database Connections
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your database connections and configure data sources
        </Typography>
      </Box>

      {/* Statistics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <DatabaseIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
            <Typography variant="h4">{connectors.length}</Typography>
            <Typography variant="body2" color="text.secondary">
              Total Connections
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
            <Typography variant="h4">
              {Object.values(testResults).filter(r => r === 'connected').length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <ErrorIcon sx={{ fontSize: 40, color: 'error.main', mb: 1 }} />
            <Typography variant="h4">
              {Object.values(testResults).filter(r => r === 'error').length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Failed
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <CloudIcon sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
            <Typography variant="h4">
              {connectors.filter(c => ['bigquery', 'snowflake', 'redshift', 'databricks'].includes(c.type)).length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Cloud
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Actions Bar */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddConnector}
          >
            Add Connection
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadConnectors}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Connector Cards */}
      <Grid container spacing={3}>
        {loading && connectors.length === 0 ? (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          </Grid>
        ) : connectors.length === 0 ? (
          <Grid item xs={12}>
            <Alert severity="info">
              No database connections configured. Click "Add Connection" to get started.
            </Alert>
          </Grid>
        ) : (
          connectors.map((connector) => {
            const dbType = DATABASE_TYPES[connector.type] || {};
            return (
              <Grid item xs={12} sm={6} md={4} key={connector.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h5" sx={{ mr: 1 }}>
                        {dbType.icon || '📊'}
                      </Typography>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6">
                          {connector.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {dbType.label || connector.type}
                        </Typography>
                      </Box>
                      {getStatusIcon(connector.id)}
                    </Box>

                    <Stack spacing={1}>
                      <Chip
                        label={dbType.category || 'Database'}
                        size="small"
                        variant="outlined"
                      />
                      <Typography variant="body2" color="text.secondary">
                        Created: {new Date(connector.created_at).toLocaleDateString()}
                      </Typography>
                    </Stack>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<TestIcon />}
                      onClick={() => testConnection(connector.id)}
                    >
                      Test
                    </Button>
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
                      color="error"
                      onClick={() => handleDeleteConnector(connector.id)}
                    >
                      Delete
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            );
          })
        )}
      </Grid>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editMode ? 'Edit Connection' : 'Add New Connection'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <TextField
              fullWidth
              label="Connection Name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              error={!!formErrors.name}
              helperText={formErrors.name}
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }} error={!!formErrors.type}>
              <InputLabel>Database Type</InputLabel>
              <Select
                value={formData.type}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  type: e.target.value,
                  config: {} // Reset config when type changes
                }))}
                label="Database Type"
                disabled={editMode}
              >
                {Object.entries(DATABASE_TYPES).map(([key, config]) => (
                  <MenuItem key={key} value={key}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography>{config.icon}</Typography>
                      <Typography>{config.label}</Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
              {formErrors.type && <FormHelperText>{formErrors.type}</FormHelperText>}
            </FormControl>

            {renderConfigForm()}

            {formErrors.submit && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {formErrors.submit}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleTestNewConnection}
            startIcon={<TestIcon />}
            disabled={!formData.type}
          >
            Test Connection
          </Button>
          <Button
            onClick={handleSaveConnector}
            variant="contained"
            startIcon={editMode ? <EditIcon /> : <AddIcon />}
          >
            {editMode ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default DatabaseConfigPage;