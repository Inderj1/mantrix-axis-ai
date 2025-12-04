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
  DialogContentText,
  DialogActions,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip as MuiTooltip,
  Tab,
  Tabs,
  Card,
  CardContent,
  useTheme,
  alpha,
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
  Warning as WarningIcon,
  TrendingUp as TrendingUpIcon,
  AccountBalance as AccountBalanceIcon,
  People as PeopleIcon,
  Speed as SpeedIcon,
  AutoAwesome as AutoAwesomeIcon,
  Map as MapIcon,
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
import QueryProgress from './QueryProgress';
import EnhancedResultsCard from './results/EnhancedResultsCard';
import AIExplanation from './results/AIExplanation';
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

// Sample queries for quick access with soft, friendly colors
const SAMPLE_QUERIES = [
  {
    category: "Revenue Analysis",
    icon: "TrendingUp",
    color: "#10b981",
    bgColor: "rgba(16, 185, 129, 0.06)",
    queries: [
      "What's our monthly recurring revenue?",
      "Show revenue by product line",
      "Compare this year vs last year revenue"
    ]
  },
  {
    category: "Cost Management",
    icon: "AccountBalance",
    color: "#3b82f6",
    bgColor: "rgba(59, 130, 246, 0.06)",
    queries: [
      "What are our biggest expense categories?",
      "Show COGS trend over time",
      "Calculate gross margin by product"
    ]
  },
  {
    category: "Customer Insights",
    icon: "People",
    color: "#8b5cf6",
    bgColor: "rgba(139, 92, 246, 0.06)",
    queries: [
      "Who are our top customers by lifetime value?",
      "Show customer acquisition trends",
      "Analyze churn rate by segment"
    ]
  },
  {
    category: "Performance Metrics",
    icon: "Speed",
    color: "#f59e0b",
    bgColor: "rgba(245, 158, 11, 0.06)",
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
  const theme = useTheme();

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
    queryProgress,
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
    sendQueryStreaming,
    resetQueryProgress,
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

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  // User persona state for personalized Quick Actions
  const [userPersona, setUserPersona] = useState(null);

  // Fetch user persona on mount
  useEffect(() => {
    const fetchUserPersona = async () => {
      try {
        const response = await apiService.getUserProfile('persona');
        const profile = response.data || response;
        if (profile && profile.role) {
          setUserPersona(profile);
        }
      } catch (error) {
        console.log('No persona found, using default Quick Actions');
      }
    };
    fetchUserPersona();
  }, []);

  // Persona-based Quick Actions
  const getQuickActions = useMemo(() => {
    const defaultActions = [
      { icon: <TrendingUpIcon />, title: "Revenue Trends", desc: "Show me monthly revenue trends", color: '#0176D3' },
      { icon: <PeopleIcon />, title: "Top Customers", desc: "Who are our top 10 customers?", color: '#2E844A' },
      { icon: <BarChartIcon />, title: "Order Analytics", desc: "What's the average order value?", color: '#FE9339' },
      { icon: <MapIcon />, title: "Regional Sales", desc: "Compare sales by region", color: '#BA01FF' },
    ];

    const personaActions = {
      cfo: [
        { icon: <AccountBalanceIcon />, title: "Financial Overview", desc: "Show me the P&L summary for this quarter", color: '#0176D3' },
        { icon: <TrendingUpIcon />, title: "Cash Flow", desc: "What's our current cash flow position?", color: '#2E844A' },
        { icon: <BarChartIcon />, title: "Budget Variance", desc: "Compare actual vs budget by department", color: '#FE9339' },
        { icon: <SpeedIcon />, title: "Financial KPIs", desc: "Show key financial ratios and metrics", color: '#BA01FF' },
      ],
      coo: [
        { icon: <SpeedIcon />, title: "Operations KPIs", desc: "Show me key operational metrics", color: '#0176D3' },
        { icon: <TimelineIcon />, title: "Process Efficiency", desc: "What's our order fulfillment time?", color: '#2E844A' },
        { icon: <StorageIcon />, title: "Inventory Status", desc: "Show current inventory levels by category", color: '#FE9339' },
        { icon: <TrendingUpIcon />, title: "Capacity Utilization", desc: "What's our production capacity utilization?", color: '#BA01FF' },
      ],
      sales_manager: [
        { icon: <TrendingUpIcon />, title: "Sales Pipeline", desc: "Show me the current sales pipeline", color: '#0176D3' },
        { icon: <PeopleIcon />, title: "Top Performers", desc: "Who are my top performing sales reps?", color: '#2E844A' },
        { icon: <MapIcon />, title: "Regional Performance", desc: "Compare sales by region this quarter", color: '#FE9339' },
        { icon: <BarChartIcon />, title: "Win Rate Analysis", desc: "What's our win rate by product category?", color: '#BA01FF' },
      ],
      supply_chain_manager: [
        { icon: <StorageIcon />, title: "Inventory Health", desc: "Show me inventory turnover by product", color: '#0176D3' },
        { icon: <TrendingUpIcon />, title: "Supplier Performance", desc: "Which suppliers have the best on-time delivery?", color: '#2E844A' },
        { icon: <SpeedIcon />, title: "Lead Times", desc: "What's our average lead time by supplier?", color: '#FE9339' },
        { icon: <BarChartIcon />, title: "Stock Levels", desc: "Show items below reorder point", color: '#BA01FF' },
      ],
      marketing_manager: [
        { icon: <TrendingUpIcon />, title: "Campaign ROI", desc: "Show me marketing campaign performance", color: '#0176D3' },
        { icon: <PeopleIcon />, title: "Customer Segments", desc: "Analyze customer segments by value", color: '#2E844A' },
        { icon: <BarChartIcon />, title: "Channel Performance", desc: "Compare revenue by marketing channel", color: '#FE9339' },
        { icon: <MapIcon />, title: "Market Analysis", desc: "Show sales trends by market segment", color: '#BA01FF' },
      ],
      analyst: [
        { icon: <AnalyticsIcon />, title: "Data Overview", desc: "Show me the main data summary", color: '#0176D3' },
        { icon: <TrendingUpIcon />, title: "Trend Analysis", desc: "Identify key trends in the data", color: '#2E844A' },
        { icon: <BarChartIcon />, title: "Comparative Analysis", desc: "Compare this period vs last period", color: '#FE9339' },
        { icon: <ScatterPlotIcon />, title: "Correlations", desc: "Find correlations in the data", color: '#BA01FF' },
      ],
    };

    if (userPersona?.role && personaActions[userPersona.role]) {
      return personaActions[userPersona.role];
    }
    return defaultActions;
  }, [userPersona]);

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

    // Use store's sendQueryStreaming - handles everything with live progress:
    // - Creating conversation if needed
    // - Adding user/assistant messages
    // - Streaming API call with progress updates
    // - Error handling
    // - Updating conversations list
    const question = inputMessage;
    setInputMessage('');

    // Scroll when user sends message
    setTimeout(scrollToBottom, 50);

    // Use streaming query for real-time progress feedback
    const result = await sendQueryStreaming(question);

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
  const handleClearAllConversations = () => {
    setConfirmDialog({
      open: true,
      title: 'Clear All Conversations',
      message: 'Are you sure you want to clear all conversations? This cannot be undone.',
      onConfirm: async () => {
        await clearAllConversations();
        setConfirmDialog(prev => ({ ...prev, open: false }));
      },
    });
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
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 3 }}>
          <Box
            sx={{
              maxWidth: '70%',
              p: 2,
              px: 3,
              bgcolor: '#f3f4f6',
              borderRadius: '16px',
            }}
          >
            <Typography
              sx={{
                fontSize: '0.9375rem',
                lineHeight: 1.6,
                color: '#111827',
              }}
            >
              {message.content}
            </Typography>
          </Box>
        </Box>
      );
    }

    // Assistant message - Simple plain text
    return (
      <Box sx={{ mb: 3, maxWidth: '85%' }}>
        {message.content && (
          <Typography
            sx={{
              fontSize: '0.9375rem',
              lineHeight: 1.7,
              color: '#374151',
              whiteSpace: 'pre-wrap',
            }}
          >
            {message.content}
          </Typography>
        )}

            {/* Error display */}
            {message.error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {message.error}
              </Alert>
            )}

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

            {/* Enhanced Results Card */}
            {message.results && message.results.length > 0 && (
              <Box>
                <EnhancedResultsCard
                  message={message}
                  onViewAnalysis={() => handleAnalyzeResults(message)}
                  onViewDetailed={() => handleViewDetailedResults(message)}
                  showChart={true}
                  chartComponent={
                    <PlotlyVisualization
                      data={message.results}
                      title={message.question || 'Query Results Visualization'}
                    />
                  }
                />

                {/* Follow-up Suggestions */}
                {message.followUpSuggestions && message.followUpSuggestions.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <FollowUpSuggestions
                      suggestions={message.followUpSuggestions}
                      onSuggestionClick={(suggestion) => {
                        setInputMessage(suggestion);
                        setTimeout(() => {
                          const inputElement = document.querySelector('input[type="text"]');
                          if (inputElement) {
                            inputElement.focus();
                          }
                        }, 100);
                      }}
                    />
                  </Box>
                )}

                {/* Agent Mode Button */}
                {onOpenAgentMode && (
                  <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="primary"
                      startIcon={<SmartToyIcon />}
                      onClick={() => {
                        const messageIndex = messages.findIndex(m => m.id === message.id);
                        let userQuestion = '';
                        for (let i = messageIndex - 1; i >= 0; i--) {
                          if (messages[i].type === 'user') {
                            userQuestion = messages[i].content;
                            break;
                          }
                        }
                        onOpenAgentMode(userQuestion);
                      }}
                      sx={{ textTransform: 'none' }}
                    >
                      Continue in Agent Mode
                    </Button>
                  </Box>
                )}

                {/* Metadata Chips */}
                {message.metadata && (message.metadata.cost || message.metadata.bytesProcessed) && (
                  <Stack direction="row" spacing={1} sx={{ mt: 2, alignItems: 'center' }}>
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
                  </Stack>
                )}
              </Box>
            )}


            {/* Empty Results - Enhanced UI */}
            {message.results && message.results.length === 0 && message.sql && (
              <Paper
                elevation={0}
                sx={{
                  borderRadius: 2,
                  border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`,
                  overflow: 'hidden',
                }}
              >
                {/* Header */}
                <Box
                  sx={{
                    px: 2.5,
                    py: 1.5,
                    bgcolor: alpha(theme.palette.warning.main, 0.08),
                    borderBottom: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                  }}
                >
                  <InfoIcon sx={{ color: theme.palette.warning.main, fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight={600}>
                    No Results Found
                  </Typography>
                </Box>

                {/* Content */}
                <Box sx={{ p: 2.5 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    The query executed successfully but didn't match any data.
                  </Typography>

                  {/* AI Explanation */}
                  {message.emptyResultNote && (
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        mb: 2,
                        borderRadius: 1.5,
                        bgcolor: alpha(theme.palette.info.main, 0.04),
                        borderLeft: `3px solid ${theme.palette.info.main}`,
                      }}
                    >
                      <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                        {message.emptyResultNote}
                      </Typography>
                    </Paper>
                  )}

                  {/* Follow-up Suggestions - NOW SHOWN FOR EMPTY RESULTS */}
                  {message.followUpSuggestions && message.followUpSuggestions.length > 0 && (
                    <FollowUpSuggestions
                      suggestions={message.followUpSuggestions}
                      onSuggestionClick={(suggestion) => {
                        setInputMessage(suggestion);
                        setTimeout(() => {
                          const inputElement = document.querySelector('input[type="text"]');
                          if (inputElement) {
                            inputElement.focus();
                          }
                        }, 100);
                      }}
                    />
                  )}
                </Box>
              </Paper>
            )}
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
      height: 'calc(100vh - 56px)',
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
        {/* Header - Clean Salesforce Style */}
        <Box sx={{
          px: 3,
          py: 2,
          bgcolor: '#ffffff',
          borderBottom: '1px solid #e5e5e5',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
        }}>
          {onBackToSearch && (
            <IconButton onClick={onBackToSearch} size="small" sx={{ color: '#706e6b' }}>
              <ArrowBackIcon />
            </IconButton>
          )}
          <Box sx={{
            width: 36,
            height: 36,
            borderRadius: '8px',
            bgcolor: '#032D60',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <AutoAwesomeIcon sx={{ color: '#1B96FF', fontSize: 20 }} />
          </Box>
          <Typography sx={{ fontWeight: 600, color: '#032D60', fontSize: '1.1rem' }}>
            AXIS AI
          </Typography>
        </Box>

        {/* Conditional Content Based on Mode */}
        {mode === 'chat' ? (
          <>
            {/* Sub-tabs - Salesforce Style */}
            <Box sx={{ px: 3, bgcolor: '#ffffff', borderBottom: '1px solid #dddbda' }}>
              <Tabs
                value={viewMode}
                onChange={(e, v) => setViewMode(v)}
                sx={{
                  '& .MuiTab-root': {
                    textTransform: 'none',
                    minHeight: '48px',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    color: '#706e6b',
                    px: 2,
                    '&.Mui-selected': {
                      color: '#0176D3',
                    }
                  },
                  '& .MuiTabs-indicator': {
                    bgcolor: '#0176D3',
                    height: 3,
                  }
                }}
              >
                <Tab value="chat" label="Chat" />
                <Tab value="history" label="History" />
              </Tabs>
            </Box>

            {/* Chat View */}
            {viewMode === 'chat' ? (
              <>
                {/* Welcome Section - Salesforce Style */}
                {showSampleQueries && messages.length === 0 && (
                  <Box sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    p: 3,
                    bgcolor: '#f3f3f3',
                    minHeight: 'calc(100vh - 336px)',
                    overflow: 'auto',
                  }}>
                    {/* Hero Section */}
                    <Box sx={{
                      bgcolor: '#ffffff',
                      borderRadius: '8px',
                      p: 4,
                      mb: 3,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                      border: '1px solid #e5e5e5',
                    }}>
                      <Box sx={{
                        width: 64,
                        height: 64,
                        borderRadius: '12px',
                        bgcolor: '#e8f4fd',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}>
                        <AutoAwesomeIcon sx={{ fontSize: 32, color: '#0176D3' }} />
                      </Box>
                      <Box>
                        <Typography sx={{ fontWeight: 700, fontSize: '1.5rem', mb: 0.5, color: '#032D60' }}>
                          Welcome to AXIS AI
                        </Typography>
                        <Typography sx={{ color: '#706e6b', fontSize: '0.95rem' }}>
                          Your intelligent assistant for data insights. Ask questions in natural language and get instant answers.
                        </Typography>
                      </Box>
                    </Box>

                    {/* Quick Actions Grid */}
                    <Typography sx={{ fontWeight: 700, color: '#032D60', fontSize: '1rem', mb: 2 }}>
                      Quick Actions
                    </Typography>
                    <Box sx={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                      gap: 2,
                      mb: 3,
                    }}>
                      {getQuickActions.map((item, idx) => (
                        <Box
                          key={idx}
                          onClick={() => setInputMessage(item.desc)}
                          sx={{
                            p: 2.5,
                            bgcolor: '#ffffff',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                            transition: 'all 0.15s ease',
                            border: '1px solid transparent',
                            '&:hover': {
                              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                              borderColor: item.color,
                              transform: 'translateY(-2px)',
                            },
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                            <Box sx={{
                              width: 44,
                              height: 44,
                              borderRadius: '8px',
                              bgcolor: `${item.color}15`,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: item.color,
                              flexShrink: 0,
                            }}>
                              {item.icon}
                            </Box>
                            <Box>
                              <Typography sx={{ fontWeight: 600, color: '#032D60', fontSize: '0.95rem', mb: 0.5 }}>
                                {item.title}
                              </Typography>
                              <Typography sx={{ color: '#706e6b', fontSize: '0.8rem' }}>
                                {item.desc}
                              </Typography>
                            </Box>
                          </Box>
                        </Box>
                      ))}
                    </Box>

                    {/* Getting Started Section */}
                    <Typography sx={{ fontWeight: 700, color: '#032D60', fontSize: '1rem', mb: 2 }}>
                      Getting Started
                    </Typography>
                    <Box sx={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: 2,
                    }}>
                      {[
                        { icon: <ChatIcon />, title: "Ask Questions", desc: "Type natural language questions about your data" },
                        { icon: <InsightsIcon />, title: "Get Insights", desc: "AI analyzes and visualizes your data automatically" },
                        { icon: <DashboardIcon />, title: "Build Dashboards", desc: "Save queries and create interactive dashboards" },
                      ].map((item, idx) => (
                        <Box key={idx} sx={{ p: 2.5, bgcolor: '#ffffff', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                            <Box sx={{ color: '#0176D3' }}>{item.icon}</Box>
                            <Typography sx={{ fontWeight: 600, color: '#032D60', fontSize: '0.9rem' }}>{item.title}</Typography>
                          </Box>
                          <Typography sx={{ color: '#706e6b', fontSize: '0.8rem' }}>{item.desc}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}

        {/* Messages Area - Clean White */}
        <Box
          data-messages-container="true"
          sx={{
            flexGrow: 1,
            minHeight: 0,
            overflow: 'auto',
            p: 3,
            bgcolor: '#ffffff',
            display: 'flex',
            flexDirection: 'column',
            maxHeight: 'calc(100vh - 336px)',
            // Minimal scrollbar
            '&::-webkit-scrollbar': {
              width: '6px',
            },
            '&::-webkit-scrollbar-track': {
              backgroundColor: 'transparent',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: '#e5e7eb',
              borderRadius: '10px',
              '&:hover': {
                backgroundColor: '#d1d5db',
              },
            },
          }}>
          <Box sx={{ maxWidth: 1200, mx: 'auto', width: '100%' }}>
            {/* Empty state is now handled by the welcome cards above */}
            
            {/* Messages - Show all messages now that we have scroll */}
            {messages.map(message => (
              <div key={message.id} id={`message-${message.id}`}>
                {renderMessage(message)}
              </div>
            ))}
            
            {/* Show streaming progress or simple loading indicator */}
            {/* Show QueryProgress when streaming, loading, or briefly after completion */}
            {(queryProgress.isStreaming || queryProgress.phase) && (
              <Box sx={{ mt: 2 }}>
                <QueryProgress
                  currentPhase={queryProgress.phase}
                  progress={queryProgress.progress}
                  message={queryProgress.message}
                  detail={queryProgress.detail}
                  sql={queryProgress.sql}
                  error={queryProgress.phase === 'error' ? queryProgress.message : null}
                />
              </Box>
            )}
            {/* Fallback loading indicator when not streaming */}
            {loading && !queryProgress.isStreaming && !queryProgress.phase && (
              <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                <CircularProgress size={20} />
                <Typography variant="body2" color="text.secondary">
                  Processing your query...
                </Typography>
              </Box>
            )}
          </Box>
        </Box>

        {/* Input Area - Salesforce Style */}
        <Box sx={{ p: 2, bgcolor: '#ffffff', borderTop: '1px solid #dddbda', flexShrink: 0 }}>
          <Box sx={{ maxWidth: 900, mx: 'auto' }}>
            <Box sx={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 1.5,
              p: 1.5,
              pl: 2,
              borderRadius: '8px',
              border: '1px solid #dddbda',
              bgcolor: '#ffffff',
              boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
              '&:focus-within': {
                borderColor: '#0176D3',
                boxShadow: '0 0 0 1px #0176D3',
              },
            }}>
              <TextField
                fullWidth
                multiline
                maxRows={4}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your data..."
                disabled={loading || isInitializing}
                variant="standard"
                InputProps={{ disableUnderline: true }}
                sx={{
                  '& .MuiInputBase-root': { fontSize: '0.95rem', lineHeight: 1.5, py: 0.5 },
                  '& .MuiInputBase-input': { '&::placeholder': { color: '#706e6b', opacity: 1 } },
                }}
              />
              <IconButton
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || loading || isInitializing}
                sx={{
                  width: 44,
                  height: 44,
                  bgcolor: inputMessage.trim() && !loading ? '#0176D3' : '#ecebea',
                  color: 'white',
                  borderRadius: '8px',
                  '&:hover': { bgcolor: '#014486' },
                  '&.Mui-disabled': { color: '#b0adab' },
                }}
              >
                {loading ? <CircularProgress size={20} sx={{ color: 'white' }} /> : <SendIcon sx={{ fontSize: 20 }} />}
              </IconButton>
            </Box>
            <Typography sx={{ mt: 1, textAlign: 'center', color: '#706e6b', fontSize: '0.75rem' }}>
              Press Enter to send • Shift+Enter for new line
            </Typography>
          </Box>
        </Box>
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
              <ResearchIcon sx={{ fontSize: 64, color: '#3b82f6', mb: 2 }} />
              <Typography variant="h4" sx={{ mb: 2 }}>
                Deep Research
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
        PaperProps={{
          sx: {
            minHeight: { xs: '100vh', sm: '80vh' },
            maxHeight: { xs: '100vh', sm: '90vh' },
          }
        }}
      >
        <DialogTitle>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <InsightsIcon color="primary" />
              <Typography variant="h6" fontWeight="bold">
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
        <DialogContent>
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

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'warning.main' }}>
          <WarningIcon />
          {confirmDialog.title}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog(prev => ({ ...prev, open: false }))}>
            Cancel
          </Button>
          <Button onClick={confirmDialog.onConfirm} variant="contained" color="warning" autoFocus>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
});

export default SimpleChatInterface;