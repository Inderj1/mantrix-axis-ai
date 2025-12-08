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
  DialogContentText,
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
  Snackbar,
  Avatar,
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
  Sync as SyncIcon,
  HourglassEmpty as PendingIcon,
  CloudSync as SyncingIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';

// Salesforce-style colors
const sfColors = {
  bgPage: '#f3f3f3',
  bgCard: '#ffffff',
  textPrimary: '#032D60',
  textSecondary: '#706e6b',
  accent: '#0176D3',
  accentHover: '#014486',
  border: '#e5e5e5',
  success: '#2E844A',
  warning: '#FE9339',
  error: '#C23934',
  iconBg: '#e8f4fd',
};

const DATABASE_TYPES = {
  bigquery: {
    label: 'Google BigQuery',
    icon: '☁️',
    color: '#4285F4',
    category: 'Cloud Data Warehouse',
    supportsOAuth: true,
    fields: [
      { name: 'project_id', label: 'Project ID', required: true, type: 'text', placeholder: 'my-gcp-project' },
      { name: 'dataset_id', label: 'Dataset', required: true, type: 'text', placeholder: 'my_dataset' },
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
    supportsOAuth: false,
    fields: [
      // Account is always required
      { name: 'account', label: 'Account', required: true, type: 'text', placeholder: 'xy12345.us-east-1', helpText: 'Your Snowflake account identifier' },
      // Auth method selector
      {
        name: 'auth_method',
        label: 'Authentication Method',
        required: true,
        type: 'select',
        default: 'password',
        options: [
          { value: 'password', label: 'Username & Password' },
          { value: 'keypair', label: 'Key Pair (RSA Private Key)' },
          { value: 'pat', label: 'Programmatic Access Token (PAT)' },
        ],
      },
      // Username (shown for all auth methods)
      { name: 'user', label: 'Username', required: true, type: 'text' },
      // Password auth fields
      { name: 'password', label: 'Password', required: true, type: 'password', showWhen: { auth_method: 'password' } },
      // Key-pair auth fields - input method selector
      {
        name: 'private_key_input_method',
        label: 'Private Key Input',
        type: 'select',
        default: 'paste',
        options: [
          { value: 'paste', label: 'Paste PEM text' },
          { value: 'upload', label: 'Upload .pem file' },
        ],
        showWhen: { auth_method: 'keypair' }
      },
      // Key-pair: Paste PEM text
      { name: 'private_key', label: 'Private Key (PEM format)', required: true, type: 'textarea', rows: 8, placeholder: '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----', showWhen: { auth_method: 'keypair', private_key_input_method: 'paste' }, helpText: 'Paste your RSA private key content' },
      // Key-pair: Upload file
      { name: 'private_key_file', label: 'Private Key File', required: true, type: 'file', accept: '.pem,.key,.p8', showWhen: { auth_method: 'keypair', private_key_input_method: 'upload' }, helpText: 'Upload your .pem or .p8 key file' },
      // Key passphrase (optional for both paste and upload)
      { name: 'private_key_passphrase', label: 'Key Passphrase (optional)', required: false, type: 'password', showWhen: { auth_method: 'keypair' }, helpText: 'If your key is encrypted' },
      // PAT auth field
      { name: 'programmatic_access_token', label: 'Access Token', required: true, type: 'password', showWhen: { auth_method: 'pat' }, helpText: 'Generate from Snowflake: Profile → Programmatic Access Tokens' },
      // Common fields (always shown)
      { name: 'warehouse', label: 'Warehouse', required: true, type: 'text', placeholder: 'COMPUTE_WH' },
      { name: 'database', label: 'Database', required: true, type: 'text' },
      { name: 'schema', label: 'Schema', required: false, type: 'text', default: 'PUBLIC' },
      { name: 'role', label: 'Role', required: false, type: 'text', helpText: 'Optional role to assume' },
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

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    severity: 'warning', // 'warning' | 'error' | 'info'
    onConfirm: null,
  });

  // Snackbar state for notifications
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success', // 'success' | 'error' | 'info' | 'warning'
  });

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
    // Set loading state for this connector
    setTestResults(prev => ({
      ...prev,
      [connectorId]: 'testing',
    }));

    try {
      const response = await apiService.testExistingConnector(connectorId);
      const success = response.data.success;
      setTestResults(prev => ({
        ...prev,
        [connectorId]: success ? 'connected' : 'error',
      }));

      // Show snackbar notification
      setSnackbar({
        open: true,
        message: success
          ? 'Connection successful!'
          : `Connection failed: ${response.data.error || 'Unknown error'}`,
        severity: success ? 'success' : 'error',
      });
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [connectorId]: 'error',
      }));

      // Show error snackbar
      setSnackbar({
        open: true,
        message: `Connection failed: ${error.response?.data?.detail || error.message}`,
        severity: 'error',
      });
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
    // Populate form with existing connector data
    // API returns connector_type, but we also support type as fallback
    const connectorType = connector.connector_type || connector.type;

    // Filter out masked sensitive values (***) - backend merges, so omitting preserves existing
    const sensitiveFields = [
      'password', 'api_key', 'secret', 'credentials', 'private_key',
      'private_key_passphrase', 'oauth_access_token', 'access_token',
      'refresh_token', 'programmatic_access_token', 'credentials_json'
    ];
    const cleanConfig = { ...(connector.config || {}) };
    sensitiveFields.forEach(field => {
      if (cleanConfig[field] === '***') {
        delete cleanConfig[field];
      }
    });

    setFormData({
      name: connector.name,
      type: connectorType,
      config: cleanConfig,
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleDeleteConnector = (connectorId) => {
    setConfirmDialog({
      open: true,
      title: 'Delete Connector',
      message: 'Are you sure you want to delete this connector? This action cannot be undone.',
      severity: 'error',
      onConfirm: async () => {
        try {
          await apiService.deleteConnector(connectorId);
          setSnackbar({
            open: true,
            message: 'Connector deleted successfully',
            severity: 'success',
          });
          loadConnectors();
        } catch (error) {
          console.error('Error deleting connector:', error);
          setSnackbar({
            open: true,
            message: `Failed to delete connector: ${error.response?.data?.detail || error.message}`,
            severity: 'error',
          });
        }
        setConfirmDialog(prev => ({ ...prev, open: false }));
      },
    });
  };

  const handleSyncConnector = async (connectorId) => {
    try {
      await apiService.syncConnector(connectorId);
      setSnackbar({
        open: true,
        message: 'Schema sync started...',
        severity: 'info',
      });

      // Poll for sync completion
      const pollInterval = setInterval(async () => {
        try {
          const response = await apiService.getConnectors();
          const connector = response.data.connectors?.find(c => c.id === connectorId);

          if (connector) {
            if (connector.sync_status === 'success') {
              clearInterval(pollInterval);
              setSnackbar({
                open: true,
                message: `Sync completed! Found ${connector.metadata?.table_count || 0} tables.`,
                severity: 'success',
              });
              loadConnectors();
            } else if (connector.sync_status === 'error' || connector.sync_error) {
              clearInterval(pollInterval);
              setSnackbar({
                open: true,
                message: `Sync failed: ${connector.sync_error || 'Unknown error'}`,
                severity: 'error',
              });
              loadConnectors();
            }
            // If still 'syncing', continue polling
          }
        } catch (pollError) {
          console.error('Error polling sync status:', pollError);
        }
      }, 2000); // Poll every 2 seconds

      // Stop polling after 5 minutes (timeout)
      setTimeout(() => {
        clearInterval(pollInterval);
      }, 300000);

      // Initial reload to show syncing state
      setTimeout(() => loadConnectors(), 500);
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Failed to start sync: ${error.response?.data?.detail || error.message}`,
        severity: 'error',
      });
    }
  };

  const handleClearSchemaCache = () => {
    setConfirmDialog({
      open: true,
      title: 'Clear Schema Cache',
      message: 'This will clear all cached schema data (Jena, Weaviate, Redis). You will need to re-sync connectors after this. Continue?',
      severity: 'warning',
      onConfirm: async () => {
        try {
          const response = await apiService.clearSchemaCache();
          setSnackbar({
            open: true,
            message: `Schema cache cleared! Jena: ${response.data.details?.jena_cleared}, Weaviate: ${response.data.details?.weaviate_cleared}, Redis: ${response.data.details?.redis_cleared}`,
            severity: 'success',
          });
        } catch (error) {
          setSnackbar({
            open: true,
            message: `Failed to clear cache: ${error.response?.data?.detail || error.message}`,
            severity: 'error',
          });
        }
        setConfirmDialog(prev => ({ ...prev, open: false }));
      },
    });
  };

  // Check if a field should be shown based on showWhen condition
  // Supports multiple conditions (all must be true - AND logic)
  const shouldShowField = (field) => {
    if (!field.showWhen) return true;

    // Check ALL conditions (AND logic)
    return Object.entries(field.showWhen).every(([conditionField, conditionValue]) => {
      const currentValue = formData.config[conditionField];
      // Handle array conditions (e.g., showWhen: { auth_method: ['password', 'keypair'] })
      if (Array.isArray(conditionValue)) {
        return conditionValue.includes(currentValue);
      }
      return currentValue === conditionValue;
    });
  };

  const getSyncStatusIcon = (connector) => {
    const status = connector.sync_status;
    if (status === 'success') {
      return (
        <Tooltip title={`Schema synced: ${connector.metadata?.table_count || 0} tables`}>
          <CheckCircleIcon sx={{ color: 'success.main', fontSize: 18 }} />
        </Tooltip>
      );
    } else if (status === 'syncing') {
      return (
        <Tooltip title="Schema sync in progress...">
          <SyncingIcon sx={{ color: 'info.main', fontSize: 18 }} className="rotating" />
        </Tooltip>
      );
    } else if (status === 'failed') {
      return (
        <Tooltip title={`Sync failed: ${connector.sync_error || 'Unknown error'}`}>
          <ErrorIcon sx={{ color: 'error.main', fontSize: 18 }} />
        </Tooltip>
      );
    }
    return (
      <Tooltip title="Schema not synced yet">
        <PendingIcon sx={{ color: 'warning.main', fontSize: 18 }} />
      </Tooltip>
    );
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.name) {
      errors.name = 'Name is required';
    }

    if (!formData.type) {
      errors.type = 'Database type is required';
    }

    // Sensitive fields that can be left blank in edit mode (backend preserves existing)
    const sensitiveFieldTypes = ['password', 'file', 'textarea'];

    if (formData.type) {
      const dbConfig = DATABASE_TYPES[formData.type];
      if (dbConfig) {
        dbConfig.fields.forEach(field => {
          // Only validate fields that are currently visible (respects showWhen conditions)
          // In edit mode, skip required validation for sensitive fields (they'll use existing values)
          const isSensitiveField = sensitiveFieldTypes.includes(field.type);
          const skipRequiredInEdit = editMode && isSensitiveField;

          if (field.required && shouldShowField(field) && !formData.config[field.name] && !skipRequiredInEdit) {
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
        await apiService.createConnector({
          connector_type: formData.type,
          name: formData.name,
          config: formData.config,
        });
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
      const response = await apiService.testConnector({
        connector_type: formData.type,
        config: formData.config,
      });
      if (response.data.success) {
        setSnackbar({
          open: true,
          message: 'Connection successful!',
          severity: 'success',
        });
      } else {
        setSnackbar({
          open: true,
          message: `Connection failed: ${response.data.error}`,
          severity: 'error',
        });
      }
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Connection failed: ${error.response?.data?.detail || error.message}`,
        severity: 'error',
      });
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
    if (status === 'testing') {
      return <CircularProgress size={20} />;
    } else if (status === 'connected') {
      return <CheckCircleIcon sx={{ color: 'success.main' }} />;
    } else if (status === 'error') {
      return <ErrorIcon sx={{ color: 'error.main' }} />;
    }
    return <WarningIcon sx={{ color: 'warning.main' }} />;
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
              setSnackbar({
                open: true,
                message: 'OAuth state mismatch. Please try again.',
                severity: 'error',
              });
              return;
            }
            // Complete the OAuth flow
            try {
              const completeResponse = await apiService.completeBigQueryOAuth({
                code: event.data.code,
                state: event.data.state,
                project_id: formData.config.project_id,
                dataset_id: formData.config.dataset_id,
                name: formData.name,
                location: formData.config.location || 'US',
              });
              if (completeResponse.data) {
                setSnackbar({
                  open: true,
                  message: 'BigQuery connection created successfully!',
                  severity: 'success',
                });
                setDialogOpen(false);
                loadConnectors();
              }
            } catch (error) {
              setSnackbar({
                open: true,
                message: `Failed to complete OAuth: ${error.response?.data?.detail || error.message}`,
                severity: 'error',
              });
            }
          } else if (event.data.type === 'oauth_error') {
            window.removeEventListener('message', handleMessage);
            setSnackbar({
              open: true,
              message: `OAuth failed: ${event.data.error}`,
              severity: 'error',
            });
          }
        };
        window.addEventListener('message', handleMessage);
      }
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Failed to initiate OAuth: ${error.response?.data?.detail || error.message}`,
        severity: 'error',
      });
    }
  };

  const renderConfigForm = () => {
    if (!formData.type) return null;

    const dbConfig = DATABASE_TYPES[formData.type];
    if (!dbConfig) return null;

    // Check if OAuth is selected for BigQuery
    const isBigQueryOAuthSelected = formData.type === 'bigquery' && formData.config.auth_method === 'oauth';

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
                  required={field.required && !editMode}
                  error={!!formErrors[field.name]}
                  helperText={formErrors[field.name] || (editMode ? 'Leave blank to keep existing value' : field.helpText)}
                  placeholder={editMode ? '(unchanged)' : undefined}
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
              ) : field.type === 'textarea' ? (
                <TextField
                  fullWidth
                  multiline
                  rows={field.rows || 4}
                  label={field.label}
                  value={formData.config[field.name] || ''}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  required={field.required && !editMode}
                  error={!!formErrors[field.name]}
                  helperText={formErrors[field.name] || (editMode ? 'Leave blank to keep existing value' : field.helpText)}
                  placeholder={editMode ? '(leave blank to keep existing)' : field.placeholder}
                  InputProps={{
                    sx: { fontFamily: 'monospace', fontSize: '0.85rem' }
                  }}
                />
              ) : field.type === 'file' ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {field.label}
                    {editMode && (
                      <Typography component="span" variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                        (leave empty to keep existing)
                      </Typography>
                    )}
                  </Typography>
                  <Button
                    variant="outlined"
                    component="label"
                    fullWidth
                  >
                    {editMode ? 'Upload New File (optional)' : `Upload ${field.label}`}
                    <input
                      type="file"
                      hidden
                      accept={field.accept || '.json'}
                      onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onload = (event) => {
                            // For private_key_file, store content in private_key field
                            const targetField = field.name === 'private_key_file' ? 'private_key' : field.name;
                            handleFieldChange(targetField, event.target.result);
                          };
                          reader.readAsText(file);
                        }
                      }}
                    />
                  </Button>
                  {(formData.config[field.name] || (field.name === 'private_key_file' && formData.config.private_key)) && (
                    <Chip
                      label={field.name.includes('private_key') ? 'Private key loaded' : 'File uploaded'}
                      size="small"
                      color="success"
                      sx={{ mt: 1 }}
                    />
                  )}
                  {field.helpText && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                      {field.helpText}
                    </Typography>
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
        {isBigQueryOAuthSelected && (
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
              disabled={!formData.name || !formData.config.project_id || !formData.config.dataset_id}
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
    <Box sx={{ bgcolor: sfColors.bgPage, minHeight: '100%', p: 3 }}>
      {/* Hero Header */}
      <Box sx={{
        bgcolor: sfColors.bgCard,
        borderRadius: '8px',
        p: 3,
        mb: 3,
        display: 'flex',
        alignItems: 'center',
        gap: 3,
        boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
        border: `1px solid ${sfColors.border}`,
      }}>
        <Avatar sx={{
          width: 64,
          height: 64,
          bgcolor: sfColors.iconBg,
        }}>
          <DatabaseIcon sx={{ fontSize: 32, color: sfColors.accent }} />
        </Avatar>
        <Box>
          <Typography sx={{ fontWeight: 700, fontSize: '1.5rem', color: sfColors.textPrimary }}>
            Database Connections
          </Typography>
          <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.95rem' }}>
            Manage your database connections and configure data sources
          </Typography>
        </Box>
      </Box>

      {/* Statistics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
            <DatabaseIcon sx={{ fontSize: 40, color: sfColors.accent, mb: 1 }} />
            <Typography sx={{ fontSize: '2rem', fontWeight: 700, color: sfColors.textPrimary }}>{connectors.length}</Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.875rem' }}>
              Total Connections
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
            <CheckCircleIcon sx={{ fontSize: 40, color: sfColors.success, mb: 1 }} />
            <Typography sx={{ fontSize: '2rem', fontWeight: 700, color: sfColors.textPrimary }}>
              {Object.values(testResults).filter(r => r === 'connected').length}
            </Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.875rem' }}>
              Active
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
            <ErrorIcon sx={{ fontSize: 40, color: sfColors.error, mb: 1 }} />
            <Typography sx={{ fontSize: '2rem', fontWeight: 700, color: sfColors.textPrimary }}>
              {Object.values(testResults).filter(r => r === 'error').length}
            </Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.875rem' }}>
              Failed
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
            <CloudIcon sx={{ fontSize: 40, color: sfColors.accent, mb: 1 }} />
            <Typography sx={{ fontSize: '2rem', fontWeight: 700, color: sfColors.textPrimary }}>
              {connectors.filter(c => ['bigquery', 'snowflake', 'redshift', 'databricks'].includes(c.type)).length}
            </Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.875rem' }}>
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
            sx={{
              bgcolor: sfColors.accent,
              '&:hover': { bgcolor: sfColors.accentHover },
              textTransform: 'none',
              fontWeight: 600,
              borderRadius: '6px',
            }}
          >
            Add Connection
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadConnectors}
            disabled={loading}
            sx={{
              borderColor: sfColors.border,
              color: sfColors.textPrimary,
              textTransform: 'none',
              fontWeight: 600,
              borderRadius: '6px',
              '&:hover': { borderColor: sfColors.accent, bgcolor: sfColors.iconBg },
            }}
          >
            Refresh
          </Button>
        </Stack>
        <Button
          variant="outlined"
          startIcon={<DeleteIcon />}
          onClick={handleClearSchemaCache}
          sx={{
            borderColor: sfColors.warning,
            color: sfColors.warning,
            textTransform: 'none',
            fontWeight: 600,
            borderRadius: '6px',
            '&:hover': { borderColor: sfColors.warning, bgcolor: 'rgba(254, 147, 57, 0.08)' },
          }}
        >
          Clear Schema Cache
        </Button>
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
            const dbType = DATABASE_TYPES[connector.connector_type] || DATABASE_TYPES[connector.type] || {};
            return (
              <Grid item xs={12} sm={6} md={4} key={connector.id}>
                <Card sx={{ boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
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
                          {dbType.label || connector.connector_type || connector.type}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {getSyncStatusIcon(connector)}
                        {getStatusIcon(connector.id)}
                      </Box>
                    </Box>

                    <Stack spacing={1}>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Chip
                          label={dbType.category || 'Database'}
                          size="small"
                          variant="outlined"
                        />
                        {connector.sync_status === 'success' && connector.metadata?.table_count > 0 && (
                          <Chip
                            label={`${connector.metadata.table_count} tables`}
                            size="small"
                            color="success"
                            variant="outlined"
                          />
                        )}
                        {connector.enabled_for_chat && (
                          <Chip
                            label="Chat enabled"
                            size="small"
                            color="primary"
                          />
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        Created: {new Date(connector.created_at).toLocaleDateString()}
                      </Typography>
                      {connector.sync_error && (
                        <Alert severity="error" sx={{ py: 0, px: 1 }}>
                          <Typography variant="caption">{connector.sync_error}</Typography>
                        </Alert>
                      )}
                    </Stack>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={testResults[connector.id] === 'testing' ? <CircularProgress size={16} /> : <TestIcon />}
                      onClick={() => testConnection(connector.id)}
                      disabled={testResults[connector.id] === 'testing'}
                    >
                      {testResults[connector.id] === 'testing' ? 'Testing...' : 'Test'}
                    </Button>
                    <Button
                      size="small"
                      startIcon={<SyncIcon />}
                      onClick={() => handleSyncConnector(connector.id)}
                      disabled={connector.sync_status === 'syncing'}
                    >
                      {connector.sync_status === 'syncing' ? 'Syncing...' : 'Sync'}
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

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          color: confirmDialog.severity === 'error' ? 'error.main' : 'warning.main'
        }}>
          {confirmDialog.severity === 'error' ? <ErrorIcon /> : <WarningIcon />}
          {confirmDialog.title}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDialog.onConfirm}
            variant="contained"
            color={confirmDialog.severity === 'error' ? 'error' : 'warning'}
            autoFocus
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DatabaseConfigPage;