import React, { useState, useEffect } from 'react';
import { ClerkProvider, useUser } from '@clerk/clerk-react';
import AuthButton from './components/AuthButton';
import { usePersistedState } from './hooks/usePersistedState';
// Removed react-router-dom imports - using tab-based navigation
import {
  Box,
  Container,
  Paper,
  Fade,
  TextField,
  Button,
  Typography,
  AppBar,
  Toolbar,
  Alert,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControlLabel,
  Checkbox,
  Grid,
  Card,
  CardContent,
  Chip,
  IconButton,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Snackbar,
  CircularProgress,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip as MuiTooltip,
  Menu,
  Stack,
  LinearProgress,
  Dialog,
  Fab,
  Badge,
  ThemeProvider,
} from '@mui/material';
import DataSourcesTab from './components/DataSourcesTab';
import AIChatInterface from './components/AIChatInterface';
import ControlCenter from './components/ControlCenter';
import SimpleChatInterface from './components/SimpleChatInterface';
import AgentModeInterface from './components/AgentModeInterface';
import EnhancedSidebar from './components/EnhancedSidebar';
import TopNavBar from './components/TopNavBar';
import ContentHub from './components/ContentHub';
import ProjectsHub from './components/ProjectsHub';
import ChatSearchPage from './components/ChatSearchPage';
import AdminHub from './components/AdminHub';
import UserProfileManager from './components/UserProfileManager';
import MarketsAIDashboard from './components/MarketsAIDashboard';
import CoreAILanding from './components/CoreAILanding';
import MargenAIDashboard from './components/margenai/MargenAIDashboard';
import MargenAILanding from './components/MargenAILanding';
import MargenAITable from './components/margenai/MargenAITable';
import SegmentAnalytics from './components/margenai/SegmentAnalytics';
import RevenueSalesAnalytics from './components/margenai/RevenueSalesAnalytics';
import CostOperationsManagement from './components/margenai/CostOperationsManagement';
import RevenueGrowthAnalytics from './components/margenai/RevenueGrowthAnalytics';
import CostCOGSAnalytics from './components/margenai/CostCOGSAnalytics';
import MarginProfitabilityAnalytics from './components/margenai/MarginProfitabilityAnalytics';
import PLGLExplorerAnalytics from './components/margenai/PLGLExplorerAnalytics';
import FinancialDriversAnalytics from './components/margenai/FinancialDriversAnalytics';
import AxisAIDashboard from './components/AxisAIDashboard';
import DocumentIntelligence from './components/DocumentIntelligence';
import ProcessMiningPage from './pages/ProcessMiningPage';
import ScenarioAIDashboard from './components/ScenarioAIDashboard';
import ForecastAIDashboard from './components/ForecastAIDashboard';
import ResultsTable from './components/ResultsTable';
import EnterprisePulse from './components/EnterprisePulse';
// import StoxShiftAI from './components/StoxShiftAI'; // File doesn't exist
import StoxAILanding from './components/StoxAILanding';
import ShortageDetector from './components/stox/ShortageDetector';
import InventoryHeatmap from './components/stox/InventoryHeatmap';
import ReallocationOptimizer from './components/stox/ReallocationOptimizer';
import InboundRiskMonitor from './components/stox/InboundRiskMonitor';
import AgingStockIntelligence from './components/stox/AgingStockIntelligence';
import DemandWorkbench from './components/stox/DemandWorkbench.jsx';
import SellThroughAnalytics from './components/stox/SellThroughAnalytics.jsx';
import SellInForecast from './components/stox/SellInForecast.jsx';
import SKUAggregation from './components/stox/SKUAggregation.jsx';
import BOMExplorer from './components/stox/BOMExplorer.jsx';
import ComponentConsolidation from './components/stox/ComponentConsolidation.jsx';
import StoreDeployment from './components/stox/StoreDeployment.jsx';
import ExecutiveCommandCenter from './components/stox/ExecutiveCommandCenter.jsx';
import ScenarioPlanner from './components/stox/ScenarioPlanner.jsx';
import Tile0ForecastSimulation from './components/stox/Tile0ForecastSimulation.jsx';
import StoreForecast from './components/stox/StoreForecast.jsx';
import StoreHealthMonitor from './components/stox/StoreHealthMonitor.jsx';
import StoreOptimization from './components/stox/StoreOptimization.jsx';
import StoreReplenishment from './components/stox/StoreReplenishment.jsx';
import StoreFinancialImpact from './components/stox/StoreFinancialImpact.jsx';
import DCDemandAggregation from './components/stox/DCDemandAggregation.jsx';
import DCHealthMonitor from './components/stox/DCHealthMonitor.jsx';
import DCOptimization from './components/stox/DCOptimization.jsx';
import DCBOM from './components/stox/DCBOM.jsx';
import DCLotSize from './components/stox/DCLotSize.jsx';
import DCSupplierExecution from './components/stox/DCSupplierExecution.jsx';
import DCFinancialImpact from './components/stox/DCFinancialImpact.jsx';
import ModuleTilesView from './components/stox/ModuleTilesView.jsx';
import FioriTileDetail from './components/stox/FioriTileDetail.jsx';
import TicketingSystem from './components/stox/TicketingSystem.jsx';
import GlobalSearch from './components/GlobalSearch';
import DocumentVisionIntelligence from './components/DocumentVisionIntelligence';
import EmailIntelligence from './components/EmailIntelligence';
import CommsConfig from './components/CommsConfig';
import RouteAI from './components/RouteAI';
import RouteAILanding from './components/RouteAILanding';
import FleetManagement from './components/routeai/FleetManagement';
import RouteOptimization from './components/routeai/RouteOptimization';
import DeliveryTracking from './components/routeai/DeliveryTracking';
import PerformanceAnalytics from './components/routeai/PerformanceAnalytics';
import FuelManagement from './components/routeai/FuelManagement';
import MaintenanceScheduler from './components/routeai/MaintenanceScheduler';
import { apiService } from './services/api';
import { sapFioriTheme, sapChartColors } from './themes/sapFioriTheme';
import { defaultTheme } from './themes/defaultTheme';
import {
  ExpandMore as ExpandMoreIcon,
  ContentCopy as ContentCopyIcon,
  Download as DownloadIcon,
  PlayArrow as PlayArrowIcon,
  Edit as EditIcon,
  BarChart as BarChartIcon,
  TableChart as TableChartIcon,
  Timeline as TimelineIcon,
  PieChart as PieChartIcon,
  History as HistoryIcon,
  Storage as StorageIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Code as CodeIcon,
  Analytics as AnalyticsIcon,
  Save as SaveIcon,
  Share as ShareIcon,
  QueryStats as QueryStatsIcon,
  Schema as SchemaIcon,
  HealthAndSafety as HealthIcon,
  Cable as CableIcon,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
  Search as SearchIcon,
  Dashboard as DashboardIcon,
  DataUsage as DataUsageIcon,
  PushPin as PushPinIcon,
  MenuOpen as MenuOpenIcon,
  Close as CloseIcon,
  Delete as DeleteIcon,
  Hub as HubIcon,
  ScatterPlot as ScatterPlotIcon,
  Radar as RadarIcon,
  ViewModule as ViewModuleIcon,
  FilterList as FilterListIcon,
  Forum as ForumIcon,
  Lock as LockIcon,
  Chat as ChatIcon,
  SmartToy as SmartToyIcon,
} from '@mui/icons-material';



