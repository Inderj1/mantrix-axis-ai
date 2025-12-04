/**
 * Navigation Component Overrides
 * Premium styling for tabs, drawer, appbar, breadcrumbs, stepper
 */

import { neutral, primary } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { transitionTokens } from '../tokens/transitions';
import { radii } from '../tokens';

export const navigationOverrides = {
  MuiAppBar: {
    styleOverrides: {
      root: {
        backgroundImage: 'none',
      },
      colorDefault: {
        backgroundColor: '#FFFFFF',
        color: neutral[900],
        boxShadow: shadowTokens.standard.sm,
      },
      colorPrimary: {
        backgroundColor: '#354A5F',
        boxShadow: '0 1px 0 0 rgba(0,0,0,0.15)',
      },
    },
  },

  MuiToolbar: {
    styleOverrides: {
      root: {
        minHeight: '64px !important',
      },
      dense: {
        minHeight: '52px !important',
      },
    },
  },

  MuiDrawer: {
    styleOverrides: {
      paper: {
        backgroundColor: '#FFFFFF',
        borderRight: `1px solid ${neutral[300]}`,
        backgroundImage: 'none',
      },
    },
  },

  MuiTabs: {
    styleOverrides: {
      root: {
        minHeight: 48,
      },
      indicator: {
        height: 3,
        backgroundColor: primary[500],
        borderRadius: '3px 3px 0 0',
      },
      flexContainer: {
        gap: 8,
      },
    },
  },

  MuiTab: {
    styleOverrides: {
      root: {
        textTransform: 'none',
        fontWeight: 400,
        fontSize: '0.9375rem',
        minHeight: 48,
        padding: '12px 16px',
        color: neutral[600],
        transition: transitionTokens.preset.color,
        '&:hover': {
          color: neutral[800],
          backgroundColor: neutral[50],
        },
        '&.Mui-selected': {
          color: primary[600],
          fontWeight: 600,
        },
        '&.Mui-disabled': {
          color: neutral[400],
        },
      },
    },
  },

  MuiBreadcrumbs: {
    styleOverrides: {
      root: {
        fontSize: '0.875rem',
      },
      separator: {
        color: neutral[400],
        marginLeft: 8,
        marginRight: 8,
      },
      li: {
        '& a': {
          color: neutral[600],
          textDecoration: 'none',
          transition: transitionTokens.preset.color,
          '&:hover': {
            color: primary[500],
          },
        },
        '& .MuiTypography-root': {
          color: neutral[800],
          fontWeight: 500,
        },
      },
    },
  },

  MuiStepper: {
    styleOverrides: {
      root: {
        padding: '24px 0',
      },
    },
  },

  MuiStep: {
    styleOverrides: {
      root: {
        padding: 0,
      },
    },
  },

  MuiStepLabel: {
    styleOverrides: {
      root: {
        '&.Mui-disabled': {
          opacity: 0.6,
        },
      },
      label: {
        fontSize: '0.875rem',
        fontWeight: 500,
        color: neutral[600],
        '&.Mui-active': {
          color: primary[600],
          fontWeight: 600,
        },
        '&.Mui-completed': {
          color: neutral[800],
          fontWeight: 500,
        },
      },
      iconContainer: {
        paddingRight: 12,
      },
    },
  },

  MuiStepIcon: {
    styleOverrides: {
      root: {
        color: neutral[300],
        fontSize: 28,
        '&.Mui-active': {
          color: primary[500],
        },
        '&.Mui-completed': {
          color: primary[500],
        },
      },
      text: {
        fontSize: '0.75rem',
        fontWeight: 600,
      },
    },
  },

  MuiStepConnector: {
    styleOverrides: {
      root: {
        '&.Mui-active': {
          '& .MuiStepConnector-line': {
            borderColor: primary[500],
          },
        },
        '&.Mui-completed': {
          '& .MuiStepConnector-line': {
            borderColor: primary[500],
          },
        },
      },
      line: {
        borderColor: neutral[300],
        borderWidth: 2,
      },
    },
  },

  MuiLink: {
    styleOverrides: {
      root: {
        color: primary[500],
        textDecorationColor: 'transparent',
        transition: transitionTokens.preset.color,
        '&:hover': {
          color: primary[700],
          textDecorationColor: primary[700],
        },
      },
    },
  },

  MuiListItemButton: {
    styleOverrides: {
      root: {
        borderRadius: radii.DEFAULT,
        margin: '2px 8px',
        padding: '10px 12px',
        transition: transitionTokens.preset.color,
        '&:hover': {
          backgroundColor: neutral[100],
        },
        '&.Mui-selected': {
          backgroundColor: primary[50],
          '&:hover': {
            backgroundColor: primary[100],
          },
          '& .MuiListItemIcon-root': {
            color: primary[600],
          },
          '& .MuiListItemText-primary': {
            color: primary[700],
            fontWeight: 600,
          },
        },
      },
    },
  },

  MuiListItemIcon: {
    styleOverrides: {
      root: {
        color: neutral[600],
        minWidth: 40,
      },
    },
  },

  MuiListItemText: {
    styleOverrides: {
      primary: {
        fontSize: '0.9375rem',
        fontWeight: 500,
        color: neutral[800],
      },
      secondary: {
        fontSize: '0.8125rem',
        color: neutral[600],
        marginTop: 2,
      },
    },
  },

  MuiDivider: {
    styleOverrides: {
      root: {
        borderColor: neutral[200],
      },
    },
  },
};

export default navigationOverrides;
