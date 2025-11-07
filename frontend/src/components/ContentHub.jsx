import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  Stack,
  Paper,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Search as SearchIcon,
  Dashboard as DashboardIcon,
  TableChart as DatasetIcon,
  Assessment as ReportIcon,
  Code as QueryIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  MoreVert as MoreIcon,
  Add as AddIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
} from '@mui/icons-material';

const ContentHub = ({ setSelectedTab }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAnchorEl, setFilterAnchorEl] = useState(null);

  // Saved content - simple list
  const savedContent = [
    { id: 1, name: 'Q4 Sales Dashboard', type: 'Dashboard', icon: <DashboardIcon />, starred: true, modified: '2h ago', owner: 'You', color: '#0a6ed1' },
    { id: 2, name: 'Customer Analysis', type: 'Dashboard', icon: <DashboardIcon />, starred: false, modified: '1d ago', owner: 'You', color: '#0a6ed1' },
    { id: 3, name: 'Revenue Report', type: 'Report', icon: <ReportIcon />, starred: true, modified: '3d ago', owner: 'You', color: '#df6e0c' },
    { id: 4, name: 'Sales by Region', type: 'Query', icon: <QueryIcon />, starred: false, modified: '1w ago', owner: 'You', color: '#107e3e' },
    { id: 5, name: 'Customer Dataset', type: 'Dataset', icon: <DatasetIcon />, starred: false, modified: '2w ago', owner: 'You', color: '#0a6ed1' },
    { id: 6, name: 'Product Performance', type: 'Dashboard', icon: <DashboardIcon />, starred: true, modified: '1mo ago', owner: 'Sarah Chen', color: '#0a6ed1' },
  ];

  // Quick filters
  const filters = [
    { label: 'All', count: savedContent.length },
    { label: 'Starred', count: savedContent.filter(item => item.starred).length },
    { label: 'Dashboards', count: savedContent.filter(item => item.type === 'Dashboard').length },
    { label: 'Reports', count: savedContent.filter(item => item.type === 'Report').length },
  ];

  const [activeFilter, setActiveFilter] = useState('All');

  const filteredContent = activeFilter === 'All'
    ? savedContent
    : activeFilter === 'Starred'
    ? savedContent.filter(item => item.starred)
    : savedContent.filter(item => item.type === activeFilter);

  return (
    <Paper elevation={1} sx={{ p: 4, borderRadius: 2, minHeight: 'calc(100vh - 180px)', bgcolor: 'background.paper' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" fontWeight={600} gutterBottom>
            My Content
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Your saved dashboards, reports, and analyses
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setSelectedTab('analyze')}
          sx={{ textTransform: 'none' }}
        >
          Create New
        </Button>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2.5, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Search your content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
          <IconButton size="small">
            <FilterIcon />
          </IconButton>
          <IconButton size="small">
            <SortIcon />
          </IconButton>
        </Stack>

        {/* Quick Filters */}
        <Stack direction="row" spacing={1}>
          {filters.map((filter) => (
            <Chip
              key={filter.label}
              label={`${filter.label} (${filter.count})`}
              onClick={() => setActiveFilter(filter.label)}
              color={activeFilter === filter.label ? 'primary' : 'default'}
              sx={{ cursor: 'pointer' }}
            />
          ))}
        </Stack>
      </Paper>

      {/* Content Grid */}
      {filteredContent.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom color="text.secondary">
            No content yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create your first dashboard or report to get started
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setSelectedTab('analyze')}
            sx={{ textTransform: 'none' }}
          >
            Create New
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={2.5}>
          {filteredContent.map((item) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={item.id}>
              <Card
                sx={{
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  height: '100%',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
                    <Avatar
                      sx={{
                        bgcolor: `${item.color}20`,
                        color: item.color,
                        width: 48,
                        height: 48,
                      }}
                    >
                      {item.icon}
                    </Avatar>
                    <Box>
                      <IconButton size="small">
                        {item.starred ? <StarIcon sx={{ color: '#FFB300' }} /> : <StarBorderIcon />}
                      </IconButton>
                      <IconButton size="small">
                        <MoreIcon />
                      </IconButton>
                    </Box>
                  </Box>
                  <Typography variant="body1" fontWeight={600} gutterBottom>
                    {item.name}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
                    <Chip
                      label={item.type}
                      size="small"
                      sx={{
                        bgcolor: `${item.color}20`,
                        color: item.color,
                        fontWeight: 600,
                        fontSize: '0.7rem',
                        height: 20,
                      }}
                    />
                  </Stack>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Modified {item.modified}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    By {item.owner}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Empty State Hint */}
      {filteredContent.length > 0 && (
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Showing {filteredContent.length} of {savedContent.length} items
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default ContentHub;
