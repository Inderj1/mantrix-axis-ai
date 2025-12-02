import React, { useState, useRef, useEffect, useMemo, useCallback, forwardRef, useImperativeHandle } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useConversationStore } from '../stores/conversationStore';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Avatar,
  Stack,
  IconButton,
  CircularProgress,
  Alert,
  Divider,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip as MuiTooltip,
  Tab,
  Tabs,
  Card,
  CardContent,
} from '@mui/material';
import {
  Send as SendIcon,
  Person as PersonIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  Link as LinkIcon,
  History as HistoryIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  DeleteOutline as DeleteOutlineIcon,
  Insights as InsightsIcon,
  Close as CloseIcon,
  ChatOutlined as ChatIcon,
  Science as ResearchIcon,
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  PlayArrow as PlayArrowIcon,
  BarChart as BarChartIcon,
  Timeline as TimelineIcon,
  PieChart as PieChartIcon,
  Analytics as AnalyticsIcon,
  TableChart as TableChartIcon,
  ScatterPlot as ScatterPlotIcon,
  Radar as RadarIcon,
  ViewModule as ViewModuleIcon,
  FilterList as FilterListIcon,
  Dashboard as DashboardIcon,
  AutoGraph as AutoGraphIcon,
  InfoOutlined as InfoIcon,
  SmartToy as SmartToyIcon,
  Storage as StorageIcon,
} from '@mui/icons-material';
import { DataGrid } from '@mui/x-data-grid';
import { apiService } from '../services/api';
import ResultAnalysis from './ResultAnalysis';
import DeepResearchInterface from './DeepResearchInterface';
import QueryLogger from './QueryLogger';
import EnhancedAnalyticsModal from './EnhancedAnalyticsModal';
import MantraxResultsView from './MantraxResultsView';
import FollowUpSuggestions from './FollowUpSuggestions';
import PlotlyVisualization from './PlotlyVisualization';
import DashboardCreationPreview from './dashboard/DashboardCreationPreview';
import MultiQueryAccordion from './MultiQueryAccordion';
import AceEditor from 'react-ace';
import 'ace-builds/src-noconflict/mode-sql';
import 'ace-builds/src-noconflict/theme-monokai';
import 'ace-builds/src-noconflict/theme-github';
import 'ace-builds/src-noconflict/ext-language_tools';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area, ScatterChart, Scatter, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Treemap, FunnelChart, Funnel,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend,
  ResponsiveContainer
} from 'recharts';

// Import images as modules for proper caching
import axisAiLogo from '../assets/axis-ai4.png';

// Chart colors
const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0', '#ffb347', '#67b7dc'];

// Helper function: Debounce utility
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Helper function: Group conversations by date
const getDateGroup = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const thisWeek = new Date(today);
  thisWeek.setDate(thisWeek.getDate() - 7);
  const thisMonth = new Date(today);
  thisMonth.setDate(thisMonth.getDate() - 30);

  if (date >= today) return 'Today';
  if (date >= yesterday) return 'Yesterday';
  if (date >= thisWeek) return 'This Week';
  if (date >= thisMonth) return 'This Month';
  return 'Older';
};

// Helper function: Group conversations
const groupConversations = (conversations) => {
  const groups = {
    'Today': [],
    'Yesterday': [],
    'This Week': [],
    'This Month': [],
    'Older': []
  };

  conversations.forEach(conv => {
    const group = getDateGroup(conv.updated_at || conv.updatedAt);
    groups[group].push(conv);
  });

  return groups;
};

// Sample queries for quick access
const SAMPLE_QUERIES = [
  { 
    category: "Revenue Analysis", 
    queries: [
      "What's our monthly recurring revenue?",
      "Show revenue by product line",
      "Compare this year vs last year revenue"
    ]
  },
  { 
    category: "Cost Management", 
    queries: [
      "What are our biggest expense categories?",
      "Show COGS trend over time",
      "Calculate gross margin by product"
    ]
  },
  { 
    category: "Customer Insights", 
    queries: [
      "Who are our top customers by lifetime value?",
      "Show customer acquisition trends",
      "Analyze churn rate by segment"
    ]
  },
  { 
    category: "Performance Metrics", 
    queries: [
      "Calculate ROI for marketing campaigns",
      "Show key performance indicators dashboard",
      "What's our cash conversion cycle?"
    ]
  }
];

