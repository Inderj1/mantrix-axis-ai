import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Divider,
  useTheme,
  useMediaQuery,
  Button,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Menu as MenuIcon,
  MenuOpen as MenuOpenIcon,
  Chat as ChatIcon,
  SmartToy as AgentIcon,
  Folder as FolderIcon,
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  Add as AddIcon,
  ControlCamera as ControlCenterIcon,
  Storage as DatabaseIcon,
  Dashboard as DashboardIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import AuthButton from './AuthButton';
import { useAuth } from '../contexts/AuthContext';
import { useConversationStore } from '../stores/conversationStore';

// Import images as modules for proper caching
import mantraLogo from '../assets/mantra9.png';

const drawerWidth = 240;
const drawerWidthCollapsed = 65;

const menuItems = [
  { text: 'Chats', icon: <ChatIcon />, path: '/chat' },
  { text: 'Dashboards', icon: <DashboardIcon />, path: '/dashboards' },
];

const bottomMenuItems = [
  { text: 'AI Persona', icon: <PersonIcon />, path: '/profile' },
  { text: 'Control Center', icon: <ControlCenterIcon />, path: '/control-center' },
];

function Layout({ children }) {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [hoveredConvId, setHoveredConvId] = useState(null);
  const { token } = useAuth();

  // Get conversation store
  const {
    conversations,
    conversationId: currentConversationId,
    loadingConversations,
    loadConversation,
    createNewConversation,
    toggleStar,
    deleteConversation,
  } = useConversationStore();

  // Derive starred conversations
  const starredConversations = conversations.filter(c => c.metadata?.starred);

  // Check if user is admin using Cognito groups from JWT token
  const isAdmin = React.useMemo(() => {
    if (!token) return false;
    try {
      const tokenPayload = JSON.parse(atob(token.split('.')[1]));
      return tokenPayload['cognito:groups']?.includes('Admins') || false;
    } catch {
      return false;
    }
  }, [token]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleCollapsedToggle = () => {
    setCollapsed(!collapsed);
  };

  const handleNewChat = async () => {
    console.log('handleNewChat called');
    try {
      await createNewConversation();
      navigate('/chat');
    } catch (error) {
      console.error('handleNewChat error:', error);
    }
  };

  const handleLoadConversation = async (convId) => {
    await loadConversation(convId);
    navigate('/chat');
  };

  const handleToggleStar = async (e, conversationId) => {
    e.stopPropagation();
    await toggleStar(conversationId);
  };

  const handleDeleteConversation = async (e, conversationId) => {
    e.stopPropagation();
    await deleteConversation(conversationId);
  };

  // Group conversations by date
  const getDateGroup = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return 'This Week';
    if (diffDays < 30) return 'This Month';
    return 'Older';
  };

  // Filter out starred and group remaining by date
  const nonStarredConversations = conversations.filter(c => !c.metadata?.starred);

  const groupedConversations = nonStarredConversations.reduce((groups, conv) => {
    const group = getDateGroup(conv.updated_at || conv.updatedAt);
    if (!groups[group]) groups[group] = [];
    groups[group].push(conv);
    return groups;
  }, {});

  const dateOrder = ['Today', 'Yesterday', 'This Week', 'This Month', 'Older'];

  const drawer = (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: '#fff',
      transition: 'width 0.3s ease',
    }}>
      {/* Logo Section with Hamburger */}
      <Box sx={{
        p: collapsed ? 1 : 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        gap: collapsed ? 0 : 1.5,
        borderBottom: '1px solid #e0e0e0',
        minHeight: 64,
      }}>
        <IconButton
          onClick={handleCollapsedToggle}
          size="small"
          sx={{
            color: '#6a6d70',
            p: 0.5,
          }}
        >
          {collapsed ? <MenuIcon /> : <MenuOpenIcon />}
        </IconButton>
        {!collapsed && (
          <Box
            component="img"
            src={mantraLogo}
            alt="CloudMantra"
            sx={{
              height: 32,
              objectFit: 'contain',
              flexShrink: 0,
            }}
          />
        )}
      </Box>

      {/* New Chat Button */}
      {!collapsed ? (
        <Box sx={{ p: 2 }}>
          <Button
            fullWidth
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleNewChat}
            sx={{
              bgcolor: '#0a6ed1',
              color: 'white',
              textTransform: 'none',
              borderRadius: 1.5,
              py: 1.2,
              fontSize: '0.9rem',
              fontWeight: 500,
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              '&:hover': {
                bgcolor: '#0854a0',
                boxShadow: '0 3px 6px rgba(0,0,0,0.15)',
              },
            }}
          >
            New chat
          </Button>
        </Box>
      ) : (
        <Box sx={{ p: 1, display: 'flex', justifyContent: 'center' }}>
          <Tooltip title="New chat" placement="right" arrow>
            <IconButton
              onClick={handleNewChat}
              sx={{
                bgcolor: '#0a6ed1',
                color: 'white',
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
      <List sx={{ px: collapsed ? 0.5 : 1.5, py: 0 }}>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
            <Tooltip title={collapsed ? item.text : ''} placement="right" arrow>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => {
                  navigate(item.path);
                  if (isMobile) {
                    setMobileOpen(false);
                  }
                }}
                sx={{
                  borderRadius: 1,
                  py: 1,
                  px: collapsed ? 1 : 1.5,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(10, 110, 209, 0.08)',
                    '&:hover': {
                      bgcolor: 'rgba(10, 110, 209, 0.12)',
                    },
                  },
                  '&:hover': {
                    bgcolor: 'rgba(0, 0, 0, 0.04)',
                  },
                }}
              >
                <ListItemIcon sx={{
                  minWidth: collapsed ? 0 : 36,
                  color: location.pathname === item.path ? '#0a6ed1' : '#6a6d70',
                }}>
                  {item.icon}
                </ListItemIcon>
                {!collapsed && (
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.9rem',
                      fontWeight: location.pathname === item.path ? 500 : 400,
                      color: location.pathname === item.path ? '#0a6ed1' : '#1A2332',
                    }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          </ListItem>
        ))}
      </List>

      {/* Starred Chats Section */}
      {!collapsed && starredConversations.length > 0 && (
        <>
          <Box sx={{ px: 2.5, pt: 2, pb: 0.5 }}>
            <Typography sx={{
              textTransform: 'uppercase',
              color: '#df6e0c',
              fontWeight: 600,
              fontSize: '0.7rem',
              letterSpacing: '0.5px',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}>
              <StarIcon sx={{ fontSize: 14 }} /> Starred
            </Typography>
          </Box>
          <List sx={{ px: 1.5, py: 0, maxHeight: 150, overflowY: 'auto' }}>
            {starredConversations.map((conv) => {
              const convId = conv.conversation_id || conv.conversationId;
              const isActive = currentConversationId === convId;
              const isHovered = hoveredConvId === convId;
              return (
                <ListItem
                  key={convId}
                  disablePadding
                  sx={{ mb: 0.25 }}
                  onMouseEnter={() => setHoveredConvId(convId)}
                  onMouseLeave={() => setHoveredConvId(null)}
                >
                  <ListItemButton
                    selected={isActive}
                    onClick={() => handleLoadConversation(convId)}
                    sx={{
                      borderRadius: 1,
                      py: 0.5,
                      px: 1,
                      minHeight: 32,
                      '&.Mui-selected': {
                        bgcolor: 'rgba(223, 110, 12, 0.08)',
                      },
                    }}
                  >
                    <ListItemText
                      primary={conv.title || 'Untitled'}
                      primaryTypographyProps={{
                        fontSize: '0.8rem',
                        noWrap: true,
                        color: isActive ? '#df6e0c' : '#1A2332',
                      }}
                    />
                    {isHovered && (
                      <Box sx={{ display: 'flex', ml: 0.5 }}>
                        <IconButton
                          size="small"
                          onClick={(e) => handleToggleStar(e, convId)}
                          sx={{ p: 0.25, color: '#df6e0c' }}
                        >
                          <StarIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => handleDeleteConversation(e, convId)}
                          sx={{ p: 0.25, color: '#999' }}
                        >
                          <DeleteIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                      </Box>
                    )}
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </>
      )}

      {/* Recent Chats Section */}
      {!collapsed && (
        <Box sx={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {loadingConversations ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={20} />
            </Box>
          ) : nonStarredConversations.length === 0 ? (
            <Box sx={{ px: 2.5, py: 2 }}>
              <Typography sx={{ fontSize: '0.85rem', color: '#5A6677' }}>
                No conversations yet
              </Typography>
            </Box>
          ) : (
            dateOrder.map((group) => {
              const convs = groupedConversations[group];
              if (!convs || convs.length === 0) return null;
              return (
                <Box key={group}>
                  <Box sx={{ px: 2.5, pt: 1.5, pb: 0.5 }}>
                    <Typography sx={{
                      textTransform: 'uppercase',
                      color: '#7A8699',
                      fontWeight: 600,
                      fontSize: '0.65rem',
                      letterSpacing: '0.5px',
                    }}>
                      {group}
                    </Typography>
                  </Box>
                  <List sx={{ px: 1.5, py: 0 }}>
                    {convs.map((conv) => {
                      const convId = conv.conversation_id || conv.conversationId;
                      const isActive = currentConversationId === convId;
                      const isHovered = hoveredConvId === convId;
                      return (
                        <ListItem
                          key={convId}
                          disablePadding
                          sx={{ mb: 0.25 }}
                          onMouseEnter={() => setHoveredConvId(convId)}
                          onMouseLeave={() => setHoveredConvId(null)}
                        >
                          <ListItemButton
                            selected={isActive}
                            onClick={() => handleLoadConversation(convId)}
                            sx={{
                              borderRadius: 1,
                              py: 0.5,
                              px: 1,
                              minHeight: 32,
                              '&.Mui-selected': {
                                bgcolor: 'rgba(10, 110, 209, 0.08)',
                              },
                            }}
                          >
                            <ListItemText
                              primary={conv.title || 'Untitled'}
                              primaryTypographyProps={{
                                fontSize: '0.8rem',
                                noWrap: true,
                                color: isActive ? '#0a6ed1' : '#1A2332',
                              }}
                            />
                            {isHovered && (
                              <Box sx={{ display: 'flex', ml: 0.5 }}>
                                <IconButton
                                  size="small"
                                  onClick={(e) => handleToggleStar(e, convId)}
                                  sx={{ p: 0.25, color: '#999' }}
                                >
                                  <StarBorderIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                                <IconButton
                                  size="small"
                                  onClick={(e) => handleDeleteConversation(e, convId)}
                                  sx={{ p: 0.25, color: '#999' }}
                                >
                                  <DeleteIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                              </Box>
                            )}
                          </ListItemButton>
                        </ListItem>
                      );
                    })}
                  </List>
                </Box>
              );
            })
          )}
        </Box>
      )}

      {/* Spacer to push bottom items down */}
      <Box sx={{ flexGrow: 1 }} />

      {/* Bottom Menu Items */}
      <Divider sx={{ borderColor: '#e0e0e0' }} />
      <List sx={{ px: collapsed ? 0.5 : 1.5, py: 1 }}>
        {bottomMenuItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
            <Tooltip title={collapsed ? item.text : ''} placement="right" arrow>
              <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => {
                navigate(item.path);
                if (isMobile) {
                  setMobileOpen(false);
                }
              }}
              sx={{
                borderRadius: 1,
                py: 1,
                px: collapsed ? 1 : 1.5,
                justifyContent: collapsed ? 'center' : 'flex-start',
                '&.Mui-selected': {
                  bgcolor: 'rgba(10, 110, 209, 0.08)',
                  '&:hover': {
                    bgcolor: 'rgba(10, 110, 209, 0.12)',
                  },
                },
                '&:hover': {
                  bgcolor: 'rgba(0, 0, 0, 0.04)',
                },
              }}
            >
              <ListItemIcon sx={{
                minWidth: collapsed ? 0 : 36,
                color: location.pathname === item.path ? '#0a6ed1' : '#6a6d70',
              }}>
                {item.icon}
              </ListItemIcon>
              {!collapsed && (
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    fontSize: '0.9rem',
                    fontWeight: location.pathname === item.path ? 500 : 400,
                    color: location.pathname === item.path ? '#0a6ed1' : '#1A2332',
                  }}
                />
              )}
            </ListItemButton>
            </Tooltip>
          </ListItem>
        ))}
        {isAdmin && (
          <>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? 'Database Connectors' : ''} placement="right" arrow>
                <ListItemButton
                  selected={location.pathname === '/database-config'}
                  onClick={() => {
                    navigate('/database-config');
                    if (isMobile) {
                      setMobileOpen(false);
                    }
                  }}
                  sx={{
                    borderRadius: 1,
                    py: 1,
                    px: collapsed ? 1 : 1.5,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    '&.Mui-selected': {
                      bgcolor: 'rgba(10, 110, 209, 0.08)',
                      '&:hover': {
                        bgcolor: 'rgba(10, 110, 209, 0.12)',
                      },
                    },
                    '&:hover': {
                      bgcolor: 'rgba(0, 0, 0, 0.04)',
                    },
                  }}
                >
                  <ListItemIcon sx={{
                    minWidth: collapsed ? 0 : 36,
                    color: location.pathname === '/database-config' ? '#0a6ed1' : '#6a6d70',
                  }}>
                    <DatabaseIcon />
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText
                      primary="Database Connectors"
                      primaryTypographyProps={{
                        fontSize: '0.9rem',
                        fontWeight: location.pathname === '/database-config' ? 500 : 400,
                        color: location.pathname === '/database-config' ? '#0a6ed1' : '#1A2332',
                      }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? 'Admin Settings' : ''} placement="right" arrow>
                <ListItemButton
                  selected={location.pathname === '/admin/settings'}
                  onClick={() => {
                    navigate('/admin/settings');
                    if (isMobile) {
                      setMobileOpen(false);
                    }
                  }}
                  sx={{
                    borderRadius: 1,
                    py: 1,
                    px: collapsed ? 1 : 1.5,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    '&.Mui-selected': {
                      bgcolor: 'rgba(10, 110, 209, 0.08)',
                      '&:hover': {
                        bgcolor: 'rgba(10, 110, 209, 0.12)',
                      },
                    },
                    '&:hover': {
                      bgcolor: 'rgba(0, 0, 0, 0.04)',
                    },
                  }}
                >
                  <ListItemIcon sx={{
                    minWidth: collapsed ? 0 : 36,
                    color: location.pathname === '/admin/settings' ? '#0a6ed1' : '#6a6d70',
                  }}>
                    <AdminIcon />
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText
                      primary="Admin Settings"
                      primaryTypographyProps={{
                        fontSize: '0.9rem',
                        fontWeight: location.pathname === '/admin/settings' ? 500 : 400,
                        color: location.pathname === '/admin/settings' ? '#0a6ed1' : '#1A2332',
                      }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          </>
        )}
      </List>
    </Box>
  );

  return (
    <>
      {/* Transparent/invisible header for mobile menu button and auth */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${collapsed ? drawerWidthCollapsed : drawerWidth}px)` },
          ml: { sm: `${collapsed ? drawerWidthCollapsed : drawerWidth}px` },
          bgcolor: 'transparent',
          boxShadow: 'none',
          transition: 'width 0.3s ease, margin-left 0.3s ease',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{
              mr: 2,
              display: { sm: 'none' },
              color: 'text.primary',
            }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }} />
          <AuthButton />
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{
          width: { sm: collapsed ? drawerWidthCollapsed : drawerWidth },
          flexShrink: { sm: 0 },
          transition: 'width 0.3s ease',
        }}
      >
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? mobileOpen : true}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: isMobile ? drawerWidth : (collapsed ? drawerWidthCollapsed : drawerWidth),
              bgcolor: '#fff',
              borderRight: '1px solid #e0e0e0',
              boxShadow: '2px 0 4px rgba(0,0,0,0.05)',
              transition: 'width 0.3s ease',
            },
          }}
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${collapsed ? drawerWidthCollapsed : drawerWidth}px)` },
          mt: 8,
          bgcolor: '#f7f7f7',
          minHeight: '100vh',
          transition: 'width 0.3s ease, margin-left 0.3s ease',
        }}
      >
        {children}
      </Box>
    </>
  );
}

export default Layout;