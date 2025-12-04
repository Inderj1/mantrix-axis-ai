import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  ListItemIcon,
  Divider,
  CircularProgress,
  LinearProgress,
  Tooltip,
  Badge,
  Paper,
  Stack,
  Switch,
  FormControlLabel,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  CloudQueue as CloudIcon,
  Storage as DatabaseIcon,
  Key as KeyIcon,
  VpnKey as PasswordIcon,
  AccountTree as SchemaIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
  PlayArrow as TestIcon,
  Info as InfoIcon,
  Close as CloseIcon,
  Check as CheckIcon,
  CloudUpload as CloudUploadIcon,
  FolderOpen as FolderIcon,
} from '@mui/icons-material';

const DataSourcesTab = () => {
  const [connections, setConnections] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    type: '',
    auth_type: '',
    description: '',
    tags: [],
    // Connection details
    host: '',
    port: '',
    database: '',
    schema: '',
    // Auth fields
    username: '',
    password: '',
    api_key: '',
    token: '',
    // Cloud specific
    project_id: '',
    account: '',
    warehouse: '',
    region: '',
    cluster_id: '',
    // File paths
    service_account_path: '',
    certificate_path: '',
    key_path: '',
    keytab_path: '',
    // Options
    ssl_enabled: true,
    ssl_mode: 'require',
    connection_timeout: 30,
    query_timeout: 300,
  });

  // Database icons mapping
  const dbIcons = {
    bigquery: '🔷',
    postgresql: '🐘',
    mysql: '🐬',
    snowflake: '❄️',
    redshift: '🔴',
    sqlserver: '🗄️',
    oracle: '🔶',
    mongodb: '🍃',
    clickhouse: '🏠',
    databricks: '🧱',
    athena: '🏛️',
    presto: '🔍',
    cassandra: '👁️',
    elasticsearch: '🔎',
    cosmos_db: '🌌',
    sqlite: '🪶',
    duckdb: '🦆',
  };

  useEffect(() => {
    loadConnections();
    loadTemplates();
  }, []);

  const loadConnections = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/connections');
      if (response.ok) {
        const data = await response.json();
        setConnections(data.connections);
      }
    } catch (error) {
      console.error('Failed to load connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/connections/templates');
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates);
        setCategories(['all', ...data.categories]);
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleCreateConnection = () => {
    setEditMode(false);
    setSelectedConnection(null);
    setFormData({
      name: '',
      type: '',
      auth_type: '',
      description: '',
      tags: [],
      host: '',
      port: '',
      database: '',
      schema: '',
      username: '',
      password: '',
      api_key: '',
      token: '',
      project_id: '',
      account: '',
      warehouse: '',
      region: '',
      cluster_id: '',
      service_account_path: '',
      certificate_path: '',
      key_path: '',
      keytab_path: '',
      ssl_enabled: true,
      ssl_mode: 'require',
      connection_timeout: 30,
      query_timeout: 300,
    });
    setActiveStep(0);
    setTestResult(null);
    setDialogOpen(true);
  };

  const handleEditConnection = (connection) => {
    setEditMode(true);
    setSelectedConnection(connection);
    setFormData({ ...connection.config });
    setActiveStep(0);
    setTestResult(null);
    setDialogOpen(true);
  };

  const handleDeleteConnection = (connectionId) => {
    setConfirmDialog({
      open: true,
      title: 'Delete Connection',
      message: 'Are you sure you want to delete this connection? This action cannot be undone.',
      onConfirm: async () => {
        try {
          const response = await fetch(`http://localhost:8000/api/v1/connections/${connectionId}`, {
            method: 'DELETE',
          });
          if (response.ok) {
            showSnackbar('Connection deleted successfully', 'success');
            loadConnections();
          }
        } catch (error) {
          showSnackbar('Failed to delete connection', 'error');
        }
        setConfirmDialog({ open: false, title: '', message: '', onConfirm: null });
      },
    });
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/connections/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: formData }),
      });
      
      const result = await response.json();
      setTestResult(result);
      
      if (result.success) {
        showSnackbar('Connection test successful!', 'success');
      } else {
        showSnackbar(`Connection test failed: ${result.message}`, 'error');
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to test connection',
        error_details: error.message,
      });
      showSnackbar('Failed to test connection', 'error');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveConnection = async () => {
    try {
      const url = editMode
        ? `http://localhost:8000/api/v1/connections/${selectedConnection.id}`
        : 'http://localhost:8000/api/v1/connections';
      
      const method = editMode ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: formData,
          test_connection: testResult?.success || false,
        }),
      });
      
      if (response.ok) {
        showSnackbar(
          editMode ? 'Connection updated successfully' : 'Connection created successfully',
          'success'
        );
        setDialogOpen(false);
        loadConnections();
      } else {
        const error = await response.json();
        showSnackbar(error.detail || 'Failed to save connection', 'error');
      }
    } catch (error) {
      showSnackbar('Failed to save connection', 'error');
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const getConnectionStatus = (connection) => {
    switch (connection.status) {
      case 'connected':
        return { icon: <CheckCircleIcon />, color: 'success', text: 'Connected' };
      case 'error':
        return { icon: <ErrorIcon />, color: 'error', text: 'Error' };
      case 'connecting':
        return { icon: <CircularProgress size={20} />, color: 'info', text: 'Connecting' };
      default:
        return { icon: <WarningIcon />, color: 'warning', text: 'Disconnected' };
    }
  };

  const getRequiredFields = () => {
    const template = templates.find(t => t.type === formData.type);
    if (!template) return [];
    return template.required_fields || [];
  };

  const getOptionalFields = () => {
    const template = templates.find(t => t.type === formData.type);
    if (!template) return [];
    return template.optional_fields || [];
  };

  const renderConnectionForm = () => {
    const template = templates.find(t => t.type === formData.type);
    
    return (
      <Box>
        <Grid container spacing={2}>
          {/* Required Fields */}
          {getRequiredFields().map((field) => (
            <Grid item xs={12} md={6} key={field}>
              <TextField
                fullWidth
                required
                label={field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ')}
                value={formData[field] || ''}
                onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
                type={field.includes('password') ? 'password' : 'text'}
                InputProps={{
                  startAdornment: field.includes('password') ? (
                    <InputAdornment position="start">
                      <PasswordIcon />
                    </InputAdornment>
                  ) : null,
                }}
              />
            </Grid>
          ))}
          
          {/* Optional Fields */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2, mb: 1 }}>
              Optional Settings
            </Typography>
          </Grid>
          
          {getOptionalFields().map((field) => (
            <Grid item xs={12} md={6} key={field}>
              <TextField
                fullWidth
                label={field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ')}
                value={formData[field] || ''}
                onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
              />
            </Grid>
          ))}
          
          {/* SSL Settings */}
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.ssl_enabled}
                  onChange={(e) => setFormData({ ...formData, ssl_enabled: e.target.checked })}
                />
              }
              label="Enable SSL/TLS"
            />
          </Grid>
          
          {formData.ssl_enabled && (
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>SSL Mode</InputLabel>
                <Select
                  value={formData.ssl_mode}
                  onChange={(e) => setFormData({ ...formData, ssl_mode: e.target.value })}
                  label="SSL Mode"
                >
                  <MenuItem value="disable">Disable</MenuItem>
                  <MenuItem value="allow">Allow</MenuItem>
                  <MenuItem value="prefer">Prefer</MenuItem>
                  <MenuItem value="require">Require</MenuItem>
                  <MenuItem value="verify-ca">Verify CA</MenuItem>
                  <MenuItem value="verify-full">Verify Full</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          )}
        </Grid>
      </Box>
    );
  };

  const renderFileUpload = (fieldName, label) => (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        {label}
      </Typography>
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          textAlign: 'center',
          cursor: 'pointer',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        <input
          type="file"
          hidden
          id={fieldName}
          onChange={(e) => {
            const file = e.target.files[0];
            if (file) {
              setFormData({ ...formData, [fieldName]: file.path || file.name });
            }
          }}
        />
        <label htmlFor={fieldName} style={{ cursor: 'pointer' }}>
          <Stack alignItems="center" spacing={1}>
            <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary">
              {formData[fieldName] || 'Click to upload or drag and drop'}
            </Typography>
          </Stack>
        </label>
      </Paper>
    </Box>
  );

  const filteredTemplates = selectedCategory === 'all'
    ? templates
    : templates.filter(t => t.category === selectedCategory);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h5">
            Data Source Connections
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage database connections and integrations
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadConnections}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateConnection}
          >
            New Connection
          </Button>
        </Stack>
      </Box>

      {/* Auto-detected Connections Alert */}
      {connections.some(c => c.config.tags?.includes('auto-detected')) && (
        <Alert 
          severity="info" 
          icon={<InfoIcon />}
          sx={{ mb: 3 }}
        >
          <Typography variant="subtitle2" fontWeight="bold">
            Auto-detected Connections
          </Typography>
          <Typography variant="body2">
            GCloud CLI connection has been automatically detected and configured. These connections are managed by the system.
          </Typography>
        </Alert>
      )}

      {/* Connection Statistics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Connections
              </Typography>
              <Typography variant="h4">
                {connections.length}
              </Typography>
              {connections.filter(c => c.config.tags?.includes('auto-detected')).length > 0 && (
                <Typography variant="caption" color="primary">
                  {connections.filter(c => c.config.tags?.includes('auto-detected')).length} auto-detected
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Active
              </Typography>
              <Typography variant="h4" color="success.main">
                {connections.filter(c => c.status === 'connected').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                With Errors
              </Typography>
              <Typography variant="h4" color="error.main">
                {connections.filter(c => c.status === 'error').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Database Types
              </Typography>
              <Typography variant="h4">
                {new Set(connections.map(c => c.config.type)).size}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Connections List */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : connections.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No connections configured
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Get started by creating your first database connection
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateConnection}
          >
            Create Connection
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {connections.map((connection) => {
            const status = getConnectionStatus(connection);
            const icon = dbIcons[connection.config.type] || '🗄️';
            
            return (
              <Grid item xs={12} sm={6} md={4} key={connection.id}>
                <Card sx={{ 
                  height: '100%', 
                  display: 'flex', 
                  flexDirection: 'column',
                  ...(connection.config.tags?.includes('auto-detected') && {
                    border: '2px solid',
                    borderColor: 'info.main',
                    bgcolor: 'info.lighter',
                  })
                }}>
                  {connection.config.tags?.includes('auto-detected') && (
                    <Box sx={{ 
                      bgcolor: 'info.main', 
                      color: 'white', 
                      px: 2, 
                      py: 0.5,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1
                    }}>
                      <CloudIcon fontSize="small" />
                      <Typography variant="caption" fontWeight="bold">
                        Auto-detected via GCloud CLI
                      </Typography>
                    </Box>
                  )}
                  <CardContent sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h2" sx={{ fontSize: 48, mr: 2 }}>
                        {icon}
                      </Typography>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" noWrap>
                          {connection.config.name}
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Chip
                            size="small"
                            icon={status.icon}
                            label={status.text}
                            color={status.color}
                          />
                          {connection.config.tags?.includes('default') && (
                            <Chip
                              size="small"
                              label="Default"
                              color="primary"
                              variant="outlined"
                            />
                          )}
                        </Stack>
                      </Box>
                      {connection.config.tags?.includes('auto-detected') && (
                        <IconButton size="small" disabled>
                          <Tooltip title="Auto-detected via GCloud CLI">
                            <InfoIcon fontSize="small" />
                          </Tooltip>
                        </IconButton>
                      )}
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {connection.config.description || 'No description'}
                    </Typography>
                    
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Chip size="small" label={connection.config.type} variant="outlined" />
                      <Chip size="small" label={connection.config.auth_type} variant="outlined" />
                      {connection.config.tags?.map((tag, idx) => (
                        <Chip 
                          key={idx} 
                          size="small" 
                          label={tag}
                          color={tag === 'gcloud' ? 'info' : 'default'}
                          variant={tag === 'auto-detected' ? 'filled' : 'outlined'}
                        />
                      ))}
                    </Stack>
                    
                    {connection.last_tested && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        Last tested: {new Date(connection.last_tested).toLocaleString()}
                      </Typography>
                    )}
                  </CardContent>
                  
                  <CardActions>
                    {connection.id !== 'default-bigquery-gcloud' && (
                      <Button
                        size="small"
                        startIcon={<EditIcon />}
                        onClick={() => handleEditConnection(connection)}
                      >
                        Edit
                      </Button>
                    )}
                    <Button
                      size="small"
                      startIcon={<TestIcon />}
                      onClick={async () => {
                        const response = await fetch(
                          `http://localhost:8000/api/v1/connections/${connection.id}/health`,
                          { method: 'POST' }
                        );
                        if (response.ok) {
                          showSnackbar('Connection test initiated', 'info');
                          setTimeout(loadConnections, 2000);
                        }
                      }}
                    >
                      Test
                    </Button>
                    {connection.id !== 'default-bigquery-gcloud' && (
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteConnection(connection.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    )}
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      {/* Create/Edit Connection Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6">
              {editMode ? 'Edit Connection' : 'Create New Connection'}
            </Typography>
            <IconButton onClick={() => setDialogOpen(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          <Stepper activeStep={activeStep} orientation="vertical">
            {/* Step 1: Choose Database Type */}
            <Step>
              <StepLabel>Choose Database Type</StepLabel>
              <StepContent>
                <Box sx={{ mb: 2 }}>
                  <Tabs
                    value={selectedCategory}
                    onChange={(e, v) => setSelectedCategory(v)}
                    variant="scrollable"
                    scrollButtons="auto"
                  >
                    {categories.map((cat) => (
                      <Tab key={cat} label={cat === 'all' ? 'All' : cat} value={cat} />
                    ))}
                  </Tabs>
                </Box>
                
                <Grid container spacing={2}>
                  {filteredTemplates.map((template) => (
                    <Grid item xs={12} sm={6} md={4} key={template.type}>
                      <Paper
                        variant={formData.type === template.type ? 'elevation' : 'outlined'}
                        sx={{
                          p: 2,
                          cursor: 'pointer',
                          border: formData.type === template.type ? 2 : 1,
                          borderColor: formData.type === template.type ? 'primary.main' : 'divider',
                          '&:hover': { bgcolor: 'action.hover' },
                        }}
                        onClick={() => setFormData({ ...formData, type: template.type })}
                      >
                        <Stack alignItems="center" spacing={1}>
                          <Typography variant="h3">
                            {template.icon}
                          </Typography>
                          <Typography variant="subtitle2" align="center">
                            {template.name}
                          </Typography>
                        </Stack>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
                
                <Box sx={{ mt: 2 }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(1)}
                    disabled={!formData.type}
                  >
                    Continue
                  </Button>
                </Box>
              </StepContent>
            </Step>

            {/* Step 2: Connection Details */}
            <Step>
              <StepLabel>Connection Details</StepLabel>
              <StepContent>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      required
                      label="Connection Name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., Production Database"
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      multiline
                      rows={2}
                      label="Description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Optional description for this connection"
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <FormControl fullWidth required>
                      <InputLabel>Authentication Type</InputLabel>
                      <Select
                        value={formData.auth_type}
                        onChange={(e) => setFormData({ ...formData, auth_type: e.target.value })}
                        label="Authentication Type"
                      >
                        {templates
                          .find(t => t.type === formData.type)
                          ?.auth_types.map((authType) => (
                            <MenuItem key={authType} value={authType}>
                              {authType.replace(/_/g, ' ').toUpperCase()}
                            </MenuItem>
                          ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
                
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Button onClick={() => setActiveStep(0)}>
                    Back
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(2)}
                    disabled={!formData.name || !formData.auth_type}
                  >
                    Continue
                  </Button>
                </Box>
              </StepContent>
            </Step>

            {/* Step 3: Authentication */}
            <Step>
              <StepLabel>Authentication & Configuration</StepLabel>
              <StepContent>
                {formData.auth_type === 'service_account' && (
                  <Box>
                    {renderFileUpload('service_account_path', 'Service Account JSON')}
                  </Box>
                )}
                
                {formData.auth_type === 'certificate' && (
                  <Box>
                    {renderFileUpload('certificate_path', 'Client Certificate')}
                    {renderFileUpload('key_path', 'Private Key')}
                  </Box>
                )}
                
                {formData.auth_type === 'kerberos' && (
                  <Box>
                    {renderFileUpload('keytab_path', 'Keytab File')}
                  </Box>
                )}
                
                {(formData.auth_type === 'password' || 
                  formData.auth_type === 'api_key' || 
                  formData.auth_type === 'token') && (
                  <Box sx={{ mt: 2 }}>
                    {renderConnectionForm()}
                  </Box>
                )}
                
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Button onClick={() => setActiveStep(1)}>
                    Back
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(3)}
                  >
                    Continue
                  </Button>
                </Box>
              </StepContent>
            </Step>

            {/* Step 4: Test Connection */}
            <Step>
              <StepLabel>Test Connection</StepLabel>
              <StepContent>
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  {testingConnection ? (
                    <Box>
                      <CircularProgress size={60} />
                      <Typography variant="body1" sx={{ mt: 2 }}>
                        Testing connection...
                      </Typography>
                    </Box>
                  ) : testResult ? (
                    <Box>
                      {testResult.success ? (
                        <CheckCircleIcon sx={{ fontSize: 60, color: 'success.main' }} />
                      ) : (
                        <ErrorIcon sx={{ fontSize: 60, color: 'error.main' }} />
                      )}
                      <Typography variant="h6" sx={{ mt: 2 }}>
                        {testResult.message}
                      </Typography>
                      {testResult.server_version && (
                        <Typography variant="body2" color="text.secondary">
                          Server: {testResult.server_version}
                        </Typography>
                      )}
                      {testResult.available_databases?.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="body2" color="text.secondary">
                            Available databases: {testResult.available_databases.length}
                          </Typography>
                        </Box>
                      )}
                      {testResult.error_details && (
                        <Alert severity="error" sx={{ mt: 2, textAlign: 'left' }}>
                          {testResult.error_details}
                        </Alert>
                      )}
                    </Box>
                  ) : (
                    <Box>
                      <SpeedIcon sx={{ fontSize: 60, color: 'text.secondary' }} />
                      <Typography variant="body1" sx={{ mt: 2 }}>
                        Ready to test your connection
                      </Typography>
                    </Box>
                  )}
                </Box>
                
                <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'center' }}>
                  <Button onClick={() => setActiveStep(2)}>
                    Back
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleTestConnection}
                    disabled={testingConnection}
                    startIcon={<TestIcon />}
                  >
                    Test Connection
                  </Button>
                  <Button
                    variant="contained"
                    onClick={handleSaveConnection}
                    disabled={testingConnection}
                    startIcon={<CheckIcon />}
                  >
                    {editMode ? 'Update' : 'Create'} Connection
                  </Button>
                </Box>
              </StepContent>
            </Step>
          </Stepper>
        </DialogContent>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, title: '', message: '', onConfirm: null })}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningIcon color="warning" />
            {confirmDialog.title}
          </Box>
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog({ open: false, title: '', message: '', onConfirm: null })}
            color="inherit"
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDialog.onConfirm}
            color="error"
            variant="contained"
            autoFocus
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DataSourcesTab;