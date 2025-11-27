/**
 * AnnotationPopover - Widget annotation creator and viewer
 *
 * Allows users to add annotations to specific points on widgets
 */

import React, { useState, useEffect } from 'react';
import {
  Popover,
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Divider,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  Close as CloseIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Note as NoteIcon,
  Flag as FlagIcon,
  TrendingUp as TrendIcon,
  Highlight as HighlightIcon
} from '@mui/icons-material';
import api from '../../services/api';

const ANNOTATION_TYPES = [
  { value: 'note', label: 'Note', icon: <NoteIcon />, color: 'default' },
  { value: 'highlight', label: 'Highlight', icon: <HighlightIcon />, color: 'primary' },
  { value: 'flag', label: 'Flag', icon: <FlagIcon />, color: 'warning' },
  { value: 'trend', label: 'Trend', icon: <TrendIcon />, color: 'success' }
];

const AnnotationPopover = ({
  anchorEl,
  open,
  onClose,
  widgetId,
  dashboardId,
  position,
  dataPoint,
  currentUserId
}) => {
  const [annotations, setAnnotations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isAdding, setIsAdding] = useState(false);

  // New annotation state
  const [newContent, setNewContent] = useState('');
  const [annotationType, setAnnotationType] = useState('note');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open && widgetId) {
      fetchAnnotations();
    }
  }, [open, widgetId]);

  const fetchAnnotations = async () => {
    if (!widgetId || !dashboardId) return;

    setLoading(true);
    try {
      const response = await api.get(`/api/v1/widgets/${widgetId}/annotations`, {
        params: { dashboard_id: dashboardId }
      });
      setAnnotations(response.data || []);
    } catch (err) {
      console.error('Failed to fetch annotations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAnnotation = async () => {
    if (!newContent.trim()) return;

    setSubmitting(true);
    try {
      await api.post(`/api/v1/widgets/${widgetId}/annotations`, {
        content: newContent,
        annotation_type: annotationType,
        position,
        data_point: dataPoint
      }, {
        params: { dashboard_id: dashboardId }
      });

      setNewContent('');
      setAnnotationType('note');
      setIsAdding(false);
      fetchAnnotations();
    } catch (err) {
      console.error('Failed to add annotation:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteAnnotation = async (annotationId) => {
    try {
      await api.delete(`/api/v1/annotations/${annotationId}`);
      fetchAnnotations();
    } catch (err) {
      console.error('Failed to delete annotation:', err);
    }
  };

  const getTypeInfo = (type) => {
    return ANNOTATION_TYPES.find(t => t.value === type) || ANNOTATION_TYPES[0];
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'center'
      }}
      transformOrigin={{
        vertical: 'top',
        horizontal: 'center'
      }}
      PaperProps={{
        sx: { width: 320, maxHeight: 400 }
      }}
    >
      <Box sx={{ p: 2 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="subtitle1">
            Annotations
          </Typography>
          <Box>
            {!isAdding && (
              <Tooltip title="Add annotation">
                <IconButton size="small" onClick={() => setIsAdding(true)}>
                  <AddIcon />
                </IconButton>
              </Tooltip>
            )}
            <IconButton size="small" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Data point info */}
        {dataPoint && (
          <Box sx={{ mb: 2, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Data Point
            </Typography>
            <Typography variant="body2">
              {typeof dataPoint === 'object'
                ? Object.entries(dataPoint).map(([k, v]) => `${k}: ${v}`).join(', ')
                : dataPoint}
            </Typography>
          </Box>
        )}

        {/* Add annotation form */}
        {isAdding && (
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
              {ANNOTATION_TYPES.map(type => (
                <Chip
                  key={type.value}
                  label={type.label}
                  size="small"
                  icon={type.icon}
                  color={annotationType === type.value ? type.color : 'default'}
                  variant={annotationType === type.value ? 'filled' : 'outlined'}
                  onClick={() => setAnnotationType(type.value)}
                  sx={{ cursor: 'pointer' }}
                />
              ))}
            </Box>

            <TextField
              fullWidth
              size="small"
              multiline
              rows={2}
              placeholder="Add a note..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              autoFocus
            />

            <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
              <Button
                size="small"
                variant="contained"
                onClick={handleAddAnnotation}
                disabled={!newContent.trim() || submitting}
              >
                {submitting ? <CircularProgress size={16} /> : 'Add'}
              </Button>
              <Button
                size="small"
                onClick={() => {
                  setIsAdding(false);
                  setNewContent('');
                }}
              >
                Cancel
              </Button>
            </Box>

            <Divider sx={{ my: 2 }} />
          </Box>
        )}

        {/* Annotations list */}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        ) : annotations.length > 0 ? (
          <List disablePadding dense>
            {annotations.map((annotation) => {
              const typeInfo = getTypeInfo(annotation.annotation_type);
              const isOwn = annotation.author_id === currentUserId;

              return (
                <ListItem
                  key={annotation.id}
                  sx={{ px: 0, alignItems: 'flex-start' }}
                >
                  <Avatar
                    sx={{
                      width: 28,
                      height: 28,
                      mr: 1,
                      bgcolor: `${typeInfo.color}.light`
                    }}
                  >
                    {React.cloneElement(typeInfo.icon, {
                      sx: { fontSize: 16 },
                      color: typeInfo.color
                    })}
                  </Avatar>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography variant="body2">
                          {annotation.content}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Typography variant="caption" color="text.secondary">
                        {annotation.author_name} - {formatDate(annotation.created_at)}
                      </Typography>
                    }
                  />
                  {isOwn && (
                    <ListItemSecondaryAction>
                      <IconButton
                        size="small"
                        edge="end"
                        onClick={() => handleDeleteAnnotation(annotation.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </ListItemSecondaryAction>
                  )}
                </ListItem>
              );
            })}
          </List>
        ) : !isAdding ? (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <Typography variant="body2" color="text.secondary">
              No annotations yet
            </Typography>
            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={() => setIsAdding(true)}
              sx={{ mt: 1 }}
            >
              Add first annotation
            </Button>
          </Box>
        ) : null}
      </Box>
    </Popover>
  );
};

export default AnnotationPopover;
