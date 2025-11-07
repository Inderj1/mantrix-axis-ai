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
  Avatar,
  IconButton,
} from '@mui/material';
import {
  Search as SearchIcon,
  Mic as MicIcon,
  Folder as FolderIcon,
  TrendingUp as TrendingIcon,
  History as HistoryIcon,
  ArrowForward as ArrowIcon,
  Business as BusinessIcon,
  AttachMoney as FinanceIcon,
  Campaign as MarketingIcon,
  People as PeopleIcon,
} from '@mui/icons-material';

const ExploreHub = ({ setSelectedTab, useSapTheme }) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Data Categories
  const categories = [
    { icon: <BusinessIcon />, label: 'Sales', count: 142, color: '#0a6ed1' },
    { icon: <FinanceIcon />, label: 'Finance', count: 89, color: '#107e3e' },
    { icon: <MarketingIcon />, label: 'Marketing', count: 67, color: '#df6e0c' },
    { icon: <PeopleIcon />, label: 'Customer', count: 134, color: '#354a5f' },
  ];

  // Trending Searches
  const trendingSearches = [
    { query: 'Q4 Revenue Analysis', count: '245 views', icon: <TrendingIcon />, color: '#107e3e' },
    { query: 'Customer Churn Rate', count: '189 views', icon: <TrendingIcon />, color: '#0a6ed1' },
    { query: 'Marketing ROI', count: '156 views', icon: <TrendingIcon />, color: '#df6e0c' },
    { query: 'Sales Pipeline', count: '134 views', icon: <TrendingIcon />, color: '#0854a0' },
  ];

  // Recent Searches
  const recentSearches = [
    'Sales by region last quarter',
    'Top performing products',
    'Customer acquisition cost',
  ];

  // Popular Datasets
  const popularDatasets = [
    { name: 'Sales Transactions', records: '2.5M', lastUpdated: '2 hours ago', icon: <FolderIcon />, color: '#0a6ed1' },
    { name: 'Customer Demographics', records: '450K', lastUpdated: '1 day ago', icon: <FolderIcon />, color: '#107e3e' },
    { name: 'Product Catalog', records: '12K', lastUpdated: '3 days ago', icon: <FolderIcon />, color: '#df6e0c' },
    { name: 'Marketing Campaigns', records: '890', lastUpdated: '1 week ago', icon: <FolderIcon />, color: '#354a5f' },
  ];

  return (
    <Paper elevation={1} sx={{ p: 4, borderRadius: 2, minHeight: 'calc(100vh - 180px)', bgcolor: 'background.paper' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          Explore
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Discover data, search insights, and browse your data catalog
        </Typography>
      </Box>

      {/* Search Bar */}
      <Paper sx={{ p: 4, mb: 4, textAlign: 'center', bgcolor: useSapTheme ? 'background.paper' : '#f5f5f5' }}>
        <Typography variant="h6" fontWeight={600} gutterBottom>
          What would you like to explore?
        </Typography>
        <TextField
          fullWidth
          placeholder="Search for data, metrics, dashboards..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ maxWidth: 800, mx: 'auto', mt: 2 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton size="small">
                  <MicIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: 'center', flexWrap: 'wrap', gap: 1 }}>
          {['Revenue', 'Customers', 'Products', 'Marketing', 'Operations'].map((tag) => (
            <Chip key={tag} label={tag} size="small" onClick={() => setSearchQuery(tag)} />
          ))}
        </Stack>
      </Paper>

      {/* Browse by Category */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
          Browse by Category
        </Typography>
        <Grid container spacing={2}>
          {categories.map((category, index) => (
            <Grid item xs={6} sm={3} key={index}>
              <Card
                sx={{
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent sx={{ textAlign: 'center', py: 3 }}>
                  <Avatar
                    sx={{
                      bgcolor: `${category.color}20`,
                      color: category.color,
                      width: 56,
                      height: 56,
                      mx: 'auto',
                      mb: 1.5,
                    }}
                  >
                    {category.icon}
                  </Avatar>
                  <Typography variant="h6" fontWeight={600} gutterBottom>
                    {category.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {category.count} datasets
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      <Grid container spacing={3}>
        {/* Trending Searches */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                🔥 Trending Now
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />}>
                View All
              </Button>
            </Box>
            <Stack spacing={2}>
              {trendingSearches.map((search, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    p: 1.5,
                    borderRadius: 1,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Avatar sx={{ bgcolor: `${search.color}20`, color: search.color, width: 40, height: 40 }}>
                    {search.icon}
                  </Avatar>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" fontWeight={500}>
                      {search.query}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {search.count}
                    </Typography>
                  </Box>
                  <IconButton size="small">
                    <ArrowIcon />
                  </IconButton>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* Popular Datasets */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                📁 Popular Datasets
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />} onClick={() => setSelectedTab('content')}>
                View All
              </Button>
            </Box>
            <Stack spacing={2}>
              {popularDatasets.map((dataset, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    p: 1.5,
                    borderRadius: 1,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Avatar sx={{ bgcolor: `${dataset.color}20`, color: dataset.color, width: 40, height: 40 }}>
                    {dataset.icon}
                  </Avatar>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" fontWeight={500}>
                      {dataset.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {dataset.records} records • Updated {dataset.lastUpdated}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Searches */}
      {recentSearches.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <HistoryIcon /> Recent Searches
              </Typography>
              <Button size="small">Clear All</Button>
            </Box>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {recentSearches.map((search, index) => (
                <Chip
                  key={index}
                  label={search}
                  onClick={() => setSearchQuery(search)}
                  sx={{ cursor: 'pointer' }}
                />
              ))}
            </Stack>
          </Paper>
        </Box>
      )}
    </Paper>
  );
};

export default ExploreHub;
