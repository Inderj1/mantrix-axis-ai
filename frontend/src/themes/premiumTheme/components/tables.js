/**
 * Table & DataGrid Component Overrides
 * Premium table styling with zebra striping and hover states
 */

import { neutral, primary } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { transitionTokens } from '../tokens/transitions';
import { radii } from '../tokens';
import { surfaceGradients } from '../effects/gradients';

export const tableOverrides = {
  // Standard MUI Table
  MuiTable: {
    styleOverrides: {
      root: {
        borderCollapse: 'separate',
        borderSpacing: 0,
      },
    },
  },

  MuiTableContainer: {
    styleOverrides: {
      root: {
        borderRadius: radii.lg,
        border: `1px solid ${neutral[300]}`,
        overflow: 'hidden',
      },
    },
  },

  MuiTableHead: {
    styleOverrides: {
      root: {
        background: surfaceGradients.card,
      },
    },
  },

  MuiTableCell: {
    styleOverrides: {
      root: {
        fontSize: '0.875rem',
        borderBottom: `1px solid ${neutral[200]}`,
        padding: '12px 16px',
      },
      head: {
        fontWeight: 600,
        color: neutral[900],
        backgroundColor: neutral[50],
        borderBottom: `2px solid ${neutral[300]}`,
        whiteSpace: 'nowrap',
      },
      body: {
        color: neutral[800],
      },
    },
  },

  MuiTableRow: {
    styleOverrides: {
      root: {
        transition: transitionTokens.preset.color,
        '&:hover': {
          backgroundColor: `rgba(10, 110, 209, 0.04)`,
        },
        '&.Mui-selected': {
          backgroundColor: `rgba(10, 110, 209, 0.08)`,
          '&:hover': {
            backgroundColor: `rgba(10, 110, 209, 0.12)`,
          },
        },
        // Zebra striping
        '&:nth-of-type(odd)': {
          backgroundColor: neutral[50],
        },
        '&:nth-of-type(odd):hover': {
          backgroundColor: `rgba(10, 110, 209, 0.04)`,
        },
      },
      head: {
        '&:hover': {
          backgroundColor: 'transparent',
        },
      },
    },
  },

  MuiTablePagination: {
    styleOverrides: {
      root: {
        borderTop: `1px solid ${neutral[300]}`,
        backgroundColor: neutral[50],
      },
      toolbar: {
        minHeight: 52,
      },
      selectLabel: {
        fontSize: '0.875rem',
        color: neutral[600],
      },
      displayedRows: {
        fontSize: '0.875rem',
        color: neutral[600],
      },
      select: {
        fontSize: '0.875rem',
      },
    },
  },

  MuiTableSortLabel: {
    styleOverrides: {
      root: {
        color: neutral[900],
        fontWeight: 600,
        '&:hover': {
          color: primary[600],
        },
        '&.Mui-active': {
          color: primary[600],
          '& .MuiTableSortLabel-icon': {
            color: primary[600],
          },
        },
      },
      icon: {
        opacity: 0.5,
        transition: transitionTokens.preset.fade,
      },
    },
  },

  // MUI X DataGrid overrides
  MuiDataGrid: {
    styleOverrides: {
      root: {
        border: `1px solid ${neutral[300]}`,
        borderRadius: radii.lg,
        overflow: 'hidden',
        '& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within': {
          outline: 'none',
        },
        '& .MuiDataGrid-row:focus, & .MuiDataGrid-row:focus-within': {
          outline: 'none',
        },
        '& .MuiDataGrid-columnHeader:focus, & .MuiDataGrid-columnHeader:focus-within': {
          outline: 'none',
        },
      },
      columnHeaders: {
        background: surfaceGradients.card,
        borderBottom: `2px solid ${neutral[300]}`,
        minHeight: '52px !important',
        maxHeight: '52px !important',
      },
      columnHeader: {
        fontWeight: 600,
        fontSize: '0.85rem',
        color: neutral[900],
        padding: '12px 16px',
        '&:hover': {
          backgroundColor: `rgba(10, 110, 209, 0.04)`,
        },
        '&:focus': {
          outline: 'none',
        },
      },
      columnHeaderTitle: {
        fontWeight: 600,
      },
      columnSeparator: {
        color: neutral[300],
      },
      sortIcon: {
        color: primary[500],
      },
      menuIcon: {
        '& .MuiSvgIcon-root': {
          color: neutral[600],
        },
      },
      row: {
        transition: 'background-color 0.15s ease-in-out',
        '&:hover': {
          backgroundColor: `rgba(10, 110, 209, 0.04)`,
        },
        '&.Mui-selected': {
          backgroundColor: `rgba(10, 110, 209, 0.08)`,
          '&:hover': {
            backgroundColor: `rgba(10, 110, 209, 0.12)`,
          },
        },
        // Zebra striping (odd rows)
        '&:nth-of-type(odd)': {
          backgroundColor: neutral[50],
        },
        '&:nth-of-type(odd):hover': {
          backgroundColor: `rgba(10, 110, 209, 0.04)`,
        },
      },
      cell: {
        fontSize: '0.875rem',
        color: neutral[800],
        borderBottom: `1px solid ${neutral[200]}`,
        padding: '12px 16px',
        '&:focus': {
          outline: 'none',
        },
      },
      footerContainer: {
        borderTop: `2px solid ${neutral[300]}`,
        backgroundColor: neutral[50],
        minHeight: 52,
      },
      toolbarContainer: {
        padding: '8px 16px',
        borderBottom: `1px solid ${neutral[300]}`,
        backgroundColor: '#FFFFFF',
      },
      panel: {
        boxShadow: shadowTokens.standard.xl,
        borderRadius: radii.lg,
        border: `1px solid ${neutral[300]}`,
      },
      panelHeader: {
        padding: '16px',
        borderBottom: `1px solid ${neutral[300]}`,
      },
      panelContent: {
        padding: '16px',
      },
      panelFooter: {
        padding: '8px 16px',
        borderTop: `1px solid ${neutral[300]}`,
      },
      filterForm: {
        padding: '16px',
      },
      columnsPanel: {
        padding: '16px',
      },
      overlay: {
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
      },
      virtualScroller: {
        backgroundColor: '#FFFFFF',
      },
    },
  },
};

export default tableOverrides;
