/**
 * CommentsPanel - Dashboard comments and discussion panel
 *
 * Features:
 * - View and add comments on dashboards
 * - Thread-based replies
 * - Comment types (general, insight, question, action_item)
 * - Edit and delete own comments
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Divider,
  TextField,
  Button,
  List,
  ListItem,
  Avatar,
  Chip,
  Menu,
  MenuItem,
  CircularProgress,
  Alert,
  Collapse,
  InputAdornment,
  Tooltip
} from '@mui/material';
import {
  Close as CloseIcon,
  Comment as CommentIcon,
  Send as SendIcon,
  Reply as ReplyIcon,
  MoreVert as MoreIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Lightbulb as InsightIcon,
  Help as QuestionIcon,
  CheckCircle as ActionIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon
} from '@mui/icons-material';
import api from '../../services/api';

const COMMENT_TYPES = [
  { value: 'general', label: 'Comment', icon: <CommentIcon fontSize="small" />, color: 'default' },
  { value: 'insight', label: 'Insight', icon: <InsightIcon fontSize="small" />, color: 'primary' },
  { value: 'question', label: 'Question', icon: <QuestionIcon fontSize="small" />, color: 'warning' },
  { value: 'action_item', label: 'Action', icon: <ActionIcon fontSize="small" />, color: 'success' }
];

const CommentsPanel = ({
  open,
  onClose,
  dashboardId,
  currentUserId
}) => {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // New comment state
  const [newComment, setNewComment] = useState('');
  const [commentType, setCommentType] = useState('general');
  const [submitting, setSubmitting] = useState(false);

  // Reply state
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState('');

  // Edit state
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState('');

  // Menu state
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [menuCommentId, setMenuCommentId] = useState(null);

  // Expanded threads
  const [expandedThreads, setExpandedThreads] = useState({});

  const inputRef = useRef(null);

  useEffect(() => {
    if (open && dashboardId) {
      fetchComments();
    }
  }, [open, dashboardId]);

  const fetchComments = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/v1/dashboards/${dashboardId}/comments`, {
        params: { include_replies: false }
      });
      setComments(response.data.comments || []);
    } catch (err) {
      console.error('Failed to fetch comments:', err);
      setError('Failed to load comments');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitComment = async () => {
    if (!newComment.trim()) return;

    setSubmitting(true);
    try {
      await api.post(`/api/v1/dashboards/${dashboardId}/comments`, {
        content: newComment,
        comment_type: commentType
      });

      setNewComment('');
      setCommentType('general');
      fetchComments();
    } catch (err) {
      console.error('Failed to add comment:', err);
      setError('Failed to add comment');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitReply = async (parentId) => {
    if (!replyText.trim()) return;

    setSubmitting(true);
    try {
      await api.post(`/api/v1/comments/${parentId}/reply`, {
        content: replyText
      });

      setReplyingTo(null);
      setReplyText('');
      fetchComments();
      // Expand the thread to show the new reply
      setExpandedThreads(prev => ({ ...prev, [parentId]: true }));
    } catch (err) {
      console.error('Failed to add reply:', err);
      setError('Failed to add reply');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateComment = async (commentId) => {
    if (!editText.trim()) return;

    try {
      await api.put(`/api/v1/comments/${commentId}`, {
        content: editText
      });

      setEditingId(null);
      setEditText('');
      fetchComments();
    } catch (err) {
      console.error('Failed to update comment:', err);
      setError('Failed to update comment');
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await api.delete(`/api/v1/comments/${commentId}`);
      fetchComments();
    } catch (err) {
      console.error('Failed to delete comment:', err);
      setError('Failed to delete comment');
    }
    setMenuAnchor(null);
  };

  const handleMenuOpen = (event, commentId) => {
    setMenuAnchor(event.currentTarget);
    setMenuCommentId(commentId);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setMenuCommentId(null);
  };

  const startEdit = (comment) => {
    setEditingId(comment.id);
    setEditText(comment.content);
    handleMenuClose();
  };

  const toggleThread = async (commentId) => {
    const isExpanded = expandedThreads[commentId];

    if (!isExpanded) {
      // Fetch replies when expanding
      try {
        const response = await api.get(`/api/v1/comments/${commentId}/replies`);
        setComments(prev => prev.map(c =>
          c.id === commentId ? { ...c, replies: response.data } : c
        ));
      } catch (err) {
        console.error('Failed to fetch replies:', err);
      }
    }

    setExpandedThreads(prev => ({
      ...prev,
      [commentId]: !isExpanded
    }));
  };

  const getTypeInfo = (type) => {
    return COMMENT_TYPES.find(t => t.value === type) || COMMENT_TYPES[0];
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;

    return date.toLocaleDateString();
  };

  const renderComment = (comment, isReply = false) => {
    const typeInfo = getTypeInfo(comment.comment_type);
    const isOwn = comment.author_id === currentUserId;
    const isEditing = editingId === comment.id;

    return (
      <ListItem
        key={comment.id}
        alignItems="flex-start"
        sx={{
          flexDirection: 'column',
          pl: isReply ? 6 : 2,
          pr: 2,
          py: 1.5,
          bgcolor: isReply ? 'action.hover' : 'transparent'
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 1 }}>
          <Avatar sx={{ width: 32, height: 32, mr: 1 }}>
            {comment.author_name?.[0]?.toUpperCase() || 'U'}
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="subtitle2">
              {comment.author_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDate(comment.created_at)}
              {comment.is_edited && ' (edited)'}
            </Typography>
          </Box>
          <Chip
            label={typeInfo.label}
            size="small"
            color={typeInfo.color}
            icon={typeInfo.icon}
            sx={{ height: 22, fontSize: '0.7rem' }}
          />
          {isOwn && (
            <IconButton size="small" onClick={(e) => handleMenuOpen(e, comment.id)}>
              <MoreIcon fontSize="small" />
            </IconButton>
          )}
        </Box>

        {/* Content */}
        {isEditing ? (
          <Box sx={{ width: '100%', mb: 1 }}>
            <TextField
              fullWidth
              multiline
              size="small"
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              autoFocus
            />
            <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
              <Button
                size="small"
                variant="contained"
                onClick={() => handleUpdateComment(comment.id)}
              >
                Save
              </Button>
              <Button
                size="small"
                onClick={() => setEditingId(null)}
              >
                Cancel
              </Button>
            </Box>
          </Box>
        ) : (
          <Typography variant="body2" sx={{ width: '100%', mb: 1 }}>
            {comment.content}
          </Typography>
        )}

        {/* Actions */}
        {!isReply && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button
              size="small"
              startIcon={<ReplyIcon />}
              onClick={() => setReplyingTo(comment.id)}
            >
              Reply
            </Button>
            {comment.reply_count > 0 && (
              <Button
                size="small"
                startIcon={expandedThreads[comment.id] ? <CollapseIcon /> : <ExpandIcon />}
                onClick={() => toggleThread(comment.id)}
              >
                {comment.reply_count} {comment.reply_count === 1 ? 'reply' : 'replies'}
              </Button>
            )}
          </Box>
        )}

        {/* Reply input */}
        {replyingTo === comment.id && (
          <Box sx={{ width: '100%', mt: 1, pl: 4 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Write a reply..."
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              multiline
              maxRows={3}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      onClick={() => handleSubmitReply(comment.id)}
                      disabled={!replyText.trim() || submitting}
                    >
                      <SendIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                )
              }}
            />
            <Button
              size="small"
              onClick={() => {
                setReplyingTo(null);
                setReplyText('');
              }}
              sx={{ mt: 0.5 }}
            >
              Cancel
            </Button>
          </Box>
        )}

        {/* Replies */}
        <Collapse in={expandedThreads[comment.id]} sx={{ width: '100%' }}>
          {comment.replies?.map(reply => renderComment(reply, true))}
        </Collapse>
      </ListItem>
    );
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { width: { xs: '100%', sm: 400 } }
      }}
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CommentIcon color="primary" />
              <Typography variant="h6">Comments</Typography>
              <Chip label={comments.length} size="small" />
            </Box>
            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Error alert */}
        {error && (
          <Alert severity="error" onClose={() => setError(null)} sx={{ m: 2 }}>
            {error}
          </Alert>
        )}

        {/* Comments list */}
        <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : comments.length > 0 ? (
            <List disablePadding>
              {comments.map(comment => renderComment(comment))}
            </List>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CommentIcon sx={{ fontSize: 48, color: 'action.disabled', mb: 1 }} />
              <Typography color="text.secondary">
                No comments yet. Start the discussion!
              </Typography>
            </Box>
          )}
        </Box>

        {/* New comment input */}
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          {/* Comment type selector */}
          <Box sx={{ display: 'flex', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
            {COMMENT_TYPES.map(type => (
              <Chip
                key={type.value}
                label={type.label}
                size="small"
                icon={type.icon}
                color={commentType === type.value ? type.color : 'default'}
                variant={commentType === type.value ? 'filled' : 'outlined'}
                onClick={() => setCommentType(type.value)}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Box>

          {/* Input field */}
          <TextField
            ref={inputRef}
            fullWidth
            multiline
            maxRows={4}
            placeholder="Add a comment..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmitComment();
              }
            }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={handleSubmitComment}
                    disabled={!newComment.trim() || submitting}
                    color="primary"
                  >
                    {submitting ? <CircularProgress size={20} /> : <SendIcon />}
                  </IconButton>
                </InputAdornment>
              )
            }}
          />
        </Box>
      </Box>

      {/* Context menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          const comment = comments.find(c => c.id === menuCommentId);
          if (comment) startEdit(comment);
        }}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem
          onClick={() => handleDeleteComment(menuCommentId)}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
    </Drawer>
  );
};

export default CommentsPanel;
