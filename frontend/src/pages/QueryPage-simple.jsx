import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  Divider,
  Card,
  CardContent,
  IconButton,
  Tooltip,
} from '@mui/material';
import { 
  PlayArrow as PlayArrowIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Code as CodeIcon,
  QueryStats as QueryStatsIcon,
  TipsAndUpdates as TipsIcon,
} from '@mui/icons-material';
import { apiService } from '../services/api';

function QueryPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const sampleQueries = [
    {
      category: 'Financial Analysis',
      icon: '💰',
      queries: [
        { text: 'Calculate quarterly revenue growth rate', complexity: 'medium' },
        { text: 'Show profit margins by business unit', complexity: 'easy' },
        { text: 'Analyze expense ratios vs industry benchmarks', complexity: 'hard' },
        { text: 'What is our EBITDA for the last fiscal year?', complexity: 'medium' },
      ]
    },
    {
      category: 'Sales & Customers',
      icon: '📊',
      queries: [
        { text: 'Top 20 customers by revenue contribution', complexity: 'easy' },
        { text: 'Customer lifetime value by segment', complexity: 'medium' },
        { text: 'Sales pipeline conversion rates by stage', complexity: 'medium' },
        { text: 'Monthly sales trends with seasonality analysis', complexity: 'hard' },
      ]
    },
    {
      category: 'Operational Metrics',
      icon: '⚙️',
      queries: [
        { text: 'Inventory turnover ratio by product category', complexity: 'medium' },
        { text: 'Average order fulfillment time by region', complexity: 'easy' },
        { text: 'Production efficiency metrics dashboard', complexity: 'hard' },
        { text: 'Supply chain cost breakdown analysis', complexity: 'medium' },
      ]
    },
    {
      category: 'Advanced Analytics',
      icon: '🤖',
      queries: [
        { text: 'Predict next quarter revenue using historical data', complexity: 'hard' },
        { text: 'Customer churn risk analysis with key factors', complexity: 'hard' },
        { text: 'Market basket analysis for cross-selling', complexity: 'hard' },
        { text: 'Anomaly detection in financial transactions', complexity: 'hard' },
      ]
    },
  ];

  const handleSubmit = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.executeQuery(query);
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSampleQuery = (queryText) => {
    setQuery(queryText);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const downloadResults = () => {
    if (!result?.execution?.results) return;
    
    const csv = [
      Object.keys(result.execution.results[0]).join(','),
      ...result.execution.results.map(row => Object.values(row).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getComplexityColor = (complexity) => {
    switch (complexity) {
      case 'easy': return 'success';
      case 'medium': return 'warning';
      case 'hard': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          Query Builder
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Build complex queries using natural language or explore sample queries
        </Typography>
      </Box>
      
      <Grid container spacing={3}>
        {/* Left Panel - Query Input */}
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <QueryStatsIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">
                Natural Language Query
              </Typography>
            </Box>
            
            <TextField
              fullWidth
              multiline
              rows={6}
              variant="outlined"
              placeholder="Examples:
• Show me total revenue by quarter for the last 2 years
• What are the top 10 products by profit margin?
• Calculate customer acquisition cost by marketing channel
• Compare operating expenses vs revenue by month
• Which regions have the highest sales growth rate?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              sx={{ mb: 2 }}
            />

            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={handleSubmit}
              disabled={!query.trim() || loading}
              startIcon={loading ? <CircularProgress size={20} sx={{ color: 'white' }} /> : <PlayArrowIcon />}
              sx={{ mb: 3 }}
            >
              {loading ? 'Generating...' : 'Generate & Execute SQL'}
            </Button>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Divider sx={{ my: 3 }} />

            {/* Sample Queries */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <TipsIcon sx={{ mr: 1, color: 'secondary.main' }} />
              <Typography variant="h6">
                Sample Queries
              </Typography>
            </Box>

            <Stack spacing={2} sx={{ maxHeight: 400, overflow: 'auto' }}>
              {sampleQueries.map((category, idx) => (
                <Card key={idx} variant="outlined">
                  <CardContent sx={{ p: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                      <span style={{ marginRight: 8, fontSize: 20 }}>{category.icon}</span>
                      {category.category}
                    </Typography>
                    <Stack spacing={1}>
                      {category.queries.map((q, qIdx) => (
                        <Box 
                          key={qIdx}
                          sx={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 1,
                            p: 1,
                            bgcolor: 'background.default',
                            borderRadius: 1,
                            cursor: 'pointer',
                            '&:hover': {
                              bgcolor: 'action.hover'
                            }
                          }}
                          onClick={() => handleSampleQuery(q.text)}
                        >
                          <Typography variant="body2" sx={{ flex: 1 }}>
                            {q.text}
                          </Typography>
                          <Chip 
                            label={q.complexity} 
                            size="small" 
                            color={getComplexityColor(q.complexity)}
                            sx={{ fontSize: '0.7rem', height: 20 }}
                          />
                        </Box>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* Right Panel - Results */}
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 3, height: '100%', minHeight: 600 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">
                Results
              </Typography>
              {result?.execution?.results && (
                <Stack direction="row" spacing={1}>
                  <Tooltip title="Copy SQL">
                    <IconButton size="small" onClick={() => copyToClipboard(result.sql)}>
                      <CopyIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Download CSV">
                    <IconButton size="small" onClick={downloadResults}>
                      <DownloadIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              )}
            </Box>
            
            {result ? (
              <Box>
                {/* Generated SQL */}
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <CodeIcon sx={{ mr: 1, color: 'text.secondary' }} />
                    <Typography variant="subtitle2">
                      Generated SQL
                    </Typography>
                  </Box>
                  <Box sx={{ 
                    p: 2, 
                    bgcolor: 'grey.100', 
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    overflow: 'auto',
                    maxHeight: 200,
                    border: 1,
                    borderColor: 'divider'
                  }}>
                    <pre style={{ margin: 0 }}>
                      {result.sql || 'No SQL generated'}
                    </pre>
                  </Box>
                </Box>
                
                {/* Query Results */}
                {result.execution?.results && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Query Results ({result.execution.results.length} rows)
                    </Typography>
                    
                    {result.execution.results.length > 0 ? (
                      <Box sx={{ 
                        overflow: 'auto',
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        maxHeight: 400
                      }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ backgroundColor: '#f5f5f5' }}>
                              {Object.keys(result.execution.results[0]).map((key) => (
                                <th key={key} style={{ 
                                  padding: '8px', 
                                  textAlign: 'left',
                                  borderBottom: '2px solid #ddd',
                                  fontWeight: 600,
                                  fontSize: '0.875rem'
                                }}>
                                  {key}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {result.execution.results.map((row, idx) => (
                              <tr key={idx} style={{ 
                                backgroundColor: idx % 2 === 0 ? '#fff' : '#fafafa',
                                '&:hover': { backgroundColor: '#f0f0f0' }
                              }}>
                                {Object.values(row).map((value, vIdx) => (
                                  <td key={vIdx} style={{ 
                                    padding: '8px',
                                    borderBottom: '1px solid #eee',
                                    fontSize: '0.875rem'
                                  }}>
                                    {value !== null && value !== undefined ? value.toString() : '-'}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </Box>
                    ) : (
                      <Alert severity="info">
                        <Typography variant="body2" fontWeight="medium">
                          The query executed successfully but returned no results.
                        </Typography>
                        {result.empty_result_note && (
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            {result.empty_result_note}
                          </Typography>
                        )}
                      </Alert>
                    )}

                    {/* Execution Metadata */}
                    {result.execution.metadata && (
                      <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                        <Chip 
                          label={`Execution Time: ${result.execution.metadata.executionTime || 'N/A'}`} 
                          size="small" 
                          variant="outlined" 
                        />
                        <Chip 
                          label={`Rows Scanned: ${result.execution.metadata.rowsScanned || 'N/A'}`} 
                          size="small" 
                          variant="outlined" 
                        />
                        {result.execution.metadata.cost && (
                          <Chip 
                            label={`Est. Cost: $${result.execution.metadata.cost.toFixed(4)}`} 
                            size="small" 
                            variant="outlined" 
                            color="warning"
                          />
                        )}
                      </Stack>
                    )}
                  </Box>
                )}
              </Box>
            ) : (
              <Box sx={{ 
                height: '100%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                minHeight: 400
              }}>
                <Box sx={{ textAlign: 'center' }}>
                  <QueryStatsIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                  <Typography color="text.secondary">
                    No results yet. Enter a query or select a sample query to get started.
                  </Typography>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default QueryPage;