import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Grid,
  Chip,
  Alert,
  Paper,
  Divider,
  Stack,
  Autocomplete,
  Avatar,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SaveIcon from '@mui/icons-material/Save';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useAuth } from '../contexts/AuthContext';
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
  iconBg: '#e8f4fd',
};

const UserProfileManager = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [roleTemplates, setRoleTemplates] = useState([]);
  const [selectedRole, setSelectedRole] = useState('custom');
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ show: false, type: '', message: '' });
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Form state - persona based, not user based
  const [formData, setFormData] = useState({
    user_id: 'persona', // Fixed ID for persona
    name: '',
    email: '',
    role: 'custom',
    department: '',
    reporting_frequency: 'weekly',
    custom_context: '',
    insight_focuses: [],
    key_metrics: [],
    preferred_visualizations: []
  });

  const insightFocusOptions = [
    { value: 'financial_performance', label: 'Financial Performance' },
    { value: 'operational_efficiency', label: 'Operational Efficiency' },
    { value: 'revenue_growth', label: 'Revenue Growth' },
    { value: 'cost_optimization', label: 'Cost Optimization' },
    { value: 'customer_analytics', label: 'Customer Analytics' },
    { value: 'product_performance', label: 'Product Performance' },
    { value: 'profitability', label: 'Profitability' },
    { value: 'cash_flow', label: 'Cash Flow' }
  ];

  const visualizationOptions = [
    { value: 'bar', label: 'Bar Chart' },
    { value: 'line', label: 'Line Chart' },
    { value: 'pie', label: 'Pie Chart' },
    { value: 'area', label: 'Area Chart' },
    { value: 'scatter', label: 'Scatter Plot' },
    { value: 'heatmap', label: 'Heatmap' }
  ];

  // Auto-populate from Cognito user data
  useEffect(() => {
    if (user && !profile) {
      // Only auto-populate if no existing profile and fields are empty
      if (!formData.name && !formData.email) {
        const userName = user?.username || '';
        const userEmail = user?.email || '';

        setFormData(prev => ({
          ...prev,
          name: userName,
          email: userEmail
        }));
      }
    }
  }, [user, profile]);

  useEffect(() => {
    loadRoleTemplates();
    loadUserProfile();
  }, []);

  const loadRoleTemplates = async () => {
    try {
      const response = await apiService.getUserProfileTemplates();
      // Handle both array response and object with data property
      const templates = Array.isArray(response.data) ? response.data : response.data || response;
      setRoleTemplates(Array.isArray(templates) ? templates : []);
    } catch (error) {
      console.error('Failed to load role templates:', error);
      setRoleTemplates([]);
    }
  };

  const loadUserProfile = async () => {
    try {
      const response = await apiService.getUserProfile('persona');
      const userProfile = response.data || response;
      if (userProfile) {
        setProfile(userProfile);
        setFormData({
          ...userProfile,
          insight_focuses: userProfile.insight_focuses || [],
          key_metrics: userProfile.key_metrics || [],
          preferred_visualizations: userProfile.preferred_visualizations || []
        });
        setSelectedRole(userProfile.role);
      }
    } catch (error) {
      console.log('No existing persona found, starting fresh');
    }
  };

  const handleRoleChange = (event) => {
    const role = event.target.value;
    setSelectedRole(role);
    setHasUnsavedChanges(true);

    // Find the template for this role
    const template = roleTemplates.find(t => t.role === role);
    if (template && role !== 'custom') {
      setFormData({
        ...formData,
        role: role,
        insight_focuses: template.insight_focuses || [],
        key_metrics: template.key_metrics || [],
        preferred_visualizations: template.preferred_visualizations || []
      });
    } else {
      setFormData({
        ...formData,
        role: role
      });
    }
  };

  const handleInputChange = (field, value) => {
    setFormData({
      ...formData,
      [field]: value
    });
    setHasUnsavedChanges(true);
  };

  const handleSaveProfile = async () => {
    setLoading(true);
    setSaveStatus({ show: false, type: '', message: '' });

    try {
      let response;
      if (profile) {
        // Update existing persona
        response = await apiService.updateUserProfile('persona', formData);
      } else {
        // Create new persona
        response = await apiService.createUserProfile(formData);
      }

      const savedProfile = response.data || response;
      setProfile(savedProfile);
      setHasUnsavedChanges(false);
      setSaveStatus({
        show: true,
        type: 'success',
        message: 'Persona saved successfully! All insights will now be tailored to this role.'
      });
    } catch (error) {
      setSaveStatus({
        show: true,
        type: 'error',
        message: `Failed to save persona: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  const getRoleTemplate = (role) => {
    return roleTemplates.find(t => t.role === role);
  };

  const currentTemplate = getRoleTemplate(selectedRole);

  return (
    <Box sx={{ p: 3, bgcolor: sfColors.bgPage, minHeight: '100%' }}>
      <Stack spacing={3}>
        {/* Hero Header */}
        <Box sx={{
          bgcolor: sfColors.bgCard,
          borderRadius: '8px',
          p: 3,
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
            <AutoAwesomeIcon sx={{ fontSize: 32, color: sfColors.accent }} />
          </Avatar>
          <Box>
            <Typography sx={{ fontWeight: 700, fontSize: '1.5rem', color: sfColors.textPrimary }}>
              AI Persona
            </Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.95rem' }}>
              Select your business role to get personalized AI insights tailored to your perspective
            </Typography>
          </Box>
        </Box>

        {/* Save Status Alert */}
        {saveStatus.show && (
          <Alert severity={saveStatus.type} onClose={() => setSaveStatus({ show: false, type: '', message: '' })}>
            {saveStatus.message}
          </Alert>
        )}

        {/* Basic Information */}
        <Card sx={{ boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
          <CardContent sx={{ p: 3 }}>
            <Typography sx={{ fontWeight: 700, fontSize: '1rem', color: sfColors.textPrimary, mb: 2 }}>
              Basic Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Name"
                  value={formData.name}
                  disabled
                  InputProps={{
                    readOnly: true,
                  }}
                  helperText="Managed by your account settings"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={formData.email}
                  disabled
                  InputProps={{
                    readOnly: true,
                  }}
                  helperText="Managed by your account settings"
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Role Selection */}
        <Card sx={{ boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
          <CardContent sx={{ p: 3 }}>
            <Typography sx={{ fontWeight: 700, fontSize: '1rem', color: sfColors.textPrimary, mb: 2 }}>
              Role & Expertise
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={selectedRole}
                label="Role"
                onChange={handleRoleChange}
              >
                <MenuItem value="custom">Custom</MenuItem>
                {roleTemplates.map((template) => (
                  <MenuItem key={template.role} value={template.role}>
                    {template.display_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {currentTemplate && currentTemplate.role !== 'custom' && (
              <Paper sx={{ mt: 2, p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="body2" color="text.secondary">
                  {currentTemplate.description}
                </Typography>
              </Paper>
            )}
          </CardContent>
        </Card>

        {/* Preferences */}
        <Card sx={{ boxShadow: '0 2px 4px rgba(0,0,0,0.08)', border: `1px solid ${sfColors.border}`, borderRadius: '8px' }}>
          <CardContent sx={{ p: 3 }}>
            <Typography sx={{ fontWeight: 700, fontSize: '1rem', color: sfColors.textPrimary, mb: 2 }}>
              Insight Preferences
            </Typography>
            <Stack spacing={3}>
              <Autocomplete
                multiple
                options={insightFocusOptions}
                getOptionLabel={(option) => option.label}
                value={insightFocusOptions.filter(opt => formData.insight_focuses.includes(opt.value))}
                onChange={(event, newValue) => {
                  handleInputChange('insight_focuses', newValue.map(v => v.value));
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Focus Areas"
                    placeholder="Select areas of interest"
                  />
                )}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip label={option.label} {...getTagProps({ index })} />
                  ))
                }
              />

              <TextField
                fullWidth
                label="Key Metrics"
                placeholder="Enter metrics separated by commas (e.g., revenue, profit, margin)"
                value={formData.key_metrics.join(', ')}
                onChange={(e) => handleInputChange('key_metrics', e.target.value.split(',').map(m => m.trim()).filter(m => m))}
                helperText="These metrics will be highlighted in your insights"
              />

              <Autocomplete
                multiple
                options={visualizationOptions}
                getOptionLabel={(option) => option.label}
                value={visualizationOptions.filter(opt => formData.preferred_visualizations.includes(opt.value))}
                onChange={(event, newValue) => {
                  handleInputChange('preferred_visualizations', newValue.map(v => v.value));
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Preferred Visualizations"
                    placeholder="Select chart types"
                  />
                )}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip label={option.label} {...getTagProps({ index })} />
                  ))
                }
              />

              <TextField
                fullWidth
                multiline
                rows={4}
                label="Additional Context"
                placeholder="Add any additional context that should be considered when generating insights..."
                value={formData.custom_context}
                onChange={(e) => handleInputChange('custom_context', e.target.value)}
              />
            </Stack>
          </CardContent>
        </Card>

        {/* Save Button */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<SaveIcon />}
            onClick={handleSaveProfile}
            disabled={loading || !hasUnsavedChanges}
            sx={{
              bgcolor: sfColors.accent,
              '&:hover': { bgcolor: sfColors.accentHover },
              textTransform: 'none',
              fontWeight: 600,
              px: 3,
              py: 1,
              borderRadius: '6px',
            }}
          >
            {loading ? 'Saving...' : hasUnsavedChanges ? 'Save Persona' : 'Saved'}
          </Button>
        </Box>
      </Stack>
    </Box>
  );
};

export default UserProfileManager;
