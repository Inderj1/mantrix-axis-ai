import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
  Typography,
  Divider,
} from '@mui/material';
import {
  Login as LoginIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { clearCache } from '../config/queryClient';
import { clearNavigationState } from '../hooks/usePersistedState';

function AuthButton() {
  const navigate = useNavigate();
  const { user, isAuthenticated, loading, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleSignOut = async () => {
    handleClose();
    // Clear React Query cache and navigation state before signing out
    await clearCache();
    clearNavigationState();
    await logout();
    navigate('/login');
  };

  const handleProfile = () => {
    handleClose();
    navigate('/profile');
  };

  const handleSignIn = () => {
    navigate('/login');
  };

  if (loading) {
    return (
      <Button disabled variant="outlined" color="inherit" sx={{ ml: 2 }}>
        Loading...
      </Button>
    );
  }

  if (!isAuthenticated) {
    return (
      <Button
        variant="contained"
        startIcon={<LoginIcon />}
        onClick={handleSignIn}
        fullWidth
        sx={{
          py: 1.25,
          px: 3,
          fontSize: '0.95rem',
          fontFamily: 'Poppins, sans-serif',
          fontWeight: 500,
          textTransform: 'none',
          bgcolor: '#1976d2',
          color: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 14px rgba(25, 118, 210, 0.25)',
          '&:hover': {
            bgcolor: '#1565c0',
            boxShadow: '0 6px 20px rgba(25, 118, 210, 0.35)',
            transform: 'translateY(-1px)',
          },
          transition: 'all 0.2s ease',
        }}
      >
        Sign In
      </Button>
    );
  }

  // Extract username from Cognito user object
  const username = user?.username || 'User';
  const userInitial = username.charAt(0).toUpperCase();

  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      <Typography variant="body2" sx={{ mr: 2, display: { xs: 'none', sm: 'block' } }}>
        {username}
      </Typography>
      <IconButton
        size="large"
        aria-label="account of current user"
        aria-controls="menu-appbar"
        aria-haspopup="true"
        onClick={handleMenu}
        color="inherit"
      >
        <Avatar sx={{ width: 32, height: 32 }}>
          {userInitial}
        </Avatar>
      </IconButton>
      <Menu
        id="menu-appbar"
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        open={Boolean(anchorEl)}
        onClose={handleClose}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="subtitle1">
            {username}
          </Typography>
        </Box>
        <Divider />
        <MenuItem onClick={handleProfile}>
          <PersonIcon sx={{ mr: 1 }} fontSize="small" />
          Profile
        </MenuItem>
        <MenuItem onClick={handleSignOut}>
          <LogoutIcon sx={{ mr: 1 }} fontSize="small" />
          Sign Out
        </MenuItem>
      </Menu>
    </Box>
  );
}

export default AuthButton;