const SimpleChatInterface = forwardRef((props, ref) => {
  const { onBackToSearch, onOpenAgentMode } = props;
  // Get authenticated user from Cognito
  const { user, loading: authLoading } = useAuth();
  const isUserLoaded = !authLoading;

  // Derive userId from authenticated user
  const userId = user?.username || 'default';

  // ============ Zustand Store ============
  const {
    // State
    conversationId,
    messages,
    conversations,
    loadingConversations,
    isInitializing,
    isLoading: loading,
    // Actions
    initialize,
    loadConversation,
    createNewConversation,
    deleteConversation,
    clearAllConversations,
    reloadConversations,
    addMessage,
    updateMessage,
    sendQuery,
    toggleStar,
    setIsLoading,
  } = useConversationStore();

  // ============ Local UI State ============
  const [inputMessage, setInputMessage] = useState('');
  const [showVisualization, setShowVisualization] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearchQuery = useDebounce(searchQuery, 300);
  const [openAnalysisDialog, setOpenAnalysisDialog] = useState(false);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [activeMessageId, setActiveMessageId] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [showSampleQueries, setShowSampleQueries] = useState(true);
  const [mode, setMode] = useState('chat'); // 'chat' or 'research'
  const [viewMode, setViewMode] = useState('chat'); // 'chat' or 'history' within chat mode
  const [showDetailedResults, setShowDetailedResults] = useState(false);
  const [detailedResultsData, setDetailedResultsData] = useState(null);
  const [editMode, setEditMode] = useState({});
  const [editedSql, setEditedSql] = useState({});
  const [visualizationType, setVisualizationType] = useState({});
  const [sqlTheme, setSqlTheme] = useState('github');
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
  const [analyticsModalData, setAnalyticsModalData] = useState(null);
  const [analyticsModalMode, setAnalyticsModalMode] = useState('modal'); // 'modal', 'drawer', 'embedded'
  const [showDeepResearch, setShowDeepResearch] = useState(false);
  const [deepResearchQuestion, setDeepResearchQuestion] = useState('');

  // Dashboard creation from chat state
  const [dashboardPreviewOpen, setDashboardPreviewOpen] = useState(false);
  const [dashboardPreviewData, setDashboardPreviewData] = useState(null);
  const [dashboardPreviewQuery, setDashboardPreviewQuery] = useState('');

  // Initialize store when user is loaded
  useEffect(() => {
    if (isUserLoaded && userId) {
      initialize(userId);
    }
  }, [isUserLoaded, userId, initialize]);

  // Auto-scroll to latest message
  useEffect(() => {
    // Small delay to ensure DOM is updated with new message
    const scrollTimeout = setTimeout(() => {
      // Scroll messages container to bottom to show latest message
      const messagesContainer = document.querySelector('[data-messages-container="true"]');
      if (messagesContainer) {
        messagesContainer.scrollTo({
          top: messagesContainer.scrollHeight,
          behavior: 'smooth'
        });
      }
    }, 100);
    
    // Keep conversations list at top when switching conversations
    if (conversationId) {
      const conversationsList = document.querySelector('[data-conversations-list="true"]');
      if (conversationsList) {
        conversationsList.scrollTop = 0;
      }
    }
    
    return () => clearTimeout(scrollTimeout);
  }, [messages, conversationId, loading]); // Scroll when messages change, conversation changes, or loading state changes

  // Listen for events from Layout sidebar (delegate to store)
  useEffect(() => {
    const handleNewConversation = () => {
      console.log('Received newConversation event');
      createNewConversation();
    };

    const handleLoadConversationEvent = (event) => {
      const { conversationId: convId } = event.detail;
      console.log('Received loadConversation event:', convId);
      loadConversation(convId);
    };

    window.addEventListener('newConversation', handleNewConversation);
    window.addEventListener('loadConversation', handleLoadConversationEvent);

    return () => {
      window.removeEventListener('newConversation', handleNewConversation);
      window.removeEventListener('loadConversation', handleLoadConversationEvent);
    };
  }, [createNewConversation, loadConversation]);

  const scrollToBottom = () => {
    const messagesContainer = document.querySelector('[data-messages-container="true"]');
    if (messagesContainer) {
      messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    // Check for dashboard creation intent first
    const dashboardIntentPatterns = [
      /create\s+(a\s+)?(new\s+)?dashboard/i,
      /build\s+(a\s+)?(new\s+)?dashboard/i,
      /make\s+(a\s+)?(new\s+)?dashboard/i,
      /new\s+dashboard\s+(for|with|showing)/i,
      /dashboard\s+(for|with|showing)/i,
    ];

    const hasDashboardIntent = dashboardIntentPatterns.some(pattern => pattern.test(inputMessage));

    if (hasDashboardIntent) {
      // Handle dashboard creation flow (not using store for this special case)
      try {
        const response = await apiService.createDashboardFromConversation(inputMessage);
        const previewData = response.data;

        setDashboardPreviewQuery(inputMessage);
        setDashboardPreviewData(previewData);
        setDashboardPreviewOpen(true);
        setInputMessage('');
      } catch (error) {
        console.error('Dashboard creation preview error:', error);
        // Fall through to regular query if dashboard creation fails
      }
      return;
    }

    // Use store's sendQuery - handles everything:
    // - Creating conversation if needed
    // - Adding user/assistant messages
    // - API call
    // - Error handling
    // - Updating conversations list
    const question = inputMessage;
    setInputMessage('');

    // Scroll when user sends message
    setTimeout(scrollToBottom, 50);

    const result = await sendQuery(question);

    // Scroll to show the response
    setTimeout(scrollToBottom, 100);

    console.log('Query result:', result);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRunModifiedSql = async (messageId, sql) => {
    setIsLoading(true);
    try {
      const response = await apiService.executeQuery(sql, { conversationId, isModifiedSql: true });
      const { data } = response;

      if (data.error) {
        addMessage({
          type: 'assistant',
          content: `Error running modified SQL: ${data.error_details?.user_friendly_message || data.error}`,
          error: data.error,
        });
        return;
      }

      // Create a new message for the modified query results
      addMessage({
        type: 'assistant',
        content: 'Modified query executed successfully.',
        sql: sql,
        results: data.execution?.results || [],
        resultCount: data.execution?.row_count || 0,
        metadata: {
          cost: data.validation?.estimated_cost_usd,
          bytesProcessed: data.validation?.total_bytes_processed,
          tablesUsed: data.tables_used,
        },
      });

      setEditMode(prev => ({ ...prev, [messageId]: false }));
    } catch (error) {
      console.error('Error running modified SQL:', error);
      addMessage({
        type: 'assistant',
        content: 'Sorry, I encountered an error running the modified SQL.',
        error: error.response?.data?.detail || error.message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const downloadCSV = (results) => {
    if (!results || results.length === 0) return;
    
    const headers = Object.keys(results[0]);
    const csv = [
      headers.join(','),
      ...results.map(row => headers.map(h => JSON.stringify(row[h] || '')).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAnalyzeResults = async (message) => {
    if (!message.results || message.results.length === 0) return;
    
    setActiveMessageId(message.timestamp);
    setAnalysisLoading(true);
    setOpenAnalysisDialog(true);
    
    // Find the original user question by looking for the previous user message
    const messageIndex = messages.findIndex(m => m.id === message.id);
    let userQuestion = 'Query results';
    
    // Look backwards from the current message to find the user's question
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (messages[i].type === 'user') {
        userQuestion = messages[i].content;
        break;
      }
    }
    
    try {
      // Log the data being sent for debugging
      // Debug logging
      console.log('Analyze Results Request:', {
        question: userQuestion,
        sql: message.sql,
        resultsCount: message.results?.length,
        resultsType: typeof message.results,
        results: message.results?.slice(0, 2), // Log first 2 results
        metadata: message.metadata
      });
      
      const response = await apiService.analyzeResults(
        userQuestion,
        message.sql,
        message.results,
        message.metadata
      );
      
      setActiveAnalysis(response.data);
    } catch (error) {
      console.error('Failed to analyze results:', error);
      
      // Log more detailed error information
      if (error.response) {
        console.error('Error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data,
          detail: error.response.data?.detail
        });
      }
      // Show error in analysis
      setActiveAnalysis({
        summary: 'An error occurred while analyzing the results. Please try again.',
        key_insights: ['Error: ' + error.message],
        trends: []
      });
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleFollowUpQuestion = (question) => {
    setInputMessage(question);
    setOpenAnalysisDialog(false);
    // Focus the input field
    setTimeout(() => {
      document.querySelector('input[type="text"]')?.focus();
    }, 100);
  };

  const handleViewDetailedResults = (message) => {
    // Find the user message that triggered this response
    const messageIndex = messages.findIndex(m => m.id === message.id);
    const userQuery = messageIndex > 0 ? messages[messageIndex - 1].content : message.content;
    
    setDetailedResultsData({
      query: userQuery,
      sql: message.sql,
      results: message.results,
      metadata: message.metadata
    });
    setShowDetailedResults(true);
  };

  const handleNewChat = async () => {
    setInputMessage('');
    await createNewConversation();
    setHistoryOpen(false);
  };

  // Delete a conversation (uses store's deleteConversation which handles everything)
  const handleDeleteConversation = async (convId) => {
    await deleteConversation(convId);
  };

  // Clear all conversations (uses store action)
  const handleClearAllConversations = async () => {
    if (!window.confirm('Are you sure you want to clear all conversations? This cannot be undone.')) {
      return;
    }
    await clearAllConversations();
  };

  // Helper to parse formatted numbers (handles $, commas, etc.)
  const parseFormattedNumber = (value) => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
      // Remove $, commas, and whitespace
      const cleaned = value.replace(/[$,\s]/g, '');
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? null : parsed;
    }
    return null;
  };

  // Prepare chart data
  const prepareChartData = (results) => {
    if (!results || results.length === 0) {
      return null;
    }

    const keys = Object.keys(results[0]);

    // Try to identify numeric columns - improved detection to handle formatted numbers
    const numericColumns = keys.filter(key => {
      return results.every(row => {
        const value = row[key];
        // Skip null/undefined values
        if (value === null || value === undefined || value === '') {
          return true;
        }
        // Check if it's a number or can be parsed as a formatted number
        if (typeof value === 'number') return true;

        // Try to parse formatted strings like "$1,234.56"
        const parsed = parseFormattedNumber(value);
        return parsed !== null;
      });
    });

    // Sanitize data: convert formatted strings to numbers for charts
    const sanitizedData = results.map(row => {
      const sanitized = { ...row };
      numericColumns.forEach(col => {
        if (sanitized[col] !== null && sanitized[col] !== undefined) {
          const parsed = parseFormattedNumber(sanitized[col]);
          if (parsed !== null) {
            sanitized[col] = parsed;
          }
        }
      });
      return sanitized;
    });

    console.log('Chart data preparation:', {
      totalColumns: keys.length,
      numericColumns: numericColumns,
      hasNumericData: numericColumns.length > 0,
      sampleData: sanitizedData[0]
    });

    return {
      data: sanitizedData,
      keys,
      numericColumns,
      hasNumericData: numericColumns.length > 0
    };
  };

  // Intelligently prepare data for specific chart type
  const prepareDataForChartType = (data, keys, numericColumns, vizType) => {
    const labelKey = keys.find(k => !numericColumns.includes(k)) || keys[0];
    const valueKey = numericColumns[0];

    // For PIE charts: Aggregate and show top categories
    if (vizType === 'pie') {
      // Group by label key and sum the primary numeric column
      const aggregated = {};
      data.forEach(row => {
        const label = String(row[labelKey] || 'Unknown');
        const value = parseFloat(row[valueKey]) || 0;
        aggregated[label] = (aggregated[label] || 0) + value;
      });

      // Convert to array and sort by value
      let pieData = Object.entries(aggregated).map(([name, value]) => ({
        name,
        value
      })).sort((a, b) => b.value - a.value);

      // Show top 8, group rest as "Others"
      if (pieData.length > 8) {
        const top8 = pieData.slice(0, 8);
        const others = pieData.slice(8).reduce((sum, item) => sum + item.value, 0);
        if (others > 0) {
          pieData = [...top8, { name: 'Others', value: others }];
        } else {
          pieData = top8;
        }
      }

      return { data: pieData, labelKey: 'name', valueKey: 'value', numericColumns: ['value'] };
    }

    // For BAR charts: Limit to top performers if too many rows
    if (vizType === 'bar' && data.length > 15) {
      // Sort by first numeric column and take top 15
      const sorted = [...data].sort((a, b) => {
        const aVal = parseFloat(a[valueKey]) || 0;
        const bVal = parseFloat(b[valueKey]) || 0;
        return bVal - aVal;
      });
      return { data: sorted.slice(0, 15), labelKey, valueKey, numericColumns };
    }

    // For LINE charts: Sort by label (assuming it's time-based or sequential)
    if (vizType === 'line') {
      // Try to sort by label - useful for time series
      const sorted = [...data].sort((a, b) => {
        const aLabel = a[labelKey];
        const bLabel = b[labelKey];
        // If labels are dates or numbers, sort accordingly
        if (!isNaN(Date.parse(aLabel)) && !isNaN(Date.parse(bLabel))) {
          return new Date(aLabel) - new Date(bLabel);
        }
        if (!isNaN(aLabel) && !isNaN(bLabel)) {
          return parseFloat(aLabel) - parseFloat(bLabel);
        }
        return String(aLabel).localeCompare(String(bLabel));
      });

      // Limit to reasonable number of data points for line chart
      if (sorted.length > 30) {
        return { data: sorted.slice(0, 30), labelKey, valueKey, numericColumns };
      }
      return { data: sorted, labelKey, valueKey, numericColumns };
    }

    // For AREA charts: Same as line
    if (vizType === 'area') {
      const sorted = [...data].sort((a, b) => {
        const aLabel = a[labelKey];
        const bLabel = b[labelKey];
        if (!isNaN(Date.parse(aLabel)) && !isNaN(Date.parse(bLabel))) {
          return new Date(aLabel) - new Date(bLabel);
        }
        return String(aLabel).localeCompare(String(bLabel));
      });
      if (sorted.length > 30) {
        return { data: sorted.slice(0, 30), labelKey, valueKey, numericColumns };
      }
      return { data: sorted, labelKey, valueKey, numericColumns };
    }

    // Default: return as is
    return { data, labelKey, valueKey, numericColumns };
  };

  // Expose methods to parent component via ref
  useImperativeHandle(ref, () => ({
    loadConversation,
    handleDeleteConversation,
    handleNewConversation: createNewConversation,
  }));

  // Render visualization based on type
  const renderVisualization = (messageId, results) => {
    console.log('renderVisualization called:', { messageId, results });

    const chartData = prepareChartData(results);
    if (!chartData || !chartData.hasNumericData) {
      return (
        <Alert severity="info">
          No numeric data available for visualization. Switch to table view.
        </Alert>
      );
    }

    const vizType = visualizationType[messageId] || 'table';

    // Intelligently prepare data based on chart type
    const { data, labelKey, valueKey, numericColumns } = prepareDataForChartType(
      chartData.data,
      chartData.keys,
      chartData.numericColumns,
      vizType
    );
    
    // Get transformation info message
    const getTransformationMessage = () => {
      if (vizType === 'pie') {
        return `Aggregated ${results.length} rows by ${labelKey}, showing top ${data.length} categories`;
      }
      if (vizType === 'bar' && results.length > 15 && data.length === 15) {
        return `Showing top 15 out of ${results.length} rows, sorted by ${valueKey}`;
      }
      if ((vizType === 'line' || vizType === 'area') && results.length > 30 && data.length === 30) {
        return `Showing first 30 data points out of ${results.length} rows`;
      }
      return null;
    };

    const transformationMsg = getTransformationMessage();

    console.log('Visualization data:', {
      vizType,
      labelKey,
      valueKey,
      numericColumns,
      dataLength: data.length
    });

    // Enhanced tooltip formatter
    const CustomTooltip = ({ active, payload, label }) => {
      if (active && payload && payload.length) {
        return (
          <Box sx={{ 
            bgcolor: 'background.paper', 
            p: 2, 
            border: 1, 
            borderColor: 'divider',
            borderRadius: 1,
            boxShadow: 2
          }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {`${labelKey}: ${label}`}
            </Typography>
            {payload.map((entry, index) => (
              <Typography key={index} variant="body2" sx={{ color: entry.color }}>
                {`${entry.dataKey}: ${typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}`}
              </Typography>
            ))}
          </Box>
        );
      }
      return null;
    };

    return (
      <Box>
        {transformationMsg && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {transformationMsg}
          </Alert>
        )}
        {renderChartByType()}
      </Box>
    );

    function renderChartByType() {
    // Helper to truncate long labels
    const truncateLabel = (label, maxLength = 20) => {
      if (!label) return '';
      const str = String(label);
      return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
    };

    switch (vizType) {
      case 'bar':
        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 20, right: 30, left: 60, bottom: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey={labelKey}
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={90}
                  interval={0}
                  tickFormatter={(value) => truncateLabel(value, 25)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  width={80}
                  tickFormatter={(value) => typeof value === 'number' ? value.toLocaleString() : value}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                {numericColumns.map((col, idx) => (
                  <Bar
                    key={col}
                    dataKey={col}
                    fill={COLORS[idx % COLORS.length]}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Box>
        );
      
      case 'line':
        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 20, right: 30, left: 60, bottom: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey={labelKey}
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={90}
                  interval={0}
                  tickFormatter={(value) => truncateLabel(value, 25)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  width={80}
                  tickFormatter={(value) => typeof value === 'number' ? value.toLocaleString() : value}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                {numericColumns.map((col, idx) => (
                  <Line
                    key={col}
                    type="monotone"
                    dataKey={col}
                    stroke={COLORS[idx % COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Box>
        );
      
      case 'pie':
        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="45%"
                  labelLine={true}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey={valueKey}
                  label={({ name, percent }) => {
                    const truncated = truncateLabel(name, 15);
                    return `${truncated}: ${(percent * 100).toFixed(0)}%`;
                  }}
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip
                  formatter={(value) => typeof value === 'number' ? `$${value.toLocaleString()}` : value}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '10px' }}
                  formatter={(value) => truncateLabel(value, 20)}
                />
              </PieChart>
            </ResponsiveContainer>
          </Box>
        );
      
      case 'area':
        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 20, right: 30, left: 60, bottom: 100 }}>
                <defs>
                  {numericColumns.map((col, idx) => (
                    <linearGradient key={col} id={`gradient-${idx}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.1}/>
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey={labelKey}
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={90}
                  interval={0}
                  tickFormatter={(value) => truncateLabel(value, 25)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  width={80}
                  tickFormatter={(value) => typeof value === 'number' ? value.toLocaleString() : value}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                {numericColumns.map((col, idx) => (
                  <Area
                    key={col}
                    type="monotone"
                    dataKey={col}
                    stroke={COLORS[idx % COLORS.length]}
                    fill={`url(#gradient-${idx})`}
                    strokeWidth={2}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        );
      
      case 'scatter':
        if (numericColumns.length < 2) {
          return (
            <Alert severity="warning">
              Scatter plot requires at least 2 numeric columns for X and Y axes.
            </Alert>
          );
        }
        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart data={data} margin={{ top: 20, right: 30, left: 60, bottom: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  type="number"
                  dataKey={numericColumns[0]}
                  name={numericColumns[0]}
                  tick={{ fontSize: 11 }}
                  label={{ value: truncateLabel(numericColumns[0], 30), position: 'insideBottom', offset: -10, fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey={numericColumns[1]}
                  name={numericColumns[1]}
                  tick={{ fontSize: 11 }}
                  width={80}
                  label={{ value: truncateLabel(numericColumns[1], 30), angle: -90, position: 'insideLeft', fontSize: 11 }}
                  tickFormatter={(value) => typeof value === 'number' ? value.toLocaleString() : value}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Scatter fill={COLORS[0]} />
              </ScatterChart>
            </ResponsiveContainer>
          </Box>
        );
      
      case 'radar':
        if (numericColumns.length < 3) {
          return (
            <Alert severity="warning">
              Radar chart works best with at least 3 numeric dimensions.
            </Alert>
          );
        }

        const radarData = numericColumns.map(col => ({
          metric: truncateLabel(col, 20),
          value: data.reduce((sum, item) => sum + (item[col] || 0), 0) / data.length,
          fullMark: Math.max(...data.map(item => item[col] || 0))
        }));

        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} margin={{ top: 20, right: 30, left: 30, bottom: 20 }}>
                <PolarGrid stroke="#f0f0f0" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 'dataMax']} tick={{ fontSize: 11 }} />
                <Radar
                  name="Average Values"
                  dataKey="value"
                  stroke={COLORS[0]}
                  fill={COLORS[0]}
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <RechartsTooltip content={<CustomTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </Box>
        );
      
      case 'treemap':
        const treemapData = data.map((item, index) => ({
          name: truncateLabel(item[labelKey], 20),
          size: item[valueKey] || 1,
          fill: COLORS[index % COLORS.length]
        }));

        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={treemapData}
                dataKey="size"
                aspectRatio={4/3}
                stroke="#fff"
                strokeWidth={2}
              />
            </ResponsiveContainer>
          </Box>
        );
      
      case 'funnel':
        const funnelData = data
          .map(item => ({
            name: truncateLabel(item[labelKey], 15),
            value: item[valueKey] || 0,
            fill: COLORS[data.indexOf(item) % COLORS.length]
          }))
          .sort((a, b) => b.value - a.value);

        return (
          <Box sx={{ width: '100%', height: 450, overflow: 'hidden', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <FunnelChart data={funnelData} margin={{ top: 20, right: 30, left: 30, bottom: 20 }}>
                <RechartsTooltip content={<CustomTooltip />} />
                <Funnel
                  dataKey="value"
                  nameKey="name"
                  labelLine={false}
                  label={({ name, value, percent }) =>
                    `${name}: ${value.toLocaleString()} (${(percent * 100).toFixed(1)}%)`
                  }
                />
              </FunnelChart>
            </ResponsiveContainer>
          </Box>
        );
      
      default:
        return null;
    }
    }
  };

  const renderMessage = (message) => {
    if (message.type === 'user') {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
          <Stack direction="row" spacing={2} alignItems="flex-start" sx={{ maxWidth: '70%' }}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                bgcolor: '#0A6ED1',
                color: '#ffffff',
                borderRadius: '6px',
                boxShadow: '0 2px 8px rgba(10, 110, 209, 0.15)',
                transition: 'all 0.3s ease',
                '&:hover': {
                  bgcolor: '#0854A0',
                  boxShadow: '0 4px 12px rgba(10, 110, 209, 0.25)',
                  transform: 'translateY(-1px)',
                }
              }}
            >
              <Typography
                variant="body1"
                sx={{
                  fontWeight: 400,
                  fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif',
                  fontSize: '0.95rem',
                  lineHeight: 1.6,
                  letterSpacing: '0.01em',
                  color: '#ffffff'
                }}
              >
                {message.content}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  display: 'block',
                  mt: 1.5,
                  color: 'rgba(255, 255, 255, 0.7)',
                  fontFamily: '"SF Pro Display", "Inter", sans-serif',
                  fontSize: '0.75rem',
                  fontWeight: 300
                }}
              >
                {message.timestamp.toLocaleTimeString()}
              </Typography>
            </Paper>
            <Avatar sx={{ bgcolor: 'grey.500' }}>
              <PersonIcon />
            </Avatar>
          </Stack>
        </Box>
      );
    }

    // Assistant message
    return (
      <Box sx={{ mb: 3 }}>
        <Box sx={{ flex: 1, maxWidth: '100%' }}>
            {/* Main message - Enhanced Summary */}
            <Card
              elevation={2}
              sx={{
                mb: 2,
                bgcolor: 'background.paper',
              }}
            >
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Stack direction="row" spacing={1.5} alignItems="flex-start">
                  <img src={axisAiLogo} alt="Axis AI" style={{ height: 72, width: 'auto', objectFit: 'contain' }} />
                  <Box sx={{ flex: 1 }}>
                    <Box
                      sx={{
                        lineHeight: 1.8,
                        color: 'text.primary',
                        fontSize: '0.95rem',
                      }}
                    >
                      {(() => {
                        // Helper function to format text with markdown-style bold
                        const formatText = (text) => {
                          if (!text) return null;

                          // Split by **bold** or *bold* patterns
                          const parts = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);

                          return parts.map((part, idx) => {
                            // Check if this is bold text
                            if (part.startsWith('**') && part.endsWith('**')) {
                              return (
                                <Box key={idx} component="span" sx={{ fontWeight: 700, color: 'text.primary' }}>
                                  {part.slice(2, -2)}
                                </Box>
                              );
                            } else if (part.startsWith('*') && part.endsWith('*')) {
                              return (
                                <Box key={idx} component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>
                                  {part.slice(1, -1)}
                                </Box>
                              );
                            }
                            return part;
                          });
                        };

                        // Split content into sections: headings, paragraphs, and lists
                        const lines = message.content.split('\n');
                        const elements = [];
                        let currentParagraph = '';
                        let inList = false;

                        lines.forEach((line, lineIdx) => {
                          const trimmedLine = line.trim();

                          // Check for markdown headings (#### H4, ### H3, ## H2, # H1)
                          const h4Match = trimmedLine.match(/^####\s+(.+)$/);
                          const h3Match = trimmedLine.match(/^###\s+(.+)$/);
                          const h2Match = trimmedLine.match(/^##\s+(.+)$/);
                          const h1Match = trimmedLine.match(/^#\s+(.+)$/);

                          // Check if this is a list item (numbered, dashed, or bulleted)
                          // Matches: "1. text", "1) text", "- text", "* text", "• text"
                          const listMatch = trimmedLine.match(/^(?:\d+[\.\)]\s+|[-*•]\s+)(.+)$/);

                          if (h4Match) {
                            // Add accumulated paragraph before heading
                            if (currentParagraph.trim()) {
                              elements.push(
                                <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2.5, fontSize: '0.93rem', lineHeight: 1.7, pl: 4 }}>
                                  {formatText(currentParagraph.trim())}
                                </Typography>
                              );
                              currentParagraph = '';
                            }
                            inList = false;

                            elements.push(
                              <Typography key={`h4-${lineIdx}`} variant="subtitle1" component="h4" sx={{ fontWeight: 700, mt: 2.5, mb: 0.75, color: 'text.secondary', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.3px', pl: 3, borderLeft: '3px solid', borderColor: 'grey.300' }}>
                                {formatText(h4Match[1])}
                              </Typography>
                            );
                          } else if (h3Match) {
                            // Add accumulated paragraph before heading
                            if (currentParagraph.trim()) {
                              elements.push(
                                <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2.5, fontSize: '0.93rem', lineHeight: 1.7, pl: 2 }}>
                                  {formatText(currentParagraph.trim())}
                                </Typography>
                              );
                              currentParagraph = '';
                            }
                            inList = false;

                            elements.push(
                              <Typography key={`h3-${lineIdx}`} variant="h6" component="h3" sx={{ fontWeight: 700, mt: 3, mb: 1, color: 'text.primary', fontSize: '1rem', pl: 1.5, position: 'relative', '&:before': { content: '""', position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', width: '4px', height: '60%', bgcolor: 'primary.light', borderRadius: '2px' } }}>
                                {formatText(h3Match[1])}
                              </Typography>
                            );
                          } else if (h2Match) {
                            // Add accumulated paragraph before heading
                            if (currentParagraph.trim()) {
                              elements.push(
                                <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2.5, fontSize: '0.93rem', lineHeight: 1.7 }}>
                                  {formatText(currentParagraph.trim())}
                                </Typography>
                              );
                              currentParagraph = '';
                            }
                            inList = false;

                            elements.push(
                              <Typography key={`h2-${lineIdx}`} variant="h5" component="h2" sx={{ fontWeight: 700, mt: 4, mb: 1.5, color: 'primary.main', fontSize: '1.125rem', borderBottom: '2px solid', borderColor: 'primary.main', pb: 0.75, display: 'inline-block', width: '100%' }}>
                                {formatText(h2Match[1])}
                              </Typography>
                            );
                          } else if (h1Match) {
                            // Add accumulated paragraph before heading
                            if (currentParagraph.trim()) {
                              elements.push(
                                <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2.5, fontSize: '0.93rem', lineHeight: 1.7 }}>
                                  {formatText(currentParagraph.trim())}
                                </Typography>
                              );
                              currentParagraph = '';
                            }
                            inList = false;

                            elements.push(
                              <Typography key={`h1-${lineIdx}`} variant="h4" component="h1" sx={{ fontWeight: 800, mt: 3, mb: 2.5, color: 'primary.dark', fontSize: '1.35rem', letterSpacing: '-0.5px', pb: 1, borderBottom: '3px solid', borderColor: 'primary.dark' }}>
                                {formatText(h1Match[1])}
                              </Typography>
                            );
                          } else if (listMatch) {
                            // Add accumulated paragraph before starting list
                            if (currentParagraph.trim()) {
                              elements.push(
                                <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2 }}>
                                  {formatText(currentParagraph.trim())}
                                </Typography>
                              );
                              currentParagraph = '';
                            }

                            inList = true;
                            // Extract text after the list marker (number, dash, asterisk, bullet)
                            const listItemText = listMatch[1];

                            elements.push(
                              <Typography key={`list-${lineIdx}`} variant="body2" component="div" sx={{ mb: 1, fontSize: '0.93rem', pl: 2 }}>
                                {formatText(listItemText)}
                              </Typography>
                            );
                          } else if (trimmedLine === '') {
                            // Empty line - end current paragraph
                            if (currentParagraph.trim()) {
                              elements.push(
                                <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2 }}>
                                  {formatText(currentParagraph.trim())}
                                </Typography>
                              );
                              currentParagraph = '';
                            }
                            inList = false;
                          } else {
                            // Regular text line
                            if (inList) {
                              // If we were in a list and now we have regular text, close the list
                              inList = false;
                            }
                            currentParagraph += (currentParagraph ? ' ' : '') + trimmedLine;
                          }
                        });

                        // Add any remaining paragraph
                        if (currentParagraph.trim()) {
                          elements.push(
                            <Typography key="para-final" variant="body2" component="div" sx={{ mb: 2 }}>
                              {formatText(currentParagraph.trim())}
                            </Typography>
                          );
                        }

                        return elements.length > 0 ? elements : formatText(message.content);
                      })()}
                    </Box>
                    {message.error && (
                      <Alert severity="error" sx={{ mt: 2 }}>
                        {message.error}
                      </Alert>
                    )}
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: 'block', mt: 1.5, fontStyle: 'italic' }}
                    >
                      {message.timestamp.toLocaleTimeString()}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            {/* Cross-Database Query Indicator */}
            {message.isCrossConnector && (
              <Chip
                icon={<StorageIcon />}
                label="Cross-Database Query"
                size="small"
                color="info"
                sx={{ mb: 1 }}
              />
            )}

            {/* SQL Query Display - Multi-Query or Single Query */}
            {message.isCrossConnector && message.connectorQueries ? (
              // Cross-Connector: Show stacked accordions for each database
              <Box sx={{ mb: 2 }}>
                <MultiQueryAccordion
                  connectorQueries={message.connectorQueries}
                  joinSpec={message.joinSpec}
                  initialResults={message.connectorResults}
                  onResultsUpdate={(newResults) => {
                    // Update message results after re-join
                    updateMessage(message.id, { results: newResults, resultCount: newResults?.length || 0 });
                  }}
                  editorTheme={sqlTheme}
                />
              </Box>
            ) : message.sql ? (
              // Single-Connector: Original accordion with edit mode
              <Accordion sx={{ mb: 2, bgcolor: 'grey.100' }}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="sql-content"
                  id="sql-header"
                  sx={{
                    '& .MuiAccordionSummary-content': {
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }
                  }}
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    <CodeIcon fontSize="small" color="action" />
                    <Typography variant="subtitle2">
                      {editMode[message.id] ? 'Edit SQL Query' : 'View Generated SQL'}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} sx={{ mr: 2 }} onClick={(e) => e.stopPropagation()}>
                    <ToggleButton
                      value="edit"
                      selected={editMode[message.id] || false}
                      onChange={() => {
                        setEditMode(prev => ({ ...prev, [message.id]: !prev[message.id] }));
                        if (!editedSql[message.id]) {
                          setEditedSql(prev => ({ ...prev, [message.id]: message.sql }));
                        }
                      }}
                      size="small"
                      sx={{ height: 28 }}
                    >
                      <EditIcon fontSize="small" sx={{ mr: 0.5 }} />
                      {editMode[message.id] ? 'View' : 'Edit'}
                    </ToggleButton>
                  </Stack>
                </AccordionSummary>
                <AccordionDetails sx={{ bgcolor: editMode[message.id] ? 'background.paper' : 'grey.900', p: 2 }}>
                  {editMode[message.id] ? (
                    <Box>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                        <Stack direction="row" spacing={1}>
                          <ToggleButtonGroup
                            value={sqlTheme}
                            exclusive
                            onChange={(e, v) => v && setSqlTheme(v)}
                            size="small"
                          >
                            <ToggleButton value="github">Light</ToggleButton>
                            <ToggleButton value="monokai">Dark</ToggleButton>
                          </ToggleButtonGroup>
                          <IconButton
                            size="small"
                            onClick={() => copyToClipboard(editedSql[message.id] || message.sql)}
                          >
                            <CopyIcon />
                          </IconButton>
                        </Stack>
                        <Button
                          variant="contained"
                          size="small"
                          startIcon={<PlayArrowIcon />}
                          onClick={() => handleRunModifiedSql(message.id, editedSql[message.id] || message.sql)}
                          disabled={loading}
                        >
                          Run Modified SQL
                        </Button>
                      </Stack>
                      <AceEditor
                        mode="sql"
                        theme={sqlTheme}
                        value={editedSql[message.id] || message.sql}
                        onChange={(value) => setEditedSql(prev => ({ ...prev, [message.id]: value }))}
                        name={`sql-editor-${message.id}`}
                        editorProps={{ $blockScrolling: true }}
                        width="100%"
                        height="200px"
                        fontSize={14}
                        showPrintMargin={false}
                        showGutter={true}
                        highlightActiveLine={true}
                        setOptions={{
                          enableBasicAutocompletion: true,
                          enableLiveAutocompletion: true,
                          enableSnippets: true,
                          showLineNumbers: true,
                          tabSize: 2,
                        }}
                      />
                    </Box>
                  ) : (
                    <>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                        <Typography variant="caption" color="white">SQL Query</Typography>
                        <IconButton size="small" onClick={() => copyToClipboard(message.sql)}>
                          <CopyIcon sx={{ color: 'white', fontSize: 18 }} />
                        </IconButton>
                      </Stack>
                      <Box sx={{
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                        color: 'white',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}>
                        {message.sql}
                      </Box>
                    </>
                  )}
                </AccordionDetails>
              </Accordion>
            ) : null}

            {/* Results Table */}
            {message.results && message.results.length > 0 && (
              <Paper elevation={1} sx={{ p: 2 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="h6">
                    Results ({message.results.length} rows)
                  </Typography>
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={() => downloadCSV(message.results)}
                    >
                      Export CSV
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<InsightsIcon />}
                      onClick={() => handleAnalyzeResults(message)}
                    >
                      View Detailed Results
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="primary"
                      startIcon={<SmartToyIcon />}
                      onClick={() => {
                        // Find the user's question
                        const messageIndex = messages.findIndex(m => m.id === message.id);
                        let userQuestion = '';
                        for (let i = messageIndex - 1; i >= 0; i--) {
                          if (messages[i].type === 'user') {
                            userQuestion = messages[i].content;
                            break;
                          }
                        }
                        // Navigate to agent mode with the question
                        if (onOpenAgentMode) {
                          onOpenAgentMode(userQuestion);
                        }
                      }}
                    >
                      Agent Mode
                    </Button>
                  </Stack>
                </Stack>

                {/* Follow-up Suggestions */}
                {message.followUpSuggestions && message.followUpSuggestions.length > 0 && (
                  <FollowUpSuggestions
                    suggestions={message.followUpSuggestions}
                    onSuggestionClick={(suggestion) => {
                      setInputMessage(suggestion);
                      // Auto-focus input field
                      setTimeout(() => {
                        const inputElement = document.querySelector('input[type="text"]');
                        if (inputElement) {
                          inputElement.focus();
                        }
                      }, 100);
                    }}
                  />
                )}

                {/* Visualization Toggle - Single Button */}
                {message.results && message.results.length > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 3, mb: 2, gap: 2 }}>
                    <Button
                      variant={showVisualization[message.id] ? 'contained' : 'outlined'}
                      startIcon={showVisualization[message.id] ? <TableChartIcon /> : <AutoGraphIcon />}
                      onClick={() => setShowVisualization(prev => ({ ...prev, [message.id]: !prev[message.id] }))}
                      size="medium"
                      sx={{
                        textTransform: 'none',
                        fontWeight: 600,
                        px: 3,
                        py: 1
                      }}
                    >
                      {showVisualization[message.id] ? 'Show Table' : 'Visualize Data'}
                    </Button>
                  </Box>
                )}

                <Box sx={{ width: '100%' }}>
                  {showVisualization[message.id] ? (
                    <PlotlyVisualization
                      data={message.results}
                      title={message.question || 'Query Results Visualization'}
                    />
                  ) : (
                    (() => {
                      try {
                        // Safety check - ensure we have data before creating columns
                        if (!message.results || message.results.length === 0 || !message.results[0]) {
                          return (
                            <Typography variant="body2" sx={{ p: 2 }}>
                              No data to display
                            </Typography>
                          );
                        }

                      const safeRows = message.results.map((row, index) => ({ id: index, ...row }));
                      const safeColumns = Object.keys(message.results[0]).map((key, index) => {
                        // Find a sample value to determine type (check multiple rows if needed)
                        let sampleValue = message.results[0][key];
                        for (let i = 0; i < Math.min(5, message.results.length) && (sampleValue === null || sampleValue === undefined); i++) {
                          sampleValue = message.results[i][key];
                        }
                        
                        const isNumeric = typeof sampleValue === 'number';
                        const keyLower = key.toLowerCase();
                        // Only apply currency formatting to columns that are clearly monetary
                        const isCurrency = keyLower.includes('amount') ||
                                          keyLower.includes('revenue') ||
                                          keyLower.includes('price') ||
                                          keyLower.includes('cost') ||
                                          keyLower.includes('margin') ||
                                          keyLower.includes('profit') ||
                                          keyLower.includes('cogs') ||
                                          keyLower.includes('budget') ||
                                          keyLower.includes('spend') ||
                                          keyLower.includes('fee') ||
                                          keyLower.includes('salary') ||
                                          keyLower.includes('payment');
                        const isFirstColumn = index === 0;
                        
                        return {
                          field: key,
                          headerName: key
                            .split('_')
                            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                            .join(' '),
                          flex: 1,
                          minWidth: 150,
                          type: isNumeric ? 'number' : 'string',
                          align: isFirstColumn ? 'left' : (isNumeric ? 'right' : 'left'),
                          headerAlign: isFirstColumn ? 'left' : (isNumeric ? 'right' : 'left'),
                          renderCell: (params) => {
                            try {
                              // Handle null/undefined values
                              if (params.value === null || params.value === undefined) {
                                return <span style={{ color: '#999', fontStyle: 'italic' }}>null</span>;
                              }
                              
                              if (isNumeric && isCurrency && typeof params.value === 'number') {
                                return `$${params.value.toLocaleString('en-US', {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2
                                })}`;
                              }
                              if (isNumeric && typeof params.value === 'number') {
                                return params.value.toLocaleString('en-US');
                              }
                              return String(params.value);
                            } catch (err) {
                              console.error('Error rendering cell:', err);
                              return String(params.value || '');
                            }
                          }
                        };
                      });

                      return (
                        <DataGrid
                          rows={safeRows}
                          columns={safeColumns}
                          initialState={{
                            pagination: {
                              paginationModel: { pageSize: 10, page: 0 },
                            },
                          }}
                          pageSizeOptions={[10, 25, 50]}
                          density="compact"
                          disableRowSelectionOnClick
                          sx={{
                            '& .MuiDataGrid-cell': {
                              fontSize: '0.875rem',
                            },
                            '& .MuiDataGrid-columnHeaders': {
                              backgroundColor: 'action.hover',
                              fontSize: '0.875rem',
                              fontWeight: 600,
                            },
                          }}
                        />
                      );
                    } catch (err) {
                      console.error('Error rendering DataGrid:', err);
                      return (
                        <Alert severity="error" sx={{ m: 2 }}>
                          Error displaying results: {err.message}
                        </Alert>
                      );
                    }
                  })()
                  )}
                </Box>

                {/* Metadata and Actions - Compact */}
                <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center' }}>
                  {message.metadata && (message.metadata.cost || message.metadata.bytesProcessed) && (
                    <>
                      {message.metadata.cost && (
                        <Chip
                          size="small"
                          label={`Cost: $${message.metadata.cost.toFixed(6)}`}
                          variant="outlined"
                          sx={{ height: 24, fontSize: '0.75rem' }}
                        />
                      )}
                      {message.metadata.bytesProcessed && (
                        <Chip
                          size="small"
                          label={`${(message.metadata.bytesProcessed / 1024 / 1024).toFixed(1)} MB`}
                          variant="outlined"
                          sx={{ height: 24, fontSize: '0.75rem' }}
                        />
                      )}
                    </>
                  )}
                </Stack>
              </Paper>
            )}


            {/* No results message */}
            {message.results && message.results.length === 0 && message.sql && (
              <Paper elevation={1} sx={{ p: 2, bgcolor: 'warning.light' }}>
                <Typography variant="body2" fontWeight="medium" gutterBottom>
                  The query executed successfully but returned no results.
                </Typography>
                {message.emptyResultNote && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {message.emptyResultNote}
                  </Typography>
                )}
              </Paper>
            )}
        </Box>
      </Box>
    );
  };

  // Memoized filtered and grouped conversations
  const groupedConversations = useMemo(() => {
    // Filter conversations based on debounced search query
    const filtered = conversations.filter(conv => {
      if (!debouncedSearchQuery) return true;
      const query = debouncedSearchQuery.toLowerCase();
      return (
        conv.title.toLowerCase().includes(query) ||
        (conv.messages && conv.messages.some(msg => msg.content.toLowerCase().includes(query)))
      );
    });

    // Group the filtered conversations
    return groupConversations(filtered);
  }, [conversations, debouncedSearchQuery]);


  return (
    <Box sx={{ 
      height: '100vh', 
      display: 'flex', 
      position: 'relative', 
      overflow: 'hidden'
    }}>
      {/* Main Content Area */}
      <Box sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <Box sx={{
          p: 2,
          borderBottom: '1px solid #e0e0e0',
          bgcolor: '#fff',
          flexShrink: 0,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            {/* Left section */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {onBackToSearch && (
                <IconButton
                  onClick={onBackToSearch}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(106, 109, 112, 0.1)',
                    '&:hover': { bgcolor: 'rgba(106, 109, 112, 0.2)' }
                  }}
                >
                  <ArrowBackIcon />
                </IconButton>
              )}
              <Box>
                <Typography variant="h6" fontWeight={600} color="#1A2332">
                  AXIS AI
                </Typography>
                <Typography variant="body2" color="#5A6677">
                  {mode === 'chat'
                    ? 'Ask Anything'
                    : 'Conduct comprehensive analysis with AI'}
                </Typography>
              </Box>
            </Box>
          </Box>
        </Box>

        {/* Conditional Content Based on Mode */}
        {mode === 'chat' ? (
          <>
            {/* Sub-tabs for Chat Mode */}
            <Box sx={{ px: 2, bgcolor: '#fff', borderBottom: '1px solid #e0e0e0' }}>
              <Tabs
                value={viewMode}
                onChange={(e, v) => setViewMode(v)}
                sx={{
                  '& .MuiTab-root': {
                    textTransform: 'none',
                    minHeight: '48px',
                    fontSize: '0.9rem',
                    fontWeight: 400,
                    color: '#5A6677',
                    '&.Mui-selected': {
                      color: '#0a6ed1',
                      fontWeight: 500,
                    }
                  },
                  '& .MuiTabs-indicator': {
                    bgcolor: '#0a6ed1',
                    height: 3,
                  }
                }}
              >
                <Tab
                  value="chat"
                  label="Chat"
                  icon={<ChatIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                />
                <Tab
                  value="history"
                  label="Execution History"
                  icon={<HistoryIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                />
              </Tabs>
            </Box>

            {/* Chat View */}
            {viewMode === 'chat' ? (
              <>
                {/* Sample Queries Panel */}
                {showSampleQueries && messages.length === 0 && (
              <Accordion 
            defaultExpanded 
            sx={{ 
              flexShrink: 0, 
              mx: 2, 
              mt: 1,
              mb: 1,
              '& .MuiAccordionSummary-root': {
                minHeight: 40,
                '& .MuiAccordionSummary-content': {
                  margin: '8px 0',
                }
              },
              '& .MuiAccordionDetails-root': {
                pt: 1,
                pb: 2,
              }
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6" sx={{ fontSize: '1rem' }}>
                Sample Queries - Click to try
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                {SAMPLE_QUERIES.map((section) => (
                  <Grid item xs={12} sm={6} md={3} key={section.category}>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'text.secondary' }}>
                        {section.category}
                      </Typography>
                      <Stack spacing={1}>
                        {section.queries.map((query, idx) => (
                          <Chip
                            key={idx}
                            label={query}
                            size="small"
                            onClick={() => setInputMessage(query)}
                            sx={{ 
                              cursor: 'pointer',
                              justifyContent: 'flex-start',
                              height: 'auto',
                              '& .MuiChip-label': {
                                whiteSpace: 'normal',
                                padding: '8px 12px',
                              },
                              '&:hover': {
                                bgcolor: 'primary.light',
                                color: 'primary.contrastText',
                              }
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Messages Area - With Scroll */}
        <Box 
          data-messages-container="true"
          sx={{ 
            flexGrow: 1,
            minHeight: 0, // Important for proper flex behavior
            overflow: 'auto', // Changed from 'hidden' to 'auto' to enable scrolling
            p: 2,
            bgcolor: 'background.default',
            display: 'flex',
            flexDirection: 'column',
            // Set a max height to ensure input area is visible
            maxHeight: 'calc(100vh - 280px)', // Adjust based on header + input area height
            // Custom scrollbar styling
            '&::-webkit-scrollbar': {
              width: '8px',
            },
            '&::-webkit-scrollbar-track': {
              backgroundColor: 'rgba(0, 0, 0, 0.05)',
              borderRadius: '4px',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: 'rgba(0, 0, 0, 0.2)',
              borderRadius: '4px',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
              },
            },
          }}>
          <Box sx={{ maxWidth: 1200, mx: 'auto', width: '100%' }}>
            {/* Empty state message - only show if truly empty (no welcome message) */}
            {messages.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 4, opacity: 0.6 }}>
                <Typography variant="h6" color="text.secondary">
                  Start a conversation by typing below or selecting a sample query
                </Typography>
              </Box>
            )}
            
            {/* Messages - Show all messages now that we have scroll */}
            {messages.map(message => (
              <div key={message.id} id={`message-${message.id}`}>
                {renderMessage(message)}
              </div>
            ))}
            
            {loading && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
                <CircularProgress size={20} />
                <Typography variant="body2" color="text.secondary">
                  Processing your query...
                </Typography>
              </Box>
            )}
          </Box>
        </Box>

        <Divider sx={{ flexShrink: 0 }} />

        {/* Input Area - Fixed */}
        <Paper elevation={3} sx={{ p: 2, borderRadius: 0, flexShrink: 0 }}>
          <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
            <Stack direction="row" spacing={2}>
              <TextField
                fullWidth
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isInitializing ? "Initializing..." : "Ask a question about your data..."}
                disabled={loading || isInitializing}
                variant="outlined"
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2,
                  }
                }}
              />
              <Button
                variant="contained"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || loading || isInitializing}
                sx={{ 
                  borderRadius: 2, 
                  px: 3,
                  minWidth: 100
                }}
                endIcon={<SendIcon />}
              >
                Send
              </Button>
            </Stack>
          </Box>
        </Paper>
              </>
            ) : (
              /* History View */
              <Box sx={{ flex: 1, p: 2, overflow: 'auto' }}>
                <QueryLogger />
              </Box>
            )}
          </>
        ) : (
          /* Research Mode */
          <Box sx={{ 
            flex: 1, 
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 3,
            p: 3
          }}>
            <Box sx={{ textAlign: 'center', maxWidth: 600 }}>
              <ResearchIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.5, mb: 1 }}>
                <Typography variant="h4">
                  Deep Research
                </Typography>
                <Chip
                  label="BETA"
                  size="small"
                  sx={{
                    bgcolor: 'warning.light',
                    color: 'warning.dark',
                    fontWeight: 700,
                    fontSize: '0.7rem',
                    height: 22
                  }}
                />
              </Box>
              <Typography variant="caption" color="warning.main" sx={{ display: 'block', mb: 2, fontStyle: 'italic' }}>
                Undergoing Pilot - Your feedback helps us improve
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                Ask complex financial questions that require comprehensive analysis.
                Our AI agents will collaborate to provide detailed insights with data validation,
                trend analysis, and actionable recommendations.
              </Typography>
            </Box>
            
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                size="large"
                startIcon={<ResearchIcon />}
                onClick={() => {
                  setShowDeepResearch(true);
                  setDeepResearchQuestion('');
                }}
              >
                Start New Research
              </Button>
              
              <Button
                variant="outlined"
                size="large"
                startIcon={<HistoryIcon />}
                onClick={() => {
                  // TODO: Show research history
                  console.log('Show research history');
                }}
              >
                View Research History
              </Button>
            </Stack>
            
            <Box sx={{ mt: 4, maxWidth: 800 }}>
              <Typography variant="h6" gutterBottom>
                Example Research Questions:
              </Typography>
              <Grid container spacing={2}>
                {[
                  "Analyze our Q3 revenue variance and identify the key drivers behind performance changes",
                  "Compare our operating margins across different product lines and recommend optimization strategies",
                  "Investigate the relationship between marketing spend and customer acquisition cost trends",
                  "Evaluate the financial impact of our supply chain initiatives on COGS and profitability"
                ].map((question, index) => (
                  <Grid item xs={12} sm={6} key={index}>
                    <Paper 
                      sx={{ 
                        p: 2, 
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' }
                      }}
                      onClick={() => {
                        setDeepResearchQuestion(question);
                        setShowDeepResearch(true);
                      }}
                    >
                      <Typography variant="body2">
                        {question}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Box>
          </Box>
        )}
      </Box>
      
      
      {/* Result Analysis Dialog */}
      <Dialog
        open={openAnalysisDialog}
        onClose={() => setOpenAnalysisDialog(false)}
        maxWidth="lg"
        fullWidth
        fullScreen={false}
        PaperProps={{
          sx: { 
            minHeight: { xs: '100vh', sm: '80vh' },
            maxHeight: { xs: '100vh', sm: '90vh' },
          }
        }}
      >
        <DialogTitle sx={{ 
          borderBottom: 1, 
          borderColor: 'divider',
          pb: 2,
        }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <InsightsIcon color="primary" />
              <Typography variant="h5" fontWeight="bold">
                AI Analysis Results
              </Typography>
            </Stack>
            <IconButton 
              onClick={() => setOpenAnalysisDialog(false)}
              size="small"
            >
              <CloseIcon />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          {activeAnalysis || analysisLoading ? (
            <ResultAnalysis
              analysis={activeAnalysis}
              loading={analysisLoading}
              onFollowUpClick={handleFollowUpQuestion}
            />
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Mantrax Detailed Results Dialog */}
      <Dialog
        open={showDetailedResults}
        onClose={() => setShowDetailedResults(false)}
        maxWidth="xl"
        fullWidth
        PaperProps={{
          sx: { 
            minHeight: '80vh',
            maxHeight: '90vh',
          }
        }}
      >
        <DialogContent sx={{ p: 0 }}>
          {showDetailedResults && detailedResultsData && (
            <MantraxResultsView
              query={detailedResultsData.query}
              sql={detailedResultsData.sql}
              results={detailedResultsData.results}
              metadata={detailedResultsData.metadata}
              onClose={() => setShowDetailedResults(false)}
            />
          )}
        </DialogContent>
      </Dialog>
      
      {/* Enhanced Analytics Modal */}
      <EnhancedAnalyticsModal
        open={showAnalyticsModal}
        onClose={() => setShowAnalyticsModal(false)}
        initialQuery={analyticsModalData?.query || ''}
        initialData={analyticsModalData?.results || null}
        mode={analyticsModalMode}
        conversationId={conversationId}
        onQueryExecute={(newResults) => {
          // Optional: Update the chat with new results if needed
          console.log('New results from analytics modal:', newResults);
        }}
      />

      {/* Deep Research Interface */}
      <DeepResearchInterface
        open={showDeepResearch}
        onClose={() => setShowDeepResearch(false)}
        initialQuestion={deepResearchQuestion}
        onResults={(results) => {
          console.log('Deep research results:', results);
          // Optionally add results to chat
          if (results.executive_summary) {
            const researchMessage = {
              id: Date.now(),
              type: 'assistant',
              content: `Deep Research Complete: ${results.executive_summary}`,
              metadata: {
                type: 'deep_research_result',
                research_id: results.research_id,
                confidence_level: results.confidence_level,
                data_quality: results.data_quality
              },
            };
            addMessage(researchMessage);
          }
        }}
      />

      {/* Dashboard Creation Preview from Chat */}
      <DashboardCreationPreview
        open={dashboardPreviewOpen}
        onClose={() => {
          setDashboardPreviewOpen(false);
          setDashboardPreviewData(null);
        }}
        previewData={dashboardPreviewData}
        originalQuery={dashboardPreviewQuery}
        onRefresh={async () => {
          // Regenerate the preview
          try {
            const response = await apiService.createDashboardFromConversation(dashboardPreviewQuery);
            setDashboardPreviewData(response.data);
          } catch (error) {
            console.error('Failed to refresh dashboard preview:', error);
          }
        }}
      />
    </Box>
  );
});

export default SimpleChatInterface;