import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Alert,
  Chip,
  Stack,
  Switch,
  FormControlLabel,
  InputAdornment,
  IconButton,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  ExpandMore as ExpandMoreIcon,
  PlayArrow as TestTubeIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

const ConnectionDialog = ({ open, connector, onClose, onSave, availableConnectors }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedType, setSelectedType] = useState('');
  const [config, setConfig] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [formErrors, setFormErrors] = useState({});

  const steps = ['Select Database', 'Configure Connection', 'Test & Save'];

  useEffect(() => {
    if (connector) {
      setSelectedType(connector.id);
      setConfig(connector.config || {});
      setActiveStep(1);
    } else {
      setSelectedType('');
      setConfig({});
      setActiveStep(0);
    }
    setTestStatus(null);
    setFormErrors({});
  }, [connector, open]);

  const handleTypeSelect = (type) => {
    setSelectedType(type);
    const selectedConnector = availableConnectors.find(c => c.id === type);
    if (selectedConnector) {
      setConfig(selectedConnector.config || {});
    }
    setActiveStep(1);
  };

  const handleConfigChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value,
    }));
    // Clear error for this field
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: null,
      }));
    }
  };

  const validateConfig = () => {
    const errors = {};
    const selectedConnector = availableConnectors.find(c => c.id === selectedType);
    
    if (!selectedConnector) return false;

    // Validate required fields based on connector type
    switch (selectedConnector.type) {
      case 'sql':
        if (selectedType === 'sqlserver') {
          if (!config.server) errors.server = 'Server is required';
        } else if (selectedType === 'oracle') {
          if (!config.host) errors.host = 'Host is required';
          if (!config.serviceName) errors.serviceName = 'Service name is required';
        } else {
          if (!config.host) errors.host = 'Host is required';
          if (!config.database) errors.database = 'Database is required';
        }
        if (!config.username) errors.username = 'Username is required';
        if (!config.password) errors.password = 'Password is required';
        break;
      
      case 'warehouse':
        if (selectedType === 'bigquery') {
          if (!config.projectId) errors.projectId = 'Project ID is required';
          if (!config.dataset) errors.dataset = 'Dataset is required';
        } else if (selectedType === 'snowflake') {
          if (!config.account) errors.account = 'Account is required';
          if (!config.warehouse) errors.warehouse = 'Warehouse is required';
          if (!config.database) errors.database = 'Database is required';
          if (!config.username) errors.username = 'Username is required';
          if (!config.password) errors.password = 'Password is required';
        }
        break;
      
      case 'nosql':
        if (selectedType === 'mongodb') {
          if (!config.connectionString) errors.connectionString = 'Connection string is required';
        }
        break;
      
      case 'vector':
        if (selectedType === 'weaviate') {
          if (!config.url) errors.url = 'URL is required';
        } else if (selectedType === 'pinecone') {
          if (!config.apiKey) errors.apiKey = 'API key is required';
          if (!config.environment) errors.environment = 'Environment is required';
        }
        break;
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleTestConnection = async () => {
    if (!validateConfig()) return;

    setIsTestingConnection(true);
    setTestStatus(null);

    // Simulate connection test
    setTimeout(() => {
      const success = Math.random() > 0.2; // 80% success rate for demo
      setTestStatus({
        success,
        message: success 
          ? 'Connection successful! Database is reachable and credentials are valid.'
          : 'Connection failed. Please check your configuration and try again.',
      });
      setIsTestingConnection(false);
      
      if (success) {
        setActiveStep(2);
      }
    }, 2000);
  };

  const handleSave = () => {
    if (!validateConfig()) return;

    const selectedConnector = availableConnectors.find(c => c.id === selectedType);
    const connectorData = {
      ...selectedConnector,
      config,
      status: testStatus?.success ? 'connected' : 'disconnected',
    };

    onSave(connectorData);
  };

  const handleNext = () => {
    if (activeStep === 1) {
      if (validateConfig()) {
        setActiveStep(2);
      }
    } else {
      setActiveStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const selectedConnector = availableConnectors.find(c => c.id === selectedType);

  const renderConnectionFields = () => {
    if (!selectedConnector) return null;

    switch (selectedConnector.type) {
      case 'sql':
        return (
          <Stack spacing={3}>
            {selectedType === 'sqlserver' ? (
              <TextField
                label="Server"
                value={config.server || ''}
                onChange={(e) => handleConfigChange('server', e.target.value)}
                error={!!formErrors.server}
                helperText={formErrors.server}
                fullWidth
                placeholder="localhost\\SQLEXPRESS"
              />
            ) : selectedType === 'oracle' ? (
              <>
                <TextField
                  label="Host"
                  value={config.host || ''}
                  onChange={(e) => handleConfigChange('host', e.target.value)}
                  error={!!formErrors.host}
                  helperText={formErrors.host}
                  fullWidth
                  placeholder="localhost"
                />
                <TextField
                  label="Service Name"
                  value={config.serviceName || ''}
                  onChange={(e) => handleConfigChange('serviceName', e.target.value)}
                  error={!!formErrors.serviceName}
                  helperText={formErrors.serviceName}
                  fullWidth
                  placeholder="ORCL"
                />
              </>
            ) : (
              <>
                <TextField
                  label="Host"
                  value={config.host || ''}
                  onChange={(e) => handleConfigChange('host', e.target.value)}
                  error={!!formErrors.host}
                  helperText={formErrors.host}
                  fullWidth
                  placeholder="localhost"
                />
                <TextField
                  label="Database"
                  value={config.database || ''}
                  onChange={(e) => handleConfigChange('database', e.target.value)}
                  error={!!formErrors.database}
                  helperText={formErrors.database}
                  fullWidth
                  placeholder="my_database"
                />
              </>
            )}
            
            <TextField
              label="Port"
              type="number"
              value={config.port || selectedConnector.config.port}
              onChange={(e) => handleConfigChange('port', parseInt(e.target.value))}
              fullWidth
            />
            
            <TextField
              label="Username"
              value={config.username || ''}
              onChange={(e) => handleConfigChange('username', e.target.value)}
              error={!!formErrors.username}
              helperText={formErrors.username}
              fullWidth
              autoComplete="username"
            />
            
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={config.password || ''}
              onChange={(e) => handleConfigChange('password', e.target.value)}
              error={!!formErrors.password}
              helperText={formErrors.password}
              fullWidth
              autoComplete="current-password"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="subtitle2">Advanced Settings</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Stack spacing={2}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.ssl || false}
                        onChange={(e) => handleConfigChange('ssl', e.target.checked)}
                      />
                    }
                    label="Use SSL"
                  />
                  <TextField
                    label="Connection Timeout (seconds)"
                    type="number"
                    value={config.timeout || 30}
                    onChange={(e) => handleConfigChange('timeout', parseInt(e.target.value))}
                    fullWidth
                  />
                </Stack>
              </AccordionDetails>
            </Accordion>
          </Stack>
        );

      case 'warehouse':
        if (selectedType === 'bigquery') {
          return (
            <Stack spacing={3}>
              <TextField
                label="Project ID"
                value={config.projectId || ''}
                onChange={(e) => handleConfigChange('projectId', e.target.value)}
                error={!!formErrors.projectId}
                helperText={formErrors.projectId}
                fullWidth
                placeholder="my-gcp-project"
              />
              <TextField
                label="Dataset"
                value={config.dataset || ''}
                onChange={(e) => handleConfigChange('dataset', e.target.value)}
                error={!!formErrors.dataset}
                helperText={formErrors.dataset}
                fullWidth
                placeholder="my_dataset"
              />
              <TextField
                label="Service Account Key"
                multiline
                rows={4}
                value={config.keyFile || ''}
                onChange={(e) => handleConfigChange('keyFile', e.target.value)}
                fullWidth
                placeholder="Paste your service account JSON key here"
              />
            </Stack>
          );
        } else if (selectedType === 'snowflake') {
          return (
            <Stack spacing={3}>
              <TextField
                label="Account"
                value={config.account || ''}
                onChange={(e) => handleConfigChange('account', e.target.value)}
                error={!!formErrors.account}
                helperText={formErrors.account}
                fullWidth
                placeholder="xy12345.us-east-1"
              />
              <TextField
                label="Warehouse"
                value={config.warehouse || ''}
                onChange={(e) => handleConfigChange('warehouse', e.target.value)}
                error={!!formErrors.warehouse}
                helperText={formErrors.warehouse}
                fullWidth
                placeholder="COMPUTE_WH"
              />
              <TextField
                label="Database"
                value={config.database || ''}
                onChange={(e) => handleConfigChange('database', e.target.value)}
                error={!!formErrors.database}
                helperText={formErrors.database}
                fullWidth
                placeholder="MY_DATABASE"
              />
              <TextField
                label="Schema"
                value={config.schema || ''}
                onChange={(e) => handleConfigChange('schema', e.target.value)}
                fullWidth
                placeholder="PUBLIC"
              />
              <TextField
                label="Username"
                value={config.username || ''}
                onChange={(e) => handleConfigChange('username', e.target.value)}
                error={!!formErrors.username}
                helperText={formErrors.username}
                fullWidth
              />
              <TextField
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={config.password || ''}
                onChange={(e) => handleConfigChange('password', e.target.value)}
                error={!!formErrors.password}
                helperText={formErrors.password}
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Stack>
          );
        }
        break;

      case 'nosql':
        if (selectedType === 'mongodb') {
          return (
            <Stack spacing={3}>
              <TextField
                label="Connection String"
                value={config.connectionString || ''}
                onChange={(e) => handleConfigChange('connectionString', e.target.value)}
                error={!!formErrors.connectionString}
                helperText={formErrors.connectionString}
                fullWidth
                placeholder="mongodb://localhost:27017"
              />
              <TextField
                label="Database"
                value={config.database || ''}
                onChange={(e) => handleConfigChange('database', e.target.value)}
                fullWidth
                placeholder="my_database"
              />
              <TextField
                label="Auth Source"
                value={config.authSource || ''}
                onChange={(e) => handleConfigChange('authSource', e.target.value)}
                fullWidth
                placeholder="admin"
              />
            </Stack>
          );
        }
        break;

      case 'vector':
        if (selectedType === 'weaviate') {
          return (
            <Stack spacing={3}>
              <TextField
                label="URL"
                value={config.url || ''}
                onChange={(e) => handleConfigChange('url', e.target.value)}
                error={!!formErrors.url}
                helperText={formErrors.url}
                fullWidth
                placeholder="http://localhost:8080"
              />
              <TextField
                label="API Key (Optional)"
                value={config.apiKey || ''}
                onChange={(e) => handleConfigChange('apiKey', e.target.value)}
                fullWidth
                placeholder="your-api-key"
              />
              <TextField
                label="Class Name"
                value={config.className || ''}
                onChange={(e) => handleConfigChange('className', e.target.value)}
                fullWidth
                placeholder="Document"
              />
            </Stack>
          );
        }
        break;

      default:
        return (
          <Alert severity="info">
            Configuration fields for {selectedConnector.name} will be available soon.
          </Alert>
        );
    }

    return null;
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Select Database Type
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Choose the type of database you want to connect to
            </Typography>
            
            <Stack spacing={2}>
              {Object.entries(
                availableConnectors.reduce((acc, connector) => {
                  if (!acc[connector.category]) acc[connector.category] = [];
                  acc[connector.category].push(connector);
                  return acc;
                }, {})
              ).map(([category, connectors]) => (
                <Box key={category}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    {category}
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                    {connectors.map((conn) => (
                      <Chip
                        key={conn.id}
                        label={`${conn.logo} ${conn.name}`}
                        onClick={() => handleTypeSelect(conn.id)}
                        color={selectedType === conn.id ? 'primary' : 'default'}
                        variant={selectedType === conn.id ? 'filled' : 'outlined'}
                        sx={{ cursor: 'pointer' }}
                      />
                    ))}
                  </Stack>
                </Box>
              ))}
            </Stack>
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Configure Connection
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Enter the connection details for your {selectedConnector?.name} database
            </Typography>
            
            {renderConnectionFields()}
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Test Connection
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Test your connection before saving
            </Typography>
            
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <Button
                variant="contained"
                startIcon={
                  isTestingConnection ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    <TestTubeIcon />
                  )
                }
                onClick={handleTestConnection}
                disabled={isTestingConnection || testStatus?.success}
                sx={{ mb: 3 }}
              >
                {isTestingConnection ? 'Testing Connection...' : 'Test Connection'}
              </Button>
              
              {testStatus && (
                <Alert
                  severity={testStatus.success ? 'success' : 'error'}
                  icon={testStatus.success ? <CheckCircleIcon /> : <ErrorIcon />}
                  sx={{ textAlign: 'left' }}
                >
                  {testStatus.message}
                </Alert>
              )}
            </Box>
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">
          {connector ? 'Edit Connection' : 'Add New Connection'}
        </Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {renderStepContent()}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        {activeStep > 0 && (
          <Button onClick={handleBack}>
            Back
          </Button>
        )}
        {activeStep < steps.length - 1 ? (
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={!selectedType || (activeStep === 1 && Object.keys(formErrors).length > 0)}
          >
            Next
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!testStatus?.success}
          >
            Save Connection
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ConnectionDialog;