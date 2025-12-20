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
  TextField,
  InputAdornment,
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
  Search as SearchIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import AuthButton from './AuthButton';
import QueryHistoryDropdown from './QueryHistoryDropdown';
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
  const [searchQuery, setSearchQuery] = useState('');
  const { token } = useAuth();

  // Get conversation store
  const {
    conversations,
    conversationId: currentConversationId,
    loadingConversations,
    isInitializing,
    loadConversation,
    createNewConversation,
    toggleStar,
    deleteConversation,
  } = useConversationStore();

  // Filter conversations by search query
  const filteredConversations = searchQuery.trim()
    ? conversations.filter(c =>
        (c.title || 'Untitled').toLowerCase().includes(searchQuery.toLowerCase())
      )
    : conversations;

  // Derive starred conversations (from filtered)
  const starredConversations = filteredConversations.filter(c => c.metadata?.starred);

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

  // Format relative time for conversation previews
  const formatRelativeTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Filter out starred and group remaining by date (from filtered conversations)
  const nonStarredConversations = filteredConversations.filter(c => !c.metadata?.starred);

  const groupedConversations = nonStarredConversations.reduce((groups, conv) => {
    const group = getDateGroup(conv.updated_at || conv.updatedAt);
    if (!groups[group]) groups[group] = [];
    groups[group].push(conv);
    return groups;
  }, {});

  const dateOrder = ['Today', 'Yesterday', 'This Week', 'This Month', 'Older'];

  // Light sidebar colors
  const sidebarColors = {
    bg: '#ffffff',
    bgHover: '#f4f6f9',
    bgActive: '#e8f4fd',
    textPrimary: '#032D60',
    textSecondary: '#706e6b',
    accent: '#0176D3',
    divider: '#e5e5e5',
  };

  const drawer = (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: sidebarColors.bg,
      borderRight: `1px solid ${sidebarColors.divider}`,
      transition: 'width 0.3s ease',
    }}>
      {/* Logo Section */}
      <Box sx={{
        p: collapsed ? 1.5 : 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        gap: collapsed ? 0 : 1.5,
        borderBottom: `1px solid ${sidebarColors.divider}`,
        minHeight: 64,
      }}>
        <IconButton
          onClick={handleCollapsedToggle}
          size="small"
          sx={{
            color: sidebarColors.textSecondary,
            p: 0.5,
            '&:hover': {
              color: sidebarColors.accent,
              bgcolor: sidebarColors.bgHover,
            },
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
            startIcon={isInitializing ? <CircularProgress size={16} color="inherit" /> : <AddIcon />}
            onClick={handleNewChat}
            disabled={isInitializing}
            sx={{
              bgcolor: sidebarColors.accent,
              color: 'white',
              textTransform: 'none',
              borderRadius: '8px',
              py: 1,
              fontSize: '0.875rem',
              fontWeight: 600,
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              '&:hover': {
                bgcolor: '#014486',
              },
              '&.Mui-disabled': {
                bgcolor: '#e5e5e5',
                color: '#9ca3af',
              },
            }}
          >
            {isInitializing ? 'Loading...' : 'New Chat'}
          </Button>
        </Box>
      ) : (
        <Box sx={{ p: 1.5, display: 'flex', justifyContent: 'center' }}>
          <Tooltip title={isInitializing ? 'Loading...' : 'New Chat'} placement="right" arrow>
            <span>
              <IconButton
                onClick={handleNewChat}
                disabled={isInitializing}
                sx={{
                  bgcolor: sidebarColors.accent,
                  color: 'white',
                  '&:hover': { bgcolor: '#014486' },
                  '&.Mui-disabled': { bgcolor: '#e5e5e5', color: '#9ca3af' },
                }}
              >
                {isInitializing ? <CircularProgress size={20} color="inherit" /> : <AddIcon />}
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      )}

      {/* Main Menu Items */}
      <List sx={{ px: collapsed ? 0.5 : 1, py: 1 }}>
        {menuItems.map((item, index) => {
          const iconColors = ['#0176D3', '#2E844A']; // Blue, Green
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? item.text : ''} placement="right" arrow>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => {
                    navigate(item.path);
                    if (isMobile) setMobileOpen(false);
                  }}
                  sx={{
                    borderRadius: '8px',
                    py: 1,
                    px: collapsed ? 1 : 1.5,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    '&.Mui-selected': {
                      bgcolor: sidebarColors.bgActive,
                      '&:hover': { bgcolor: sidebarColors.bgActive },
                    },
                    '&:hover': {
                      bgcolor: sidebarColors.bgHover,
                    },
                  }}
                >
                  <ListItemIcon sx={{
                    minWidth: collapsed ? 0 : 36,
                    color: iconColors[index % iconColors.length],
                  }}>
                    {item.icon}
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText
                      primary={item.text}
                      primaryTypographyProps={{
                        fontSize: '0.875rem',
                        fontWeight: location.pathname === item.path ? 600 : 400,
                        color: sidebarColors.textPrimary,
                      }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          );
        })}
      </List>

      {/* Search Conversations */}
      {!collapsed && (
        <Box sx={{ px: 1.5, py: 1 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ fontSize: 18, color: sidebarColors.textSecondary }} />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={() => setSearchQuery('')}
                    sx={{ p: 0.25, color: sidebarColors.textSecondary }}
                  >
                    <ClearIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </InputAdornment>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '8px',
                bgcolor: sidebarColors.bgHover,
                fontSize: '0.85rem',
                '& fieldset': { borderColor: 'transparent' },
                '&:hover fieldset': { borderColor: sidebarColors.divider },
                '&.Mui-focused fieldset': { borderColor: sidebarColors.accent, borderWidth: 1 },
                '&.Mui-focused': { bgcolor: '#fff' },
              },
              '& .MuiInputBase-input': {
                py: 0.75,
                color: sidebarColors.textPrimary,
                '&::placeholder': { color: sidebarColors.textSecondary, opacity: 1 },
              },
            }}
          />
          {searchQuery && (
            <Typography variant="caption" sx={{ color: sidebarColors.textSecondary, mt: 0.5, display: 'block', px: 0.5 }}>
              {filteredConversations.length} result{filteredConversations.length !== 1 ? 's' : ''}
            </Typography>
          )}
        </Box>
      )}

      {/* Starred Chats Section */}
      {!collapsed && starredConversations.length > 0 && (
        <>
          <Box sx={{ px: 2, pt: 2, pb: 0.5 }}>
            <Typography sx={{
              textTransform: 'uppercase',
              color: '#FE9339',
              fontWeight: 700,
              fontSize: '0.65rem',
              letterSpacing: '1px',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}>
              <StarIcon sx={{ fontSize: 12, color: '#FE9339' }} /> Starred
            </Typography>
          </Box>
          <List sx={{ px: 1, py: 0, maxHeight: 180, overflowY: 'auto' }}>
            {starredConversations.map((conv) => {
              const convId = conv.conversation_id || conv.conversationId;
              const isActive = currentConversationId === convId;
              const isHovered = hoveredConvId === convId;
              const relativeTime = formatRelativeTime(conv.updated_at || conv.updatedAt);
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
                      borderRadius: '8px',
                      py: 0.75,
                      px: 1,
                      minHeight: 40,
                      borderLeft: '3px solid #FE9339',
                      '&.Mui-selected': { bgcolor: sidebarColors.bgActive },
                      '&:hover': { bgcolor: sidebarColors.bgHover },
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Typography sx={{
                          fontSize: '0.8rem',
                          fontWeight: isActive ? 600 : 400,
                          color: sidebarColors.textPrimary,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          flex: 1,
                        }}>
                          {conv.title || 'Untitled'}
                        </Typography>
                        {!isHovered && relativeTime && (
                          <Typography sx={{ fontSize: '0.65rem', color: sidebarColors.textSecondary, ml: 1, flexShrink: 0 }}>
                            {relativeTime}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                    {isHovered && (
                      <Box sx={{ display: 'flex', ml: 0.5 }}>
                        <IconButton size="small" onClick={(e) => handleToggleStar(e, convId)} sx={{ p: 0.25, color: '#FE9339' }}>
                          <StarIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                        <IconButton size="small" onClick={(e) => handleDeleteConversation(e, convId)} sx={{ p: 0.25, color: sidebarColors.textSecondary, '&:hover': { color: '#ef4444' } }}>
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
              <CircularProgress size={20} sx={{ color: sidebarColors.accent }} />
            </Box>
          ) : nonStarredConversations.length === 0 ? (
            <Box sx={{ px: 2, py: 2 }}>
              <Typography sx={{ fontSize: '0.85rem', color: sidebarColors.textSecondary }}>
                No conversations yet
              </Typography>
            </Box>
          ) : (
            dateOrder.map((group) => {
              const convs = groupedConversations[group];
              if (!convs || convs.length === 0) return null;
              return (
                <Box key={group}>
                  <Box sx={{ px: 2, pt: 1.5, pb: 0.5 }}>
                    <Typography sx={{
                      textTransform: 'uppercase',
                      color: sidebarColors.textSecondary,
                      fontWeight: 700,
                      fontSize: '0.65rem',
                      letterSpacing: '1px',
                    }}>
                      {group}
                    </Typography>
                  </Box>
                  <List sx={{ px: 1, py: 0 }}>
                    {convs.map((conv) => {
                      const convId = conv.conversation_id || conv.conversationId;
                      const isActive = currentConversationId === convId;
                      const isHovered = hoveredConvId === convId;
                      const relativeTime = formatRelativeTime(conv.updated_at || conv.updatedAt);
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
                              borderRadius: '8px',
                              py: 0.75,
                              px: 1,
                              minHeight: 40,
                              '&.Mui-selected': { bgcolor: sidebarColors.bgActive },
                              '&:hover': { bgcolor: sidebarColors.bgHover },
                            }}
                          >
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <Typography sx={{
                                  fontSize: '0.8rem',
                                  fontWeight: isActive ? 600 : 400,
                                  color: sidebarColors.textPrimary,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  flex: 1,
                                }}>
                                  {conv.title || 'Untitled'}
                                </Typography>
                                {!isHovered && relativeTime && (
                                  <Typography sx={{ fontSize: '0.65rem', color: sidebarColors.textSecondary, ml: 1, flexShrink: 0 }}>
                                    {relativeTime}
                                  </Typography>
                                )}
                              </Box>
                            </Box>
                            {isHovered && (
                              <Box sx={{ display: 'flex', ml: 0.5 }}>
                                <IconButton size="small" onClick={(e) => handleToggleStar(e, convId)} sx={{ p: 0.25, color: sidebarColors.textSecondary, '&:hover': { color: '#FE9339' } }}>
                                  <StarBorderIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                                <IconButton size="small" onClick={(e) => handleDeleteConversation(e, convId)} sx={{ p: 0.25, color: sidebarColors.textSecondary, '&:hover': { color: '#ef4444' } }}>
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

      {/* Spacer to push bottom items down - only when sidebar is collapsed */}
      {collapsed && <Box sx={{ flexGrow: 1 }} />}

      {/* Bottom Menu Items */}
      <Divider sx={{ borderColor: sidebarColors.divider }} />
      <List sx={{ px: collapsed ? 0.5 : 1, py: 1 }}>
        {bottomMenuItems.map((item, index) => {
          const iconColors = ['#BA01FF', '#FF5D2D']; // Purple, Red-orange
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? item.text : ''} placement="right" arrow>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => {
                    navigate(item.path);
                    if (isMobile) setMobileOpen(false);
                  }}
                  sx={{
                    borderRadius: '8px',
                    py: 1,
                    px: collapsed ? 1 : 1.5,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    '&.Mui-selected': { bgcolor: sidebarColors.bgActive, '&:hover': { bgcolor: sidebarColors.bgActive } },
                    '&:hover': { bgcolor: sidebarColors.bgHover },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, color: iconColors[index % iconColors.length] }}>
                    {item.icon}
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText primary={item.text} primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: location.pathname === item.path ? 600 : 400, color: sidebarColors.textPrimary }} />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          );
        })}
        {isAdmin && (
          <>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? 'Database Connectors' : ''} placement="right" arrow>
                <ListItemButton
                  selected={location.pathname === '/database-config'}
                  onClick={() => { navigate('/database-config'); if (isMobile) setMobileOpen(false); }}
                  sx={{
                    borderRadius: '8px',
                    py: 1,
                    px: collapsed ? 1 : 1.5,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    '&.Mui-selected': { bgcolor: sidebarColors.bgActive, '&:hover': { bgcolor: sidebarColors.bgActive } },
                    '&:hover': { bgcolor: sidebarColors.bgHover },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, color: '#00A1E0' }}>
                    <DatabaseIcon />
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText primary="Database Connectors" primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: location.pathname === '/database-config' ? 600 : 400, color: sidebarColors.textPrimary }} />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? 'Admin Settings' : ''} placement="right" arrow>
                <ListItemButton
                  selected={location.pathname === '/admin/settings'}
                  onClick={() => { navigate('/admin/settings'); if (isMobile) setMobileOpen(false); }}
                  sx={{
                    borderRadius: '8px',
                    py: 1,
                    px: collapsed ? 1 : 1.5,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    '&.Mui-selected': { bgcolor: sidebarColors.bgActive, '&:hover': { bgcolor: sidebarColors.bgActive } },
                    '&:hover': { bgcolor: sidebarColors.bgHover },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, color: '#FF538A' }}>
                    <AdminIcon />
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText primary="Admin Settings" primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: location.pathname === '/admin/settings' ? 600 : 400, color: sidebarColors.textPrimary }} />
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
      {/* Top Header Bar with user profile */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${collapsed ? drawerWidthCollapsed : drawerWidth}px)` },
          ml: { sm: `${collapsed ? drawerWidthCollapsed : drawerWidth}px` },
          bgcolor: '#ffffff',
          borderBottom: '1px solid #e5e5e5',
          transition: 'width 0.3s ease, margin-left 0.3s ease',
        }}
      >
        <Toolbar sx={{ minHeight: '56px !important' }}>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{
              mr: 2,
              display: { sm: 'none' },
              color: '#032D60',
            }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }} />
          <QueryHistoryDropdown
            onViewResults={(query) => {
              // Navigate to chat - the conversation should be loaded automatically
              navigate('/chat');
              console.log('[Layout] View results for query:', query.executionId);
            }}
          />
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
              bgcolor: '#ffffff',
              borderRight: '1px solid #e5e5e5',
              boxShadow: 'none',
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
          p: 0,
          width: { sm: `calc(100% - ${collapsed ? drawerWidthCollapsed : drawerWidth}px)` },
          mt: '56px',
          bgcolor: '#f3f3f3',
          minHeight: 'calc(100vh - 56px)',
          transition: 'width 0.3s ease, margin-left 0.3s ease',
        }}
      >
        {children}
      </Box>
    </>
  );
}

export default Layout;