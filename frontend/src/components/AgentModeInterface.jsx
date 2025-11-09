import React, { useState, useRef, useEffect, useMemo, useCallback, forwardRef, useImperativeHandle } from 'react';
import { useUser } from '@clerk/clerk-react';
import {
  Box,
  Paper,
  TextField,
  Autocomplete,
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as PendingIcon,
  Brightness1 as DotIcon,
  AccountTree as AccountTreeIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  TableChart as TableIcon,
  PivotTableChart as PivotIcon,
  LineStyle as LineChartIcon2,
} from '@mui/icons-material';
import { DataGrid } from '@mui/x-data-grid';
import PivotTableUI from 'react-pivottable/PivotTableUI';
import 'react-pivottable/pivottable.css';
import TableRenderers from 'react-pivottable/TableRenderers';
import { apiService } from '../services/api';
import ResultAnalysis from './ResultAnalysis';
import DeepResearchInterface from './DeepResearchInterface';
import QueryLogger from './QueryLogger';
import EnhancedAnalyticsModal from './EnhancedAnalyticsModal';
import MantraxResultsView from './MantraxResultsView';
import FollowUpSuggestions from './FollowUpSuggestions';
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

// No conversation grouping needed - Agent Mode has no history

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

// Smart completion patterns - complete questions based on what user types
const SMART_COMPLETIONS = {
  'show': [
    'profitability by customer segment',
    'revenue trends over time',
    'top performing products this quarter',
    'margin analysis by product line',
    'cost breakdown by department'
  ],
  'analyze': [
    'customer lifetime value trends',
    'product mix profitability',
    'seasonal sales patterns',
    'margin compression factors',
    'inventory turnover rates'
  ],
  'compare': [
    'this quarter vs last quarter performance',
    'regional sales effectiveness',
    'product line margins',
    'customer acquisition costs across channels'
  ],
  'what': [
    'are the fastest growing customer segments?',
    'is driving margin erosion?',
    'products have the highest contribution margin?',
    'are the sales trends by region?'
  ],
  'customer': [
    'profitability segmentation analysis',
    'lifetime value distribution',
    'churn risk indicators',
    'acquisition cost efficiency'
  ],
  'product': [
    'performance across all channels',
    'margin contribution analysis',
    'inventory health metrics',
    'cannibalization impact'
  ],
  'revenue': [
    'growth drivers and detractors',
    'mix variance analysis',
    'forecasted vs actual performance',
    'concentration risk by customer'
  ],
  'profit': [
    'margin trends by segment',
    'waterfall from gross to net',
    'improvement opportunities',
    'variance from plan analysis'
  ],
};

