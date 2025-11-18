import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Box,
  Container,
  Typography,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
} from '@mui/material';
import {
  QueryStats as QueryStatsIcon,
  Chat as ChatIcon,
  AccountTree as ProcessIcon,
  Psychology as AnalysisIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';

const features = [
  {
    title: 'Chat Explorer',
    description: 'Natural language interface for querying your BigQuery data',
    icon: <ChatIcon sx={{ fontSize: 40 }} />,
    path: '/chat',
    color: '#1976d2',
  },
  {
    title: 'Process Mining',
    description: 'Analyze and visualize your business processes',
    icon: <ProcessIcon sx={{ fontSize: 40 }} />,
    path: '/process-mining',
    color: '#388e3c',
  },
  {
    title: 'What-If Analysis',
    description: 'Explore scenarios and predict outcomes',
    icon: <AnalysisIcon sx={{ fontSize: 40 }} />,
    path: '/whatif-analysis',
    color: '#7b1fa2',
  },
  {
    title: 'Query Builder',
    description: 'Advanced SQL query construction interface',
    icon: <QueryStatsIcon sx={{ fontSize: 40 }} />,
    path: '/query',
    color: '#d32f2f',
  },
];

function HomePage() {
  console.log('HomePage component rendering!');

  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const isSignedIn = isAuthenticated;

  return (
    <Box sx={{ flexGrow: 1, bgcolor: 'background.default', minHeight: '100vh' }}>
      <Container maxWidth="lg" sx={{ pt: 8, pb: 6 }}>
        {/* Hero Section */}
        <Paper
          elevation={0}
          sx={{
            p: 6,
            mb: 6,
            background: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
            color: 'white',
            borderRadius: 3,
          }}
        >
          <Typography variant="h2" component="h1" gutterBottom fontWeight="bold">
            Welcome to AXIS.AI
          </Typography>
          <Typography variant="h5" component="p" sx={{ mb: 4, opacity: 0.9 }}>
            AI-Powered Supply Chain Intelligence Platform
          </Typography>
          {!isSignedIn ? (
            <Button
              variant="contained"
              size="large"
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                fontWeight: 600,
                '&:hover': { bgcolor: 'grey.100' },
              }}
              onClick={() => navigate('/login')}
            >
              Sign In
            </Button>
          ) : (
            <Button
              variant="contained"
              size="large"
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                fontWeight: 600,
                '&:hover': { bgcolor: 'grey.100' },
              }}
              onClick={() => navigate('/chat')}
            >
              Get Started
            </Button>
          )}
        </Paper>

        {/* Features Grid */}
        <Typography variant="h4" component="h2" gutterBottom sx={{ mb: 4 }}>
          Explore Our Features
        </Typography>
        
        <Grid container spacing={4}>
          {features.map((feature) => (
            <Grid item xs={12} sm={6} md={3} key={feature.path}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
                  <Box
                    sx={{
                      display: 'inline-flex',
                      p: 2,
                      borderRadius: 2,
                      bgcolor: `${feature.color}15`,
                      color: feature.color,
                      mb: 2,
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Typography gutterBottom variant="h6" component="h3">
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
                <CardActions sx={{ justifyContent: 'center', pb: 2 }}>
                  <Button
                    size="small"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => navigate(feature.path)}
                  >
                    Open
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Info Section */}
        <Paper sx={{ mt: 6, p: 4, bgcolor: 'grey.50', borderRadius: 2 }}>
          <Typography variant="h5" gutterBottom>
            About This Platform
          </Typography>
          <Typography variant="body1" paragraph>
            Our NLP to SQL platform leverages advanced AI to convert natural language queries
            into optimized BigQuery SQL. With industry-specific features, intelligent caching,
            and a user-friendly interface, you can explore your data without writing complex SQL.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {isSignedIn ? (
              'You are signed in. Access any feature from the navigation menu or cards above.'
            ) : (
              'Sign in to access all features and start querying your data.'
            )}
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
}

export default HomePage;