import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Stack,
  Card,
  CardContent,
  Grid,
  Chip,
  Tabs,
  Tab,
  Avatar,
  useTheme,
  alpha,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Divider,
  Tooltip,
  Badge,
  TextField,
} from '@mui/material';
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarExport,
  GridToolbarDensitySelector,
  GridToolbarQuickFilter,
} from '@mui/x-data-grid';
import {
  Receipt as ReceiptIcon,
  Description as InvoiceIcon,
  LocalShipping as ShippingIcon,
  Inventory as InventoryIcon,
  ShoppingCart as OrderIcon,
  AccountBalance as BankIcon,
  Business as ContractIcon,
  Assignment as DocumentIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Visibility as VisibilityIcon,
  Image as ImageIcon,
  CloudUpload as UploadIcon,
  Scanner as ScannerIcon,
  BarChart as AnalyticsIcon,
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { useCustomTypes } from '../hooks/useCustomTypes';
import CustomTypeConfig from './CustomTypeConfig';

// Custom Toolbar
function CustomToolbar() {
  return (
    <GridToolbarContainer sx={{ p: 1, justifyContent: 'space-between' }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <GridToolbarColumnsButton />
        <GridToolbarFilterButton />
        <GridToolbarDensitySelector />
        <GridToolbarExport />
      </Box>
      <GridToolbarQuickFilter
        sx={{ minWidth: 300 }}
        debounceMs={300}
        placeholder="Search all columns..."
      />
    </GridToolbarContainer>
  );
}

// Sample data generator for different document types
const generateDocumentData = (docType, count = 15) => {
  const baseDate = Date.now();

  const documentData = {
    'invoices': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      document_id: `INV-${10000 + i}`,
      vendor_name: ['Tech Supplies Inc', 'Global Manufacturing', 'Quality Parts Ltd', 'Office Pro', 'Industrial Supply'][i % 5],
      invoice_date: new Date(baseDate - i * 86400000).toLocaleDateString(),
      due_date: new Date(baseDate + (30 - i) * 86400000).toLocaleDateString(),
      total_amount: (Math.random() * 50000 + 5000).toFixed(2),
      tax_amount: (Math.random() * 4000 + 400).toFixed(2),
      line_items: Math.floor(Math.random() * 15) + 1,
      payment_status: ['Paid', 'Pending', 'Overdue', 'Partial'][i % 4],
      ocr_confidence: (95 + Math.random() * 4).toFixed(1) + '%',
      validation_status: ['Validated', 'Needs Review', 'Auto-Approved'][i % 3],
      extracted_fields: ['Vendor', 'Amount', 'Date', 'PO Number', 'Tax'],
      image_url: '/sample/invoice-' + (i % 3 + 1) + '.png',
      processing_time: (Math.random() * 3 + 0.5).toFixed(2) + 's',
      matched_po: i % 3 === 0 ? `PO-${2000 + i}` : null,
      currency: 'USD',
    })),

    'purchase-orders': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      document_id: `PO-${20000 + i}`,
      vendor_name: ['Acme Corp', 'Widget Co', 'Parts Unlimited', 'Supply Chain Pro', 'Manufacturing Direct'][i % 5],
      po_date: new Date(baseDate - i * 86400000).toLocaleDateString(),
      delivery_date: new Date(baseDate + (i * 7 + 14) * 86400000).toLocaleDateString(),
      total_value: (Math.random() * 100000 + 10000).toFixed(2),
      items_count: Math.floor(Math.random() * 25) + 1,
      status: ['Open', 'Partially Received', 'Received', 'Invoiced'][i % 4],
      ocr_confidence: (93 + Math.random() * 6).toFixed(1) + '%',
      validation_status: ['Validated', 'Pending Review'][i % 2],
      requestor: ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams'][i % 4],
      department: ['Procurement', 'Operations', 'Manufacturing', 'IT'][i % 4],
      image_url: '/sample/po-' + (i % 2 + 1) + '.png',
      approval_status: ['Approved', 'Pending Approval'][i % 2],
      shipping_address: 'Extracted',
    })),

    'receipts': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      document_id: `RCP-${30000 + i}`,
      merchant_name: ['Office Depot', 'Staples', 'Amazon Business', 'Best Buy', 'Home Depot', 'FedEx', 'UPS Store'][i % 7],
      receipt_date: new Date(baseDate - i * 86400000).toLocaleDateString(),
      total_amount: (Math.random() * 500 + 10).toFixed(2),
      payment_method: ['Credit Card', 'Debit Card', 'Cash', 'Company Card'][i % 4],
      category: ['Office Supplies', 'Equipment', 'Shipping', 'Travel', 'Utilities'][i % 5],
      employee: ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams', 'Charlie Brown'][i % 5],
      ocr_confidence: (90 + Math.random() * 9).toFixed(1) + '%',
      validation_status: ['Approved', 'Needs Review', 'Rejected'][i % 3],
      expense_report: i % 2 === 0 ? `EXP-${4000 + i}` : 'Not Assigned',
      reimbursement_status: ['Reimbursed', 'Pending', 'Processed'][i % 3],
      image_url: '/sample/receipt-' + (i % 4 + 1) + '.png',
      items_extracted: Math.floor(Math.random() * 10) + 1,
    })),

    'shipping-documents': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      document_id: `SHIP-${40000 + i}`,
      tracking_number: `1Z999AA${10000000 + i}`,
      carrier: ['UPS', 'FedEx', 'DHL', 'USPS', 'FreightCo'][i % 5],
      ship_date: new Date(baseDate - i * 86400000).toLocaleDateString(),
      expected_delivery: new Date(baseDate + (i * 2 + 3) * 86400000).toLocaleDateString(),
      origin: ['New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX', 'Phoenix, AZ'][i % 5],
      destination: ['Miami, FL', 'Seattle, WA', 'Boston, MA', 'Denver, CO', 'Atlanta, GA'][i % 5],
      package_count: Math.floor(Math.random() * 5) + 1,
      total_weight: (Math.random() * 500 + 10).toFixed(2) + ' lbs',
      shipping_cost: (Math.random() * 200 + 25).toFixed(2),
      status: ['In Transit', 'Delivered', 'Out for Delivery', 'Processing'][i % 4],
      ocr_confidence: (92 + Math.random() * 7).toFixed(1) + '%',
      related_po: i % 3 === 0 ? `PO-${2000 + i}` : null,
      image_url: '/sample/shipping-' + (i % 3 + 1) + '.png',
    })),

    'inventory-labels': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      document_id: `INV-LABEL-${50000 + i}`,
      sku: `SKU-${100000 + i}`,
      product_name: ['Industrial Motor', 'Control Panel', 'Steel Sheets', 'Electronic Components', 'Safety Equipment'][i % 5],
      barcode: `${Math.floor(Math.random() * 1000000000000)}`,
      qr_code: 'Extracted',
      quantity: Math.floor(Math.random() * 1000) + 10,
      location: [`A${i % 10 + 1}-B${i % 5 + 1}-C${i % 3 + 1}`],
      batch_number: `BATCH-${new Date().getFullYear()}-${1000 + i}`,
      expiry_date: i % 3 === 0 ? new Date(baseDate + 365 * 86400000).toLocaleDateString() : 'N/A',
      unit_price: (Math.random() * 500 + 10).toFixed(2),
      ocr_confidence: (94 + Math.random() * 5).toFixed(1) + '%',
      validation_status: ['Verified', 'Needs Verification'][i % 2],
      warehouse: ['Warehouse A', 'Warehouse B', 'Distribution Center 1'][i % 3],
      image_url: '/sample/label-' + (i % 3 + 1) + '.png',
      last_scanned: new Date(baseDate - Math.random() * 7 * 86400000).toLocaleDateString(),
    })),

    'financial-documents': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      document_id: `FIN-${60000 + i}`,
      document_type: ['Bank Statement', 'Check', 'Wire Transfer', 'Payment Receipt', 'Tax Document'][i % 5],
      date: new Date(baseDate - i * 86400000).toLocaleDateString(),
      amount: (Math.random() * 100000 + 1000).toFixed(2),
      account_number: `****${Math.floor(Math.random() * 9000) + 1000}`,
      transaction_id: `TXN-${Math.floor(Math.random() * 1000000000)}`,
      payee: ['Tech Supplies Inc', 'Office Pro', 'Utility Company', 'Payroll Services', 'Tax Authority'][i % 5],
      status: ['Reconciled', 'Pending', 'Cleared'][i % 3],
      ocr_confidence: (91 + Math.random() * 8).toFixed(1) + '%',
      validation_status: ['Validated', 'Under Review'][i % 2],
      extracted_fields: ['Amount', 'Date', 'Account', 'Reference'],
      matched_transaction: i % 2 === 0,
      category: ['Operating Expense', 'Capital Expenditure', 'Revenue', 'Tax'][i % 4],
      image_url: '/sample/financial-' + (i % 2 + 1) + '.png',
    })),
  };

  return documentData[docType] || [];
};

