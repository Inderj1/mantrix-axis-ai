import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { signIn, resetPassword, confirmResetPassword } from 'aws-amplify/auth';
import {
  Box,
  Container,
  Typography,
  Paper,
  Stack,
  Divider,
  TextField,
  Button,
  IconButton,
  InputAdornment,
  Alert,
  Link,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Chat as ChatIcon,
  SmartToy as RobotIcon,
  Storage as DatabaseIcon,
  Lock as LockIcon,
  CheckCircle as CheckIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';

function HomePage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading, checkUser } = useAuth();
  const hasRedirected = useRef(false);

  // Sign in state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Forgot password state
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotPasswordStep, setForgotPasswordStep] = useState(1); // 1: enter username, 2: enter code
  const [resetUsername, setResetUsername] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [resetError, setResetError] = useState('');
  const [resetSuccess, setResetSuccess] = useState('');
  const [resetLoading, setResetLoading] = useState(false);

  // If user is authenticated, redirect to chat (only once)
  useEffect(() => {
    if (!authLoading && isAuthenticated && !hasRedirected.current) {
      hasRedirected.current = true;
      navigate('/chat', { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate]);

  const handleSignIn = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signIn({ username, password });
      await checkUser();
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Failed to sign in. Please check your credentials.');
      console.error('Sign in error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPasswordOpen = () => {
    setShowForgotPassword(true);
    setForgotPasswordStep(1);
    setResetUsername('');
    setResetCode('');
    setNewPassword('');
    setConfirmPassword('');
    setResetError('');
    setResetSuccess('');
  };

  const handleForgotPasswordClose = () => {
    setShowForgotPassword(false);
    setResetError('');
    setResetSuccess('');
  };

  const handleSendResetCode = async (e) => {
    e.preventDefault();
    setResetError('');
    setResetLoading(true);

    try {
      await resetPassword({ username: resetUsername });
      setResetSuccess('Reset code sent to your email!');
      setForgotPasswordStep(2);
    } catch (err) {
      setResetError(err.message || 'Failed to send reset code. Please try again.');
      console.error('Reset password error:', err);
    } finally {
      setResetLoading(false);
    }
  };

  const handleConfirmReset = async (e) => {
    e.preventDefault();
    setResetError('');

    if (newPassword !== confirmPassword) {
      setResetError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setResetError('Password must be at least 8 characters long');
      return;
    }

    setResetLoading(true);

    try {
      await confirmResetPassword({
        username: resetUsername,
        confirmationCode: resetCode,
        newPassword: newPassword,
      });
      setResetSuccess('Password reset successfully! You can now sign in.');
      setTimeout(() => {
        handleForgotPasswordClose();
      }, 2000);
    } catch (err) {
      setResetError(err.message || 'Failed to reset password. Please check your code.');
      console.error('Confirm reset error:', err);
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#f5f5f5',
        py: 2,
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={3}
          sx={{
            p: 4,
            borderRadius: 4,
            textAlign: 'center',
            bgcolor: 'white',
          }}
        >
          {/* Logo Section */}
          <Box sx={{ mb: 2 }}>
            <Box
              sx={{
                width: 80,
                height: 80,
                margin: '0 auto',
                mb: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #1976d2 0%, #2196f3 100%)',
                borderRadius: '16px',
                boxShadow: '0 4px 20px rgba(25, 118, 210, 0.3)',
              }}
            >
              <RobotIcon sx={{ fontSize: 48, color: 'white' }} />
            </Box>
            <Typography
              variant="h5"
              component="h1"
              fontWeight="bold"
              sx={{ color: '#1976d2', mb: 0.5 }}
            >
              AXIS AI
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Your AI Conversational Interface
            </Typography>
          </Box>

          {/* Features List */}
          <Stack spacing={1} sx={{ mb: 2, textAlign: 'left' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <ChatIcon sx={{ color: '#1976d2', fontSize: 24 }} />
              <Box>
                <Typography variant="body2" fontWeight="600">
                  Natural Language Chat
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Ask questions in plain English
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <RobotIcon sx={{ color: '#1976d2', fontSize: 24 }} />
              <Box>
                <Typography variant="body2" fontWeight="600">
                  Autonomous Agent Mode
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  AI executes complex tasks independently
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <DatabaseIcon sx={{ color: '#1976d2', fontSize: 24 }} />
              <Box>
                <Typography variant="body2" fontWeight="600">
                  Enterprise Data Access
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Connect to your databases securely
                </Typography>
              </Box>
            </Box>
          </Stack>

          {/* Authentication Form */}
          <Box component="form" onSubmit={handleSignIn} sx={{ mb: 2 }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2, fontSize: '0.75rem' }}>
                {error}
              </Alert>
            )}

            <TextField
              fullWidth
              size="small"
              label="Username"
              placeholder="Enter your Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              sx={{ mb: 1.5 }}
              InputProps={{
                sx: { fontSize: '0.875rem' },
              }}
              InputLabelProps={{
                sx: { fontSize: '0.875rem' },
              }}
            />

            <TextField
              fullWidth
              size="small"
              type={showPassword ? 'text' : 'password'}
              label="Password"
              placeholder="Enter your Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              sx={{ mb: 2 }}
              InputProps={{
                sx: { fontSize: '0.875rem' },
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              InputLabelProps={{
                sx: { fontSize: '0.875rem' },
              }}
            />

            <Button
              fullWidth
              type="submit"
              variant="contained"
              disabled={loading}
              sx={{
                py: 1,
                fontSize: '0.875rem',
                fontWeight: 600,
                textTransform: 'none',
                borderRadius: 1,
                mb: 1.5,
              }}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </Button>

            <Link
              component="button"
              type="button"
              variant="body2"
              onClick={handleForgotPasswordOpen}
              sx={{
                fontSize: '0.75rem',
                cursor: 'pointer',
                textDecoration: 'none',
                '&:hover': { textDecoration: 'underline' },
              }}
            >
              Forgot your password?
            </Link>
          </Box>

          {/* Security Section */}
          <Divider sx={{ mb: 1.5 }}>
            <Typography variant="caption" color="text.secondary" fontSize="0.7rem">
              SECURE AUTHENTICATION
            </Typography>
          </Divider>

          <Stack
            direction="row"
            spacing={2}
            justifyContent="center"
            sx={{ mb: 1.5 }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <LockIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              <Typography variant="caption" color="text.secondary">
                256-bit SSL
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <CheckIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              <Typography variant="caption" color="text.secondary">
                SSO Enabled
              </Typography>
            </Box>
          </Stack>

          {/* Footer */}
          <Typography variant="caption" color="text.secondary" display="block" fontSize="0.7rem">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            display="block"
            fontSize="0.7rem"
            sx={{ mt: 0.5 }}
          >
            © 2024 Cloud Mantra, Inc. All rights reserved.
          </Typography>
        </Paper>
      </Container>

      {/* Forgot Password Dialog */}
      <Dialog
        open={showForgotPassword}
        onClose={handleForgotPasswordClose}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: 'center' }}>
          <Typography variant="h6" fontWeight="bold" color="primary">
            Reset Password
          </Typography>
        </DialogTitle>
        <DialogContent>
          {resetError && (
            <Alert severity="error" sx={{ mb: 2, fontSize: '0.75rem' }}>
              {resetError}
            </Alert>
          )}
          {resetSuccess && (
            <Alert severity="success" sx={{ mb: 2, fontSize: '0.75rem' }}>
              {resetSuccess}
            </Alert>
          )}

          {forgotPasswordStep === 1 ? (
            // Step 1: Enter username
            <Box component="form" onSubmit={handleSendResetCode}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter your username to receive a password reset code via email.
              </Typography>
              <TextField
                fullWidth
                size="small"
                label="Username"
                placeholder="Enter your username"
                value={resetUsername}
                onChange={(e) => setResetUsername(e.target.value)}
                required
                autoFocus
                sx={{ mb: 2 }}
                InputProps={{
                  sx: { fontSize: '0.875rem' },
                }}
                InputLabelProps={{
                  sx: { fontSize: '0.875rem' },
                }}
              />
            </Box>
          ) : (
            // Step 2: Enter code and new password
            <Box component="form" onSubmit={handleConfirmReset}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter the verification code sent to your email and your new password.
              </Typography>
              <TextField
                fullWidth
                size="small"
                label="Verification Code"
                placeholder="Enter 6-digit code"
                value={resetCode}
                onChange={(e) => setResetCode(e.target.value)}
                required
                autoFocus
                sx={{ mb: 1.5 }}
                InputProps={{
                  sx: { fontSize: '0.875rem' },
                }}
                InputLabelProps={{
                  sx: { fontSize: '0.875rem' },
                }}
              />
              <TextField
                fullWidth
                size="small"
                type={showNewPassword ? 'text' : 'password'}
                label="New Password"
                placeholder="Enter new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                sx={{ mb: 1.5 }}
                InputProps={{
                  sx: { fontSize: '0.875rem' },
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        edge="end"
                      >
                        {showNewPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                InputLabelProps={{
                  sx: { fontSize: '0.875rem' },
                }}
              />
              <TextField
                fullWidth
                size="small"
                type={showNewPassword ? 'text' : 'password'}
                label="Confirm Password"
                placeholder="Re-enter new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                sx={{ mb: 1 }}
                InputProps={{
                  sx: { fontSize: '0.875rem' },
                }}
                InputLabelProps={{
                  sx: { fontSize: '0.875rem' },
                }}
              />
              <Typography variant="caption" color="text.secondary">
                Password must be at least 8 characters long
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={handleForgotPasswordClose}
            size="small"
          >
            Cancel
          </Button>
          {forgotPasswordStep === 1 ? (
            <Button
              onClick={handleSendResetCode}
              variant="contained"
              disabled={resetLoading || !resetUsername}
              size="small"
              sx={{ fontSize: '0.75rem' }}
            >
              {resetLoading ? 'Sending...' : 'Send Code'}
            </Button>
          ) : (
            <Button
              onClick={handleConfirmReset}
              variant="contained"
              disabled={resetLoading || !resetCode || !newPassword || !confirmPassword}
              size="small"
              sx={{ fontSize: '0.75rem' }}
            >
              {resetLoading ? 'Resetting...' : 'Reset Password'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default HomePage;