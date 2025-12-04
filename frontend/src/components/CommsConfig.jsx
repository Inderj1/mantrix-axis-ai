import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Stack,
  IconButton,
  Chip,
  Grid,
  Switch,
  FormControlLabel,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Settings as SettingsIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

const CommsConfig = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [communicationTypes, setCommunicationTypes] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const [fields, setFields] = useState([]);
  const [openTypeDialog, setOpenTypeDialog] = useState(false);
  const [openFieldDialog, setOpenFieldDialog] = useState(false);
  const [editingType, setEditingType] = useState(null);
  const [editingField, setEditingField] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  // Form states for communication type
  const [typeForm, setTypeForm] = useState({
    name: '',
    display_name: '',
    description: '',
    icon: 'Email',
    color: '#2196F3',
    tab_order: 0,
    is_active: true,
  });

  // Form states for field definition
  const [fieldForm, setFieldForm] = useState({
    field_name: '',
    display_name: '',
    field_type: 'text',
    is_required: false,
    is_searchable: true,
    is_filterable: true,
    is_sortable: true,
    column_order: 0,
    column_width: 150,
    dropdown_options: [],
  });

  const fieldTypes = [
    'text', 'number', 'date', 'datetime', 'email', 'dropdown', 'boolean', 'currency', 'url', 'textarea'
  ];

  const iconOptions = [
    'Email', 'Business', 'Person', 'Receipt', 'Notifications', 'ShoppingCart',
    'Inventory', 'TrendingUp', 'Assessment', 'Assignment'
  ];

  useEffect(() => {
    fetchCommunicationTypes();
  }, []);

  useEffect(() => {
    if (selectedType) {
      fetchFields(selectedType.id);
    }
  }, [selectedType]);

  const fetchCommunicationTypes = async () => {
    try {
      const response = await fetch('/api/v1/comms/config/types?active_only=false');
      if (response.ok) {
        const data = await response.json();
        setCommunicationTypes(data);
        if (data.length > 0 && !selectedType) {
          setSelectedType(data[0]);
        }
      }
    } catch (err) {
      setError('Failed to load communication types');
    }
  };

  const fetchFields = async (typeId) => {
    try {
      const response = await fetch(`/api/v1/comms/config/fields/${typeId}`);
      if (response.ok) {
        const data = await response.json();
        setFields(data);
      }
    } catch (err) {
      setError('Failed to load fields');
    }
  };

  const handleSaveType = async () => {
    try {
      const url = editingType
        ? `/api/v1/comms/config/types/${editingType.id}`
        : '/api/v1/comms/config/types';

      const method = editingType ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(typeForm),
      });

      if (response.ok) {
        setSuccess(editingType ? 'Type updated successfully' : 'Type created successfully');
        setOpenTypeDialog(false);
        setEditingType(null);
        fetchCommunicationTypes();
        resetTypeForm();
      }
    } catch (err) {
      setError('Failed to save communication type');
    }
  };

  const handleSaveField = async () => {
    try {
      const url = editingField
        ? `/api/v1/comms/config/fields/${editingField.id}`
        : '/api/v1/comms/config/fields';

      const method = editingField ? 'PUT' : 'POST';

      const fieldData = {
        ...fieldForm,
        communication_type_id: selectedType.id,
      };

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fieldData),
      });

      if (response.ok) {
        setSuccess(editingField ? 'Field updated successfully' : 'Field created successfully');
        setOpenFieldDialog(false);
        setEditingField(null);
        fetchFields(selectedType.id);
        resetFieldForm();
      }
    } catch (err) {
      setError('Failed to save field');
    }
  };

  const handleDeleteType = (id) => {
    setConfirmDialog({
      open: true,
      title: 'Delete Communication Type',
      message: 'Are you sure you want to delete this communication type?',
      onConfirm: async () => {
        try {
          const response = await fetch(`/api/v1/comms/config/types/${id}`, { method: 'DELETE' });
          if (response.ok) {
            setSuccess('Type deleted successfully');
            fetchCommunicationTypes();
          }
        } catch (err) {
          setError('Failed to delete communication type');
        }
        setConfirmDialog(prev => ({ ...prev, open: false }));
      },
    });
  };

  const handleDeleteField = (id) => {
    setConfirmDialog({
      open: true,
      title: 'Delete Field',
      message: 'Are you sure you want to delete this field?',
      onConfirm: async () => {
        try {
          const response = await fetch(`/api/v1/comms/config/fields/${id}`, { method: 'DELETE' });
          if (response.ok) {
            setSuccess('Field deleted successfully');
            fetchFields(selectedType.id);
          }
        } catch (err) {
          setError('Failed to delete field');
        }
        setConfirmDialog(prev => ({ ...prev, open: false }));
      },
    });
  };

  const resetTypeForm = () => {
    setTypeForm({
      name: '',
      display_name: '',
      description: '',
      icon: 'Email',
      color: '#2196F3',
      tab_order: 0,
      is_active: true,
    });
  };

  const resetFieldForm = () => {
    setFieldForm({
      field_name: '',
      display_name: '',
      field_type: 'text',
      is_required: false,
      is_searchable: true,
      is_filterable: true,
      is_sortable: true,
      column_order: 0,
      column_width: 150,
      dropdown_options: [],
    });
  };

  const handleEditType = (type) => {
    setEditingType(type);
    setTypeForm(type);
    setOpenTypeDialog(true);
  };

  const handleEditField = (field) => {
    setEditingField(field);
    setFieldForm(field);
    setOpenFieldDialog(true);
  };

  const typeColumns = [
    { field: 'display_name', headerName: 'Display Name', width: 200 },
    { field: 'name', headerName: 'System Name', width: 200 },
    { field: 'icon', headerName: 'Icon', width: 120 },
    {
      field: 'color',
      headerName: 'Color',
      width: 120,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 20, height: 20, bgcolor: params.value, borderRadius: 1 }} />
          {params.value}
        </Box>
      ),
    },
    { field: 'tab_order', headerName: 'Order', width: 100 },
    {
      field: 'is_active',
      headerName: 'Active',
      width: 100,
      renderCell: (params) => <Chip label={params.value ? 'Yes' : 'No'} size="small" color={params.value ? 'success' : 'default'} />,
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 150,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <IconButton size="small" onClick={() => handleEditType(params.row)}>
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={() => handleDeleteType(params.row.id)}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Stack>
      ),
    },
  ];

  const fieldColumns = [
    { field: 'display_name', headerName: 'Display Name', width: 200 },
    { field: 'field_name', headerName: 'Field Name', width: 150 },
    { field: 'field_type', headerName: 'Type', width: 120 },
    { field: 'column_width', headerName: 'Width', width: 100 },
    { field: 'column_order', headerName: 'Order', width: 100 },
    {
      field: 'is_required',
      headerName: 'Required',
      width: 100,
      renderCell: (params) => <Chip label={params.value ? 'Yes' : 'No'} size="small" />,
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 150,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <IconButton size="small" onClick={() => handleEditField(params.row)}>
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={() => handleDeleteField(params.row.id)}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Stack>
      ),
    },
  ];

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              EMAIL INTEL Configuration
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Configure communication types and custom fields
            </Typography>
          </Box>
          <SettingsIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        </Stack>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="Communication Types" />
          <Tab label="Field Definitions" disabled={!selectedType} />
        </Tabs>
      </Paper>

      {activeTab === 0 && (
        <Paper>
          <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Communication Types</Typography>
            <Button startIcon={<AddIcon />} variant="contained" onClick={() => { resetTypeForm(); setOpenTypeDialog(true); }}>
              Add Type
            </Button>
          </Box>
          <Box sx={{ height: 500 }}>
            <DataGrid
              rows={communicationTypes}
              columns={typeColumns}
              pageSize={10}
              onRowClick={(params) => setSelectedType(params.row)}
              sx={{ border: 'none' }}
            />
          </Box>
        </Paper>
      )}

      {activeTab === 1 && selectedType && (
        <Paper>
          <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Fields for: {selectedType.display_name}</Typography>
            <Button startIcon={<AddIcon />} variant="contained" onClick={() => { resetFieldForm(); setOpenFieldDialog(true); }}>
              Add Field
            </Button>
          </Box>
          <Box sx={{ height: 500 }}>
            <DataGrid
              rows={fields}
              columns={fieldColumns}
              pageSize={10}
              sx={{ border: 'none' }}
            />
          </Box>
        </Paper>
      )}

      {/* Type Dialog */}
      <Dialog open={openTypeDialog} onClose={() => setOpenTypeDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingType ? 'Edit' : 'Add'} Communication Type</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="System Name"
              value={typeForm.name}
              onChange={(e) => setTypeForm({ ...typeForm, name: e.target.value.replace(/\s/g, '_').toLowerCase() })}
              fullWidth
            />
            <TextField
              label="Display Name"
              value={typeForm.display_name}
              onChange={(e) => setTypeForm({ ...typeForm, display_name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Description"
              value={typeForm.description}
              onChange={(e) => setTypeForm({ ...typeForm, description: e.target.value })}
              multiline
              rows={2}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Icon</InputLabel>
              <Select value={typeForm.icon} onChange={(e) => setTypeForm({ ...typeForm, icon: e.target.value })}>
                {iconOptions.map(icon => <MenuItem key={icon} value={icon}>{icon}</MenuItem>)}
              </Select>
            </FormControl>
            <TextField
              label="Color"
              type="color"
              value={typeForm.color}
              onChange={(e) => setTypeForm({ ...typeForm, color: e.target.value })}
              fullWidth
            />
            <TextField
              label="Tab Order"
              type="number"
              value={typeForm.tab_order}
              onChange={(e) => setTypeForm({ ...typeForm, tab_order: parseInt(e.target.value) })}
              fullWidth
            />
            <FormControlLabel
              control={<Switch checked={typeForm.is_active} onChange={(e) => setTypeForm({ ...typeForm, is_active: e.target.checked })} />}
              label="Active"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenTypeDialog(false)}>Cancel</Button>
          <Button onClick={handleSaveType} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Field Dialog */}
      <Dialog open={openFieldDialog} onClose={() => setOpenFieldDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingField ? 'Edit' : 'Add'} Field</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <TextField
                label="Field Name"
                value={fieldForm.field_name}
                onChange={(e) => setFieldForm({ ...fieldForm, field_name: e.target.value.replace(/\s/g, '_').toLowerCase() })}
                fullWidth
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                label="Display Name"
                value={fieldForm.display_name}
                onChange={(e) => setFieldForm({ ...fieldForm, display_name: e.target.value })}
                fullWidth
              />
            </Grid>
            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Field Type</InputLabel>
                <Select value={fieldForm.field_type} onChange={(e) => setFieldForm({ ...fieldForm, field_type: e.target.value })}>
                  {fieldTypes.map(type => <MenuItem key={type} value={type}>{type}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={3}>
              <TextField
                label="Column Width"
                type="number"
                value={fieldForm.column_width}
                onChange={(e) => setFieldForm({ ...fieldForm, column_width: parseInt(e.target.value) })}
                fullWidth
              />
            </Grid>
            <Grid item xs={3}>
              <TextField
                label="Column Order"
                type="number"
                value={fieldForm.column_order}
                onChange={(e) => setFieldForm({ ...fieldForm, column_order: parseInt(e.target.value) })}
                fullWidth
              />
            </Grid>
            {fieldForm.field_type === 'dropdown' && (
              <Grid item xs={12}>
                <TextField
                  label="Dropdown Options (comma-separated)"
                  value={fieldForm.dropdown_options?.join(', ') || ''}
                  onChange={(e) => setFieldForm({ ...fieldForm, dropdown_options: e.target.value.split(',').map(s => s.trim()) })}
                  fullWidth
                />
              </Grid>
            )}
            <Grid item xs={3}>
              <FormControlLabel
                control={<Switch checked={fieldForm.is_required} onChange={(e) => setFieldForm({ ...fieldForm, is_required: e.target.checked })} />}
                label="Required"
              />
            </Grid>
            <Grid item xs={3}>
              <FormControlLabel
                control={<Switch checked={fieldForm.is_searchable} onChange={(e) => setFieldForm({ ...fieldForm, is_searchable: e.target.checked })} />}
                label="Searchable"
              />
            </Grid>
            <Grid item xs={3}>
              <FormControlLabel
                control={<Switch checked={fieldForm.is_filterable} onChange={(e) => setFieldForm({ ...fieldForm, is_filterable: e.target.checked })} />}
                label="Filterable"
              />
            </Grid>
            <Grid item xs={3}>
              <FormControlLabel
                control={<Switch checked={fieldForm.is_sortable} onChange={(e) => setFieldForm({ ...fieldForm, is_sortable: e.target.checked })} />}
                label="Sortable"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenFieldDialog(false)}>Cancel</Button>
          <Button onClick={handleSaveField} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          {confirmDialog.title}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>{confirmDialog.message}</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog(prev => ({ ...prev, open: false }))}>
            Cancel
          </Button>
          <Button onClick={confirmDialog.onConfirm} variant="contained" color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CommsConfig;