const AgentModeInterface = forwardRef((props, ref) => {
  const { onConversationsChange, onConversationIdChange, onLoadingChange, onBackToSearch, initialQuestion, onQuestionUsed } = props;
  // Get authenticated user from Clerk
  const { user, isLoaded: isUserLoaded } = useUser();

  // Derive userId from authenticated user or use email as fallback
  const userId = user?.id || user?.primaryEmailAddress?.emailAddress || 'default';

  // Pre-populate with welcome message
  const [messages, setMessages] = useState([{
    id: Date.now(),
    type: 'assistant',
    content: 'Welcome to Agent Mode! I\'m your autonomous AI agent capable of multi-step reasoning, planning, and execution. Describe complex tasks and I\'ll break them down into steps, execute them, and provide comprehensive insights.',
    timestamp: new Date(),
  }]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState([]);
  // No conversation history for Agent Mode - removed conversationId, conversations, loadingConversations
  const [openAnalysisDialog, setOpenAnalysisDialog] = useState(false);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [activeMessageId, setActiveMessageId] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [showSampleQueries, setShowSampleQueries] = useState(true);
  const [mode, setMode] = useState('chat'); // 'chat' or 'research'
  // No viewMode needed - removed history view
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
  const [tableViewMode, setTableViewMode] = useState({}); // Track view mode per query index
  const [tableChartType, setTableChartType] = useState({}); // Track chart type per query index
  const [tablePivotState, setTablePivotState] = useState({}); // Track pivot state per query index
  const initializationRef = useRef(false);

  console.log('AgentModeInterface rendering, mode:', mode, 'userId:', userId);


  // No initialization needed - Agent Mode has no conversation persistence
  // Messages are kept only in current session memory

  // Auto-scroll to latest message
  useEffect(() => {
    const scrollTimeout = setTimeout(() => {
      const messagesContainer = document.querySelector('[data-messages-container="true"]');
      if (messagesContainer) {
        messagesContainer.scrollTo({
          top: messagesContainer.scrollHeight,
          behavior: 'smooth'
        });
      }
    }, 100);

    return () => clearTimeout(scrollTimeout);
  }, [messages, loading]); // Scroll when messages change or loading state changes

  // Handle initial question from chat interface
  useEffect(() => {
    if (initialQuestion) {
      setInputMessage(initialQuestion);
      if (onQuestionUsed) {
        onQuestionUsed();
      }
    }
  }, [initialQuestion, onQuestionUsed]);

  // No conversation management functions - Agent Mode has no persistence

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

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const queryText = inputMessage;
    setInputMessage('');
    setLoading(true);

    // Create placeholder message that will be updated progressively
    const responseMessageId = (Date.now() + 1).toString();
    const initialResponseMessage = {
      id: responseMessageId,
      type: 'assistant',
      content: '',
      streaming: true,
      statusMessages: [],
      agentsUsed: [],
      routing: {},
      results: [],
      resultCount: 0,
      sql: null,
      allSqlQueries: [],
      executionPlan: null,
      executionLogs: [],
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, initialResponseMessage]);

    // Immediately scroll when user sends message
    setTimeout(scrollToBottom, 50);

    try {
      // Call streaming agent analysis endpoint
      console.log('Starting streaming query to agent system:', queryText);
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/v1/agents/analyze-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: queryText,
          context: {}
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // Read stream
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('Stream complete');
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim() || line.startsWith(':')) continue; // Skip empty and heartbeat

          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const event = JSON.parse(jsonStr);
              console.log('SSE Event:', event);

              // Update message based on event type
              setMessages(prev => prev.map(msg => {
                if (msg.id !== responseMessageId) return msg;

                const updated = { ...msg };

                switch (event.type) {
                  case 'status':
                    updated.statusMessages = [...(updated.statusMessages || []), event.message];
                    // Keep status messages visible, don't replace content
                    if (!updated.content || updated.streaming) {
                      updated.content = event.message;
                    }
                    break;

                  case 'routing':
                    updated.routing = event.data;
                    updated.agentsUsed = event.data.experts || [];
                    updated.statusMessages = [...(updated.statusMessages || []), `Agents: ${event.data.experts?.join(', ') || 'N/A'}`];
                    break;

                  case 'sql_generation':
                    updated.statusMessages = [...(updated.statusMessages || []), `Generating SQL for: ${event.data.query}`];
                    break;

                  case 'sql_execution':
                    updated.statusMessages = [...(updated.statusMessages || []), `Executing query...`];
                    break;

                  case 'query_results':
                    const queryData = event.data;
                    updated.allSqlQueries = [...(updated.allSqlQueries || []), queryData];
                    updated.sql = queryData.sql;
                    updated.results = queryData.results;
                    updated.resultCount = queryData.row_count;
                    updated.statusMessages = [...(updated.statusMessages || []), `Retrieved ${queryData.row_count} rows`];
                    break;

                  case 'execution_plan':
                    updated.executionPlan = event.data;
                    break;

                  case 'execution_log':
                    updated.executionLogs = [...(updated.executionLogs || []), event.data];
                    break;

                  case 'analysis':
                    // Attach insights to the last query in allSqlQueries (don't set message.content to avoid duplication)
                    if (updated.allSqlQueries && updated.allSqlQueries.length > 0) {
                      const lastQueryIndex = updated.allSqlQueries.length - 1;
                      updated.allSqlQueries = updated.allSqlQueries.map((q, idx) =>
                        idx === lastQueryIndex ? { ...q, insights: event.data } : q
                      );
                    }
                    updated.streaming = false;
                    break;

                  case 'complete':
                    const finalData = event.data;
                    // Don't set content here to avoid duplicate display (analysis is already in query.insights)
                    // Only set agentsUsed if we don't already have it from routing event
                    if (!updated.agentsUsed || updated.agentsUsed.length === 0) {
                      updated.agentsUsed = finalData.agents_used || [];
                    }
                    // Keep the initial routing from the routing event, don't override
                    if (!updated.routing || Object.keys(updated.routing).length === 0) {
                      updated.routing = finalData.routing || {};
                    }
                    updated.executionPlan = finalData.execution_plan || updated.executionPlan;
                    updated.executionLogs = finalData.execution_logs || updated.executionLogs;
                    updated.streaming = false;
                    break;

                  case 'error':
                    updated.content = `❌ Error: ${event.error}`;
                    updated.error = event.error;
                    updated.streaming = false;
                    break;
                }

                return updated;
              }));

              // Scroll after each update
              setTimeout(scrollToBottom, 100);

            } catch (parseError) {
              console.error('Failed to parse SSE event:', parseError, jsonStr);
            }
          }
        }
      }

    } catch (error) {
      console.error('Streaming error:', error);
      setMessages(prev => prev.map(msg => {
        if (msg.id !== responseMessageId) return msg;
        return {
          ...msg,
          content: `❌ Sorry, I encountered an error: ${error.message}`,
          error: error.message,
          streaming: false
        };
      }));

      setTimeout(scrollToBottom, 100);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRunModifiedSql = async (messageId, sql) => {
    setLoading(true);
    try {
      const response = await apiService.executeQuery(sql, { isModifiedSql: true });
      const { data } = response;
      
      if (data.error) {
        const errorMessage = {
          id: Date.now() + 1,
          type: 'assistant',
          content: `Error running modified SQL: ${data.error_details?.user_friendly_message || data.error}`,
          error: data.error,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMessage]);
        return;
      }

      // Create a new message for the modified query results
      const resultMessage = {
        id: Date.now() + 1,
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
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, resultMessage]);
      setEditMode(prev => ({ ...prev, [messageId]: false }));
    } catch (error) {
      console.error('Error running modified SQL:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: 'Sorry, I encountered an error running the modified SQL.',
        error: error.response?.data?.detail || error.message,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
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

  // No conversation management functions - Agent Mode has no persistence

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

  // No methods exposed to parent - Agent Mode has no conversation management

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
            {/* Corporate Streaming Progress - Horizontal Stepper */}
            {message.statusMessages && message.statusMessages.length > 0 && (
            <Accordion
              defaultExpanded={true}
              sx={{
                mb: 3,
                background: 'linear-gradient(to bottom, #ffffff, #f8fafc)',
                border: '1px solid',
                borderColor: '#e2e8f0',
                borderRadius: 2,
                '&:before': {
                  display: 'none'
                },
                boxShadow: 2
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{
                  minHeight: 56,
                  '& .MuiAccordionSummary-content': {
                    margin: '12px 0'
                  }
                }}
              >
                {/* Collapsed Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
                  <CheckCircleIcon sx={{ color: '#10b981', fontSize: 18 }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography
                      variant="subtitle1"
                      sx={{
                        fontWeight: 600,
                        color: '#1e293b',
                        fontSize: '0.9rem',
                        letterSpacing: '0.01em',
                        fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                      }}
                    >
                      Analysis Complete
                    </Typography>
                    {message.routing && message.routing.orchestrator && (
                      <Typography
                        variant="caption"
                        sx={{
                          color: '#64748b',
                          fontSize: '0.75rem',
                          fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                        }}
                      >
                        Orchestrator: {message.routing.orchestrator}
                      </Typography>
                    )}
                  </Box>
                  <Chip
                    label={`${message.statusMessages.length} steps completed`}
                    size="small"
                    sx={{
                      bgcolor: '#f1f5f9',
                      color: '#475569',
                      fontWeight: 600,
                      fontSize: '0.7rem'
                    }}
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 3, pt: 2 }}>
                {/* Progress Steps */}
                <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Typography
                      variant="subtitle2"
                      sx={{
                        fontWeight: 600,
                        color: '#475569',
                        fontSize: '0.8rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                      }}
                    >
                      Execution Steps
                    </Typography>
                  </Box>
                  {message.routing && message.routing.orchestrator && (
                    <Chip
                      label={`Orchestrator: ${message.routing.orchestrator}`}
                      size="small"
                      variant="outlined"
                      sx={{
                        borderColor: '#cbd5e1',
                        color: '#475569',
                        fontSize: '0.7rem',
                        height: 24,
                        fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                      }}
                    />
                  )}
                </Box>

                {/* Progress Bar */}
                <Box sx={{
                  height: '6px',
                  bgcolor: '#e2e8f0',
                  borderRadius: 1,
                  position: 'relative',
                  overflow: 'hidden',
                  mb: 3
                }}>
                  <Box sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    height: '100%',
                    width: message.streaming ? `${Math.min((message.statusMessages.length / 8) * 100, 100)}%` : '100%',
                    background: message.streaming ? 'linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%)' : 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
                    borderRadius: 1,
                    transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&::after': message.streaming ? {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      bottom: 0,
                      right: 0,
                      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
                      animation: 'shimmer 2s infinite'
                    } : {}
                  }} />
                </Box>

                {/* Horizontal Stepper - Show all steps with status */}
                <Box sx={{ position: 'relative' }}>
                  <Stack spacing={2.5}>
                    {message.statusMessages.map((status, idx) => {
                      // If streaming is done, mark all as completed. Otherwise, show active state for last item
                      const isCompleted = !message.streaming || idx < message.statusMessages.length - 1;
                      const isActive = message.streaming && idx === message.statusMessages.length - 1;
                      const stepNumber = idx + 1;

                      return (
                        <Box
                          key={idx}
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 2,
                            opacity: isActive ? 1 : 0.7,
                            transform: isActive ? 'scale(1.02)' : 'scale(1)',
                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          }}
                        >
                          {/* Step Number */}
                          <Box sx={{
                            minWidth: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            bgcolor: isCompleted ? '#10b981' : isActive ? '#1e3a8a' : '#e2e8f0',
                            color: isCompleted || isActive ? 'white' : '#94a3b8',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.875rem',
                            fontWeight: 700,
                            flexShrink: 0,
                            boxShadow: isActive ? '0 4px 12px rgba(30, 58, 138, 0.3)' : 'none',
                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                            fontFamily: "'Inter', -apple-system, system-ui, sans-serif",
                            position: 'relative',
                            '&::after': isActive ? {
                              content: '""',
                              position: 'absolute',
                              inset: '-4px',
                              borderRadius: '50%',
                              padding: '2px',
                              background: 'linear-gradient(90deg, #3b82f6, #1e3a8a, #3b82f6)',
                              WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
                              WebkitMaskComposite: 'xor',
                              maskComposite: 'exclude',
                              animation: 'spin 2s linear infinite',
                              opacity: 0.6
                            } : {}
                          }}>
                            {stepNumber}
                          </Box>

                          {/* Step Content */}
                          <Box sx={{ flex: 1 }}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '0.875rem',
                                color: isActive ? '#1e293b' : '#64748b',
                                fontWeight: isActive ? 600 : 500,
                                lineHeight: 1.5,
                                fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                              }}
                            >
                              {status}{isActive ? '...' : ''}
                            </Typography>
                          </Box>

                          {/* Status Badge */}
                          {isCompleted && (
                            <Chip
                              label="Done"
                              size="small"
                              sx={{
                                bgcolor: '#d1fae5',
                                color: '#065f46',
                                fontWeight: 600,
                                fontSize: '0.7rem',
                                height: 20,
                                '& .MuiChip-label': { px: 1 },
                                fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                              }}
                            />
                          )}
                          {isActive && (
                            <Chip
                              label="Processing..."
                              size="small"
                              sx={{
                                bgcolor: '#dbeafe',
                                color: '#1e3a8a',
                                fontWeight: 600,
                                fontSize: '0.7rem',
                                height: 20,
                                '& .MuiChip-label': { px: 1 },
                                fontFamily: "'Inter', -apple-system, system-ui, sans-serif"
                              }}
                            />
                          )}
                        </Box>
                      );
                    })}
                  </Stack>
                </Box>
              </AccordionDetails>
            </Accordion>
            )}

            <style>
              {`
                @keyframes shimmer {
                  0% { transform: translateX(-100%); }
                  100% { transform: translateX(100%); }
                }
                @keyframes pulse {
                  0%, 100% { opacity: 1; }
                  50% { opacity: 0.5; }
                }
                @keyframes spin {
                  from { transform: rotate(0deg); }
                  to { transform: rotate(360deg); }
                }
              `}
            </style>

            {/* Final AI Response - Only shown when streaming is complete */}
            {!message.streaming && message.content && (
            <Card
              elevation={2}
              sx={{
                mb: 2,
                bgcolor: 'background.paper',
              }}
            >
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Stack direction="row" spacing={1.5} alignItems="flex-start">
                  <Box
                    component="img"
                    src="/axis-ai4.png"
                    alt="AXIS AI"
                    sx={{ height: 72, width: 'auto', objectFit: 'contain' }}
                  />
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

                    {/* Agent Collaboration Info */}
                    {/* Hide metadata sections when streaming is complete - they're already in progress section */}
                    {false && message.agentsUsed && message.agentsUsed.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.7rem' }}>
                          Agents Involved:
                        </Typography>
                        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {message.agentsUsed.map((agent, idx) => (
                            <Chip
                              key={idx}
                              label={agent}
                              size="small"
                              sx={{
                                bgcolor: 'primary.50',
                                color: 'primary.700',
                                fontWeight: 500,
                                fontSize: '0.75rem'
                              }}
                            />
                          ))}
                        </Box>
                      </Box>
                    )}

                    {/* Execution Plan - Hidden from final response */}
                    {false && !message.streaming && message.executionPlan && (
                      <Accordion sx={{ mt: 2, bgcolor: 'primary.50', border: '1px solid', borderColor: 'primary.200' }} elevation={0}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <PlayArrowIcon fontSize="small" color="primary" />
                            <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase', color: 'primary.main' }}>
                              Execution Plan
                            </Typography>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Grid container spacing={2}>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Agent</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>{message.executionPlan.agent}</Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Mode</Typography>
                              <Chip label={message.executionPlan.mode} size="small" color="primary" sx={{ fontSize: '0.7rem' }} />
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Expected Queries</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>{message.executionPlan.expected_queries}</Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Executed Queries</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, color: message.executionPlan.actual_queries_executed >= message.executionPlan.expected_queries ? 'success.main' : 'warning.main' }}>
                                {message.executionPlan.actual_queries_executed}
                              </Typography>
                            </Grid>
                            <Grid item xs={12}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Total Duration</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>{message.executionPlan.total_duration}</Typography>
                            </Grid>
                            {message.executionPlan.sub_tasks && message.executionPlan.sub_tasks.length > 0 && (
                              <Grid item xs={12}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mb: 1, display: 'block' }}>
                                  Sub-Tasks Identified ({message.executionPlan.sub_tasks.length})
                                </Typography>
                                {message.executionPlan.sub_tasks.map((task, idx) => (
                                  <Box key={idx} sx={{ display: 'flex', gap: 1, mb: 0.5 }}>
                                    <Chip label={idx + 1} size="small" sx={{ minWidth: '24px', height: '20px', fontSize: '0.7rem' }} />
                                    <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>{task}</Typography>
                                  </Box>
                                ))}
                              </Grid>
                            )}
                          </Grid>
                        </AccordionDetails>
                      </Accordion>
                    )}

                    {/* Execution Timeline - Hidden from final response */}
                    {false && !message.streaming && message.executionLogs && message.executionLogs.length > 0 && (
                      <Accordion sx={{ mt: 2 }} elevation={0}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <HistoryIcon fontSize="small" />
                            <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase' }}>
                              Execution Timeline ({message.executionLogs.length} steps)
                            </Typography>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Box sx={{ position: 'relative', pl: 3 }}>
                            {/* Timeline line */}
                            <Box sx={{
                              position: 'absolute',
                              left: '8px',
                              top: '8px',
                              bottom: '8px',
                              width: '2px',
                              bgcolor: 'divider'
                            }} />

                            {message.executionLogs.map((log, idx) => (
                              <Box key={idx} sx={{ position: 'relative', mb: 2 }}>
                                {/* Timeline dot */}
                                <Box sx={{
                                  position: 'absolute',
                                  left: '-19px',
                                  top: '4px',
                                  width: '12px',
                                  height: '12px',
                                  borderRadius: '50%',
                                  bgcolor: log.status === 'completed' ? 'success.main' : log.status === 'started' ? 'info.main' : 'grey.400',
                                  border: '2px solid white'
                                }} />

                                <Box>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                      {log.step}
                                    </Typography>
                                    {log.duration && (
                                      <Chip label={log.duration} size="small" sx={{ fontSize: '0.65rem', height: '18px' }} />
                                    )}
                                  </Box>
                                  <Typography variant="caption" color="text.secondary">
                                    {log.details}
                                  </Typography>
                                  {log.sql && (
                                    <Box sx={{ mt: 0.5, p: 1, bgcolor: 'grey.100', borderRadius: 1, fontFamily: 'monospace', fontSize: '0.7rem' }}>
                                      {log.sql}...
                                    </Box>
                                  )}
                                </Box>
                              </Box>
                            ))}
                          </Box>
                        </AccordionDetails>
                      </Accordion>
                    )}

                    {/* Agent Routing Info - Hidden from final response */}
                    {false && message.routing && message.routing.orchestrator && (
                      <Accordion sx={{ mt: 2 }} elevation={0}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase' }}>
                            View Agent Collaboration Details
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            <strong>Orchestrator:</strong> {message.routing.orchestrator}
                          </Typography>
                          {message.routing.domains && message.routing.domains.map((domain, idx) => (
                            <Box key={idx} sx={{ mt: 1, pl: 2, borderLeft: '2px solid', borderColor: 'primary.200' }}>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {domain.expert}
                              </Typography>
                              <Box sx={{ mt: 0.5, pl: 2 }}>
                                {domain.sub_agents.map((subAgent, subIdx) => (
                                  <Typography key={subIdx} variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                    • {subAgent}
                                  </Typography>
                                ))}
                              </Box>
                            </Box>
                          ))}
                        </AccordionDetails>
                      </Accordion>
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
            )}

            {/* SQL Queries and Results - Multiple if available */}
            {message.allSqlQueries && message.allSqlQueries.length > 0 ? (
              // Multiple queries - show each with its own results
              message.allSqlQueries.map((queryData, idx) => (
                <Box key={idx} sx={{ mb: 3 }}>
                  {/* SQL Query Accordion */}
                  <Accordion sx={{ mb: 2, bgcolor: 'grey.100' }}>
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon />}
                      aria-controls={`sql-content-${idx}`}
                      id={`sql-header-${idx}`}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <CodeIcon fontSize="small" color="action" />
                        <Typography variant="subtitle2">
                          SQL Query #{idx + 1} - {queryData.query || 'View Generated SQL'}
                        </Typography>
                        <Chip label={`${queryData.row_count || 0} rows`} size="small" color="primary" sx={{ ml: 1 }} />
                      </Stack>
                    </AccordionSummary>
                    <AccordionDetails sx={{ bgcolor: 'grey.900', p: 2 }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                        <Typography variant="caption" color="white">SQL Query</Typography>
                        <IconButton size="small" onClick={() => copyToClipboard(queryData.sql)}>
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
                        {queryData.sql}
                      </Box>
                    </AccordionDetails>
                  </Accordion>

                  {/* Results Table for this query */}
                  {queryData.results && queryData.results.length > 0 && (() => {
                    const queryIndex = `${message.id}-${idx}`;
                    const currentViewMode = tableViewMode[queryIndex] || 'table';
                    const currentChartType = tableChartType[queryIndex] || 'bar';
                    const currentPivotState = tablePivotState[queryIndex] || {};

                    // Prepare DataGrid columns
                    const columns = Object.keys(queryData.results[0]).map((key) => {
                      const isAmount = key.toLowerCase().includes('amount') ||
                                      key.toLowerCase().includes('revenue') ||
                                      key.toLowerCase().includes('cost') ||
                                      key.toLowerCase().includes('total') ||
                                      key.toLowerCase().includes('price');

                      return {
                        field: key,
                        headerName: key
                          .split('_')
                          .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                          .join(' '),
                        flex: 1,
                        minWidth: 150,
                        renderCell: (params) => {
                          if (typeof params.value === 'number') {
                            if (isAmount) {
                              return `$${params.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                            }
                            return params.value.toLocaleString('en-US');
                          }
                          return params.value || '';
                        },
                        align: typeof queryData.results[0][key] === 'number' ? 'right' : 'left',
                        headerAlign: typeof queryData.results[0][key] === 'number' ? 'right' : 'left',
                      };
                    });

                    const rows = queryData.results.map((row, index) => ({
                      id: row.id || index,
                      ...row,
                    }));

                    // Prepare chart data
                    const prepareChartData = () => {
                      const numericColumns = Object.keys(queryData.results[0]).filter(key =>
                        typeof queryData.results[0][key] === 'number' && !key.toLowerCase().includes('id')
                      );
                      const categoricalColumns = Object.keys(queryData.results[0]).filter(key =>
                        typeof queryData.results[0][key] === 'string'
                      );

                      const xAxisColumn = categoricalColumns[0] || Object.keys(queryData.results[0])[0];

                      // Aggregate data if needed
                      const aggregated = {};
                      queryData.results.forEach(row => {
                        const key = row[xAxisColumn];
                        if (!aggregated[key]) {
                          aggregated[key] = { [xAxisColumn]: key };
                          numericColumns.forEach(col => {
                            aggregated[key][col] = 0;
                          });
                        }
                        numericColumns.forEach(col => {
                          aggregated[key][col] += row[col] || 0;
                        });
                      });

                      return Object.values(aggregated);
                    };

                    const chartData = prepareChartData();

                    return (
                      <Paper elevation={1} sx={{ p: 2 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                          <Typography variant="h6">
                            Results ({queryData.results.length} rows)
                          </Typography>
                          <Stack direction="row" spacing={1}>
                            <ToggleButtonGroup
                              value={currentViewMode}
                              exclusive
                              onChange={(e, newMode) => {
                                if (newMode) {
                                  setTableViewMode(prev => ({ ...prev, [queryIndex]: newMode }));
                                }
                              }}
                              size="small"
                            >
                              <ToggleButton value="table">
                                <TableIcon sx={{ mr: 0.5 }} fontSize="small" />
                                Table
                              </ToggleButton>
                              <ToggleButton value="pivot">
                                <PivotIcon sx={{ mr: 0.5 }} fontSize="small" />
                                Pivot
                              </ToggleButton>
                              <ToggleButton value="chart">
                                <BarChartIcon sx={{ mr: 0.5 }} fontSize="small" />
                                Chart
                              </ToggleButton>
                            </ToggleButtonGroup>
                            <Button
                              size="small"
                              startIcon={<DownloadIcon />}
                              onClick={() => downloadCSV(queryData.results)}
                            >
                              Export CSV
                            </Button>
                          </Stack>
                        </Stack>

                        {/* Table View */}
                        {currentViewMode === 'table' && (
                          <Box sx={{ height: 400, width: '100%' }}>
                            <DataGrid
                              rows={rows}
                              columns={columns}
                              initialState={{
                                pagination: {
                                  paginationModel: { pageSize: 10, page: 0 },
                                },
                              }}
                              pageSizeOptions={[10, 25, 50, 100]}
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
                          </Box>
                        )}

                        {/* Pivot Table View */}
                        {currentViewMode === 'pivot' && (
                          <Box sx={{ width: '100%', overflow: 'auto' }}>
                            <PivotTableUI
                              data={queryData.results}
                              onChange={s => setTablePivotState(prev => ({ ...prev, [queryIndex]: s }))}
                              renderers={TableRenderers}
                              {...currentPivotState}
                            />
                          </Box>
                        )}

                        {/* Chart View */}
                        {currentViewMode === 'chart' && (
                          <Box>
                            <Tabs
                              value={currentChartType}
                              onChange={(e, v) => setTableChartType(prev => ({ ...prev, [queryIndex]: v }))}
                              sx={{ mb: 2 }}
                            >
                              <Tab value="bar" label="Bar" />
                              <Tab value="line" label="Line" />
                              <Tab value="pie" label="Pie" />
                              <Tab value="area" label="Area" />
                            </Tabs>

                            <ResponsiveContainer width="100%" height={400}>
                              {currentChartType === 'bar' && chartData.length > 0 && (
                                <BarChart data={chartData}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey={Object.keys(chartData[0] || {})[0]} />
                                  <YAxis />
                                  <RechartsTooltip />
                                  <Legend />
                                  {Object.keys(chartData[0] || {}).slice(1).map((key, idx) => (
                                    <Bar key={key} dataKey={key} fill={COLORS[idx % COLORS.length]} />
                                  ))}
                                </BarChart>
                              )}

                              {currentChartType === 'line' && chartData.length > 0 && (
                                <LineChart data={chartData}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey={Object.keys(chartData[0] || {})[0]} />
                                  <YAxis />
                                  <RechartsTooltip />
                                  <Legend />
                                  {Object.keys(chartData[0] || {}).slice(1).map((key, idx) => (
                                    <Line
                                      key={key}
                                      type="monotone"
                                      dataKey={key}
                                      stroke={COLORS[idx % COLORS.length]}
                                      strokeWidth={2}
                                    />
                                  ))}
                                </LineChart>
                              )}

                              {currentChartType === 'pie' && chartData.length > 0 && (
                                <PieChart>
                                  <Pie
                                    data={chartData}
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={120}
                                    fill="#8884d8"
                                    dataKey={Object.keys(chartData[0] || {}).find(k => typeof chartData[0][k] === 'number')}
                                    label
                                  >
                                    {chartData.map((entry, index) => (
                                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                  </Pie>
                                  <RechartsTooltip />
                                  <Legend />
                                </PieChart>
                              )}

                              {currentChartType === 'area' && chartData.length > 0 && (
                                <AreaChart data={chartData}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey={Object.keys(chartData[0] || {})[0]} />
                                  <YAxis />
                                  <RechartsTooltip />
                                  <Legend />
                                  {Object.keys(chartData[0] || {}).slice(1).map((key, idx) => (
                                    <Area
                                      key={key}
                                      type="monotone"
                                      dataKey={key}
                                      fill={COLORS[idx % COLORS.length]}
                                      stroke={COLORS[idx % COLORS.length]}
                                    />
                                  ))}
                                </AreaChart>
                              )}
                            </ResponsiveContainer>

                            {chartData.length === 0 && (
                              <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Typography color="text.secondary">
                                  No data available for chart visualization
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        )}
                      </Paper>
                    );
                  })()}

                  {/* AI Insights for this query - Shown at the end */}
                  {queryData.insights && (
                    <Card elevation={2} sx={{ mt: 2, bgcolor: 'background.paper' }}>
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Stack direction="row" spacing={1.5} alignItems="flex-start">
                          <Box
                            component="img"
                            src="/axis-ai4.png"
                            alt="AXIS AI"
                            sx={{ height: 72, width: 'auto', objectFit: 'contain', display: 'block' }}
                          />
                          <Box sx={{ flex: 1 }}>
                            <Box sx={{ color: 'text.primary', fontSize: '0.95rem', lineHeight: 1.8 }}>
                              {(() => {
                                // Helper function to format text with markdown-style bold
                                const formatText = (text) => {
                                  if (!text) return null;
                                  const parts = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);
                                  return parts.map((part, partIdx) => {
                                    if (part.startsWith('**') && part.endsWith('**')) {
                                      return (
                                        <Box key={partIdx} component="span" sx={{ fontWeight: 700, color: 'text.primary' }}>
                                          {part.slice(2, -2)}
                                        </Box>
                                      );
                                    } else if (part.startsWith('*') && part.endsWith('*')) {
                                      return (
                                        <Box key={partIdx} component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>
                                          {part.slice(1, -1)}
                                        </Box>
                                      );
                                    }
                                    return part;
                                  });
                                };

                                // Remove triple backticks from beginning and end
                                let cleanedInsights = queryData.insights;
                                if (cleanedInsights.startsWith('```')) {
                                  cleanedInsights = cleanedInsights.replace(/^```[a-zA-Z]*\n?/, '');
                                }
                                if (cleanedInsights.endsWith('```')) {
                                  cleanedInsights = cleanedInsights.replace(/\n?```$/, '');
                                }

                                const lines = cleanedInsights.split('\n');
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
                                  const listMatch = trimmedLine.match(/^(?:\d+[\.\)]\s+|[-*•]\s+)(.+)$/);

                                  if (h4Match) {
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
                                      <Typography key={`h4-${lineIdx}`} variant="subtitle1" component="h4" sx={{ fontWeight: 700, mt: 2.5, mb: 0.75, color: 'text.secondary', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.3px', borderLeft: '3px solid', borderColor: 'grey.300' }}>
                                        {formatText(h4Match[1])}
                                      </Typography>
                                    );
                                  } else if (h3Match) {
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
                                      <Typography key={`h3-${lineIdx}`} variant="h6" component="h3" sx={{ fontWeight: 700, mt: 3, mb: 1, color: 'text.primary', fontSize: '1rem', position: 'relative', '&:before': { content: '""', position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', width: '4px', height: '60%', bgcolor: 'primary.light', borderRadius: '2px' } }}>
                                        {formatText(h3Match[1])}
                                      </Typography>
                                    );
                                  } else if (h2Match) {
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
                                    if (currentParagraph.trim()) {
                                      elements.push(
                                        <Typography key={`para-${lineIdx}`} variant="body2" component="div" sx={{ mb: 2 }}>
                                          {formatText(currentParagraph.trim())}
                                        </Typography>
                                      );
                                      currentParagraph = '';
                                    }
                                    inList = true;
                                    const listItemText = listMatch[1];
                                    elements.push(
                                      <Typography key={`list-${lineIdx}`} variant="body2" component="div" sx={{ mb: 1, fontSize: '0.93rem' }}>
                                        {formatText(listItemText)}
                                      </Typography>
                                    );
                                  } else if (trimmedLine === '') {
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
                                    if (inList) {
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

                                return elements.length > 0 ? elements : formatText(queryData.insights);
                              })()}
                            </Box>
                          </Box>
                        </Stack>
                      </CardContent>
                    </Card>
                  )}
                </Box>
              ))
            ) : null}


            {/* Single query fallback */}
            {!message.allSqlQueries && message.sql && (
              // Single query - original display
              <>
                <Accordion sx={{ mb: 2, bgcolor: 'grey.100' }}>
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    aria-controls="sql-content"
                    id="sql-header"
                  >
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CodeIcon fontSize="small" color="action" />
                      <Typography variant="subtitle2">
                        View Generated SQL
                      </Typography>
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails sx={{ bgcolor: 'grey.900', p: 2 }}>
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
                  </AccordionDetails>
                </Accordion>

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
                      onClick={() => handleViewDetailedResults(message)}
                    >
                      View Detailed Results
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      color="secondary"
                      startIcon={<AutoGraphIcon />}
                      onClick={() => {
                        const messageIndex = messages.findIndex(m => m.id === message.id);
                        let userQuestion = 'Query results';
                        // Look backwards from the current message to find the user's question
                        for (let i = messageIndex - 1; i >= 0; i--) {
                          if (messages[i].type === 'user') {
                            userQuestion = messages[i].content;
                            break;
                          }
                        }
                        setAnalyticsModalData({
                          query: userQuestion,
                          results: {
                            rows: message.results,
                            metadata: message.metadata,
                            sql: message.sql,
                          },
                        });
                        setShowAnalyticsModal(true);
                      }}
                    >
                      Analytics Workbench
                    </Button>
                    
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<ResearchIcon />}
                      onClick={() => {
                        const userMessage = messages[messages.findIndex(m => m.id === message.id) - 1];
                        const researchQuestion = userMessage?.content 
                          ? `Based on this query result: "${userMessage.content}", provide a deeper analysis of the trends, patterns, and business implications.`
                          : 'Analyze the trends and patterns in this data';
                        
                        setDeepResearchQuestion(researchQuestion);
                        setShowDeepResearch(true);
                      }}
                    >
                      Deep Research
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

                {/* Visualization Toggle */}
                {(() => {
                  const chartData = prepareChartData(message.results);
                  console.log('Visualization toggle check:', {
                    messageId: message.id,
                    hasResults: !!message.results,
                    resultsLength: message.results?.length,
                    chartData: chartData,
                    hasNumericData: chartData?.hasNumericData
                  });
                  return chartData?.hasNumericData;
                })() && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 2 }}>
                    <ToggleButtonGroup
                      value={visualizationType[message.id] || 'table'}
                      exclusive
                      onChange={(e, v) => v && setVisualizationType(prev => ({ ...prev, [message.id]: v }))}
                      size="small"
                    >
                      <ToggleButton value="table">
                        <MuiTooltip title="Table View"><TableChartIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="bar">
                        <MuiTooltip title="Bar Chart"><BarChartIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="line">
                        <MuiTooltip title="Line Chart"><TimelineIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="pie">
                        <MuiTooltip title="Pie Chart"><PieChartIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="area">
                        <MuiTooltip title="Area Chart"><AnalyticsIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="scatter">
                        <MuiTooltip title="Scatter Plot"><ScatterPlotIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="radar">
                        <MuiTooltip title="Radar Chart"><RadarIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="treemap">
                        <MuiTooltip title="Treemap"><ViewModuleIcon /></MuiTooltip>
                      </ToggleButton>
                      <ToggleButton value="funnel">
                        <MuiTooltip title="Funnel Chart"><FilterListIcon /></MuiTooltip>
                      </ToggleButton>
                    </ToggleButtonGroup>
                  </Box>
                )}
                
                <Box sx={{ height: 400, width: '100%' }}>
                  {visualizationType[message.id] && visualizationType[message.id] !== 'table' ? (
                    renderVisualization(message.id, message.results)
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
                        const isAmount = key.toLowerCase().includes('amount') || 
                                       key.toLowerCase().includes('total') ||
                                       key.toLowerCase().includes('revenue') ||
                                       key.toLowerCase().includes('cost') ||
                                       key.toLowerCase().includes('cogs');
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
                              
                              if (isNumeric && isAmount && typeof params.value === 'number') {
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
                  </Paper>
                )}
              </>
            )}

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
        </Box>
      </Box>
    );
  };

  // No conversation grouping needed - Agent Mode has no history


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
        <Paper elevation={1} sx={{ p: 1.5, borderRadius: 0, position: 'relative', zIndex: 10, flexShrink: 0 }}>
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
                <Typography variant="h5" fontWeight={600}>
                  Agent Mode
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {mode === 'chat'
                    ? 'Autonomous AI Agent with Multi-Step Reasoning'
                    : 'Conduct comprehensive analysis with AI Agent'}
                </Typography>
              </Box>
            </Box>
          </Box>
        </Paper>

        {/* Conditional Content Based on Mode */}
        {console.log('Current mode:', mode)}
        {mode === 'chat' ? (
          <>
            {/* No tabs needed - Agent Mode has no history view */}

            {/* Chat View */}
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
            
          </Box>
        </Box>

        <Divider sx={{ flexShrink: 0 }} />

        {/* Input Area - Fixed */}
        <Paper elevation={3} sx={{ p: 2, borderRadius: 0, flexShrink: 0 }}>
          <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
            <Stack direction="row" spacing={2}>
              <Autocomplete
                fullWidth
                freeSolo
                value={inputMessage}
                onChange={(event, newValue) => {
                  setInputMessage(typeof newValue === 'string' ? newValue : '');
                }}
                onInputChange={(event, newInputValue) => {
                  setInputMessage(newInputValue);

                  // Generate smart suggestions based on input
                  if (newInputValue && newInputValue.trim().length >= 2) {
                    const input = newInputValue.toLowerCase().trim();
                    const suggestions = [];

                    // Check if input starts with any of our smart completion triggers
                    Object.keys(SMART_COMPLETIONS).forEach(trigger => {
                      if (input.startsWith(trigger)) {
                        // Add completions for this trigger
                        SMART_COMPLETIONS[trigger].forEach(completion => {
                          suggestions.push(`${trigger} ${completion}`);
                        });
                      } else if (trigger.startsWith(input)) {
                        // Show trigger options if user is typing a trigger word
                        SMART_COMPLETIONS[trigger].slice(0, 2).forEach(completion => {
                          suggestions.push(`${trigger} ${completion}`);
                        });
                      }
                    });

                    // Remove duplicates and limit
                    const uniqueSuggestions = [...new Set(suggestions)].slice(0, 6);
                    setAutocompleteSuggestions(uniqueSuggestions);
                  } else {
                    setAutocompleteSuggestions([]);
                  }
                }}
                options={autocompleteSuggestions}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Ask a question about your data..."
                    disabled={loading}
                    variant="outlined"
                    onKeyDown={handleKeyDown}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        borderRadius: 2,
                      }
                    }}
                  />
                )}
                sx={{ flex: 1 }}
              />
              <Button
                variant="contained"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || loading}
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
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, researchMessage]);
          }
        }}
      />
    </Box>
  );
});

export default AgentModeInterface;