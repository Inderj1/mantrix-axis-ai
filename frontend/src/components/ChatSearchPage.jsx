import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Typography,
  InputAdornment,
  Chip,
  Stack,
  IconButton,
  Menu,
  MenuItem,
  CircularProgress,
  Alert,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import {
  Search as SearchIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Delete as DeleteIcon,
  Folder as FolderIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';

const ChatSearchPage = ({
  userId = 'default',
  onOpenConversation,
  starredConversations = [],
  onToggleStar,
  onDeleteConversation,
  projects = [],
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [conversations, setConversations] = useState([]);
  const [filteredConversations, setFilteredConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedConv, setSelectedConv] = useState(null);
  const [sortModel, setSortModel] = useState([
    { field: 'updated_at', sort: 'desc' }
  ]);

  // Load all conversations on mount
  useEffect(() => {
    loadConversations();
  }, [userId]);

  // Filter conversations when search query changes
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredConversations(conversations);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = conversations.filter(conv => {
        const title = (conv.title || 'Untitled Conversation').toLowerCase();
        const messages = conv.messages || [];

        // Search in title
        if (title.includes(query)) return true;

        // Search in messages
        return messages.some(msg =>
          msg.content && msg.content.toLowerCase().includes(query)
        );
      });
      setFilteredConversations(filtered);
    }
  }, [searchQuery, conversations]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.listConversations(userId, 100, 0);
      console.log('API Response:', response);

      // Handle different response structures
      const conversationsList = response.data?.conversations || response.data || [];
      console.log('Conversations list:', conversationsList);

      // Debug: Log first conversation to see date fields
      if (conversationsList.length > 0) {
        console.log('First conversation:', conversationsList[0]);
        console.log('Created at:', conversationsList[0].created_at);
        console.log('Updated at:', conversationsList[0].updated_at);
      }

      setConversations(conversationsList);
      setFilteredConversations(conversationsList);
    } catch (err) {
      console.error('Error loading conversations:', err);
      setError('Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const handleMenuOpen = (event, conv) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedConv(conv);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedConv(null);
  };

  const handleToggleStarClick = () => {
    if (selectedConv) {
      onToggleStar(selectedConv.conversation_id || selectedConv.conversationId);
    }
    handleMenuClose();
  };

  const handleDeleteClick = async () => {
    if (selectedConv) {
      await onDeleteConversation(selectedConv.conversation_id || selectedConv.conversationId);
      // Reload conversations after delete
      loadConversations();
    }
    handleMenuClose();
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';

    const date = new Date(timestamp);

    // Check if date is valid
    if (isNaN(date.getTime())) return 'N/A';

    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  const getConversationPreview = (conv) => {
    const messages = conv.messages || [];
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) return 'No messages yet';

    const content = lastMessage.content || '';
    return content.length > 150 ? content.substring(0, 150) + '...' : content;
  };

  const getProjectName = (projectId) => {
    const project = projects.find(p => p.project_id === projectId);
    return project?.name || null;
  };

  const isStarred = (convId) => {
    return starredConversations.some(c =>
      (c.conversation_id || c.conversationId) === convId
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper elevation={0} sx={{ p: 3, mb: 2, borderRadius: 2 }}>
        <Typography variant="h5" sx={{ mb: 2, fontWeight: 600 }}>
          All Conversations
        </Typography>

        {/* Search Bar */}
        <TextField
          fullWidth
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 1 }}
        />

        <Typography variant="body2" color="text.secondary">
          {filteredConversations.length} conversation{filteredConversations.length !== 1 ? 's' : ''} found
        </Typography>
      </Paper>

      {/* DataGrid Content */}
      <Box sx={{ flex: 1, width: '100%' }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <DataGrid
          rows={filteredConversations.map(conv => ({
            id: conv.conversation_id || conv.conversationId,
            title: conv.title || 'Untitled Conversation',
            preview: getConversationPreview(conv),
            starred: isStarred(conv.conversation_id || conv.conversationId),
            projectName: getProjectName(conv.project_id),
            messageCount: (conv.messages || []).length,
            created_at: conv.created_at,
            updated_at: conv.updated_at || conv.created_at,
            _raw: conv
          }))}
          columns={[
            {
              field: 'title',
              headerName: 'Title',
              flex: 1,
              minWidth: 300,
              renderCell: (params) => (
                <Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 500,
                      color: '#1A2332',
                    }}
                  >
                    {params.value}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      display: 'block',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {params.row.preview}
                  </Typography>
                </Box>
              ),
            },
            {
              field: 'messageCount',
              headerName: 'Messages',
              width: 100,
              type: 'number',
            },
            {
              field: 'created_at',
              headerName: 'Created',
              width: 180,
              type: 'dateTime',
              valueGetter: (params) => params ? new Date(params) : null,
              renderCell: (params) => formatDate(params.value),
            },
            {
              field: 'updated_at',
              headerName: 'Last Updated',
              width: 180,
              type: 'dateTime',
              valueGetter: (params) => params ? new Date(params) : null,
              renderCell: (params) => formatDate(params.value),
            },
            {
              field: 'actions',
              headerName: 'Actions',
              width: 80,
              sortable: false,
              renderCell: (params) => (
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleMenuOpen(e, params.row._raw);
                  }}
                  sx={{
                    '&:hover': {
                      bgcolor: 'rgba(106, 109, 112, 0.1)',
                    }
                  }}
                >
                  <MoreVertIcon fontSize="small" />
                </IconButton>
              ),
            },
          ]}
          loading={loading}
          sortModel={sortModel}
          onSortModelChange={setSortModel}
          onRowClick={(params) => onOpenConversation(params.id)}
          density="standard"
          pageSizeOptions={[10, 25, 50, 100]}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 25 },
            },
          }}
          sx={{
            border: 'none',
            '& .MuiDataGrid-cell:focus': {
              outline: 'none',
            },
            '& .MuiDataGrid-row': {
              cursor: 'pointer',
            },
            '& .MuiDataGrid-columnHeaders': {
              bgcolor: '#F8FAFB',
              borderRadius: '6px 6px 0 0',
            },
          }}
        />
      </Box>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleToggleStarClick}>
          {selectedConv && isStarred(selectedConv.conversation_id || selectedConv.conversationId) ? (
            <>
              <StarBorderIcon sx={{ mr: 1, fontSize: 20 }} />
              Unstar
            </>
          ) : (
            <>
              <StarIcon sx={{ mr: 1, fontSize: 20 }} />
              Star
            </>
          )}
        </MenuItem>
        <MenuItem onClick={handleDeleteClick} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1, fontSize: 20 }} />
          Delete
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default ChatSearchPage;
