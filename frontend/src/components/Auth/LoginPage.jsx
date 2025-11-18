import React from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { Box, Paper, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

function LoginPage() {
  const navigate = useNavigate();
  const { checkUser } = useAuth();

  const handleAuthSuccess = async () => {
    await checkUser();
    navigate('/chat');
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
        backgroundImage: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Paper
        elevation={24}
        sx={{
          p: 4,
          maxWidth: 450,
          width: '100%',
          borderRadius: 3,
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography
            variant="h4"
            gutterBottom
            sx={{
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Mantrix Axis AI
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Sign in to continue to your account
          </Typography>
        </Box>

        <Authenticator
          initialState="signIn"
          components={{
            SignIn: {
              Header() {
                return null; // Hide default header
              },
            },
            SignUp: {
              Header() {
                return null;
              },
            },
          }}
          services={{
            async handleSignIn(formData) {
              const { username, password } = formData;
              // This will be handled by Amplify automatically
              return formData;
            },
          }}
        >
          {({ signOut, user }) => {
            if (user) {
              handleAuthSuccess();
            }
            return null;
          }}
        </Authenticator>
      </Paper>
    </Box>
  );
}

export default LoginPage;
