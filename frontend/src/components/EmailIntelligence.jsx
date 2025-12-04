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
  Badge,
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
  TextField,
  InputAdornment,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  FormGroup,
  FormControlLabel,
  Checkbox,
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
  Email as EmailIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Business as BusinessIcon,
  Person as PersonIcon,
  Receipt as ReceiptIcon,
  Notifications as NotificationsIcon,
  Refresh as RefreshIcon,
  ShoppingCart as ShoppingCartIcon,
  Inventory as InventoryIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon,
  Assignment as AssignmentIcon,
  Settings as SettingsIcon,
  SentimentSatisfied as SentimentPositiveIcon,
  SentimentDissatisfied as SentimentNegativeIcon,
  SentimentNeutral as SentimentNeutralIcon,
  Visibility as VisibilityIcon,
  OpenInNew as OpenInNewIcon,
  AttachFile as AttachFileIcon,
  Schedule as ScheduleIcon,
  Search as SearchIcon,
  FilterList as FilterListIcon,
  Download as DownloadIcon,
  ViewColumn as ViewColumnIcon,
  Clear as ClearIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useCustomTypes } from '../hooks/useCustomTypes';
import CustomTypeConfig from './CustomTypeConfig';

// Custom Toolbar for DataGrid
function CustomToolbar({ onExport }) {
  return (
    <GridToolbarContainer sx={{ p: 1, justifyContent: 'space-between' }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <GridToolbarColumnsButton />
        <GridToolbarFilterButton />
        <GridToolbarDensitySelector />
        <GridToolbarExport />
      </Box>
      <GridToolbarQuickFilter
        sx={{
          minWidth: 300,
          '& .MuiInput-root': {
            fontSize: '0.875rem',
          }
        }}
        debounceMs={300}
        placeholder="Search all columns..."
      />
    </GridToolbarContainer>
  );
}
// Icon mapping
const iconMap = {
  Email: EmailIcon,
  Business: BusinessIcon,
  Person: PersonIcon,
  Receipt: ReceiptIcon,
  Notifications: NotificationsIcon,
  ShoppingCart: ShoppingCartIcon,
  Inventory: InventoryIcon,
  TrendingUp: TrendingUpIcon,
  Assessment: AssessmentIcon,
  Assignment: AssignmentIcon,
};

// Sample data generator
const generateSampleData = (typeName, count = 10) => {
  const sampleData = {
    'customer-inquiries': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      customer_name: ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams', 'Charlie Brown', 'Michael Chen', 'Sarah Parker', 'David Kumar', 'Emma Wilson', 'Robert Garcia'][i % 10],
      customer_email: ['john.doe@techcorp.com', 'jane.smith@retail.com', 'bob.j@enterprise.com', 'alice.w@startup.io', 'charlie@consulting.com', 'mchen@manufacturing.com', 'sparker@logistics.com', 'dkumar@finance.com', 'ewilson@healthcare.com', 'rgarcia@education.org'][i % 10],
      subject: [
        'Urgent: API Integration Issues - Request for Technical Support',
        'Product Return Authorization - Order #45892',
        'Enterprise License Pricing for 500+ Users',
        'Feature Request: SSO Integration with Azure AD',
        'Critical Bug: Payment Processing Failure on Checkout',
        'Implementation Timeline for Q1 2024 Deployment',
        'Account Upgrade - Need Migration Assistance',
        'Training Resources for New Platform Features',
        'Data Export Request - GDPR Compliance',
        'Performance Issues During Peak Hours'
      ][i % 10],
      inquiry_type: ['technical_support', 'product_inquiry', 'billing', 'feature_request', 'bug_report', 'implementation'][i % 6],
      status: ['open', 'in_progress', 'pending_customer', 'resolved', 'closed'][i % 5],
      priority: ['low', 'medium', 'high', 'critical'][i % 4],
      received_date: new Date(Date.now() - i * 86400000).toLocaleDateString(),
      response_time: [2, 5, 12, 24, 48, 1, 3, 8, 16, 36][i % 10] + ' hours',
      assigned_to: ['Support Team', 'Sales Team', 'Engineering', 'Product Manager', 'Customer Success'][i % 5],
      products_mentioned: [
        'Enterprise API Gateway, Analytics Dashboard',
        'Core Platform License',
        'Premium Support Package',
        'SSO Integration Module',
        'Payment Processing API',
        'Cloud Infrastructure',
        'Mobile SDK, iOS Framework',
        'Training Portal Access',
        'Data Export Tool',
        'Performance Monitoring Suite'
      ][i % 10],
      attachments: i % 3 === 0 ? Math.floor(Math.random() * 3) + 1 : 0,
      thread_length: Math.floor(Math.random() * 8) + 1,
      sla_breach: i % 7 === 0,
      content: [
        'Hi Team,\n\nWe are experiencing critical issues with the API integration. Our production environment has been throwing 503 errors intermittently for the past 2 hours. This is affecting our customer-facing application.\n\nError details:\n- Endpoint: /api/v2/transactions\n- Error code: 503 Service Unavailable\n- Frequency: ~40% of requests\n\nWe need immediate assistance as this is impacting our SLA commitments to customers.\n\nBest regards,\nJohn',
        'Hello,\n\nI would like to initiate a return for Order #45892 (Enterprise Platform License). The product does not meet our requirements as discussed during the sales process.\n\nOrder Details:\n- Order Date: Dec 15, 2024\n- License Type: 100 User Seats\n- Amount: $12,500\n\nPlease provide the RMA number and return instructions.\n\nThanks,\nJane',
        'Dear Sales Team,\n\nWe are evaluating your platform for enterprise-wide deployment across 500+ users in 12 global offices. Could you please provide:\n\n1. Volume pricing for 500-1000 users\n2. Multi-year commitment discounts\n3. Professional services costs\n4. Implementation timeline estimate\n5. Reference customers at similar scale\n\nWe are targeting Q1 2024 for go-live.\n\nRegards,\nBob Johnson',
        'Hello Product Team,\n\nOur organization requires Single Sign-On (SSO) integration with Azure Active Directory. This is a critical requirement for our security compliance.\n\nKey requirements:\n- SAML 2.0 support\n- Multi-factor authentication\n- Role-based access control sync\n- Auto-provisioning/deprovisioning\n\nWhat is your roadmap for this feature?\n\nBest,\nAlice',
        'URGENT - Critical Payment Bug\n\nWe are seeing payment failures on checkout with the following error:\n"Payment gateway timeout - transaction aborted"\n\nThis started approximately 3 hours ago. We have lost 15+ transactions totaling $8,500+.\n\nPlease investigate immediately!\n\nCharlie Brown\nCTO, Retail Corp',
        'Hi Implementation Team,\n\nWe need to finalize the deployment timeline for our Q1 2024 implementation. Our internal stakeholders are requesting:\n\n- Detailed project plan with milestones\n- Resource requirements from our side\n- Training schedule for admins and users\n- Data migration approach and timeline\n- Cutover plan and rollback procedures\n\nCan we schedule a planning call this week?\n\nMichael',
        'Hello,\n\nWe would like to upgrade our account from Professional to Enterprise tier. We need assistance with:\n\n1. Data migration from current plan\n2. User permissions reconfiguration\n3. New features enablement\n4. Billing proration details\n\nWhat is the estimated timeline for this upgrade?\n\nSarah Parker',
        'Dear Support,\n\nOur team is struggling with the new dashboard features released last month. Do you have:\n\n- Video tutorials\n- Documentation for advanced features\n- Best practices guide\n- Sample templates/configurations\n\nWe would also like to schedule a training session for our 25 users.\n\nDavid Kumar',
        'Hello Data Team,\n\nPer GDPR Article 20, we request a complete export of all data associated with our account:\n\n- User data and activity logs\n- Transaction records\n- Configuration settings\n- Uploaded documents and files\n\nPlease provide in machine-readable format (JSON/CSV) within the required 30-day timeframe.\n\nEmma Wilson\nData Protection Officer',
        'Hi Support,\n\nWe are experiencing severe performance degradation during peak hours (2-5 PM EST):\n\n- Page load times: 8-12 seconds (normally <2s)\n- API response times: 3000-5000ms (normally <500ms)\n- Timeout errors on reports\n\nThis is affecting 150+ concurrent users. Can you investigate server capacity and optimization?\n\nRobert Garcia'
      ][i % 10],
      sentiment: ['positive', 'neutral', 'negative', 'urgent'][i % 4],
      extracted_amounts: i % 3 === 0 ? ['$' + (Math.random() * 50000 + 1000).toFixed(2)] : [],
      extracted_dates: i % 2 === 0 ? [new Date(Date.now() + (i * 7 - 14) * 86400000).toLocaleDateString()] : [],
      language: 'English',
      tags: [['urgent', 'technical'], ['return', 'refund'], ['sales', 'enterprise'], ['feature', 'security'], ['critical', 'bug']][i % 5],
    })),

    'vendor-communications': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      vendor_name: ['Tech Supplies Inc', 'Global Manufacturing Co', 'Quality Parts Ltd', 'Logistics Pro Solutions', 'Materials Direct Corp', 'Industrial Components LLC', 'Supply Chain Partners', 'Premier Distributors Inc', 'Worldwide Suppliers', 'Express Logistics'][i % 10],
      vendor_email: ['orders@techsupplies.com', 'sales@globalman.com', 'purchasing@qualityparts.com', 'contact@logipro.com', 'support@matdirect.com', 'sales@indcomp.com', 'orders@scpartners.com', 'inquiry@premierdist.com', 'info@worldwidesup.com', 'service@expresslog.com'][i % 10],
      contact_person: ['James Miller', 'Susan Chen', 'Robert Taylor', 'Maria Garcia', 'Tom Anderson', 'Linda Brown', 'Kevin Wang', 'Patricia Davis', 'Mark Wilson', 'Jennifer Lee'][i % 10],
      subject: [
        'PO Confirmation #PO-2024-' + (1000 + i) + ' - Industrial Equipment',
        'Urgent: Delivery Delay Notice - Shipment #SH-' + (5000 + i),
        'Invoice #INV-2024-' + (8000 + i) + ' - Payment Due in 30 Days',
        'Contract Renewal Discussion - Annual Agreement 2024',
        'Payment Received Confirmation - Invoice #INV-2024-' + (8000 + i - 1),
        'Quote Request Response - Material Pricing for Q1 2024',
        'Quality Issue Report - Lot #QC-' + (3000 + i),
        'Shipping Schedule Update - Multiple Orders',
        'New Product Catalog - 2024 Spring Collection',
        'Account Review Meeting Request - Strategic Partnership'
      ][i % 10],
      communication_type: ['purchase_order', 'delivery_update', 'invoice', 'contract', 'payment', 'quote', 'quality_issue', 'general'][i % 8],
      status: ['pending_review', 'acknowledged', 'confirmed', 'completed', 'on_hold', 'requires_action'][i % 6],
      amount: (Math.random() * 150000 + 10000).toFixed(2),
      po_number: 'PO-2024-' + (1000 + i),
      items_ordered: [
        'Industrial Motors (50 units), Control Panels (25 units)',
        'Raw Materials - Steel Sheets (5000 kg)',
        'Electronic Components Bundle',
        'Office Supplies - Bulk Order',
        'Manufacturing Tools - Various',
        'Safety Equipment & PPE',
        'IT Hardware & Accessories',
        'Packaging Materials (Pallets, Boxes)',
        'Chemical Supplies - Industrial Grade',
        'Maintenance Parts & Consumables'
      ][i % 10],
      delivery_date: new Date(Date.now() + (i * 5 + 10) * 86400000).toLocaleDateString(),
      payment_terms: ['Net 30', 'Net 60', 'Net 90', '2/10 Net 30', 'Due on Receipt', 'COD'][i % 6],
      shipping_method: ['Standard Ground', 'Express Air', 'Freight - LTL', 'Freight - FTL', 'International Shipping'][i % 5],
      date: new Date(Date.now() - i * 86400000).toLocaleDateString(),
      thread_id: 'THREAD-' + (2000 + i),
      attachments: i % 2 === 0 ? Math.floor(Math.random() * 4) + 1 : 0,
      content: [
        'Dear Procurement Team,\n\nThank you for your purchase order PO-2024-' + (1000 + i) + '. We are pleased to confirm receipt and acceptance of your order:\n\nOrder Details:\n- Industrial Motors (50 units) @ $850/unit = $42,500\n- Control Panels (25 units) @ $1,200/unit = $30,000\n- Shipping & Handling: $2,500\n- Total: $75,000\n\nEstimated Ship Date: ' + new Date(Date.now() + 7 * 86400000).toLocaleDateString() + '\nEstimated Delivery: ' + new Date(Date.now() + 14 * 86400000).toLocaleDateString() + '\n\nPayment terms: Net 30 days\n\nPlease confirm delivery address and contact for receiving.\n\nBest regards,\nJames Miller\nSales Manager, Tech Supplies Inc',
        'URGENT NOTICE\n\nRegarding Shipment #SH-' + (5000 + i) + '\n\nWe regret to inform you of a delay in your scheduled shipment due to customs clearance issues at the port of entry.\n\nOriginal Delivery: ' + new Date(Date.now() + 3 * 86400000).toLocaleDateString() + '\nRevised Delivery: ' + new Date(Date.now() + 10 * 86400000).toLocaleDateString() + '\n\nWe apologize for this inconvenience and are working with customs officials to expedite clearance. We will provide daily updates on the status.\n\nFor urgent needs, we can arrange partial shipment via air freight at additional cost.\n\nSusan Chen\nLogistics Coordinator',
        'Invoice Statement\n\nInvoice #: INV-2024-' + (8000 + i) + '\nDate: ' + new Date(Date.now() - 2 * 86400000).toLocaleDateString() + '\nPO Reference: PO-2024-' + (900 + i) + '\n\nItems:\n- Raw Materials - Steel Sheets (5000 kg) @ $2.50/kg = $12,500\n- Processing & Cutting Services = $3,000\n- Quality Inspection Fee = $500\n- Delivery Charges = $1,000\n\nSubtotal: $17,000\nTax (8%): $1,360\nTotal Due: $18,360\n\nPayment Terms: Net 30 Days\nDue Date: ' + new Date(Date.now() + 28 * 86400000).toLocaleDateString() + '\n\nRemit payment to:\nQuality Parts Ltd\nAccount #: 1234567890\nRouting #: 987654321\n\nThank you for your business!\nRobert Taylor, Accounts Receivable',
        'Subject: Annual Contract Renewal - Strategic Partnership Discussion\n\nDear Partner,\n\nAs we approach the end of our current annual agreement, we would like to discuss renewal terms and potential expansion of our partnership for 2024.\n\nCurrent Contract Summary:\n- Volume: $2.5M annually\n- Discount: 15% on standard pricing\n- Payment Terms: Net 60\n- Delivery: 2-week standard lead time\n\nProposed 2024 Terms:\n- Projected Volume: $3.2M (28% increase)\n- Enhanced Discount: 18% (tier-based)\n- Extended Terms: Net 90 for orders >$50K\n- Priority Delivery: 10-day lead time\n- Dedicated Account Manager\n- Quarterly Business Reviews\n\nCan we schedule a meeting to discuss?\n\nMaria Garcia\nKey Account Manager',
        'Payment Confirmation\n\nDear Accounts Payable,\n\nWe acknowledge receipt of payment for Invoice #INV-2024-' + (8000 + i - 1) + ':\n\nPayment Details:\n- Amount: $45,250.00\n- Payment Method: Wire Transfer\n- Reference #: WIRE-' + (9000 + i) + '\n- Date Received: ' + new Date(Date.now() - 1 * 86400000).toLocaleDateString() + '\n\nYour account has been credited. Updated account balance: $0.00\n\nThank you for your prompt payment. We value your business!\n\nTom Anderson\nAccounts Receivable Manager\nMaterials Direct Corp',
        'Re: Quote Request - Material Pricing Q1 2024\n\nThank you for your inquiry regarding bulk material pricing for Q1 2024.\n\nQuote Summary:\n1. Industrial Components Bundle\n   - Quantity: 10,000 units\n   - Unit Price: $12.50\n   - Total: $125,000\n   - Lead Time: 3-4 weeks\n\n2. Electronic Assemblies\n   - Quantity: 5,000 units  \n   - Unit Price: $28.75\n   - Total: $143,750\n   - Lead Time: 4-6 weeks\n\nVolume Discounts:\n- Orders >$200K: Additional 5% discount\n- Quarterly commitments: Additional 3% discount\n\nQuote valid for 30 days. Terms: Net 60.\n\nLinda Brown\nSales Director',
        'Quality Issue Report - Immediate Action Required\n\nLot #: QC-' + (3000 + i) + '\nPO Reference: PO-2024-' + (950 + i) + '\n\nWe have identified quality issues with the recent shipment:\n\nIssues Identified:\n- 15% of units failed dimensional tolerance specs\n- Surface finish below acceptable standards\n- Packaging damage on 8 pallets\n\nImmediate Actions:\n1. Shipment placed on hold\n2. Quality engineer assigned for inspection\n3. Root cause analysis initiated\n4. Replacement parts ordered\n\nWe request:\n- Return authorization for defective units\n- Expedited replacement shipment\n- Quality improvement plan\n- Credit memo for defective items\n\nThis is impacting our production schedule.\n\nKevin Wang\nQuality Assurance Manager',
        'Shipping Schedule Update\n\nDear Logistics Team,\n\nPlease find updated shipping schedule for your pending orders:\n\n1. PO-2024-' + (1100 + i) + ' - Ships ' + new Date(Date.now() + 3 * 86400000).toLocaleDateString() + '\n2. PO-2024-' + (1101 + i) + ' - Ships ' + new Date(Date.now() + 5 * 86400000).toLocaleDateString() + '\n3. PO-2024-' + (1102 + i) + ' - Ships ' + new Date(Date.now() + 8 * 86400000).toLocaleDateString() + '\n\nTracking information will be provided once shipments are dispatched.\n\nAll shipments via: Express Logistics, Standard Ground Service\nEstimated transit: 5-7 business days\n\nPlease confirm receiving dock availability.\n\nPatricia Davis\nShipping Coordinator',
        '2024 Spring Product Catalog - New Arrivals\n\nDear Valued Customer,\n\nWe are excited to announce our 2024 Spring Product Collection!\n\nHighlights:\n- 500+ New SKUs\n- Enhanced product specifications\n- Competitive pricing (average 8% reduction)\n- Improved lead times\n- Expanded warranty coverage\n\nFeatured Categories:\n- Advanced Manufacturing Tools\n- Energy-Efficient Motors\n- Smart Control Systems  \n- IoT-Enabled Sensors\n- Sustainable Materials\n\nPlease review the attached catalog and schedule a presentation with your team.\n\nEarly order incentive: 10% discount on orders placed before ' + new Date(Date.now() + 30 * 86400000).toLocaleDateString() + '\n\nMark Wilson\nProduct Manager',
        'Strategic Account Review - Partnership Growth\n\nDear Executive Team,\n\nI would like to schedule our quarterly account review meeting to discuss:\n\nAgenda:\n1. 2023 Performance Review\n   - Order volume: $4.2M (18% YoY growth)\n   - On-time delivery: 97.5%\n   - Quality metrics: 99.2% acceptance\n\n2. 2024 Strategic Initiatives\n   - New product lines alignment\n   - Supply chain optimization\n   - Cost reduction opportunities\n   - Technology integration\n\n3. Partnership Enhancement\n   - Vendor managed inventory (VMI) pilot\n   - EDI integration implementation\n   - Collaborative forecasting\n   - Joint innovation projects\n\nProposed Date: Next two weeks\nDuration: 2-3 hours\nLocation: Your facility or virtual\n\nJennifer Lee\nVP, Strategic Accounts'
      ][i % 10],
      urgency: ['low', 'medium', 'high', 'critical'][i % 4],
      auto_extracted_entities: [
        ['PO-2024-' + (1000 + i), '$75,000', 'Industrial Motors', 'Control Panels'],
        ['Shipment #SH-' + (5000 + i), 'customs clearance', new Date(Date.now() + 10 * 86400000).toLocaleDateString()],
        ['Invoice #INV-2024-' + (8000 + i), '$18,360', 'Net 30 Days'],
        ['Annual Contract', '$2.5M', '15% discount', '2024'],
        ['Wire Transfer', '$45,250.00', 'WIRE-' + (9000 + i)],
        ['Quote', '$125,000', '10,000 units', '3-4 weeks'],
        ['Lot #QC-' + (3000 + i), '15% defective', 'Quality Issue'],
        ['PO-2024-' + (1100 + i), 'Express Logistics', '5-7 business days'],
        ['2024 Spring', '500+ New SKUs', '10% discount'],
        ['$4.2M', '97.5% on-time', '99.2% quality']
      ][i % 10],
      action_items: i % 3 === 0,
      requires_approval: i % 4 === 0,
      language: 'English',
    })),

    'invoice-notifications': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      invoice_number: 'INV-' + (10000 + i),
      vendor_name: ['Tech Supplies Inc', 'Global Manufacturing', 'Quality Parts Ltd', 'Logistics Pro', 'Materials Direct'][i % 5],
      invoice_amount: (Math.random() * 50000 + 1000).toFixed(2),
      due_date: new Date(Date.now() + (i * 7 - 14) * 86400000).toLocaleDateString(),
      status: ['pending', 'approved', 'paid', 'overdue'][i % 4],
      payment_terms: ['Net 30', 'Net 60', 'Net 90', 'Due on Receipt'][i % 4],
      received_date: new Date(Date.now() - i * 86400000).toLocaleDateString(),
      content: `Invoice notification for services/products delivered. Total amount: $${(Math.random() * 50000 + 1000).toFixed(2)}. Payment terms: ${['Net 30', 'Net 60', 'Net 90', 'Due on Receipt'][i % 4]}.`,
      match_status: ['matched', 'mismatch', 'pending_review'][i % 3],
    })),

    'order-confirmations': Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      order_number: 'ORD-' + (20000 + i),
      customer_name: ['Acme Corp', 'Widget Industries', 'Tech Solutions', 'Global Retail', 'Enterprise Systems'][i % 5],
      order_total: (Math.random() * 100000 + 5000).toFixed(2),
      order_date: new Date(Date.now() - i * 86400000).toLocaleDateString(),
      delivery_date: new Date(Date.now() + (i * 3 + 7) * 86400000).toLocaleDateString(),
      status: ['confirmed', 'processing', 'shipped', 'delivered'][i % 4],
      items_count: Math.floor(Math.random() * 20) + 1,
      content: `Order confirmation for ${Math.floor(Math.random() * 20) + 1} items. Total value: $${(Math.random() * 100000 + 5000).toFixed(2)}. Estimated delivery: ${new Date(Date.now() + (i * 3 + 7) * 86400000).toLocaleDateString()}.`,
      payment_status: ['pending', 'completed', 'processing'][i % 3],
    })),
  };

  return sampleData[typeName] || [];
};

