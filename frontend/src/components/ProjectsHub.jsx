import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  IconButton,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Menu,
  MenuItem,
  Paper,
  InputAdornment,
} from '@mui/material';
import {
  Add as AddIcon,
  Folder as FolderIcon,
  MoreVert as MoreIcon,
  Search as SearchIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Unarchive as UnarchiveIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';

const ProjectsHub = () => {
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    color: '#0a6ed1',
    icon: 'folder'
  });

  // Load projects on component mount
  useEffect(() => {
    if (user) {
      loadProjects();
    }
  }, [user]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await apiService.get(`/api/v1/projects?user_id=${user.id}`);
      setProjects(response.data || []);
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    try {
      const response = await apiService.post(`/api/v1/projects?user_id=${user.id}`, newProject);
      setProjects([response.data, ...projects]);
      setCreateDialogOpen(false);
      setNewProject({ name: '', description: '', color: '#0a6ed1', icon: 'folder' });
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  const handleUpdateProject = async () => {
    try {
      const response = await apiService.put(`/api/v1/projects/${selectedProject.project_id}`, {
        name: selectedProject.name,
        description: selectedProject.description,
        color: selectedProject.color,
        icon: selectedProject.icon
      });
      setProjects(projects.map(p => p.project_id === selectedProject.project_id ? response.data : p));
      setEditDialogOpen(false);
      setSelectedProject(null);
    } catch (error) {
      console.error('Error updating project:', error);
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (!window.confirm('Are you sure you want to delete this project? Conversations will not be deleted.')) {
      return;
    }

    try {
      await apiService.delete(`/api/v1/projects/${projectId}`);
      setProjects(projects.filter(p => p.project_id !== projectId));
      handleCloseMenu();
    } catch (error) {
      console.error('Error deleting project:', error);
    }
  };

  const handleArchiveProject = async (projectId, isArchived) => {
    try {
      const response = await apiService.put(`/api/v1/projects/${projectId}`, {
        is_archived: !isArchived
      });
      setProjects(projects.map(p => p.project_id === projectId ? response.data : p));
      handleCloseMenu();
    } catch (error) {
      console.error('Error archiving project:', error);
    }
  };

  const handleOpenMenu = (event, project) => {
    setAnchorEl(event.currentTarget);
    setSelectedProject(project);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
    setSelectedProject(null);
  };

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (project.description && project.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <Paper elevation={1} sx={{ p: 4, borderRadius: 2, minHeight: 'calc(100vh - 180px)', bgcolor: 'background.paper' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h5" sx={{ mb: 2, fontWeight: 600 }}>
            Projects
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Organize your conversations into projects
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          sx={{
            bgcolor: '#0a6ed1',
            '&:hover': { bgcolor: '#0854a0' }
          }}
        >
          New Project
        </Button>
      </Box>

      {/* Search */}
      <TextField
        fullWidth
        placeholder="Search projects..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      {/* Projects Grid */}
      <Grid container spacing={3}>
        {filteredProjects.map((project) => (
          <Grid item xs={12} sm={6} md={4} key={project.project_id}>
            <Card
              sx={{
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <FolderIcon sx={{ color: project.color || '#0a6ed1', fontSize: 32 }} />
                    {project.is_archived && (
                      <Chip label="Archived" size="small" sx={{ height: 20 }} />
                    )}
                  </Box>
                  <IconButton
                    size="small"
                    onClick={(e) => handleOpenMenu(e, project)}
                  >
                    <MoreIcon />
                  </IconButton>
                </Box>

                <Typography
                  variant="h6"
                  fontWeight={500}
                  gutterBottom
                  noWrap
                  sx={{
                    fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif',
                  }}
                >
                  {project.name}
                </Typography>

                {project.description && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      mb: 2,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif',
                    }}
                  >
                    {project.description}
                  </Typography>
                )}

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif',
                    }}
                  >
                    {project.conversation_count} {project.conversation_count === 1 ? 'conversation' : 'conversations'}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif',
                    }}
                  >
                    {new Date(project.updated_at).toLocaleDateString()}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleCloseMenu}
      >
        <MenuItem onClick={() => {
          setEditDialogOpen(true);
          handleCloseMenu();
        }}>
          <EditIcon sx={{ mr: 1, fontSize: 20 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={() => handleArchiveProject(selectedProject?.project_id, selectedProject?.is_archived)}>
          {selectedProject?.is_archived ? <UnarchiveIcon sx={{ mr: 1, fontSize: 20 }} /> : <ArchiveIcon sx={{ mr: 1, fontSize: 20 }} />}
          {selectedProject?.is_archived ? 'Unarchive' : 'Archive'}
        </MenuItem>
        <MenuItem onClick={() => handleDeleteProject(selectedProject?.project_id)} sx={{ color: '#bb0000' }}>
          <DeleteIcon sx={{ mr: 1, fontSize: 20 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* Create Project Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Project Name"
            value={newProject.name}
            onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
            sx={{ mt: 2, mb: 2 }}
            required
          />
          <TextField
            fullWidth
            label="Description"
            value={newProject.description}
            onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
            multiline
            rows={3}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Color"
            type="color"
            value={newProject.color}
            onChange={(e) => setNewProject({ ...newProject, color: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateProject}
            variant="contained"
            disabled={!newProject.name}
            sx={{ bgcolor: '#0a6ed1', '&:hover': { bgcolor: '#0854a0' } }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Project Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Project</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Project Name"
            value={selectedProject?.name || ''}
            onChange={(e) => setSelectedProject({ ...selectedProject, name: e.target.value })}
            sx={{ mt: 2, mb: 2 }}
            required
          />
          <TextField
            fullWidth
            label="Description"
            value={selectedProject?.description || ''}
            onChange={(e) => setSelectedProject({ ...selectedProject, description: e.target.value })}
            multiline
            rows={3}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Color"
            type="color"
            value={selectedProject?.color || '#0a6ed1'}
            onChange={(e) => setSelectedProject({ ...selectedProject, color: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpdateProject}
            variant="contained"
            disabled={!selectedProject?.name}
            sx={{ bgcolor: '#0a6ed1', '&:hover': { bgcolor: '#0854a0' } }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default ProjectsHub;
