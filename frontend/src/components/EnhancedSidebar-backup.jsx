import React, { useState } from 'react';
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Divider,
  Stack,
  Badge,
  Chip,
  Tooltip,
  Avatar,
  Collapse,
} from '@mui/material';
import {
  ForumOutlined as ForumIcon,
  ChevronLeft as ChevronLeftIcon,
  Menu as MenuIcon,
  MenuOpen as MenuOpenIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Search as SearchIcon,
  Explore as DataExplorerIcon,
  Bookmark as BookmarkIcon,
  Insights as InsightsIcon,
  Notifications as NotificationsIcon,
  Visibility as VisibilityIcon,
  Dashboard as DashboardIcon,
  Share as ShareIcon,
  Star as StarIcon,
  Storage as StorageIcon,
  AccountTree as AccountTreeIcon,
  Folder as FolderIcon,
  AutoAwesome as AutoAwesomeIcon,
  ModelTraining as ModelTrainingIcon,
  Assessment as AssessmentIcon,
  Schedule as ScheduleIcon,
  History as HistoryIcon,
  People as PeopleIcon,
  Comment as CommentIcon,
  AdminPanelSettings as AdminIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Home as HomeIcon,
} from '@mui/icons-material';

const EnhancedSidebar = ({
  drawerOpen,
  setDrawerOpen,
  selectedTab,
  setSelectedTab,
  apiHealth,
  useSapTheme,
}) => {
  const [expandedSections, setExpandedSections] = useState({
    search: false,
    insights: false,
    dashboards: false,
    data: false,
    ai: false,
    reports: false,
    collab: false,
    admin: false,
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const menuItems = [
    // Main tiles (always visible)
    {
      id: 0,
      icon: <HomeIcon />,
      primary: 'Home',
      secondary: 'Dashboard Overview',
      color: '#2196F3',
      isMainTile: true,
    },

    // Search & Explore - Expandable
    {
      id: 'search',
      icon: <SearchIcon />,
      primary: 'Search & Explore',
      secondary: '3 modules',
      color: '#4CAF50',
      isExpandable: true,
      sectionKey: 'search',
      subItems: [
        { id: 1, icon: <SearchIcon />, primary: 'Natural Language Search', color: '#4CAF50' },
        { id: 2, icon: <DataExplorerIcon />, primary: 'Data Explorer', color: '#FF9800' },
        { id: 3, icon: <BookmarkIcon />, primary: 'Saved Searches', color: '#9C27B0' },
      ],
    },

    // Insights & Analytics - Expandable
    {
      id: 'insights',
      icon: <InsightsIcon />,
      primary: 'Insights & Analytics',
      secondary: '3 modules',
      color: '#00BCD4',
      isExpandable: true,
      sectionKey: 'insights',
      subItems: [
        { id: 4, icon: <InsightsIcon />, primary: 'Automated Insights', color: '#00BCD4' },
        { id: 5, icon: <NotificationsIcon />, primary: 'Anomalies & Alerts', color: '#F44336' },
        { id: 6, icon: <VisibilityIcon />, primary: 'Watchlist', color: '#FF5722' },
      ],
    },

    // Dashboards - Expandable
    {
      id: 'dashboards',
      icon: <DashboardIcon />,
      primary: 'Dashboards',
      secondary: '3 modules',
      color: '#3F51B5',
      isExpandable: true,
      sectionKey: 'dashboards',
      subItems: [
        { id: 7, icon: <DashboardIcon />, primary: 'My Dashboards', color: '#3F51B5' },
        { id: 8, icon: <ShareIcon />, primary: 'Shared with Me', color: '#2196F3' },
        { id: 9, icon: <StarIcon />, primary: 'Favorites', color: '#FFC107' },
      ],
    },

    // Data Management - Expandable
    {
      id: 'data',
      icon: <StorageIcon />,
      primary: 'Data Management',
      secondary: '3 modules',
      color: '#607D8B',
      isExpandable: true,
      sectionKey: 'data',
      subItems: [
        { id: 10, icon: <StorageIcon />, primary: 'Data Sources', color: '#607D8B' },
        { id: 11, icon: <AccountTreeIcon />, primary: 'Business Views', color: '#795548' },
        { id: 12, icon: <FolderIcon />, primary: 'Data Catalog', color: '#009688' },
      ],
    },

    // AI & ML - Expandable
    {
      id: 'ai',
      icon: <AutoAwesomeIcon />,
      primary: 'AI & ML',
      secondary: '3 modules',
      color: '#E91E63',
      isExpandable: true,
      sectionKey: 'ai',
      subItems: [
        { id: 13, icon: <AutoAwesomeIcon />, primary: 'AutoML', color: '#E91E63' },
        { id: 14, icon: <ModelTrainingIcon />, primary: 'Predictive Models', color: '#9C27B0' },
        { id: 15, icon: <AssessmentIcon />, primary: 'Model Performance', color: '#673AB7' },
      ],
    },

    // Reports - Expandable
    {
      id: 'reports',
      icon: <ScheduleIcon />,
      primary: 'Reports',
      secondary: '2 modules',
      color: '#00BCD4',
      isExpandable: true,
      sectionKey: 'reports',
      subItems: [
        { id: 16, icon: <ScheduleIcon />, primary: 'Scheduled Reports', color: '#00BCD4' },
        { id: 17, icon: <HistoryIcon />, primary: 'Report History', color: '#009688' },
      ],
    },

    // Collaboration - Expandable
    {
      id: 'collab',
      icon: <PeopleIcon />,
      primary: 'Collaboration',
      secondary: '2 modules',
      color: '#4CAF50',
      isExpandable: true,
      sectionKey: 'collab',
      subItems: [
        { id: 18, icon: <PeopleIcon />, primary: 'Team Spaces', color: '#4CAF50' },
        { id: 19, icon: <CommentIcon />, primary: 'Comments', color: '#2196F3' },
      ],
    },

    // Admin - Expandable
    {
      id: 'admin',
      icon: <AdminIcon />,
      primary: 'Administration',
      secondary: '3 modules',
      color: '#F44336',
      isExpandable: true,
      sectionKey: 'admin',
      subItems: [
        { id: 20, icon: <AdminIcon />, primary: 'User Management', color: '#F44336' },
        { id: 21, icon: <SecurityIcon />, primary: 'Security & Audit', color: '#FF5722' },
        { id: 22, icon: <SettingsIcon />, primary: 'System Settings', color: '#607D8B' },
      ],
    },
  ];

  const sidebarBgColor = useSapTheme ? 'background.paper' : '#0f0f23';
  const sidebarTextColor = useSapTheme ? 'text.primary' : '#e0e0e0';
  const hoverBgColor = useSapTheme ? 'action.hover' : 'rgba(255,255,255,0.08)';

  return (
    <Drawer
      variant="permanent"
      open={drawerOpen}
      sx={{
        width: drawerOpen ? 240 : 64,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerOpen ? 240 : 64,
          boxSizing: 'border-box',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          bgcolor: sidebarBgColor,
          borderRight: 0,
          overflowX: 'hidden',
          boxShadow: useSapTheme ? '2px 0 8px rgba(0,0,0,0.1)' : '2px 0 12px rgba(0,0,0,0.5)',
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
          bgcolor: useSapTheme ? 'background.paper' : 'background.paper',
          borderBottom: '1px solid',
          borderColor: useSapTheme ? 'divider' : 'rgba(255,255,255,0.1)',
          position: 'relative',
        }}
      >
        {drawerOpen ? (
          <>
            {/* Logo - Left aligned */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-start',
                flex: 1,
              }}
            >
              <Box
                component="img"
                src="/mantra9.png"
                alt="Mantra9"
                sx={{
                  height: 40,
                  width: 'auto',
                  objectFit: 'contain',
                }}
              />
            </Box>

            {/* Hamburger Menu Button */}
            <IconButton
              onClick={() => setDrawerOpen(!drawerOpen)}
              size="small"
              sx={{
                color: useSapTheme ? 'text.primary' : 'text.primary',
              }}
            >
              <MenuOpenIcon />
            </IconButton>
          </>
        ) : (
          /* Centered Menu Button when collapsed */
          <Box sx={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
            <IconButton
              onClick={() => setDrawerOpen(!drawerOpen)}
              size="small"
              sx={{
                color: useSapTheme ? 'text.primary' : 'text.primary',
              }}
            >
              <MenuIcon />
            </IconButton>
          </Box>
        )}
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', py: 1.5 }}>
        <List sx={{ px: 0.5, py: 0 }}>
          {menuItems.map((item) => (
            <Box key={item.id}>
              {/* Main Tile */}
              {(item.isMainTile || item.isExpandable) && (
                <Tooltip
                  key={item.id}
                  title={!drawerOpen ? item.primary : item.disabled ? 'Coming Soon' : ''}
                  placement="right"
                >
                  <ListItemButton
                    selected={selectedTab === item.id}
                    onClick={() => !item.disabled && setSelectedTab(item.id)}
                    disabled={item.disabled}
                    sx={{
                      borderRadius: 2,
                      mb: 0.25,
                      mx: 0.25,
                      minHeight: 36,
                      transition: 'all 0.2s',
                      color: useSapTheme ? 'inherit' : sidebarTextColor,
                      position: 'relative',
                      overflow: 'hidden',
                      opacity: item.disabled ? 0.5 : 1,
                      cursor: item.disabled ? 'not-allowed' : 'pointer',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        left: 0,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        width: 3,
                        height: '70%',
                        bgcolor: item.color,
                        borderRadius: '0 2px 2px 0',
                        opacity: 0,
                        transition: 'opacity 0.2s',
                      },
                      '&:hover': {
                        bgcolor: hoverBgColor,
                        transform: drawerOpen ? 'translateX(4px)' : 'none',
                        '&::before': {
                          opacity: 0.5,
                        },
                      },
                      '&.Mui-selected': {
                        bgcolor: useSapTheme
                          ? 'primary.main'
                          : `${item.color}20`,
                        color: useSapTheme ? 'white' : 'white',
                        '&::before': {
                          opacity: 1,
                        },
                        '&:hover': {
                          bgcolor: useSapTheme
                            ? 'primary.dark'
                            : `${item.color}30`,
                        },
                        '& .MuiListItemIcon-root': {
                          color: useSapTheme ? 'white' : item.color,
                        },
                      },
                    }}
                  >
                    <ListItemIcon
                      sx={{
                        minWidth: drawerOpen ? 36 : 'auto',
                        color: 'inherit',
                      }}
                    >
                      <Box
                        sx={{
                          width: 28,
                          height: 28,
                          borderRadius: 1.5,
                          bgcolor:
                            selectedTab === item.id
                              ? 'transparent'
                              : useSapTheme
                              ? `${item.color}15`
                              : `${item.color}20`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'all 0.2s',
                          position: 'relative',
                        }}
                      >
                        {item.badge && !drawerOpen ? (
                          <Badge
                            badgeContent={item.badge}
                            color="primary"
                            sx={{
                              '& .MuiBadge-badge': {
                                fontSize: '0.6rem',
                                height: 16,
                                minWidth: 16,
                                top: -4,
                                right: -4,
                              },
                            }}
                          >
                            {item.icon}
                          </Badge>
                        ) : (
                          item.icon
                        )}
                        {item.status && drawerOpen && (
                          <DotIcon
                            sx={{
                              position: 'absolute',
                              top: 2,
                              right: 2,
                              fontSize: 10,
                              color: item.status === 'new' ? '#4CAF50' : 
                                     item.status === 'coming-soon' ? '#FF9800' : 
                                     '#4CAF50',
                            }}
                          />
                        )}
                      </Box>
                    </ListItemIcon>
                    {drawerOpen && (
                      <ListItemText
                        primary={
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={1}
                          >
                            <Typography variant="body2" fontWeight={500}>
                              {item.primary}
                            </Typography>
                            {item.badge && (
                              <Chip
                                label={item.badge}
                                size="small"
                                sx={{
                                  height: 20,
                                  fontSize: '0.65rem',
                                  bgcolor: useSapTheme
                                    ? 'primary.light'
                                    : item.color,
                                  color: 'white',
                                }}
                              />
                            )}
                            {item.status === 'coming-soon' && (
                              <Chip
                                label="Soon"
                                size="small"
                                sx={{
                                  height: 18,
                                  fontSize: '0.6rem',
                                  bgcolor: 'rgba(255, 152, 0, 0.2)',
                                  color: '#FF9800',
                                  border: '1px solid #FF9800',
                                }}
                              />
                            )}
                            {item.status === 'new' && (
                              <Chip
                                label="New"
                                size="small"
                                sx={{
                                  height: 18,
                                  fontSize: '0.6rem',
                                  bgcolor: 'rgba(76, 175, 80, 0.2)',
                                  color: '#4CAF50',
                                  border: '1px solid #4CAF50',
                                }}
                              />
                            )}
                          </Stack>
                        }
                        secondary={null}
                        primaryTypographyProps={{ fontWeight: 500 }}
                        secondaryTypographyProps={{
                          sx: {
                            color: useSapTheme
                              ? 'text.secondary'
                              : 'rgba(255,255,255,0.5)',
                            fontSize: '0.7rem',
                            display: 'none',
                          },
                        }}
                      />
                    )}
                  </ListItemButton>
                </Tooltip>
              ))}
            </List>

            {sectionIndex < menuItems.length - 1 && (
              <Divider
                sx={{
                  my: 2,
                  mx: 2,
                  borderColor: useSapTheme
                    ? 'divider'
                    : 'rgba(255,255,255,0.08)',
                }}
              />
            )}
          </Box>
        ))}
      </Box>
    </Drawer>
  );
};

export default EnhancedSidebar;