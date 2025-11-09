import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Tooltip,
  Typography,
  Divider,
  Button,
  CircularProgress,
} from '@mui/material';
import {
  Menu as MenuIcon,
  MenuOpen as MenuOpenIcon,
  AdminPanelSettings as AdminIcon,
  Chat as ChatIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  Delete as DeleteIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  SmartToy as AgentIcon,
  Person as PersonIcon,
} from '@mui/icons-material';

const EnhancedSidebar = ({
  drawerOpen,
  setDrawerOpen,
  selectedTab,
  setSelectedTab,
  useSapTheme,
  conversations = [],
  conversationId,
  onLoadConversation,
  onDeleteConversation,
  onNewChat,
  onOpenChatHistory,
  loadingConversations = false,
  starredConversations = [],
  onToggleStar,
}) => {
  // Get conversations without project and filter out duplicate "New Conversation" entries
  const conversationsWithoutProject = (() => {
    const filtered = conversations.filter(conv => !conv.project_id);

    // Find all "New Conversation" entries with only welcome messages (unused)
    const newConversations = filtered.filter(conv =>
      conv.title === 'New Conversation' &&
      (!conv.messages || conv.messages.length <= 1)
    );

    // If there are multiple unused "New Conversation" entries, keep only the most recent one
    if (newConversations.length > 1) {
      const mostRecentNew = newConversations[0]; // Already sorted by date
      const unusedNewIds = newConversations.slice(1).map(c => c.conversation_id || c.conversationId);

      return filtered.filter(conv =>
        !unusedNewIds.includes(conv.conversation_id || conv.conversationId)
      );
    }

    return filtered;
  })();

  const mainMenuItems = [
    {
      id: 'chat',
      icon: <ChatIcon />,
      primary: 'Chats',
      color: '#6a6d70',
    },
    {
      id: 'agent',
      icon: <AgentIcon />,
      primary: 'Agent Mode',
      color: '#6a6d70',
    },
    {
      id: 'content',
      icon: <FolderIcon />,
      primary: 'Projects',
      color: '#6a6d70',
    },
    {
      id: 'persona',
      icon: <PersonIcon />,
      primary: 'AI Persona',
      color: '#6a6d70',
    },
  ];

  const adminMenuItem = {
    id: 'admin',
    icon: <AdminIcon />,
    primary: 'Control Center',
    color: '#6a6d70',
  };

  return (
    <Drawer
      variant="permanent"
      open={drawerOpen}
      sx={{
        width: drawerOpen ? 240 : 0,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerOpen ? 240 : 0,
          boxSizing: 'border-box',
          transition: 'width 0.3s',
          bgcolor: useSapTheme ? 'background.paper' : '#0f0f23',
          borderRight: 0,
          overflowX: 'hidden',
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          minHeight: 64,
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        {drawerOpen ? (
          <>
            <Box component="img" src="/mantra9.png" alt="Mantra9" sx={{ height: 40 }} />
            <IconButton onClick={() => setDrawerOpen(false)} size="small">
              <MenuOpenIcon />
            </IconButton>
          </>
        ) : (
          <IconButton onClick={() => setDrawerOpen(true)} size="small">
            <MenuIcon />
          </IconButton>
        )}
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', py: 1 }}>
        {/* New Chat Button */}
        {drawerOpen && (
          <Box sx={{ px: 2, mb: 2 }}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => {
                setSelectedTab('chat');
                if (onNewChat) onNewChat();
              }}
              sx={{
                justifyContent: 'flex-start',
                borderRadius: '6px',
                py: 1.25,
                bgcolor: '#0a6ed1',
                color: '#ffffff',
                fontWeight: 500,
                textTransform: 'none',
                boxShadow: 'none',
                transition: 'all 0.2s ease',
                '&:hover': {
                  bgcolor: '#0854a0',
                  boxShadow: '0px 2px 6px rgba(0, 0, 0, 0.15)',
                },
              }}
            >
              New chat
            </Button>
          </Box>
        )}

        {!drawerOpen && (
          <Box sx={{ px: 1, mb: 2 }}>
            <Tooltip title="New chat" placement="right">
              <IconButton
                onClick={() => {
                  setSelectedTab('chat');
                  if (onNewChat) onNewChat();
                }}
                sx={{
                  width: '100%',
                  borderRadius: '6px',
                  bgcolor: '#0a6ed1',
                  color: '#ffffff',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: '#0854a0',
                  },
                }}
              >
                <AddIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}

        {/* Main Menu Items */}
        <List sx={{ px: 1 }}>
          {mainMenuItems.map((item) => (
            <Tooltip key={item.id} title={!drawerOpen ? item.primary : ''} placement="right">
              <ListItemButton
                selected={selectedTab === item.id}
                onClick={() => {
                  setSelectedTab(item.id);
                  if (item.id === 'chat' && onOpenChatHistory) {
                    onOpenChatHistory();
                  }
                }}
                sx={{
                  borderRadius: 2,
                  mb: 0.5,
                  minHeight: 44,
                  justifyContent: drawerOpen ? 'flex-start' : 'center',
                  px: drawerOpen ? 2 : 1.5,
                  bgcolor: 'transparent',
                  '&:hover': {
                    bgcolor: 'rgba(106, 109, 112, 0.1)',
                  },
                  '&.Mui-selected': {
                    bgcolor: 'rgba(106, 109, 112, 0.15)',
                    '&:hover': {
                      bgcolor: 'rgba(106, 109, 112, 0.2)',
                    },
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: drawerOpen ? 40 : 'auto',
                    color: item.color,
                    display: 'flex',
                    justifyContent: 'center',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                {drawerOpen && (
                  <ListItemText
                    primary={item.primary}
                    primaryTypographyProps={{
                      fontSize: '0.9rem',
                      fontWeight: selectedTab === item.id ? 500 : 400,
                      color: '#32363a',
                    }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          ))}
        </List>

        {/* Starred Section */}
        {drawerOpen && starredConversations.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ px: 2, mb: 1 }}>
              <Typography variant="caption" sx={{ color: '#6a6d70', fontWeight: 500, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Starred
              </Typography>
            </Box>

            {/* Starred Conversations List */}
            <Box sx={{ px: 1, mb: 2, maxHeight: '200px', overflowY: 'auto' }}>
              <List sx={{ py: 0 }}>
                {starredConversations.map((conv) => {
                  const isActive = (conv.conversation_id || conv.conversationId) === conversationId;
                  const displayTitle = conv.title || 'New Conversation';

                  return (
                    <ListItemButton
                      key={conv.conversation_id || conv.conversationId}
                      selected={isActive}
                      onClick={() => {
                        setSelectedTab('chat');
                        if (onLoadConversation) {
                          onLoadConversation(conv.conversation_id || conv.conversationId);
                        }
                      }}
                      sx={{
                        borderRadius: 2,
                        mb: 0.5,
                        px: 1.5,
                        py: 1,
                        bgcolor: 'transparent',
                        '&:hover': {
                          bgcolor: 'rgba(106, 109, 112, 0.1)',
                          '& .star-btn': {
                            opacity: 1,
                          },
                        },
                        '&.Mui-selected': {
                          bgcolor: 'rgba(106, 109, 112, 0.08)',
                          '&:hover': {
                            bgcolor: 'rgba(106, 109, 112, 0.12)',
                          },
                        },
                      }}
                    >
                      <Box sx={{ flex: 1, minWidth: 0, mr: 1 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontSize: '0.875rem',
                            fontWeight: isActive ? 500 : 400,
                            color: '#1A2332',
                            noWrap: true,
                          }}
                        >
                          {displayTitle}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        className="star-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onToggleStar) {
                            onToggleStar(conv.conversation_id || conv.conversationId);
                          }
                        }}
                        sx={{
                          p: 0.5,
                          color: '#df6e0c',
                          '&:hover': {
                            bgcolor: 'rgba(223, 110, 12, 0.1)',
                          },
                        }}
                      >
                        <StarIcon sx={{ fontSize: 16 }} />
                      </IconButton>
                    </ListItemButton>
                  );
                })}
              </List>
            </Box>
          </>
        )}

        {/* Recent Chats Section */}
        {drawerOpen && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ px: 2, mb: 1 }}>
              <Typography variant="caption" sx={{ color: '#6a6d70', fontWeight: 500, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Recent Chats
              </Typography>
            </Box>

            {/* Conversations List */}
            <Box sx={{ px: 1, flex: 1, overflowY: 'auto' }}>
              {loadingConversations ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                  <CircularProgress size={20} />
                </Box>
              ) : conversationsWithoutProject.length === 0 ? (
                <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 3, px: 2, fontSize: '0.85rem' }}>
                  No conversations yet
                </Typography>
              ) : (
                <List sx={{ py: 0 }}>
                  {conversationsWithoutProject
                    .slice(0, 10)
                    .map((conv) => {
                      const isActive = (conv.conversation_id || conv.conversationId) === conversationId;
                      const displayTitle = conv.title || 'New Conversation';
                      const isStarred = starredConversations.some(
                        starredConv => (starredConv.conversation_id || starredConv.conversationId) === (conv.conversation_id || conv.conversationId)
                      );

                      return (
                        <ListItemButton
                          key={conv.conversation_id || conv.conversationId}
                          selected={isActive}
                          onClick={() => {
                            setSelectedTab('chat');
                            if (onLoadConversation) {
                              onLoadConversation(conv.conversation_id || conv.conversationId);
                            }
                          }}
                          sx={{
                            borderRadius: 2,
                            mb: 0.5,
                            px: 1.5,
                            py: 1,
                            bgcolor: 'transparent',
                            '&:hover': {
                              bgcolor: 'rgba(106, 109, 112, 0.1)',
                              '& .action-btn': {
                                opacity: 1,
                              },
                            },
                            '&.Mui-selected': {
                              bgcolor: 'rgba(106, 109, 112, 0.08)',
                              '&:hover': {
                                bgcolor: 'rgba(106, 109, 112, 0.12)',
                              },
                            },
                          }}
                        >
                          <Box sx={{ flex: 1, minWidth: 0, mr: 1 }}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '0.875rem',
                                fontWeight: isActive ? 500 : 400,
                                color: '#1A2332',
                                noWrap: true,
                              }}
                            >
                              {displayTitle}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <IconButton
                              size="small"
                              className="action-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onToggleStar) {
                                  onToggleStar(conv.conversation_id || conv.conversationId);
                                }
                              }}
                              sx={{
                                opacity: isStarred ? 1 : 0,
                                transition: 'opacity 0.2s',
                                p: 0.5,
                                color: isStarred ? '#df6e0c' : '#6a6d70',
                                '&:hover': {
                                  bgcolor: 'rgba(223, 110, 12, 0.1)',
                                  color: '#df6e0c',
                                },
                              }}
                            >
                              {isStarred ? <StarIcon sx={{ fontSize: 16 }} /> : <StarBorderIcon sx={{ fontSize: 16 }} />}
                            </IconButton>
                            <IconButton
                              size="small"
                              className="action-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onDeleteConversation) {
                                  onDeleteConversation(conv.conversation_id || conv.conversationId);
                                }
                              }}
                              sx={{
                                opacity: 0,
                                transition: 'opacity 0.2s',
                                p: 0.5,
                                '&:hover': {
                                  bgcolor: 'rgba(187, 0, 0, 0.1)',
                                  color: '#bb0000',
                                },
                              }}
                            >
                              <DeleteIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Box>
                        </ListItemButton>
                      );
                    })}
                </List>
              )}
            </Box>
          </>
        )}

        {/* Admin Section at Bottom */}
        <Box sx={{ px: 1, pb: 1, borderTop: '1px solid', borderColor: 'divider', pt: 1 }}>
          <Tooltip title={!drawerOpen ? adminMenuItem.primary : ''} placement="right">
            <ListItemButton
              selected={selectedTab === adminMenuItem.id}
              onClick={() => setSelectedTab(adminMenuItem.id)}
              sx={{
                borderRadius: 2,
                minHeight: 44,
                justifyContent: drawerOpen ? 'flex-start' : 'center',
                px: drawerOpen ? 2 : 1.5,
                bgcolor: 'transparent',
                '&:hover': {
                  bgcolor: 'rgba(106, 109, 112, 0.1)',
                },
                '&.Mui-selected': {
                  bgcolor: 'rgba(106, 109, 112, 0.15)',
                  '&:hover': {
                    bgcolor: 'rgba(106, 109, 112, 0.2)',
                  },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: drawerOpen ? 40 : 'auto',
                  color: adminMenuItem.color,
                  display: 'flex',
                  justifyContent: 'center',
                }}
              >
                {adminMenuItem.icon}
              </ListItemIcon>
              {drawerOpen && (
                <ListItemText
                  primary={adminMenuItem.primary}
                  primaryTypographyProps={{
                    fontSize: '0.9rem',
                    fontWeight: selectedTab === adminMenuItem.id ? 500 : 400,
                    color: '#32363a',
                  }}
                />
              )}
            </ListItemButton>
          </Tooltip>
        </Box>
      </Box>
    </Drawer>
  );
};

export default EnhancedSidebar;