// Helper functions
const formatNumber = (num) => {
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
  return num.toString();
};

const formatBytes = (bytes) => {
  if (bytes >= 1e12) return `${(bytes / 1e12).toFixed(2)} TB`;
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(2)} KB`;
  return `${bytes} bytes`;
};

function App() {
  // Get authenticated user
  const { user } = useUser();

  // Removed navigate and location - using tab-based navigation
  // Theme state - SAP theme is now default
  const useSapTheme = true;
  const currentTheme = sapFioriTheme;
  
  // State management
  const [loading, setLoading] = useState(false);
  const [selectedTab, setSelectedTab] = usePersistedState('mantrix-selectedTab', 'chat');
  const [drawerOpen, setDrawerOpen] = usePersistedState('mantrix-drawerOpen', true);
  const [coreAIView, setCoreAIView] = useState('landing'); // 'landing', 'margen', 'stox', 'route'
  const [stoxView, setStoxView] = usePersistedState('mantrix-stoxView', 'landing'); // 'landing', 'stoxshift'
  const [margenView, setMargenView] = usePersistedState('mantrix-margenView', 'landing'); // 'landing', 'revenue-sales', 'cost-operations', etc.
  const [routeView, setRouteView] = usePersistedState('mantrix-routeView', 'landing'); // 'landing', module IDs
  const [currentFioriTile, setCurrentFioriTile] = useState(null); // { tileId, title, moduleId, moduleColor }
  const [axisAIView, setAxisAIView] = useState('landing'); // 'landing', 'forecast', 'budget', 'driver', 'scenario', 'insights'
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [apiHealth, setApiHealth] = useState(null);
  const [connectors, setConnectors] = useState([]);
  const [selectedHistoryQuery, setSelectedHistoryQuery] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [tableDetailsOpen, setTableDetailsOpen] = useState(false);
  const [selectedTable, setSelectedTable] = useState(null);
  const [queryHistory, setQueryHistory] = useState([]);

  // Conversation state (shared between sidebar and chat interface)
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [starredConversations, setStarredConversations] = useState([]);
  const [chatView, setChatView] = useState('chat'); // 'search' or 'chat' - default to 'chat' to show recent conversation

  // Agent Mode state
  const [agentModeInitialQuestion, setAgentModeInitialQuestion] = useState(null);

  // Projects state
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  // Toggle star for a conversation
  const handleToggleStar = (convId) => {
    const conversation = conversations.find(c => (c.conversation_id || c.conversationId) === convId);
    if (!conversation) return;

    setStarredConversations(prev => {
      const isStarred = prev.some(c => (c.conversation_id || c.conversationId) === convId);
      if (isStarred) {
        // Unstar - remove from starred list
        return prev.filter(c => (c.conversation_id || c.conversationId) !== convId);
      } else {
        // Star - add to starred list
        return [...prev, conversation];
      }
    });
  };

  // Refs to SimpleChatInterface functions
  const chatInterfaceRef = React.useRef(null);
  const hasInitializedSession = React.useRef(false);
  const [schemaData, setSchemaData] = useState({
    summary: {
      totalTables: 0,
      totalColumns: 0,
      totalRows: 0,
      totalSize: 0,
      totalRelationships: 0,
      dataSources: 0
    },
    schemas: []
  });
  const [loadingSchema, setLoadingSchema] = useState(false);
  
  // Data Explorer filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [dataSourceFilter, setDataSourceFilter] = useState('');
  const [schemaFilter, setSchemaFilter] = useState('');
  const [tableTypeFilter, setTableTypeFilter] = useState('');
  const [viewMode, setViewMode] = useState('table');

  // Handle search navigation
  const handleSearchNavigation = (action) => {
    console.log('Search navigation:', action);

    // Navigate to the appropriate tab
    if (action.tabId !== undefined) {
      setSelectedTab(action.tabId);
    }

    // Handle CORE.AI specific navigation
    if (action.view) {
      // Check if this is a STOX.AI navigation
      if (action.view === 'stox' || action.view === 'margen' || ['demand-workbench', 'demand-flow', 'demand-forecasting', 'outbound-replenishment', 'dc-inventory', 'supply-planning', 'bom-explosion', 'component-consolidation', 'analytics-whatif', 'store-forecasting', 'store-health-monitor', 'store-optimization', 'store-replenishment', 'store-financial-impact', 'dc-demand-aggregation', 'dc-health-monitor', 'dc-optimization', 'dc-bom', 'dc-lot-size', 'dc-supplier-exec', 'dc-financial-impact'].includes(action.view)) {
        // First set CORE.AI view to STOX
        setCoreAIView('stox');

        // Then navigate to the specific STOX module
        if (action.view !== 'stox') {
          setStoxView(action.view);
        }
      } else {
        setCoreAIView(action.view);
      }

      // Handle STOXSHIFT.AI specific navigation
      if (action.stoxshiftTile) {
        // This would require passing props to StoxShiftAI to auto-select tile/tab
        // For now, we'll just navigate to the page
        console.log('Navigate to STOXSHIFT tile:', action.stoxshiftTile, 'tab:', action.stoxshiftTab);
      }
    }

    // Handle AXIS.AI specific navigation
    if (action.axisView) {
      setAxisAIView(action.axisView);
    }
  };

  // Initialize
  useEffect(() => {
    checkApiHealth();
    loadQueryHistory();
    loadConnectors();
  }, []);

  // Load schema data when Data Explorer tab is selected
  useEffect(() => {
    if (selectedTab === 5) {
      loadSchemaData();
    }
  }, [selectedTab]);

  // Load projects when user is authenticated
  useEffect(() => {
    if (user) {
      loadProjects();
      loadConversations();
    }
  }, [user?.id]);

  // Initialize chat view when user logs in (but not on refresh)
  useEffect(() => {
    if (user && !hasInitializedSession.current) {
      // Check if this is a fresh login or a page refresh
      const sessionKey = `mantrix-session-${user.id}`;
      const hasSession = sessionStorage.getItem(sessionKey);

      if (!hasSession) {
        // Fresh login - default to new chat
        hasInitializedSession.current = true;
        sessionStorage.setItem(sessionKey, 'true');

        // Set to chat tab and chat view
        setSelectedTab('chat');
        setChatView('chat');

        // Clear any existing conversation to start fresh
        setConversationId(null);
      } else {
        // Page refresh - keep existing persisted state
        hasInitializedSession.current = true;
      }
    }
  }, [user?.id]);

  // Load conversations from API
  const loadConversations = async () => {
    if (!user) return;

    try {
      setLoadingConversations(true);
      const response = await apiService.get(`/api/v1/conversations?user_id=${user.id}&limit=50&skip=0`);
      const loadedConversations = response.data?.conversations || [];

      // Sort by updated_at (most recent first)
      const sortedConversations = loadedConversations.sort((a, b) => {
        const dateA = new Date(a.updated_at || a.updatedAt);
        const dateB = new Date(b.updated_at || b.updatedAt);
        return dateB - dateA;
      });

      setConversations(sortedConversations);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  };

  // API Functions
  const checkApiHealth = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/health`);
      if (response.ok) {
        const health = await response.json();
        setApiHealth(health);
        showSnackbar('API is healthy', 'success');
      } else {
        setApiHealth({ status: 'unhealthy' });
        showSnackbar('API health check failed', 'error');
      }
    } catch (error) {
      setApiHealth({ status: 'error', message: error.message });
      showSnackbar('Cannot connect to API', 'error');
    }
  };

  const loadConnectors = () => {
    // Simulated connectors data
    setConnectors([
      { name: 'BigQuery', status: 'connected', icon: '🔷', color: '#4285F4' },
      { name: 'Weaviate', status: 'connected', icon: '🟢', color: '#00FF00' },
      { name: 'Redis', status: 'connected', icon: '🔴', color: '#DC382D' },
      { name: 'Anthropic API', status: 'connected', icon: '🤖', color: '#7C3AED' },
    ]);
  };

  const loadProjects = async () => {
    if (!user) return;

    try {
      setLoadingProjects(true);
      const response = await apiService.get(`/api/v1/projects?user_id=${user.id}`);
      setProjects(response.data || []);
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadSchemaData = async () => {
    setLoadingSchema(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/schemas`);
      if (response.ok) {
        const data = await response.json();
        // Transform backend response to match frontend structure
        const transformedData = {
          summary: {
            totalTables: data.total_count || 0,
            totalColumns: data.tables ? data.tables.reduce((sum, table) => sum + (table.columns ? table.columns.length : 0), 0) : 0,
            totalRows: data.tables ? data.tables.reduce((sum, table) => sum + (table.row_count || 0), 0) : 0,
            totalSize: data.tables ? data.tables.reduce((sum, table) => sum + (table.size_bytes || 0), 0) : 0,
            totalRelationships: 0, // Would need to be calculated from table relationships
            dataSources: 1 // BigQuery
          },
          schemas: [{
            source: 'BigQuery',
            database: 'Dataset',
            tables: data.tables || []
          }]
        };
        setSchemaData(transformedData);
      } else {
        // Use mock data for now
        setSchemaData({
          summary: {
            totalTables: 42,
            totalColumns: 847,
            totalRows: 2400000,
            totalSize: 125829120, // 120 MB in bytes
            totalRelationships: 18,
            dataSources: 3
          },
          schemas: [
            {
              source: 'BigQuery',
              database: '1k_dataset',
              tables: [
                {
                  name: 'CE11000',
                  description: 'COPA main transaction table',
                  rowCount: 5000000,
                  sizeBytes: 256000000,
                  lastModified: '2 hours ago',
                  relationships: 3,
                  columns: [
                    { name: 'GJAHR', type: 'INTEGER', nullable: false, description: 'Fiscal Year' },
                    { name: 'PERIO', type: 'INTEGER', nullable: false, description: 'Posting Period' },
                    { name: 'KOKRS', type: 'STRING', nullable: false, description: 'Controlling Area' },
                    { name: 'VV001', type: 'NUMERIC', nullable: true, description: 'Revenue' },
                  ]
                },
                {
                  name: 'products',
                  description: 'Product master data',
                  rowCount: 8421,
                  sizeBytes: 12582912,
                  lastModified: '1 day ago',
                  relationships: 5
                }
              ]
            },
            {
              source: 'PostgreSQL',
              database: 'operations_db',
              tables: [
                {
                  name: 'orders',
                  description: 'Customer orders',
                  rowCount: 543210,
                  sizeBytes: 67108864,
                  lastModified: '30 minutes ago',
                  relationships: 4
                }
              ]
            }
          ]
        });
        showSnackbar('Using sample data for demonstration', 'info');
      }
    } catch (error) {
      console.error('Error loading schema:', error);
      // Use mock data on error
      setSchemaData({
        summary: {
          totalTables: 42,
          totalColumns: 847,
          totalRows: 2400000,
          totalSize: 125829120,
          totalRelationships: 18,
          dataSources: 3
        },
        schemas: [
          {
            source: 'BigQuery',
            database: 'copa_export_copa_data_000000000000',
            tables: [
              {
                name: 'CE11000',
                description: 'COPA main transaction table',
                rowCount: 5000000,
                sizeBytes: 256000000,
                lastModified: '2 hours ago',
                relationships: 3
              }
            ]
          }
        ]
      });
      showSnackbar('Using sample data (API unavailable)', 'warning');
    } finally {
      setLoadingSchema(false);
    }
  };

  const loadQueryHistory = () => {
    const history = localStorage.getItem('queryHistory');
    if (history) {
      setQueryHistory(JSON.parse(history));
    }
  };

  const saveToHistory = (queryData) => {
    const newHistory = [{
      id: Date.now(),
      timestamp: new Date().toISOString(),
      ...queryData
    }, ...queryHistory].slice(0, 50);
    setQueryHistory(newHistory);
    localStorage.setItem('queryHistory', JSON.stringify(newHistory));
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  // Filter function for Data Explorer tables
  const filterTables = (schemas) => {
    if (!schemas) return [];
    
    return schemas.map(schema => {
      // First apply data source filter
      if (dataSourceFilter && schema.source.toLowerCase() !== dataSourceFilter.toLowerCase()) {
        return null;
      }
      
      // Apply schema filter (database name)
      if (schemaFilter && !schema.database.toLowerCase().includes(schemaFilter.toLowerCase())) {
        return null;
      }
      
      // Filter tables within the schema
      const filteredTables = (schema.tables || []).filter(table => {
        // Apply search term filter
        if (searchTerm) {
          const searchLower = searchTerm.toLowerCase();
          const matchesName = table.name.toLowerCase().includes(searchLower);
          const matchesDescription = (table.description || '').toLowerCase().includes(searchLower);
          const matchesColumns = (table.columns || []).some(col => 
            col.name.toLowerCase().includes(searchLower) || 
            (col.description || '').toLowerCase().includes(searchLower)
          );
          
          if (!matchesName && !matchesDescription && !matchesColumns) {
            return false;
          }
        }
        
        // Apply table type filter
        if (tableTypeFilter) {
          const tableType = table.type || 'table';
          if (tableTypeFilter === 'table' && tableType !== 'table') return false;
          if (tableTypeFilter === 'view' && tableType !== 'view') return false;
          if (tableTypeFilter === 'materialized' && tableType !== 'materialized_view') return false;
        }
        
        return true;
      });
      
      // Return schema with filtered tables
      return {
        ...schema,
        tables: filteredTables
      };
    }).filter(schema => schema !== null && schema.tables.length > 0);
  };





  return (
    <ThemeProvider theme={currentTheme}>
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Enhanced Sidebar */}
      <EnhancedSidebar
        drawerOpen={drawerOpen}
        setDrawerOpen={setDrawerOpen}
        selectedTab={selectedTab}
        setSelectedTab={setSelectedTab}
        apiHealth={apiHealth}
        useSapTheme={useSapTheme}
        conversations={conversations}
        conversationId={conversationId}
        loadingConversations={loadingConversations}
        starredConversations={starredConversations}
        onToggleStar={handleToggleStar}
        onOpenChatHistory={() => {
          setChatView('search');
        }}
        onLoadConversation={(convId) => {
          console.log('Loading conversation:', convId);
          setConversationId(convId);
          setChatView('chat');
          setSelectedTab('chat');
          // Load the conversation in the chat interface
          setTimeout(() => {
            if (chatInterfaceRef.current?.loadConversation) {
              chatInterfaceRef.current.loadConversation(convId);
            }
          }, 100);
        }}
        onDeleteConversation={(convId) => {
          if (chatInterfaceRef.current?.handleDeleteConversation) {
            chatInterfaceRef.current.handleDeleteConversation(convId);
          }
        }}
        onNewChat={() => {
          // Switch to chat view first
          setChatView('chat');
          setSelectedTab('chat');
          // Then call handleNewConversation after a brief delay to ensure component is mounted
          setTimeout(() => {
            if (chatInterfaceRef.current?.handleNewConversation) {
              chatInterfaceRef.current.handleNewConversation();
            }
          }, 100);
        }}
      />

      {/* Main Content */}
      <Box sx={{
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        width: '100%',
        bgcolor: '#f7f7f7'
      }}>
        {/* Top Navigation Bar with Global Search */}
        <TopNavBar
          useSapTheme={useSapTheme}
          setSelectedTab={setSelectedTab}
          drawerOpen={drawerOpen}
          setDrawerOpen={setDrawerOpen}
          user={user}
        />

        <Container maxWidth="xl" sx={{
          mt: 3,
          mb: 3,
          flexGrow: 1,
          overflow: 'hidden',
          width: '100%',
          px: { xs: 2, sm: 3 }
        }}>
          {/* Chat - Natural Language Interface */}
          {selectedTab === 'chat' && (
            <Box sx={{
              height: 'calc(100vh - 100px)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              pb: 0
            }}>
              {chatView === 'search' ? (
                <ChatSearchPage
                  userId={user?.id || 'default'}
                  onOpenConversation={(convId) => {
                    if (chatInterfaceRef.current?.loadConversation) {
                      chatInterfaceRef.current.loadConversation(convId);
                      setChatView('chat');
                    }
                  }}
                  starredConversations={starredConversations}
                  onToggleStar={handleToggleStar}
                  onDeleteConversation={async (convId) => {
                    if (chatInterfaceRef.current?.deleteConversation) {
                      await chatInterfaceRef.current.deleteConversation(convId);
                    }
                  }}
                  projects={projects}
                />
              ) : (
                <SimpleChatInterface
                  ref={chatInterfaceRef}
                  onConversationsChange={setConversations}
                  onConversationIdChange={setConversationId}
                  onLoadingChange={setLoadingConversations}
                  onBackToSearch={() => setChatView('search')}
                  onOpenAgentMode={(question) => {
                    setAgentModeInitialQuestion(question);
                    setSelectedTab('agent');
                  }}
                />
              )}
            </Box>
          )}

          {/* Agent Mode - Autonomous AI Agent */}
          {selectedTab === 'agent' && (
            <Box sx={{
              height: 'calc(100vh - 100px)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              pb: 0
            }}>
              <AgentModeInterface
                onConversationsChange={setConversations}
                onConversationIdChange={setConversationId}
                onLoadingChange={setLoadingConversations}
                initialQuestion={agentModeInitialQuestion}
                onQuestionUsed={() => setAgentModeInitialQuestion(null)}
              />
            </Box>
          )}

          {/* Projects (Content Hub) */}
          {selectedTab === 'content' && <ProjectsHub setSelectedTab={setSelectedTab} useSapTheme={useSapTheme} />}

          {/* Artifacts */}
          {selectedTab === 'artifacts' && (
            <Box sx={{ p: 4 }}>
              <Typography variant="h4" fontWeight={400} gutterBottom>
                Artifacts
              </Typography>
              <Typography color="text.secondary">
                Coming soon - View and manage your generated artifacts
              </Typography>
            </Box>
          )}

          {/* AI Persona - Configure AI Response Personality */}
          {selectedTab === 'persona' && <UserProfileManager />}

          {/* Admin - Settings & Administration */}
          {selectedTab === 'admin' && <AdminHub setSelectedTab={setSelectedTab} useSapTheme={useSapTheme} />}
        </Container>
      </Box>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
    </ThemeProvider>
  );
}

// Import auth config
import authConfig from './auth_config.json';

// Authentication wrapper component
function AuthenticatedApp() {
  const { isSignedIn, isLoaded, user } = useUser();
  const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

  // If Clerk is not configured, show the app without authentication
  if (!clerkPubKey) {
    console.warn('Clerk authentication not configured');
    return <App />;
  }

  // Show loading while Clerk is initializing
  if (!isLoaded) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // If not signed in, show enhanced login screen
  if (!isSignedIn) {
    return (
      <Box sx={{
        display: 'flex',
        minHeight: '100vh',
        bgcolor: '#f7f7f7',
        fontFamily: 'Poppins, sans-serif',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'relative',
      }}>
        {/* Import Poppins font */}
        <style>
          {`
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

            @keyframes fadeInUp {
              from {
                opacity: 0;
                transform: translateY(20px);
              }
              to {
                opacity: 1;
                transform: translateY(0);
              }
            }
          `}
        </style>

        {/* Background decoration */}
        <Box sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          overflow: 'hidden',
          zIndex: 0,
        }}>
          <Box sx={{
            position: 'absolute',
            top: '-50%',
            right: '-25%',
            width: '80%',
            height: '100%',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(10, 110, 209, 0.025) 0%, transparent 60%)',
          }} />
          <Box sx={{
            position: 'absolute',
            bottom: '-50%',
            left: '-25%',
            width: '80%',
            height: '100%',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(10, 110, 209, 0.015) 0%, transparent 60%)',
          }} />
        </Box>
        {/* Login Form */}
        <Paper sx={{
          p: { xs: 3, sm: 4, md: 5 },
          maxWidth: 420,
          width: '90%',
          borderRadius: '12px',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.1), 0 20px 40px rgba(0, 0, 0, 0.06)',
          background: 'white',
          position: 'relative',
          zIndex: 1,
          border: '1px solid rgba(0, 0, 0, 0.06)',
          animation: 'fadeInUp 0.5s ease-out',
        }}>
          {/* Logo */}
          <Box sx={{ textAlign: 'center', mb: 0.5 }}>
            <img
              src="/axis-ai2.png"
              alt="AXIS AI"
              style={{ height: 120, objectFit: 'contain' }}
            />
          </Box>

          <Typography sx={{
            fontSize: { xs: '1.5rem', sm: '2rem' },
            fontWeight: 700,
            mb: 1.5,
            textAlign: 'center',
            color: '#32363a',
            fontFamily: 'Poppins, sans-serif',
            letterSpacing: '-0.5px',
          }}>
            AXIS AI
          </Typography>
          <Typography sx={{
            fontSize: '0.875rem',
            mb: 3,
            textAlign: 'center',
            color: '#6a6d70',
            fontFamily: 'Poppins, sans-serif',
            fontWeight: 400,
          }}>
            Your AI Conversational Interface
          </Typography>

          {/* Feature Highlights */}
          <Box sx={{ mb: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <ChatIcon sx={{ color: '#0a6ed1', fontSize: 24 }} />
              <Typography sx={{ fontSize: '0.875rem', color: '#32363a', fontFamily: 'Poppins, sans-serif' }}>
                <strong>Natural Language Chat</strong> - Ask questions in plain English
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <SmartToyIcon sx={{ color: '#0a6ed1', fontSize: 24 }} />
              <Typography sx={{ fontSize: '0.875rem', color: '#32363a', fontFamily: 'Poppins, sans-serif' }}>
                <strong>Autonomous Agent Mode</strong> - AI executes complex tasks independently
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <StorageIcon sx={{ color: '#0a6ed1', fontSize: 24 }} />
              <Typography sx={{ fontSize: '0.875rem', color: '#32363a', fontFamily: 'Poppins, sans-serif' }}>
                <strong>Enterprise Data Access</strong> - Connect to your databases securely
              </Typography>
            </Box>
          </Box>

          {/* Auth Button */}
          <Box sx={{ mb: 4 }}>
            <AuthButton />
          </Box>

          <Divider sx={{ my: 4 }}>
            <Typography sx={{
              fontSize: '0.75rem',
              color: '#94a3b8',
              fontFamily: 'Poppins, sans-serif',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
            }}>
              Secure Authentication
            </Typography>
          </Divider>

          {/* Security Features */}
          <Box sx={{ mt: 4 }}>
            <Box sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 3,
              mb: 3,
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LockIcon sx={{ fontSize: 16, color: '#64748b' }} />
                <Typography sx={{
                  fontSize: '0.8rem',
                  color: '#64748b',
                  fontFamily: 'Poppins, sans-serif',
                }}>
                  256-bit SSL
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CheckCircleIcon sx={{ fontSize: 16, color: '#64748b' }} />
                <Typography sx={{
                  fontSize: '0.8rem',
                  color: '#64748b',
                  fontFamily: 'Poppins, sans-serif',
                }}>
                  SSO Enabled
                </Typography>
              </Box>
            </Box>

            <Typography sx={{
              fontSize: '0.75rem',
              color: '#94a3b8',
              fontFamily: 'Poppins, sans-serif',
              textAlign: 'center',
              mt: 4,
            }}>
              By signing in, you agree to our Terms of Service and Privacy Policy
            </Typography>

            <Typography sx={{
              fontSize: '0.7rem',
              color: '#cbd5e1',
              fontFamily: 'Poppins, sans-serif',
              textAlign: 'center',
              mt: 2,
            }}>
              © 2024 Cloud Mantra, Inc. All rights reserved.
            </Typography>
          </Box>
        </Paper>
      </Box>
    );
  }

  // Check email authorization
  const userEmail = user?.primaryEmailAddress?.emailAddress;
  if (userEmail) {
    const { authorized_emails, authorized_domains } = authConfig.authentication.access_control;

    // Check if email is in whitelist
    const isEmailAuthorized = authorized_emails.includes(userEmail);

    // Check if domain is authorized
    const userDomain = userEmail.split('@')[1];
    const isDomainAuthorized = authorized_domains.includes(userDomain);

    if (!isEmailAuthorized && !isDomainAuthorized) {
      // User is signed in but not authorized
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <Paper sx={{ p: 4, textAlign: 'center', maxWidth: 500 }}>
            <Typography variant="h4" gutterBottom color="error">
              Access Denied
            </Typography>
            <Typography variant="body1" paragraph>
              Your email address ({userEmail}) is not authorized to access this application.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Please contact your administrator to request access.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Authorized domains: {authorized_domains.join(', ')}
            </Typography>
            <Box sx={{ mt: 3 }}>
              <AuthButton />
            </Box>
          </Paper>
        </Box>
      );
    }
  }

  // User is authenticated and authorized, show the main app
  return <App />;
}

// Export the wrapped component
function AppWithAuth() {
  const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

  if (!clerkPubKey) {
    // No Clerk key, just show the app
    return <App />;
  }

  return (
    <ClerkProvider publishableKey={clerkPubKey}>
      <AuthenticatedApp />
    </ClerkProvider>
  );
}

export default AppWithAuth;
