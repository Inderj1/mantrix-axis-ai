import React, { useState, useEffect, useRef } from 'react';
import { useClerk } from '@clerk/clerk-react';
import {
  Box,
  AppBar,
  Toolbar,
  TextField,
  InputAdornment,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  Badge,
  Typography,
  Chip,
} from '@mui/material';
import {
  Search as SearchIcon,
  MicNone as MicIcon,
  Close as CloseIcon,
  TrendingUp as TrendingIcon,
  Dashboard as DashboardIcon,
  TableChart as TableIcon,
  InsertChart as ChartIcon,
  Person as PersonIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Help as HelpIcon,
  Logout as LogoutIcon,
  AutoAwesome as AIIcon,
  Menu as MenuIcon,
} from '@mui/icons-material';

const TopNavBar = ({ useSapTheme, setSelectedTab, drawerOpen, setDrawerOpen, user }) => {
  const { signOut } = useClerk();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [voiceActive, setVoiceActive] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const searchRef = useRef(null);

  // Sample autocomplete suggestions - will be dynamic from API
  const suggestions = [
    { type: 'recent', icon: <TrendingIcon />, text: 'Q4 Sales Dashboard', category: 'Dashboard' },
    { type: 'recent', icon: <TableIcon />, text: 'Revenue Analysis', category: 'Report' },
    { type: 'suggestion', icon: <ChartIcon />, text: 'Customer Churn Rate', category: 'Metric' },
    { type: 'suggestion', icon: <DashboardIcon />, text: 'Inventory Forecast', category: 'Analysis' },
    { type: 'ai', icon: <AIIcon />, text: 'What drove revenue growth last quarter?', category: 'AI Query' },
    { type: 'ai', icon: <AIIcon />, text: 'Show me top performing products', category: 'AI Query' },
  ];

  // Filter suggestions based on query
  const filteredSuggestions = searchQuery.length > 0
    ? suggestions.filter(s =>
        s.text.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : suggestions.slice(0, 4); // Show top 4 when empty

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSuggestions(false);
        setSearchFocused(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchFocus = () => {
    setSearchFocused(true);
    setShowSuggestions(true);
  };

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setShowSuggestions(true);
  };

  const handleSuggestionClick = (suggestion) => {
    setSearchQuery(suggestion.text);
    setShowSuggestions(false);
    // Navigate to chat for all queries
    setSelectedTab('chat');
  };

  const handleVoiceToggle = () => {
    setVoiceActive(!voiceActive);
    // Voice input implementation would go here
    if (!voiceActive) {
      console.log('Starting voice input...');
      // Simulated voice activation
      setTimeout(() => setVoiceActive(false), 3000);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setShowSuggestions(false);
  };

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    try {
      await signOut();
      // Clear session storage on logout
      sessionStorage.clear();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <AppBar
      position="static"
      elevation={1}
      sx={{
        bgcolor: useSapTheme ? 'background.paper' : 'background.default',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between', py: 0.5 }}>
        {/* Left: Hamburger Menu */}
        <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
          {!drawerOpen && (
            <IconButton onClick={() => setDrawerOpen(true)} size="large">
              <MenuIcon />
            </IconButton>
          )}
        </Box>

        {/* Right: Actions */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 200, justifyContent: 'flex-end' }}>
          {/* User Name */}
          {user && (
            <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500 }}>
              {user.fullName || user.firstName || user.emailAddresses?.[0]?.emailAddress || 'User'}
            </Typography>
          )}

          {/* User Profile */}
          <IconButton onClick={handleProfileMenuOpen} size="small">
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
              <PersonIcon sx={{ fontSize: 20 }} />
            </Avatar>
          </IconButton>

          {/* Profile Menu */}
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleProfileMenuClose}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            PaperProps={{
              sx: { width: 240, mt: 1 },
            }}
          >
            <MenuItem>
              <ListItemIcon>
                <PersonIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Profile</ListItemText>
            </MenuItem>
            <MenuItem>
              <ListItemIcon>
                <SettingsIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Settings</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Logout</ListItemText>
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopNavBar;
