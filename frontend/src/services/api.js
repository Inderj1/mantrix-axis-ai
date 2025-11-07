import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const apiService = {
  // Health check
  checkHealth: () => api.get('/api/v1/health'),

  // Query endpoints
  generateSQL: (question, options = {}) => {
    // Don't send dataset parameter - let backend use its configured values
    return api.post('/api/v1/generate', { 
      question, 
      ...options 
    });
  },
  
  executeQuery: (question, options = {}) => {
    // Don't send dataset parameter - let backend use its configured values
    const { conversationId, ...otherOptions } = options;
    return api.post('/api/v1/query', { 
      question,
      conversationId: conversationId,
      options: otherOptions 
    });
  },
  
  // Schema endpoints
  getSchemas: () => api.get('/api/v1/schemas'),
  
  // Query suggestions
  getQuerySuggestions: (context) => 
    api.post('/api/v1/query-suggestions', { context }),
  
  // Cache endpoints
  getCacheStats: () => api.get('/api/v1/cache/stats'),
  getPopularQueries: (limit = 10) => 
    api.get(`/api/v1/cache/popular?limit=${limit}`),
  
  // Optimization endpoints
  optimizeQuery: (sql) => 
    api.post('/api/v1/optimize', { sql }),
  
  // Query explanation
  explainQuery: (question, sql) => 
    api.post('/api/v1/explain', { question, sql }),
  
  // Error correction
  correctError: (question, sql, error) => 
    api.post('/api/v1/correct-error', { question, sql, error }),
  
  // Result analysis
  analyzeResults: (question, sql, results, metadata = null) =>
    api.post('/api/v1/analyze-results', { 
      question, 
      sql, 
      results,
      metadata 
    }),
  
  // Document Intelligence endpoints
  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/v1/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  listDocuments: () => api.get('/api/v1/documents'),
  
  deleteDocument: (documentId) => 
    api.delete(`/api/v1/documents/${documentId}`),
  
  analyzeDocument: (documentId, analysisType = 'comprehensive', options = {}) =>
    api.post('/api/v1/documents/analyze', {
      document_id: documentId,
      analysis_type: analysisType,
      options: options || {},
    }),
  
  askDocumentQuestion: (documentIds, question) =>
    api.post('/api/v1/documents/question', {
      document_ids: documentIds,
      question,
    }),
  
  // Conversation endpoints
  createConversation: (userId = 'default', title = 'New Conversation') =>
    api.post('/api/v1/conversations', {
      user_id: userId,
      title,
    }),
  
  listConversations: (userId = 'default', limit = 50, skip = 0) =>
    api.get('/api/v1/conversations', {
      params: { user_id: userId, limit, skip }
    }),
  
  getConversation: (conversationId) =>
    api.get(`/api/v1/conversations/${conversationId}`),
  
  addMessage: (conversationId, message) =>
    api.put(`/api/v1/conversations/${conversationId}/messages`, {
      message: {
        id: message.id,
        type: message.type,
        content: message.content,
        timestamp: message.timestamp,
        sql: message.sql,
        results: message.results,
        result_count: message.resultCount || message.result_count,
        error: message.error,
        metadata: message.metadata
      },
    }),
  
  updateConversation: (conversationId, updates) =>
    api.patch(`/api/v1/conversations/${conversationId}`, updates),
  
  deleteConversation: (conversationId) =>
    api.delete(`/api/v1/conversations/${conversationId}`),
  
  deleteAllConversations: (userId = 'default') =>
    api.delete(`/api/v1/conversations/user/${userId}/all`),
  
  searchConversations: (query, userId = 'default', limit = 20) =>
    api.post('/api/v1/conversations/search', {
      query,
      user_id: userId,
      limit,
    }),
  
  // Analytics endpoints for Core.AI dashboard
  getAnalyticsDashboard: () => 
    api.get('/api/v1/analytics/dashboard'),
  
  getCustomerSegments: () =>
    api.get('/api/v1/analytics/segments'),
  
  getRevenueTrends: (months = 12) =>
    api.get(`/api/v1/analytics/revenue-trends?months=${months}`),
  
  getRetentionAnalytics: () =>
    api.get('/api/v1/analytics/retention'),
  
  getProductAnalytics: () =>
    api.get('/api/v1/analytics/products'),
  
  getTopCustomers: (segment = null, limit = 20) => {
    const params = new URLSearchParams({ limit });
    if (segment) params.append('segment', segment);
    return api.get(`/api/v1/analytics/top-customers?${params}`);
  },
  
  getAIInsights: () =>
    api.get('/api/v1/analytics/insights'),
  
  getCohortInsights: () =>
    api.get('/api/v1/analytics/cohort-insights'),
  
  getPerformanceInsights: (context = null) =>
    api.get('/api/v1/analytics/performance-insights', {
      params: context ? { context } : {}
    }),
  
  getRecommendations: (focusArea = null) =>
    api.get('/api/v1/analytics/recommendations', {
      params: focusArea ? { focus_area: focusArea } : {}
    }),
  
  askFollowUpQuestion: (question, context) =>
    api.post('/api/v1/analytics/insights/follow-up', {
      question,
      context
    }),
  
  getChurnRiskCustomers: (recencyDays = 180) =>
    api.get(`/api/v1/analytics/churn-risk?recency_days=${recencyDays}`),
  
  // Customer 360 endpoints
  getCustomer360: (customerId) => 
    api.get(`/api/v1/analytics/customer/${customerId}`),
  
  searchCustomers: (searchTerm, limit = 50) => 
    api.get('/api/v1/analytics/customers/search', {
      params: { q: searchTerm, limit }
    }),
  
  // Product Performance endpoints  
  getProductMetrics: () => 
    api.get('/api/v1/analytics/products/metrics'),
  
  getProductBySegment: (productId) => 
    api.get(`/api/v1/analytics/products/${productId}/segments`),
  
  getProductTrends: (productId, months = 12) => 
    api.get(`/api/v1/analytics/products/${productId}/trends?months=${months}`),
  
  // Financial Analytics endpoints
  getFinancialSummary: () => 
    api.get('/api/v1/analytics/financial/summary'),
  
  getFinancialTrends: (months = 24) => 
    api.get(`/api/v1/analytics/financial/trends?months=${months}`),
  
  getProfitabilityAnalysis: () => 
    api.get('/api/v1/analytics/financial/profitability'),
  
  // Data Tables endpoints
  getCustomerMasterTable: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.offset !== undefined) queryParams.append('offset', params.offset);
    if (params.limit !== undefined) queryParams.append('limit', params.limit);
    if (params.search) queryParams.append('search', params.search);
    if (params.segment) queryParams.append('segment', params.segment);
    if (params.abc_class) queryParams.append('abc_class', params.abc_class);
    return api.get(`/api/v1/analytics/tables/customer-master?${queryParams.toString()}`);
  },
  
  getTransactionTable: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.offset !== undefined) queryParams.append('offset', params.offset);
    if (params.limit !== undefined) queryParams.append('limit', params.limit);
    if (params.customer_id) queryParams.append('customer_id', params.customer_id);
    if (params.product) queryParams.append('product', params.product);
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    return api.get(`/api/v1/analytics/tables/transactions?${queryParams.toString()}`);
  },
  
  getSegmentationPerformanceTable: () => 
    api.get('/api/v1/analytics/tables/segmentation-performance'),
  
  getCohortRetentionTable: () => 
    api.get('/api/v1/analytics/tables/cohort-retention'),
  
  getCohortRevenueTable: () => 
    api.get('/api/v1/analytics/tables/cohort-revenue'),
  
  getTimeSeriesPerformanceTable: (segment = null) => {
    const url = segment 
      ? `/api/v1/analytics/tables/time-series-performance?segment=${segment}`
      : '/api/v1/analytics/tables/time-series-performance';
    return api.get(url);
  },
  
  getProductCustomerMatrixTable: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.top_products) queryParams.append('top_products', params.top_products);
    if (params.segment) queryParams.append('segment', params.segment);
    return api.get(`/api/v1/analytics/tables/product-customer-matrix?${queryParams.toString()}`);
  },
  
  // Research endpoints
  createResearchPlan: (query, depth = 'standard', focusAreas = null) =>
    api.post('/api/v1/research/plan', { 
      query, 
      depth, 
      focus_areas: focusAreas 
    }),
  
  executeResearchPlan: (planId, parallel = true) =>
    api.post(`/api/v1/research/execute/${planId}`, { parallel }),
  
  getResearchStatus: (executionId) =>
    api.get(`/api/v1/research/status/${executionId}`),
  
  getResearchResults: (executionId) =>
    api.get(`/api/v1/research/results/${executionId}`),
  
  // Query logs endpoints
  getQueryLogs: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.limit !== undefined) queryParams.append('limit', params.limit);
    if (params.offset !== undefined) queryParams.append('offset', params.offset);
    if (params.mode) queryParams.append('mode', params.mode);
    return api.get(`/api/v1/query-logs?${queryParams.toString()}`);
  },
  
  clearQueryLogs: () =>
    api.delete('/api/v1/query-logs'),
  
  // Mantrax Agent endpoints
  formatResultsWithMantrax: (query, sql, results, metadata = null) =>
    api.post('/api/v1/mantrax/format-results', {
      query,
      sql,
      results,
      metadata
    }),
  
  listMantraxAgents: () =>
    api.get('/api/v1/mantrax/agents'),
  
  getMantraxAgentHistory: (agentName, limit = 10) =>
    api.get(`/api/v1/mantrax/agents/${agentName}/history?limit=${limit}`),
  
  // Executive Analytics endpoints
  getExecutiveSummary: () =>
    api.get('/api/v1/executive/summary'),
  
  getRevenueProfitability: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.group_by) queryParams.append('group_by', params.group_by);
    if (params.time_period) queryParams.append('time_period', params.time_period);
    return api.get(`/api/v1/executive/revenue-profitability?${queryParams.toString()}`);
  },
  
  getCashWorkingCapital: () =>
    api.get('/api/v1/executive/cash-working-capital'),
  
  getGrowthMarketPosition: () =>
    api.get('/api/v1/executive/growth-market-position'),
  
  getActionAccountability: () =>
    api.get('/api/v1/executive/action-accountability'),
  
  getGLHierarchy: (level, accountGroup = null) => {
    const url = accountGroup
      ? `/api/v1/executive/gl-hierarchy/${level}?account_group=${accountGroup}`
      : `/api/v1/executive/gl-hierarchy/${level}`;
    return api.get(url);
  },

  // User Profile endpoints
  getUserProfileTemplates: () =>
    api.get('/api/v1/user-profiles/templates'),

  getUserProfileTemplate: (role) =>
    api.get(`/api/v1/user-profiles/templates/${role}`),

  listUserProfiles: () =>
    api.get('/api/v1/user-profiles'),

  getUserProfile: (userId) =>
    api.get(`/api/v1/user-profiles/${userId}`),

  createUserProfile: (profileData) =>
    api.post('/api/v1/user-profiles', profileData),

  updateUserProfile: (userId, updateData) =>
    api.put(`/api/v1/user-profiles/${userId}`, updateData),

  deleteUserProfile: (userId) =>
    api.delete(`/api/v1/user-profiles/${userId}`),

  getUserPersonalizationContext: (userId) =>
    api.get(`/api/v1/user-profiles/${userId}/context`),

  // Format results with personalization
  formatResultsWithMantrax: (query, sql, results, metadata = null, userId = null) =>
    api.post('/api/v1/mantrax/format-results', {
      query,
      sql,
      results,
      metadata,
      user_id: userId
    }),

  // Markets.AI endpoints
  getMarketSignals: (params = {}) =>
    api.get('/api/v1/markets/signals', { params }),

  getMarketSignal: (signalId) =>
    api.get(`/api/v1/markets/signals/${signalId}`),

  getSignalsByCategory: (category) =>
    api.get(`/api/v1/markets/categories/${category}`),

  getMarketSummary: () =>
    api.get('/api/v1/markets/summary'),

  getCategoryConfig: (customerId = null) =>
    api.get('/api/v1/markets/config', { params: customerId ? { customer_id: customerId } : {} }),

  saveCategoryConfig: (config) =>
    api.post('/api/v1/markets/config', config),

  updateMarketSignal: (signalId, update) =>
    api.patch(`/api/v1/markets/signals/${signalId}`, update),

  createMarketSignal: (signal) =>
    api.post('/api/v1/markets/signals', signal),

  forceMarketRefresh: (category = null) =>
    api.post('/api/v1/markets/refresh', null, { params: category ? { category } : {} }),

  getSchedulerStatus: () =>
    api.get('/api/v1/markets/scheduler/status'),

  // Generic HTTP methods
  get: (url, config) => api.get(url, config),
  post: (url, data, config) => api.post(url, data, config),
  put: (url, data, config) => api.put(url, data, config),
  delete: (url, config) => api.delete(url, config),
};

export default api;