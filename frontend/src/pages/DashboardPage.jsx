/**
 * DashboardPage - Main dashboard view and management page
 *
 * Routes:
 * - /dashboards - Dashboard list
 * - /dashboards/:id - View/edit specific dashboard
 * - /dashboards/new - Create new dashboard
 * - /dashboards/shared/:token - View shared dashboard (no auth)
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Menu,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  Fab,
  Tooltip,
  Avatar,
} from '@mui/material';
import {
  Add as AddIcon,
  Dashboard as DashboardIcon,
  MoreVert as MoreIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Share as ShareIcon,
  ContentCopy as CopyIcon,
  ViewModule as TemplateIcon
} from '@mui/icons-material';

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

import { useDashboardStore } from '../stores/dashboardStore';
import { DashboardBuilder } from '../components/dashboard';
import api from '../services/api';

// Dashboard List View
const DashboardList = () => {
  const navigate = useNavigate();
  const { dashboards, isLoading, error, fetchDashboards, deleteDashboard, createDashboard } = useDashboardStore();

  const [menuAnchor, setMenuAnchor] = useState(null);
  const [selectedDashboard, setSelectedDashboard] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [newDashboardName, setNewDashboardName] = useState('');
  const [templates, setTemplates] = useState([]);

  // Load dashboards on mount
  useEffect(() => {
    fetchDashboards();
    loadTemplates();
  }, [fetchDashboards]);

  // Load templates
  const loadTemplates = async () => {
    try {
      const response = await api.get('/api/v1/dashboards/templates/');
      setTemplates(response.data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  // Handle menu open
  const handleMenuOpen = (event, dashboard) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setSelectedDashboard(dashboard);
  };

  // Handle menu close
  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedDashboard(null);
  };

  // Handle delete
  const handleDelete = async () => {
    if (selectedDashboard) {
      await deleteDashboard(selectedDashboard.id);
      handleMenuClose();
    }
  };

  // Handle create new dashboard
  const handleCreate = async () => {
    if (newDashboardName.trim()) {
      const newDashboard = await createDashboard({
        name: newDashboardName,
        widgets: []
      });
      setCreateDialogOpen(false);
      setNewDashboardName('');
      navigate(`/dashboards/${newDashboard.id}`);
    }
  };

  // Handle create from template
  const handleCreateFromTemplate = async (templateId) => {
    try {
      const response = await api.post(
        `/api/v1/dashboards/from-template/${templateId}?name=${encodeURIComponent(newDashboardName || 'New Dashboard')}`
      );
      setTemplateDialogOpen(false);
      setNewDashboardName('');
      navigate(`/dashboards/${response.data.id}`);
    } catch (err) {
      console.error('Failed to create from template:', err);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', bgcolor: sfColors.bgPage }}>
        <CircularProgress sx={{ color: sfColors.accent }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, bgcolor: sfColors.bgPage, minHeight: '100%' }}>
      {/* Hero Header */}
      <Box sx={{
        bgcolor: sfColors.bgCard,
        borderRadius: '8px',
        p: 3,
        mb: 3,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
        border: `1px solid ${sfColors.border}`,
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Avatar sx={{
            width: 64,
            height: 64,
            bgcolor: sfColors.iconBg,
          }}>
            <DashboardIcon sx={{ fontSize: 32, color: sfColors.accent }} />
          </Avatar>
          <Box>
            <Typography sx={{ fontWeight: 700, fontSize: '1.5rem', color: sfColors.textPrimary }}>
              Dashboards
            </Typography>
            <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.95rem' }}>
              Create and manage your data visualizations
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<TemplateIcon />}
            onClick={() => setTemplateDialogOpen(true)}
            sx={{
              borderColor: sfColors.border,
              color: sfColors.textPrimary,
              textTransform: 'none',
              fontWeight: 600,
              borderRadius: '6px',
              '&:hover': { borderColor: sfColors.accent, bgcolor: sfColors.iconBg },
            }}
          >
            From Template
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{
              bgcolor: sfColors.accent,
              '&:hover': { bgcolor: sfColors.accentHover },
              textTransform: 'none',
              fontWeight: 600,
              borderRadius: '6px',
            }}
          >
            New Dashboard
          </Button>
        </Box>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
      )}

      {/* Dashboard Grid */}
      {dashboards.length === 0 ? (
        <Box sx={{
          textAlign: 'center',
          py: 8,
          bgcolor: sfColors.bgCard,
          borderRadius: '8px',
          border: `1px solid ${sfColors.border}`,
        }}>
          <DashboardIcon sx={{ fontSize: 64, color: sfColors.textSecondary, mb: 2, opacity: 0.5 }} />
          <Typography sx={{ fontWeight: 600, color: sfColors.textPrimary, mb: 1 }}>
            No dashboards yet
          </Typography>
          <Typography sx={{ color: sfColors.textSecondary, mb: 3, fontSize: '0.95rem' }}>
            Create your first dashboard to visualize your data
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{
              bgcolor: sfColors.accent,
              '&:hover': { bgcolor: sfColors.accentHover },
              textTransform: 'none',
              fontWeight: 600,
              borderRadius: '6px',
            }}
          >
            Create Dashboard
          </Button>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {dashboards.map(dashboard => (
            <Grid item xs={12} sm={6} md={4} key={dashboard.id}>
              <Card
                sx={{
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
                  border: `1px solid ${sfColors.border}`,
                  borderRadius: '8px',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 16px rgba(0,0,0,0.12)',
                    borderColor: sfColors.accent,
                  }
                }}
                onClick={() => navigate(`/dashboards/${dashboard.id}`)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography sx={{ fontWeight: 600, color: sfColors.textPrimary, fontSize: '1rem' }} noWrap>
                        {dashboard.name}
                      </Typography>
                      <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.875rem', mt: 0.5 }}>
                        {dashboard.widgets?.length || 0} widgets
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, dashboard)}
                    >
                      <MoreIcon />
                    </IconButton>
                  </Box>

                  {/* Tags */}
                  {dashboard.is_public && (
                    <Chip
                      label="Public"
                      size="small"
                      color="success"
                      variant="outlined"
                      sx={{ mt: 1 }}
                    />
                  )}

                  <Typography sx={{ color: sfColors.textSecondary, fontSize: '0.75rem', mt: 1 }} display="block">
                    Updated {new Date(dashboard.updated_at).toLocaleDateString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          navigate(`/dashboards/${selectedDashboard?.id}`);
          handleMenuClose();
        }}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>Create New Dashboard</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Dashboard Name"
            fullWidth
            value={newDashboardName}
            onChange={(e) => setNewDashboardName(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleCreate()}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>

      {/* Template Dialog */}
      <Dialog open={templateDialogOpen} onClose={() => setTemplateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create from Template</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="Dashboard Name"
            fullWidth
            value={newDashboardName}
            onChange={(e) => setNewDashboardName(e.target.value)}
            sx={{ mb: 2 }}
          />

          <Typography variant="subtitle2" gutterBottom>
            Choose a template:
          </Typography>

          <Grid container spacing={2}>
            {templates.map(template => (
              <Grid item xs={12} key={template.id}>
                <Card
                  variant="outlined"
                  sx={{
                    cursor: 'pointer',
                    '&:hover': { borderColor: 'primary.main' }
                  }}
                  onClick={() => handleCreateFromTemplate(template.id)}
                >
                  <CardContent sx={{ py: 1.5 }}>
                    <Typography variant="subtitle1">{template.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {template.description}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {template.widgets?.length || 0} widgets
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTemplateDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// Shared Dashboard View (no auth required)
const SharedDashboardView = () => {
  const { token } = useParams();
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadSharedDashboard = async () => {
      try {
        const response = await api.get(`/api/v1/dashboards/shared/${token}`);
        setDashboard(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Dashboard not found');
      } finally {
        setIsLoading(false);
      }
    };

    loadSharedDashboard();
  }, [token]);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  // Use DashboardBuilder in readonly mode
  return <DashboardBuilder dashboardId={dashboard.id} readonly={true} />;
};

// Main Dashboard Page Component
const DashboardPage = () => {
  const { id, token } = useParams();
  const location = useLocation();

  // Shared dashboard view
  if (location.pathname.includes('/shared/')) {
    return <SharedDashboardView />;
  }

  // Dashboard builder view
  if (id) {
    return (
      <Box sx={{ height: '100%' }}>
        <DashboardBuilder dashboardId={id} />
      </Box>
    );
  }

  // Dashboard list view
  return <DashboardList />;
};

export default DashboardPage;
