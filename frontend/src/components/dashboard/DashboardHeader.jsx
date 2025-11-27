/**
 * DashboardHeader - Dashboard title bar with actions
 */
import React from 'react';
import {
  Box,
  Typography,
  IconButton,
  Button,
  Chip,
  Tooltip,
  TextField
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Share as ShareIcon,
  Download as DownloadIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  AutoAwesome as InsightsIcon
} from '@mui/icons-material';

const DashboardHeader = ({
  dashboard,
  editMode,
  isDirty,
  readonly,
  onToggleEdit,
  onSave,
  onShare,
  onExport,
  onInsights
}) => {
  const [isEditingTitle, setIsEditingTitle] = React.useState(false);
  const [titleValue, setTitleValue] = React.useState(dashboard?.name || '');

  React.useEffect(() => {
    setTitleValue(dashboard?.name || '');
  }, [dashboard?.name]);

  const handleTitleSave = () => {
    // TODO: Save title to backend
    setIsEditingTitle(false);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        px: 2,
        py: 1.5,
        borderBottom: '1px solid',
        borderColor: 'divider',
        backgroundColor: 'background.paper'
      }}
    >
      {/* Title */}
      <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
        {isEditingTitle && editMode ? (
          <>
            <TextField
              value={titleValue}
              onChange={(e) => setTitleValue(e.target.value)}
              size="small"
              variant="standard"
              autoFocus
              sx={{ width: 300 }}
            />
            <IconButton size="small" onClick={handleTitleSave}>
              <CheckIcon fontSize="small" />
            </IconButton>
            <IconButton size="small" onClick={() => setIsEditingTitle(false)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </>
        ) : (
          <>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 'medium',
                cursor: editMode ? 'pointer' : 'default'
              }}
              onClick={() => editMode && setIsEditingTitle(true)}
            >
              {dashboard?.name || 'Untitled Dashboard'}
            </Typography>
            {isDirty && (
              <Chip label="Unsaved" size="small" color="warning" variant="outlined" />
            )}
            {dashboard?.is_public && (
              <Chip label="Public" size="small" color="success" variant="outlined" />
            )}
          </>
        )}
      </Box>

      {/* Actions */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {/* AI Insights */}
        <Tooltip title="AI Insights">
          <IconButton onClick={onInsights} color="primary">
            <InsightsIcon />
          </IconButton>
        </Tooltip>

        {/* Export */}
        <Tooltip title="Export">
          <IconButton onClick={onExport}>
            <DownloadIcon />
          </IconButton>
        </Tooltip>

        {/* Share */}
        {!readonly && (
          <Tooltip title="Share">
            <IconButton onClick={onShare}>
              <ShareIcon />
            </IconButton>
          </Tooltip>
        )}

        {/* Save (only in edit mode) */}
        {editMode && isDirty && (
          <Button
            variant="contained"
            color="primary"
            size="small"
            startIcon={<SaveIcon />}
            onClick={onSave}
          >
            Save
          </Button>
        )}

        {/* Edit Toggle */}
        {!readonly && (
          <Button
            variant={editMode ? 'contained' : 'outlined'}
            color={editMode ? 'secondary' : 'primary'}
            size="small"
            startIcon={<EditIcon />}
            onClick={onToggleEdit}
          >
            {editMode ? 'Done' : 'Edit'}
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default DashboardHeader;
