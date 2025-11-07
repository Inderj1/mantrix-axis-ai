import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Paper,
  Stack,
} from '@mui/material';
import {
  Add as AddIcon,
  Code as CodeIcon,
  DashboardCustomize as DragDropIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';

const AnalyzeHub = ({ setSelectedTab }) => {
  return (
    <Box sx={{ p: 3, maxWidth: 1000, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          Create New Analysis
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Choose your preferred method to build visualizations
        </Typography>
      </Box>

      {/* Main Creation Options - 2 large cards */}
      <Grid container spacing={4} sx={{ mb: 4 }}>
        {/* Visual Builder */}
        <Grid item xs={12} md={6}>
          <Card
            sx={{
              height: 360,
              cursor: 'pointer',
              transition: 'all 0.3s',
              position: 'relative',
              overflow: 'hidden',
              '&:hover': {
                transform: 'translateY(-8px)',
                boxShadow: 8,
              },
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '5px',
                bgcolor: '#0a6ed1',
              },
            }}
          >
            <CardContent sx={{ textAlign: 'center', py: 6 }}>
              <Box
                sx={{
                  width: 100,
                  height: 100,
                  borderRadius: '50%',
                  bgcolor: '#0a6ed120',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 3,
                }}
              >
                <DragDropIcon sx={{ fontSize: 50, color: '#0a6ed1' }} />
              </Box>
              <Typography variant="h5" fontWeight={600} gutterBottom>
                Visual Builder
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3, px: 3 }}>
                Drag and drop interface to create charts and dashboards. No coding required.
              </Typography>
              <Button
                variant="contained"
                size="large"
                startIcon={<AddIcon />}
                sx={{ textTransform: 'none', mb: 2 }}
              >
                Start Building
              </Button>
              <Typography variant="caption" display="block" color="text.secondary" sx={{ px: 2 }}>
                ✓ Point and click interface<br />
                ✓ 20+ chart types<br />
                ✓ Real-time preview
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Code-Based */}
        <Grid item xs={12} md={6}>
          <Card
            sx={{
              height: 360,
              cursor: 'pointer',
              transition: 'all 0.3s',
              position: 'relative',
              overflow: 'hidden',
              '&:hover': {
                transform: 'translateY(-8px)',
                boxShadow: 8,
              },
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '5px',
                bgcolor: '#107e3e',
              },
            }}
          >
            <CardContent sx={{ textAlign: 'center', py: 6 }}>
              <Box
                sx={{
                  width: 100,
                  height: 100,
                  borderRadius: '50%',
                  bgcolor: '#107e3e20',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 3,
                }}
              >
                <CodeIcon sx={{ fontSize: 50, color: '#107e3e' }} />
              </Box>
              <Typography variant="h5" fontWeight={600} gutterBottom>
                Code Editor
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3, px: 3 }}>
                Write SQL, Python, or R queries for advanced analytics and custom visualizations.
              </Typography>
              <Button
                variant="contained"
                size="large"
                startIcon={<CodeIcon />}
                sx={{ textTransform: 'none', bgcolor: '#107e3e', '&:hover': { bgcolor: '#388E3C' }, mb: 2 }}
              >
                Open Editor
              </Button>
              <Typography variant="caption" display="block" color="text.secondary" sx={{ px: 2 }}>
                ✓ SQL & Python support<br />
                ✓ Syntax highlighting<br />
                ✓ Query history
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Helpful Tips */}
      <Stack spacing={2}>
        <Paper sx={{ p: 2.5, bgcolor: 'background.default', borderLeft: '4px solid #0a6ed1' }}>
          <Typography variant="body2" fontWeight={500} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ChatIcon sx={{ fontSize: 18 }} />
            Prefer natural language?
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Go to the <strong>Chat</strong> tab to ask questions in plain English and get instant visualizations
          </Typography>
          <Button
            size="small"
            onClick={() => setSelectedTab('chat')}
            sx={{ mt: 1, textTransform: 'none' }}
          >
            Open Chat →
          </Button>
        </Paper>

        <Paper sx={{ p: 2.5, bgcolor: 'background.default', textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            All your work will be saved in <strong>Content</strong> tab
          </Typography>
          <Button size="small" onClick={() => setSelectedTab('content')} sx={{ mt: 1, textTransform: 'none' }}>
            View My Content →
          </Button>
        </Paper>
      </Stack>
    </Box>
  );
};

export default AnalyzeHub;