const EmailIntelligence = ({ onNavigateToConfig }) => {
  const theme = useTheme();
  const [selectedType, setSelectedType] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Custom types management
  const { customTypes, addType, updateType, deleteType } = useCustomTypes('email-intel-custom-types');
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [editingType, setEditingType] = useState(null);

  // Configuration state
  const [config, setConfig] = useState({ types: [], fields: {} });
  const [communicationData, setCommunicationData] = useState({});
  const [stats, setStats] = useState({});

  // Content dialog state
  const [contentDialog, setContentDialog] = useState({
    open: false,
    title: '',
    content: '',
    data: null,
  });

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  // Sample configuration data
  const sampleConfig = {
    types: [
      {
        id: 1,
        name: 'customer-inquiries',
        display_name: 'Customer Inquiries',
        description: 'Track and manage customer questions and support requests',
        icon: 'Person',
        color: '#2196F3',
        tab_order: 1,
        is_active: true
      },
      {
        id: 2,
        name: 'vendor-communications',
        display_name: 'Vendor Communications',
        description: 'Manage communications with suppliers and vendors',
        icon: 'Business',
        color: '#FF9800',
        tab_order: 2,
        is_active: true
      },
      {
        id: 3,
        name: 'invoice-notifications',
        display_name: 'Invoice Notifications',
        description: 'Track invoices and payment notifications',
        icon: 'Receipt',
        color: '#4CAF50',
        tab_order: 3,
        is_active: true
      },
      {
        id: 4,
        name: 'order-confirmations',
        display_name: 'Order Confirmations',
        description: 'Monitor order confirmations and delivery updates',
        icon: 'ShoppingCart',
        color: '#9C27B0',
        tab_order: 4,
        is_active: true
      }
    ],
    fields: {
      1: [
        { id: 1, communication_type_id: 1, field_name: 'customer_name', display_name: 'Customer Name', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 1, column_width: 180 },
        { id: 2, communication_type_id: 1, field_name: 'customer_email', display_name: 'Email', field_type: 'email', is_sortable: true, is_filterable: true, column_order: 2, column_width: 200 },
        { id: 3, communication_type_id: 1, field_name: 'subject', display_name: 'Subject', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 3, column_width: 250 },
        { id: 4, communication_type_id: 1, field_name: 'inquiry_type', display_name: 'Type', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 4, column_width: 120 },
        { id: 5, communication_type_id: 1, field_name: 'status', display_name: 'Status', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 5, column_width: 130 },
        { id: 6, communication_type_id: 1, field_name: 'priority', display_name: 'Priority', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 6, column_width: 120 },
        { id: 7, communication_type_id: 1, field_name: 'sentiment', display_name: 'Sentiment', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 7, column_width: 120 },
        { id: 8, communication_type_id: 1, field_name: 'received_date', display_name: 'Received', field_type: 'date', is_sortable: true, is_filterable: true, column_order: 8, column_width: 130 }
      ],
      2: [
        { id: 9, communication_type_id: 2, field_name: 'vendor_name', display_name: 'Vendor Name', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 1, column_width: 200 },
        { id: 10, communication_type_id: 2, field_name: 'vendor_email', display_name: 'Email', field_type: 'email', is_sortable: true, is_filterable: true, column_order: 2, column_width: 200 },
        { id: 11, communication_type_id: 2, field_name: 'subject', display_name: 'Subject', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 3, column_width: 250 },
        { id: 12, communication_type_id: 2, field_name: 'communication_type', display_name: 'Type', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 4, column_width: 150 },
        { id: 13, communication_type_id: 2, field_name: 'status', display_name: 'Status', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 5, column_width: 130 },
        { id: 14, communication_type_id: 2, field_name: 'amount', display_name: 'Amount', field_type: 'currency', is_sortable: true, is_filterable: true, column_order: 6, column_width: 130 },
        { id: 15, communication_type_id: 2, field_name: 'urgency', display_name: 'Urgency', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 7, column_width: 120 },
        { id: 16, communication_type_id: 2, field_name: 'date', display_name: 'Date', field_type: 'date', is_sortable: true, is_filterable: true, column_order: 8, column_width: 130 }
      ],
      3: [
        { id: 17, communication_type_id: 3, field_name: 'invoice_number', display_name: 'Invoice #', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 1, column_width: 150 },
        { id: 18, communication_type_id: 3, field_name: 'vendor_name', display_name: 'Vendor', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 2, column_width: 200 },
        { id: 19, communication_type_id: 3, field_name: 'invoice_amount', display_name: 'Amount', field_type: 'currency', is_sortable: true, is_filterable: true, column_order: 3, column_width: 150 },
        { id: 20, communication_type_id: 3, field_name: 'due_date', display_name: 'Due Date', field_type: 'date', is_sortable: true, is_filterable: true, column_order: 4, column_width: 130 },
        { id: 21, communication_type_id: 3, field_name: 'status', display_name: 'Status', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 5, column_width: 130 },
        { id: 22, communication_type_id: 3, field_name: 'payment_terms', display_name: 'Payment Terms', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 6, column_width: 140 },
        { id: 23, communication_type_id: 3, field_name: 'match_status', display_name: 'Match Status', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 7, column_width: 140 },
        { id: 24, communication_type_id: 3, field_name: 'received_date', display_name: 'Received', field_type: 'date', is_sortable: true, is_filterable: true, column_order: 8, column_width: 130 }
      ],
      4: [
        { id: 25, communication_type_id: 4, field_name: 'order_number', display_name: 'Order #', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 1, column_width: 150 },
        { id: 26, communication_type_id: 4, field_name: 'customer_name', display_name: 'Customer', field_type: 'text', is_sortable: true, is_filterable: true, column_order: 2, column_width: 200 },
        { id: 27, communication_type_id: 4, field_name: 'order_total', display_name: 'Total', field_type: 'currency', is_sortable: true, is_filterable: true, column_order: 3, column_width: 150 },
        { id: 28, communication_type_id: 4, field_name: 'items_count', display_name: 'Items', field_type: 'number', is_sortable: true, is_filterable: true, column_order: 4, column_width: 100 },
        { id: 29, communication_type_id: 4, field_name: 'status', display_name: 'Status', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 5, column_width: 130 },
        { id: 30, communication_type_id: 4, field_name: 'payment_status', display_name: 'Payment', field_type: 'dropdown', is_sortable: true, is_filterable: true, column_order: 6, column_width: 130 },
        { id: 31, communication_type_id: 4, field_name: 'order_date', display_name: 'Order Date', field_type: 'date', is_sortable: true, is_filterable: true, column_order: 7, column_width: 130 },
        { id: 32, communication_type_id: 4, field_name: 'delivery_date', display_name: 'Delivery Date', field_type: 'date', is_sortable: true, is_filterable: true, column_order: 8, column_width: 140 }
      ]
    }
  };

  // Fetch configuration
  useEffect(() => {
    fetchConfiguration();
  }, []);

  // Refetch configuration when custom types change
  useEffect(() => {
    fetchConfiguration();
  }, [customTypes]);

  // Fetch data when tab changes
  useEffect(() => {
    if (config.types.length > 0) {
      const currentType = config.types[activeTab];
      if (currentType && !communicationData[currentType.name]) {
        fetchDataForType(currentType.name);
      }
    }
  }, [activeTab, config.types]);

  const fetchConfiguration = async () => {
    try {
      const response = await fetch('/api/v1/comms/config/complete');
      if (response.ok) {
        const data = await response.json();

        // Merge with custom types
        const mergedConfig = {
          ...data,
          types: [...data.types, ...customTypes],
        };
        setConfig(mergedConfig);

        // Calculate stats
        const statsObj = {};
        mergedConfig.types.forEach(type => {
          statsObj[type.name] = 0;
        });
        setStats(statsObj);

        // Fetch data for first type
        if (mergedConfig.types.length > 0) {
          fetchDataForType(mergedConfig.types[0].name);
        }
      } else {
        // Use sample config if API fails
        console.log('Using sample configuration data');

        // Merge with custom types
        const mergedConfig = {
          ...sampleConfig,
          types: [...sampleConfig.types, ...customTypes],
        };
        setConfig(mergedConfig);

        // Calculate stats
        const statsObj = {};
        mergedConfig.types.forEach(type => {
          statsObj[type.name] = 0;
        });
        setStats(statsObj);

        // Fetch data for first type
        if (mergedConfig.types.length > 0) {
          fetchDataForType(mergedConfig.types[0].name);
        }
      }
    } catch (err) {
      console.error('Error fetching configuration:', err);
      // Use sample config on error
      console.log('Using sample configuration data due to error');

      // Merge with custom types
      const mergedConfig = {
        ...sampleConfig,
        types: [...sampleConfig.types, ...customTypes],
      };
      setConfig(mergedConfig);

      // Calculate stats
      const statsObj = {};
      mergedConfig.types.forEach(type => {
        statsObj[type.name] = 0;
      });
      setStats(statsObj);

      // Fetch data for first type
      if (mergedConfig.types.length > 0) {
        fetchDataForType(sampleConfig.types[0].name);
      }
    }
  };

  const fetchDataForType = async (typeName) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/comms/config/data/${typeName}`);
      if (response.ok) {
        const data = await response.json();
        setCommunicationData(prev => ({
          ...prev,
          [typeName]: data
        }));

        // Update stats
        setStats(prev => ({
          ...prev,
          [typeName]: data.length
        }));
      } else {
        // Use sample data if API fails
        const sampleData = generateSampleData(typeName, 15);
        setCommunicationData(prev => ({
          ...prev,
          [typeName]: sampleData
        }));
        setStats(prev => ({
          ...prev,
          [typeName]: sampleData.length
        }));
      }
    } catch (err) {
      console.error(`Error fetching data for ${typeName}:`, err);
      // Use sample data on error
      const sampleData = generateSampleData(typeName, 15);
      setCommunicationData(prev => ({
        ...prev,
        [typeName]: sampleData
      }));
      setStats(prev => ({
        ...prev,
        [typeName]: sampleData.length
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleViewContent = (row) => {
    setContentDialog({
      open: true,
      title: row.subject || row.invoice_number || row.order_number || 'Communication Details',
      content: row.content || 'No content available',
      data: row,
    });
  };

  const handleCloseContent = () => {
    setContentDialog({ open: false, title: '', content: '', data: null });
  };

  const refreshData = () => {
    if (config.types.length > 0) {
      const currentType = config.types[activeTab];
      if (currentType) {
        fetchDataForType(currentType.name);
      }
    }
  };

  const refreshAll = () => {
    fetchConfiguration();
    config.types.forEach(type => {
      fetchDataForType(type.name);
    });
  };

  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase() || '';
    if (['resolved', 'confirmed', 'closed', 'matched', 'completed'].includes(statusLower)) {
      return theme.palette.success.main;
    }
    if (['pending', 'open', 'in_progress'].includes(statusLower)) {
      return theme.palette.warning.main;
    }
    if (['escalated', 'urgent', 'critical', 'mismatch', 'failed'].includes(statusLower)) {
      return theme.palette.error.main;
    }
    return theme.palette.grey[500];
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return <SentimentPositiveIcon sx={{ color: theme.palette.success.main }} />;
      case 'negative':
        return <SentimentNegativeIcon sx={{ color: theme.palette.error.main }} />;
      default:
        return <SentimentNeutralIcon sx={{ color: theme.palette.grey[500] }} />;
    }
  };

  // Build dynamic columns based on field configuration
  const buildColumnsForType = (typeId) => {
    const fields = config.fields[typeId] || [];

    const columns = fields.map(field => {
      const baseColumn = {
        field: field.field_name,
        headerName: field.display_name,
        width: field.column_width || 150,
        sortable: field.is_sortable,
        filterable: field.is_filterable,
      };

      // Custom renderers based on field type
      switch (field.field_type) {
        case 'currency':
          return {
            ...baseColumn,
            renderCell: (params) => (
              <Typography variant="body2" fontWeight={600}>
                ${typeof params.value === 'number' ? params.value.toFixed(2) : params.value}
              </Typography>
            ),
          };

        case 'dropdown':
          if (field.field_name.includes('status') || field.field_name.includes('match')) {
            return {
              ...baseColumn,
              renderCell: (params) => (
                <Chip
                  label={params.value}
                  size="small"
                  sx={{
                    bgcolor: alpha(getStatusColor(params.value), 0.1),
                    color: getStatusColor(params.value)
                  }}
                />
              ),
            };
          }
          if (field.field_name === 'priority' || field.field_name === 'severity') {
            return {
              ...baseColumn,
              renderCell: (params) => (
                <Chip
                  label={params.value}
                  size="small"
                  color={
                    params.value === 'critical' ? 'error' :
                    params.value === 'high' ? 'warning' : 'default'
                  }
                />
              ),
            };
          }
          return {
            ...baseColumn,
            renderCell: (params) => (
              <Chip label={params.value} size="small" />
            ),
          };

        case 'boolean':
          return {
            ...baseColumn,
            renderCell: (params) => (
              params.value ? <CheckIcon color="success" /> : <ErrorIcon color="error" />
            ),
          };

        case 'email':
          return {
            ...baseColumn,
            renderCell: (params) => (
              <a href={`mailto:${params.value}`} style={{ textDecoration: 'none', color: theme.palette.primary.main }}>
                {params.value}
              </a>
            ),
          };

        case 'url':
          return {
            ...baseColumn,
            renderCell: (params) => (
              <a href={params.value} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: theme.palette.primary.main }}>
                Link
              </a>
            ),
          };

        default:
          // Special handling for specific field names
          if (field.field_name.includes('name') && field.column_order <= 2) {
            return {
              ...baseColumn,
              renderCell: (params) => (
                <Stack direction="row" spacing={1} alignItems="center">
                  <Avatar sx={{ width: 32, height: 32, bgcolor: theme.palette.primary.main }}>
                    {params.value?.charAt(0)?.toUpperCase()}
                  </Avatar>
                  <Typography variant="body2">{params.value}</Typography>
                </Stack>
              ),
            };
          }
          if (field.field_name === 'sentiment') {
            return {
              ...baseColumn,
              renderCell: (params) => getSentimentIcon(params.value),
            };
          }
          return baseColumn;
      }
    });

    // Add Actions column
    columns.push({
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <Tooltip title="View Full Content">
            <IconButton
              size="small"
              color="primary"
              onClick={() => handleViewContent(params.row)}
            >
              <VisibilityIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          {params.row.attachments && (
            <Tooltip title={`${params.row.attachments} Attachment(s)`}>
              <IconButton size="small">
                <Badge badgeContent={params.row.attachments} color="secondary">
                  <AttachFileIcon fontSize="small" />
                </Badge>
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      ),
    });

    return columns;
  };

  const getTotalEmails = () => {
    return Object.values(stats).reduce((acc, val) => acc + val, 0);
  };

  const getIconComponent = (iconName) => {
    const IconComponent = iconMap[iconName] || EmailIcon;
    return IconComponent;
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

  // Tile Landing View
  if (!selectedType) {
    // Filter tiles based on search query
    const filteredTypes = config.types.filter((type) =>
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
                  bgcolor: alpha('#2196F3', 0.1),
                }}
              >
                <EmailIcon sx={{ fontSize: 36, color: '#2196F3' }} />
              </Avatar>
              <Box>
                <Typography variant="h4" fontWeight={700}>
                  EMAIL INTEL
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Configurable Communication Intelligence Platform
                </Typography>
              </Box>
            </Box>
            <Stack direction="row" spacing={2}>
              <Button startIcon={<SettingsIcon />} variant="outlined" onClick={onNavigateToConfig}>
                Configure
              </Button>
              <Button startIcon={<RefreshIcon />} variant="outlined" onClick={refreshAll} disabled={loading}>
                Refresh
              </Button>
            </Stack>
          </Stack>

          {/* Search Bar */}
          <TextField
            fullWidth
            placeholder="Search communication types..."
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

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Grid container spacing={1.5}>
          {filteredTypes.map((type, index) => {
            const IconComponent = getIconComponent(type.icon);
            const colors = ['#2196F3', '#FF9800', '#4CAF50', '#9C27B0'];
            const color = type.color || colors[index % colors.length];

            return (
              <Grid item xs={12} sm={6} md={4} key={type.id}>
                <Card
                  sx={{
                    height: 200,
                    cursor: 'pointer',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                    border: '1px solid',
                    borderColor: alpha(color, 0.15),
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
                      background: `linear-gradient(135deg, ${color} 0%, ${alpha(color, 0.7)} 100%)`,
                      opacity: 0.8,
                    },
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: `0 12px 24px ${alpha(color, 0.15)}`,
                      borderColor: color,
                      '& .module-icon': {
                        transform: 'scale(1.15)',
                        bgcolor: color,
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
                          bgcolor: alpha(color, 0.1),
                          color: color,
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
                            sx={{ width: 24, height: 24, color: color }}
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
                    <Typography variant="body1" sx={{ fontWeight: 700, color: color, mb: 0.5, fontSize: '0.9rem', lineHeight: 1.3 }}>
                      {type.display_name}
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary', mb: 'auto', lineHeight: 1.4, fontSize: '0.7rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {type.description}
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, pt: 1, borderTop: '1px solid', borderColor: alpha(color, 0.1) }}>
                      <Chip label={`${stats[type.name] || 0} Communications`} size="small" sx={{ height: 22, fontSize: '0.65rem', bgcolor: alpha(color, 0.08), color: color, fontWeight: 600 }} />
                      <OpenInNewIcon className="module-arrow" sx={{ color: color, fontSize: 18, opacity: 0.5, transition: 'all 0.3s ease' }} />
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
                    Create your own communication type
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
              No communication types found
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
  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Box>
            <Button startIcon={<OpenInNewIcon sx={{ transform: 'rotate(180deg)' }} />} onClick={() => setSelectedType(null)} variant="text" sx={{ mb: 1 }}>
              Back to Communication Types
            </Button>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              {selectedType.display_name}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {selectedType.description}
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button startIcon={<RefreshIcon />} variant="outlined" onClick={refreshAll} disabled={loading}>
              Refresh
            </Button>
          </Stack>
        </Stack>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Data Grid */}
      <Paper>
        <Box sx={{ height: 650, width: '100%' }}>
          <DataGrid
            rows={communicationData[selectedType.name] || []}
            columns={buildColumnsForType(selectedType.id)}
            density="compact"
            initialState={{
              pagination: {
                paginationModel: { pageSize: 25, page: 0 },
              },
            }}
            pageSizeOptions={[10, 25, 50, 100]}
            loading={loading}
            checkboxSelection
            disableRowSelectionOnClick
            slots={{
              toolbar: CustomToolbar,
            }}
            slotProps={{
              toolbar: {
                showQuickFilter: true,
                quickFilterProps: { debounceMs: 500 },
              },
            }}
            sx={{
              border: 'none',
              '& .MuiDataGrid-cell:focus': {
                outline: 'none',
              },
              '& .MuiDataGrid-row:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.05),
              },
              '& .MuiDataGrid-columnHeaders': {
                backgroundColor: theme.palette.mode === 'light' ? 'grey.100' : 'grey.900',
                fontSize: '0.875rem',
                fontWeight: 600,
              },
              '& .MuiDataGrid-toolbarContainer': {
                padding: 2,
                backgroundColor: theme.palette.mode === 'light' ? 'grey.50' : 'grey.900',
                borderBottom: '1px solid',
                borderColor: 'divider',
              },
              '& .MuiDataGrid-footerContainer': {
                borderTop: '1px solid',
                borderColor: 'divider',
              },
            }}
          />
        </Box>
      </Paper>

      {/* Empty State */}
      {config.types.length === 0 && !loading && (
        <Paper sx={{ p: 8, textAlign: 'center' }}>
          <SettingsIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            No Communication Types Configured
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Get started by configuring your first communication type
          </Typography>
          <Button
            variant="contained"
            startIcon={<SettingsIcon />}
            onClick={onNavigateToConfig}
          >
            Configure EMAIL INTEL
          </Button>
        </Paper>
      )}

      {/* Content Viewer Dialog */}
      <Dialog
        open={contentDialog.open}
        onClose={handleCloseContent}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" alignItems="center" spacing={2}>
            <EmailIcon color="primary" />
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6">{contentDialog.title}</Typography>
              {contentDialog.data && (
                <Typography variant="caption" color="text.secondary">
                  <ScheduleIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
                  {contentDialog.data.received_date || contentDialog.data.date || contentDialog.data.order_date}
                </Typography>
              )}
            </Box>
            <IconButton onClick={handleCloseContent} size="small">
              <OpenInNewIcon />
            </IconButton>
          </Stack>
        </DialogTitle>
        <Divider />
        <DialogContent>
          {contentDialog.data && (
            <>
              {/* Metadata Section */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                {contentDialog.data.customer_name && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Customer</Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {contentDialog.data.customer_name}
                    </Typography>
                  </Grid>
                )}
                {contentDialog.data.vendor_name && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Vendor</Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {contentDialog.data.vendor_name}
                    </Typography>
                  </Grid>
                )}
                {contentDialog.data.customer_email && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Email</Typography>
                    <Typography variant="body2">{contentDialog.data.customer_email}</Typography>
                  </Grid>
                )}
                {contentDialog.data.vendor_email && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Email</Typography>
                    <Typography variant="body2">{contentDialog.data.vendor_email}</Typography>
                  </Grid>
                )}
                {contentDialog.data.status && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Status</Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Chip
                        label={contentDialog.data.status}
                        size="small"
                        sx={{
                          bgcolor: alpha(getStatusColor(contentDialog.data.status), 0.1),
                          color: getStatusColor(contentDialog.data.status)
                        }}
                      />
                    </Box>
                  </Grid>
                )}
                {contentDialog.data.priority && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Priority</Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Chip
                        label={contentDialog.data.priority}
                        size="small"
                        color={
                          contentDialog.data.priority === 'critical' ? 'error' :
                          contentDialog.data.priority === 'high' ? 'warning' : 'default'
                        }
                      />
                    </Box>
                  </Grid>
                )}
                {contentDialog.data.invoice_amount && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Amount</Typography>
                    <Typography variant="h6" color="primary">
                      ${contentDialog.data.invoice_amount}
                    </Typography>
                  </Grid>
                )}
                {contentDialog.data.order_total && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Order Total</Typography>
                    <Typography variant="h6" color="primary">
                      ${contentDialog.data.order_total}
                    </Typography>
                  </Grid>
                )}
                {contentDialog.data.sentiment && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Sentiment</Typography>
                    <Box sx={{ mt: 0.5 }}>
                      {getSentimentIcon(contentDialog.data.sentiment)}
                      <Typography variant="body2" component="span" sx={{ ml: 1, textTransform: 'capitalize' }}>
                        {contentDialog.data.sentiment}
                      </Typography>
                    </Box>
                  </Grid>
                )}
              </Grid>

              <Divider sx={{ my: 2 }} />

              {/* Content Section */}
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Communication Content
                </Typography>
                <Paper sx={{ p: 2, bgcolor: 'grey.50', border: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {contentDialog.content}
                  </Typography>
                </Paper>
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseContent}>Close</Button>
          <Button variant="contained" startIcon={<OpenInNewIcon />}>
            Open Full View
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
        moduleType="email"
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

export default EmailIntelligence;