const DocumentVisionIntelligence = ({ onNavigateToConfig }) => {
  const theme = useTheme();
  const [selectedType, setSelectedType] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [documentData, setDocumentData] = useState({});
  const [stats, setStats] = useState({});
  const [imageDialog, setImageDialog] = useState({ open: false, imageUrl: '', data: null });
  const [searchQuery, setSearchQuery] = useState('');
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  // Custom types management
  const { customTypes, addType, updateType, deleteType } = useCustomTypes('vision-studio-custom-types');
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [editingType, setEditingType] = useState(null);

  const defaultDocumentTypes = [
    {
      id: 1,
      name: 'invoices',
      display_name: 'Invoices',
      description: 'AI-extracted invoice data with automatic PO matching',
      icon: InvoiceIcon,
      color: '#2196F3',
    },
    {
      id: 2,
      name: 'purchase-orders',
      display_name: 'Purchase Orders',
      description: 'Automated PO processing and approval workflows',
      icon: OrderIcon,
      color: '#FF9800',
    },
    {
      id: 3,
      name: 'receipts',
      display_name: 'Receipts',
      description: 'Expense receipt scanning and categorization',
      icon: ReceiptIcon,
      color: '#4CAF50',
    },
    {
      id: 4,
      name: 'shipping-documents',
      display_name: 'Shipping Documents',
      description: 'Shipping label and tracking document extraction',
      icon: ShippingIcon,
      color: '#9C27B0',
    },
    {
      id: 5,
      name: 'inventory-labels',
      display_name: 'Inventory Labels',
      description: 'Barcode, QR code, and label data extraction',
      icon: InventoryIcon,
      color: '#00BCD4',
    },
    {
      id: 6,
      name: 'financial-documents',
      display_name: 'Financial Documents',
      description: 'Bank statements, checks, and payment processing',
      icon: BankIcon,
      color: '#E91E63',
    },
  ];

  // Icon mapping for custom types
  const iconMap = {
    Email: DocumentIcon,
    Description: InvoiceIcon,
    Assessment: AnalyticsIcon,
    Settings: SettingsIcon,
    BarChart: AnalyticsIcon,
    PieChart: AnalyticsIcon,
    TrendingUp: AnalyticsIcon,
    Speed: AnalyticsIcon,
    Storage: InventoryIcon,
    Cloud: UploadIcon,
  };

  const getIconComponent = (iconName) => {
    return iconMap[iconName] || DocumentIcon;
  };

  // Merge default and custom types
  const documentTypes = [
    ...defaultDocumentTypes,
    ...customTypes.map(type => ({
      ...type,
      icon: getIconComponent(type.icon),
    })),
  ];

  useEffect(() => {
    loadInitialData();
  }, [customTypes]);

  useEffect(() => {
    if (activeTab < documentTypes.length) {
      const currentType = documentTypes[activeTab];
      if (!documentData[currentType.name]) {
        loadDataForType(currentType.name);
      }
    }
  }, [activeTab]);

  const loadInitialData = () => {
    const initialStats = {};
    documentTypes.forEach(type => {
      const data = generateDocumentData(type.name, 15);
      setDocumentData(prev => ({ ...prev, [type.name]: data }));
      initialStats[type.name] = data.length;
    });
    setStats(initialStats);
  };

  // Custom type handlers
  const handleAddCustomType = () => {
    setEditingType(null);
    setConfigDialogOpen(true);
  };

  const handleEditCustomType = (type) => {
    setEditingType(type);
    setConfigDialogOpen(true);
  };

  const handleSaveCustomType = (formData) => {
    if (editingType) {
      updateType(editingType.id, formData);
    } else {
      addType(formData);
    }
    setConfigDialogOpen(false);
    setEditingType(null);
  };

  const handleDeleteCustomType = (typeId) => {
    setConfirmDialog({
      open: true,
      title: 'Delete Custom Type',
      message: 'Are you sure you want to delete this custom type?',
      onConfirm: () => {
        deleteType(typeId);
        if (selectedType?.id === typeId) {
          setSelectedType(null);
        }
        setConfirmDialog(prev => ({ ...prev, open: false }));
      },
    });
  };

  const loadDataForType = (typeName) => {
    setLoading(true);
    setTimeout(() => {
      const data = generateDocumentData(typeName, 15);
      setDocumentData(prev => ({ ...prev, [typeName]: data }));
      setStats(prev => ({ ...prev, [typeName]: data.length }));
      setLoading(false);
    }, 500);
  };

  const handleViewImage = (row) => {
    setImageDialog({
      open: true,
      imageUrl: row.image_url,
      data: row,
    });
  };

  const handleCloseImage = () => {
    setImageDialog({ open: false, imageUrl: '', data: null });
  };

  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase() || '';
    if (['validated', 'approved', 'paid', 'delivered', 'verified', 'reconciled'].some(s => statusLower.includes(s))) {
      return theme.palette.success.main;
    }
    if (['pending', 'review', 'processing'].some(s => statusLower.includes(s))) {
      return theme.palette.warning.main;
    }
    if (['rejected', 'overdue', 'failed'].some(s => statusLower.includes(s))) {
      return theme.palette.error.main;
    }
    return theme.palette.grey[500];
  };

  const buildColumnsForType = (typeName) => {
    const commonColumns = [
      {
        field: 'actions',
        headerName: 'Image',
        width: 80,
        sortable: false,
        renderCell: (params) => (
          <Tooltip title="View Document Image">
            <IconButton size="small" color="primary" onClick={() => handleViewImage(params.row)}>
              <ImageIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ),
      },
    ];

    const typeSpecificColumns = {
      'invoices': [
        { field: 'document_id', headerName: 'Invoice #', width: 130 },
        { field: 'vendor_name', headerName: 'Vendor', width: 200 },
        { field: 'invoice_date', headerName: 'Date', width: 120 },
        { field: 'total_amount', headerName: 'Amount', width: 120, renderCell: (params) => `$${params.value}` },
        { field: 'payment_status', headerName: 'Status', width: 130, renderCell: (params) => (
          <Chip label={params.value} size="small" sx={{ bgcolor: alpha(getStatusColor(params.value), 0.1), color: getStatusColor(params.value) }} />
        )},
        { field: 'ocr_confidence', headerName: 'OCR Confidence', width: 140 },
        { field: 'validation_status', headerName: 'Validation', width: 140 },
        { field: 'matched_po', headerName: 'Matched PO', width: 130 },
      ],
      'purchase-orders': [
        { field: 'document_id', headerName: 'PO #', width: 130 },
        { field: 'vendor_name', headerName: 'Vendor', width: 200 },
        { field: 'po_date', headerName: 'PO Date', width: 120 },
        { field: 'total_value', headerName: 'Value', width: 120, renderCell: (params) => `$${params.value}` },
        { field: 'items_count', headerName: 'Items', width: 90 },
        { field: 'status', headerName: 'Status', width: 150, renderCell: (params) => (
          <Chip label={params.value} size="small" sx={{ bgcolor: alpha(getStatusColor(params.value), 0.1), color: getStatusColor(params.value) }} />
        )},
        { field: 'ocr_confidence', headerName: 'OCR Confidence', width: 140 },
        { field: 'department', headerName: 'Department', width: 130 },
      ],
      'receipts': [
        { field: 'document_id', headerName: 'Receipt #', width: 140 },
        { field: 'merchant_name', headerName: 'Merchant', width: 180 },
        { field: 'receipt_date', headerName: 'Date', width: 120 },
        { field: 'total_amount', headerName: 'Amount', width: 110, renderCell: (params) => `$${params.value}` },
        { field: 'category', headerName: 'Category', width: 140 },
        { field: 'employee', headerName: 'Employee', width: 150 },
        { field: 'validation_status', headerName: 'Status', width: 130, renderCell: (params) => (
          <Chip label={params.value} size="small" sx={{ bgcolor: alpha(getStatusColor(params.value), 0.1), color: getStatusColor(params.value) }} />
        )},
        { field: 'ocr_confidence', headerName: 'OCR Confidence', width: 140 },
      ],
      'shipping-documents': [
        { field: 'document_id', headerName: 'Document #', width: 140 },
        { field: 'tracking_number', headerName: 'Tracking #', width: 180 },
        { field: 'carrier', headerName: 'Carrier', width: 110 },
        { field: 'origin', headerName: 'Origin', width: 150 },
        { field: 'destination', headerName: 'Destination', width: 150 },
        { field: 'status', headerName: 'Status', width: 140, renderCell: (params) => (
          <Chip label={params.value} size="small" sx={{ bgcolor: alpha(getStatusColor(params.value), 0.1), color: getStatusColor(params.value) }} />
        )},
        { field: 'package_count', headerName: 'Packages', width: 100 },
        { field: 'ocr_confidence', headerName: 'OCR Confidence', width: 140 },
      ],
      'inventory-labels': [
        { field: 'document_id', headerName: 'Label ID', width: 150 },
        { field: 'sku', headerName: 'SKU', width: 140 },
        { field: 'product_name', headerName: 'Product', width: 200 },
        { field: 'quantity', headerName: 'Qty', width: 90 },
        { field: 'location', headerName: 'Location', width: 130 },
        { field: 'warehouse', headerName: 'Warehouse', width: 160 },
        { field: 'validation_status', headerName: 'Status', width: 150, renderCell: (params) => (
          <Chip label={params.value} size="small" sx={{ bgcolor: alpha(getStatusColor(params.value), 0.1), color: getStatusColor(params.value) }} />
        )},
        { field: 'ocr_confidence', headerName: 'OCR Confidence', width: 140 },
      ],
      'financial-documents': [
        { field: 'document_id', headerName: 'Document #', width: 140 },
        { field: 'document_type', headerName: 'Type', width: 150 },
        { field: 'date', headerName: 'Date', width: 120 },
        { field: 'amount', headerName: 'Amount', width: 130, renderCell: (params) => `$${params.value}` },
        { field: 'payee', headerName: 'Payee', width: 180 },
        { field: 'status', headerName: 'Status', width: 130, renderCell: (params) => (
          <Chip label={params.value} size="small" sx={{ bgcolor: alpha(getStatusColor(params.value), 0.1), color: getStatusColor(params.value) }} />
        )},
        { field: 'category', headerName: 'Category', width: 160 },
        { field: 'ocr_confidence', headerName: 'OCR Confidence', width: 140 },
      ],
    };

    return [...commonColumns, ...(typeSpecificColumns[typeName] || [])];
  };

  const getTotalDocuments = () => {
    return Object.values(stats).reduce((acc, val) => acc + val, 0);
  };

  // Tile Landing View
  if (!selectedType) {
    // Filter tiles based on search query
    const filteredTypes = documentTypes.filter((type) =>
      type.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      type.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
        <Box sx={{ mb: 4 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                sx={{
                  width: 64,
                  height: 64,
                  bgcolor: alpha('#9C27B0', 0.1),
                }}
              >
                <DocumentIcon sx={{ fontSize: 36, color: '#9C27B0' }} />
              </Avatar>
              <Box>
                <Typography variant="h4" fontWeight={700}>
                  VISION.AI - Document Intelligence
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  AI-powered OCR and document processing platform
                </Typography>
              </Box>
            </Box>
            <Stack direction="row" spacing={2}>
              <Button startIcon={<SettingsIcon />} variant="outlined" onClick={onNavigateToConfig}>
                Configure
              </Button>
              <Button startIcon={<RefreshIcon />} variant="outlined" onClick={loadInitialData}>
                Refresh
              </Button>
            </Stack>
          </Stack>

          {/* Search Bar */}
          <TextField
            fullWidth
            placeholder="Search document types..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon sx={{ color: 'text.secondary', mr: 1 }} />,
              endAdornment: searchQuery && (
                <IconButton size="small" onClick={() => setSearchQuery('')}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              ),
            }}
            sx={{
              mt: 2,
              '& .MuiOutlinedInput-root': {
                backgroundColor: alpha(theme.palette.primary.main, 0.02),
              },
            }}
          />
        </Box>

        <Grid container spacing={1.5}>
          {filteredTypes.map((type, index) => {
            const IconComponent = type.icon;
            return (
              <Grid item xs={12} sm={6} md={4} key={type.id}>
                <Card
                  sx={{
                    height: 200,
                    cursor: 'pointer',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                    border: '1px solid',
                    borderColor: alpha(type.color, 0.15),
                    borderRadius: 2,
                    overflow: 'hidden',
                    position: 'relative',
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: 3,
                      background: `linear-gradient(135deg, ${type.color} 0%, ${alpha(type.color, 0.7)} 100%)`,
                      opacity: 0.8,
                    },
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: `0 12px 24px ${alpha(type.color, 0.15)}`,
                      borderColor: type.color,
                      '& .module-icon': {
                        transform: 'scale(1.15)',
                        bgcolor: type.color,
                        color: 'white',
                      },
                      '& .module-arrow': {
                        opacity: 1,
                        transform: 'translateX(4px)',
                      },
                    },
                  }}
                  onClick={() => setSelectedType(type)}
                >
                  <CardContent sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                      <Avatar
                        className="module-icon"
                        sx={{
                          width: 40,
                          height: 40,
                          bgcolor: alpha(type.color, 0.1),
                          color: type.color,
                          transition: 'all 0.3s ease',
                        }}
                      >
                        <IconComponent sx={{ fontSize: 22 }} />
                      </Avatar>
                      {type.isCustom && (
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditCustomType(type);
                            }}
                            sx={{ width: 24, height: 24, color: type.color }}
                          >
                            <EditIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteCustomType(type.id);
                            }}
                            sx={{ width: 24, height: 24, color: '#F44336' }}
                          >
                            <DeleteIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Box>
                      )}
                    </Box>
                    <Typography variant="body1" sx={{ fontWeight: 700, color: type.color, mb: 0.5, fontSize: '0.9rem', lineHeight: 1.3 }}>
                      {type.display_name}
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary', mb: 'auto', lineHeight: 1.4, fontSize: '0.7rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {type.description}
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, pt: 1, borderTop: '1px solid', borderColor: alpha(type.color, 0.1) }}>
                      <Chip label={`${stats[type.name] || 0} Documents`} size="small" sx={{ height: 22, fontSize: '0.65rem', bgcolor: alpha(type.color, 0.08), color: type.color, fontWeight: 600 }} />
                      <ArrowForwardIcon className="module-arrow" sx={{ color: type.color, fontSize: 18, opacity: 0.5, transition: 'all 0.3s ease' }} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}

          {/* Add Custom Type Tile */}
          {!searchQuery && (
            <Grid item xs={12} sm={6} md={4}>
              <Card
                sx={{
                  height: 200,
                  cursor: 'pointer',
                  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                  border: '2px dashed',
                  borderColor: 'divider',
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    borderColor: 'primary.main',
                    bgcolor: alpha(theme.palette.primary.main, 0.02),
                  },
                }}
                onClick={handleAddCustomType}
              >
                <CardContent sx={{ textAlign: 'center' }}>
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      bgcolor: alpha(theme.palette.primary.main, 0.1),
                      color: 'primary.main',
                      mx: 'auto',
                      mb: 2,
                    }}
                  >
                    <AddIcon sx={{ fontSize: 32 }} />
                  </Avatar>
                  <Typography variant="body1" fontWeight={600} color="primary">
                    Add Custom Type
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Create your own document type
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>

        {/* No Results Message */}
        {filteredTypes.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <SearchIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No document types found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try adjusting your search query
            </Typography>
          </Box>
        )}
      </Box>
    );
  }

  // Detail View for Selected Type
  const currentTypeIndex = documentTypes.findIndex(t => t.id === selectedType.id);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Box>
            <Button startIcon={<ArrowBackIcon />} onClick={() => setSelectedType(null)} variant="text" sx={{ mb: 1 }}>
              Back to Document Types
            </Button>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              {selectedType.display_name}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {selectedType.description}
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button startIcon={<UploadIcon />} variant="outlined">
              Upload Documents
            </Button>
            <Button startIcon={<RefreshIcon />} variant="outlined" onClick={loadInitialData}>
              Refresh
            </Button>
          </Stack>
        </Stack>
      </Box>

      {/* Data Grid */}
      <Paper>
        <Box sx={{ height: 650, width: '100%' }}>
          <DataGrid
            rows={documentData[selectedType.name] || []}
            columns={buildColumnsForType(selectedType.name)}
            density="compact"
            initialState={{
              pagination: { paginationModel: { pageSize: 25, page: 0 } },
            }}
            pageSizeOptions={[10, 25, 50, 100]}
            loading={loading}
            checkboxSelection
            disableRowSelectionOnClick
            slots={{ toolbar: CustomToolbar }}
            sx={{
              border: 'none',
              '& .MuiDataGrid-cell:focus': { outline: 'none' },
              '& .MuiDataGrid-row:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.05),
              },
              '& .MuiDataGrid-columnHeaders': {
                backgroundColor: theme.palette.mode === 'light' ? 'grey.100' : 'grey.900',
                fontSize: '0.875rem',
                fontWeight: 600,
              },
            }}
          />
        </Box>
      </Paper>

      {/* Image Preview Dialog */}
      <Dialog open={imageDialog.open} onClose={handleCloseImage} maxWidth="md" fullWidth>
        <DialogTitle>
          <Stack direction="row" alignItems="center" spacing={2}>
            <ImageIcon color="primary" />
            <Typography variant="h6">Document Image Preview</Typography>
          </Stack>
        </DialogTitle>
        <Divider />
        <DialogContent>
          {imageDialog.data && (
            <>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Document ID</Typography>
                  <Typography variant="body1" fontWeight={600}>{imageDialog.data.document_id}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">OCR Confidence</Typography>
                  <Typography variant="body1" fontWeight={600}>{imageDialog.data.ocr_confidence}</Typography>
                </Grid>
              </Grid>
              <Box sx={{
                bgcolor: 'grey.100',
                p: 3,
                borderRadius: 2,
                textAlign: 'center',
                minHeight: 300,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Typography variant="body2" color="text.secondary">
                  📄 Document image would be displayed here
                  <br />
                  <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                    Path: {imageDialog.imageUrl}
                  </Typography>
                </Typography>
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseImage}>Close</Button>
          <Button variant="contained" startIcon={<AnalyticsIcon />}>
            View Extracted Data
          </Button>
        </DialogActions>
      </Dialog>

      {/* Custom Type Config Dialog */}
      <CustomTypeConfig
        open={configDialogOpen}
        onClose={() => {
          setConfigDialogOpen(false);
          setEditingType(null);
        }}
        onSave={handleSaveCustomType}
        editType={editingType}
        moduleType="vision"
      />

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          {confirmDialog.title}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
            color="inherit"
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDialog.onConfirm}
            color="error"
            variant="contained"
            autoFocus
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentVisionIntelligence;
