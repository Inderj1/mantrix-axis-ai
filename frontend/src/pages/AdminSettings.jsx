import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  Tabs,
  Tab,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Switch,
  FormControlLabel,
  Chip,
  Divider,
  Alert,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Add as AddIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  PersonAdd as PersonAddIcon,
  LockReset as LockResetIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import authConfig from '../auth_config.json';
import { apiService } from '../services/api';

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function AdminSettings() {
  const [tabValue, setTabValue] = useState(0);
  const [config, setConfig] = useState(authConfig);
  const [newEmail, setNewEmail] = useState('');
  const [newDomain, setNewDomain] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // User Management state
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    temporaryPassword: '',
    firstName: '',
    lastName: '',
    organizationId: '',
    role: 'user',
  });
  const [showPassword, setShowPassword] = useState(false);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleAuthToggle = (key) => {
    setConfig(prev => ({
      ...prev,
      authentication: {
        ...prev.authentication,
        [key]: !prev.authentication[key]
      }
    }));
  };

  const handleRouteToggle = (route) => {
    setConfig(prev => ({
      ...prev,
      authentication: {
        ...prev.authentication,
        protected_routes: {
          ...prev.authentication.protected_routes,
          [route]: !prev.authentication.protected_routes[route]
        }
      }
    }));
  };

  const handleAddEmail = () => {
    if (newEmail && !config.authentication.access_control.authorized_emails.includes(newEmail)) {
      setConfig(prev => ({
        ...prev,
        authentication: {
          ...prev.authentication,
          access_control: {
            ...prev.authentication.access_control,
            authorized_emails: [...prev.authentication.access_control.authorized_emails, newEmail]
          }
        }
      }));
      setNewEmail('');
    }
  };

  const handleRemoveEmail = (email) => {
    setConfig(prev => ({
      ...prev,
      authentication: {
        ...prev.authentication,
        access_control: {
          ...prev.authentication.access_control,
          authorized_emails: prev.authentication.access_control.authorized_emails.filter(e => e !== email)
        }
      }
    }));
  };

  const handleAddDomain = () => {
    if (newDomain && !config.authentication.access_control.authorized_domains.includes(newDomain)) {
      setConfig(prev => ({
        ...prev,
        authentication: {
          ...prev.authentication,
          access_control: {
            ...prev.authentication.access_control,
            authorized_domains: [...prev.authentication.access_control.authorized_domains, newDomain]
          }
        }
      }));
      setNewDomain('');
    }
  };

  const handleRemoveDomain = (domain) => {
    setConfig(prev => ({
      ...prev,
      authentication: {
        ...prev.authentication,
        access_control: {
          ...prev.authentication.access_control,
          authorized_domains: prev.authentication.access_control.authorized_domains.filter(d => d !== domain)
        }
      }
    }));
  };

  const handleSave = async () => {
    try {
      // In a real app, this would save to backend
      localStorage.setItem('authConfig', JSON.stringify(config));
      setSnackbar({ open: true, message: 'Settings saved successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to save settings', severity: 'error' });
    }
  };

  // User Management functions
  const loadUsers = async () => {
    setLoadingUsers(true);
    try {
      const response = await apiService.get('/api/v1/admin/cognito/users');
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
      setSnackbar({ open: true, message: 'Failed to load users', severity: 'error' });
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleCreateUser = async () => {
    try {
      await apiService.post('/api/v1/admin/cognito/users', newUser);
      setSnackbar({ open: true, message: 'User created successfully', severity: 'success' });
      setShowCreateUser(false);
      setNewUser({
        username: '',
        email: '',
        temporaryPassword: '',
        firstName: '',
        lastName: '',
        organizationId: '',
        role: 'user',
      });
      loadUsers();
    } catch (error) {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to create user',
        severity: 'error'
      });
    }
  };

  const handleResetPassword = async () => {
    try {
      await apiService.post(`/api/v1/admin/cognito/users/${selectedUser.username}/reset-password`);
      setSnackbar({ open: true, message: 'Password reset email sent', severity: 'success' });
      setShowResetPassword(false);
      setSelectedUser(null);
    } catch (error) {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to reset password',
        severity: 'error'
      });
    }
  };

  const handleDeleteUser = async (username) => {
    if (!window.confirm(`Are you sure you want to delete user: ${username}?`)) {
      return;
    }
    try {
      await apiService.delete(`/api/v1/admin/cognito/users/${username}`);
      setSnackbar({ open: true, message: 'User deleted successfully', severity: 'success' });
      loadUsers();
    } catch (error) {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to delete user',
        severity: 'error'
      });
    }
  };

  useEffect(() => {
    if (tabValue === 4) {  // User Management tab
      loadUsers();
    }
  }, [tabValue]);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Admin Settings
      </Typography>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
          <Tab label="Authentication" />
          <Tab label="Access Control" />
          <Tab label="Protected Routes" />
          <Tab label="SSO Settings" />
          <Tab label="User Management" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <Typography variant="h6" gutterBottom>
          Authentication Settings
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={config.authentication.enabled}
              onChange={() => handleAuthToggle('enabled')}
            />
          }
          label="Enable Authentication"
        />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          When disabled, all users can access the application without signing in.
        </Typography>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Typography variant="h6" gutterBottom>
          Authorized Emails
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            label="Email Address"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddEmail()}
          />
          <Button
            variant="contained"
            onClick={handleAddEmail}
            startIcon={<AddIcon />}
          >
            Add
          </Button>
        </Box>
        <List>
          {config.authentication.access_control.authorized_emails.map((email) => (
            <ListItem key={email}>
              <ListItemText primary={email} />
              <ListItemSecondaryAction>
                {config.authentication.access_control.roles.admin.includes(email) && (
                  <Chip label="Admin" size="small" color="primary" sx={{ mr: 1 }} />
                )}
                <IconButton edge="end" onClick={() => handleRemoveEmail(email)}>
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" gutterBottom>
          Authorized Domains
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            label="Domain (e.g., company.com)"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddDomain()}
          />
          <Button
            variant="contained"
            onClick={handleAddDomain}
            startIcon={<AddIcon />}
          >
            Add
          </Button>
        </Box>
        <List>
          {config.authentication.access_control.authorized_domains.map((domain) => (
            <ListItem key={domain}>
              <ListItemText primary={domain} />
              <ListItemSecondaryAction>
                <IconButton edge="end" onClick={() => handleRemoveDomain(domain)}>
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Typography variant="h6" gutterBottom>
          Protected Routes
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Select which routes require authentication.
        </Typography>
        <List>
          {Object.entries(config.authentication.protected_routes).map(([route, isProtected]) => (
            <ListItem key={route}>
              <ListItemText 
                primary={route}
                secondary={isProtected ? 'Authentication required' : 'Public access'}
              />
              <ListItemSecondaryAction>
                <Switch
                  checked={isProtected}
                  onChange={() => handleRouteToggle(route)}
                />
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Typography variant="h6" gutterBottom>
          SSO Configuration
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={config.authentication.sso.enabled}
              onChange={() => setConfig(prev => ({
                ...prev,
                authentication: {
                  ...prev.authentication,
                  sso: {
                    ...prev.authentication.sso,
                    enabled: !prev.authentication.sso.enabled
                  }
                }
              }))}
            />
          }
          label="Enable SSO"
        />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          Allow users to sign in using their organization's SSO provider.
        </Typography>
        
        <Typography variant="subtitle1" gutterBottom>
          Enabled Providers:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {config.authentication.sso.providers.map((provider) => (
            <Chip key={provider} label={provider} color="primary" />
          ))}
        </Box>
        
        <Alert severity="info" sx={{ mt: 3 }}>
          SSO configuration requires setup in your Cognito dashboard. Visit the AWS Cognito console to configure SSO providers.
        </Alert>
      </TabPanel>

      <TabPanel value={tabValue} index={4}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">
            Cognito User Management
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={loadUsers}
              disabled={loadingUsers}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<PersonAddIcon />}
              onClick={() => setShowCreateUser(true)}
            >
              Create User
            </Button>
          </Box>
        </Box>

        {loadingUsers ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Organization ID</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.username}>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.status}
                        size="small"
                        color={user.status === 'CONFIRMED' ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>{new Date(user.created).toLocaleDateString()}</TableCell>
                    <TableCell>{user.organizationId || '-'}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedUser(user);
                          setShowResetPassword(true);
                        }}
                        title="Reset Password"
                      >
                        <LockResetIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteUser(user.username)}
                        title="Delete User"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {users.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary">No users found</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </TabPanel>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={handleSave}
          startIcon={<SaveIcon />}
        >
          Save Settings
        </Button>
      </Box>

      {/* Create User Dialog */}
      <Dialog open={showCreateUser} onClose={() => setShowCreateUser(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New User</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Username"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Email"
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="First Name"
              value={newUser.firstName}
              onChange={(e) => setNewUser({ ...newUser, firstName: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Last Name"
              value={newUser.lastName}
              onChange={(e) => setNewUser({ ...newUser, lastName: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Temporary Password"
              type={showPassword ? 'text' : 'password'}
              value={newUser.temporaryPassword}
              onChange={(e) => setNewUser({ ...newUser, temporaryPassword: e.target.value })}
              required
              fullWidth
              helperText="User will be required to change this on first login"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Organization ID"
              value={newUser.organizationId}
              onChange={(e) => setNewUser({ ...newUser, organizationId: e.target.value })}
              fullWidth
              helperText="Optional: Assign user to an organization"
            />
            <TextField
              label="Role"
              select
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              fullWidth
            >
              <MenuItem value="user">User</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateUser(false)}>Cancel</Button>
          <Button
            onClick={handleCreateUser}
            variant="contained"
            disabled={!newUser.username || !newUser.email || !newUser.firstName || !newUser.lastName || !newUser.temporaryPassword}
          >
            Create User
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={showResetPassword} onClose={() => setShowResetPassword(false)}>
        <DialogTitle>Reset Password</DialogTitle>
        <DialogContent>
          <Typography>
            Send a password reset email to <strong>{selectedUser?.email}</strong>?
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            The user will receive an email with instructions to reset their password.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowResetPassword(false)}>Cancel</Button>
          <Button onClick={handleResetPassword} variant="contained">
            Send Reset Email
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
}

export default AdminSettings;