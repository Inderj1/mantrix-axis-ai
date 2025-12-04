/**
 * Feedback Component Overrides
 * Premium styling for alerts, chips, snackbars, tooltips, progress
 */

import { neutral, primary, semantic } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { transitionTokens } from '../tokens/transitions';
import { radii } from '../tokens';

export const feedbackOverrides = {
  MuiAlert: {
    styleOverrides: {
      root: {
        borderRadius: radii.DEFAULT,
        padding: '12px 16px',
        alignItems: 'flex-start',
      },
      icon: {
        marginRight: 12,
        padding: '2px 0',
      },
      message: {
        padding: 0,
        fontSize: '0.875rem',
        lineHeight: 1.5,
      },
      standardSuccess: {
        backgroundColor: semantic.success.light,
        color: semantic.success.dark,
        border: `1px solid rgba(16, 126, 62, 0.2)`,
        '& .MuiAlert-icon': {
          color: semantic.success.main,
        },
      },
      standardError: {
        backgroundColor: semantic.error.light,
        color: semantic.error.dark,
        border: `1px solid rgba(187, 0, 0, 0.2)`,
        '& .MuiAlert-icon': {
          color: semantic.error.main,
        },
      },
      standardWarning: {
        backgroundColor: semantic.warning.light,
        color: semantic.warning.dark,
        border: `1px solid rgba(223, 110, 12, 0.2)`,
        '& .MuiAlert-icon': {
          color: semantic.warning.main,
        },
      },
      standardInfo: {
        backgroundColor: semantic.info.light,
        color: semantic.info.dark,
        border: `1px solid rgba(10, 110, 209, 0.2)`,
        '& .MuiAlert-icon': {
          color: semantic.info.main,
        },
      },
      filled: {
        fontWeight: 500,
      },
      outlined: {
        backgroundColor: '#FFFFFF',
      },
    },
  },

  MuiAlertTitle: {
    styleOverrides: {
      root: {
        fontWeight: 600,
        marginBottom: 4,
        fontSize: '0.9375rem',
      },
    },
  },

  MuiChip: {
    styleOverrides: {
      root: {
        borderRadius: radii.chip,
        fontWeight: 500,
        fontSize: '0.8125rem',
        transition: transitionTokens.preset.color,
      },
      filled: {
        backgroundColor: neutral[100],
        color: neutral[800],
        '&:hover': {
          backgroundColor: neutral[200],
        },
      },
      filledPrimary: {
        backgroundColor: primary[50],
        color: primary[700],
        '&:hover': {
          backgroundColor: primary[100],
        },
      },
      outlined: {
        borderColor: neutral[300],
        color: neutral[700],
        '&:hover': {
          backgroundColor: neutral[50],
        },
      },
      outlinedPrimary: {
        borderColor: primary[300],
        color: primary[600],
        '&:hover': {
          backgroundColor: primary[50],
        },
      },
      sizeSmall: {
        height: 24,
        fontSize: '0.75rem',
      },
      sizeMedium: {
        height: 32,
      },
      deleteIcon: {
        color: 'inherit',
        opacity: 0.7,
        '&:hover': {
          opacity: 1,
        },
      },
      clickable: {
        cursor: 'pointer',
        '&:active': {
          boxShadow: 'none',
        },
      },
    },
  },

  MuiSnackbar: {
    styleOverrides: {
      root: {
        '& .MuiSnackbarContent-root': {
          borderRadius: radii.DEFAULT,
          boxShadow: shadowTokens.standard.xl,
        },
      },
    },
  },

  MuiSnackbarContent: {
    styleOverrides: {
      root: {
        backgroundColor: neutral[900],
        color: '#FFFFFF',
        fontSize: '0.875rem',
        padding: '8px 16px',
      },
      message: {
        padding: '4px 0',
      },
      action: {
        marginRight: -8,
      },
    },
  },

  MuiTooltip: {
    styleOverrides: {
      tooltip: {
        backgroundColor: neutral[900],
        color: '#FFFFFF',
        fontSize: '0.8125rem',
        fontWeight: 400,
        padding: '8px 12px',
        borderRadius: radii.tooltip,
        boxShadow: shadowTokens.standard.lg,
        maxWidth: 300,
      },
      arrow: {
        color: neutral[900],
      },
    },
  },

  MuiLinearProgress: {
    styleOverrides: {
      root: {
        height: 6,
        borderRadius: 3,
        backgroundColor: neutral[200],
      },
      bar: {
        borderRadius: 3,
      },
      barColorPrimary: {
        backgroundColor: primary[500],
      },
      barColorSecondary: {
        backgroundColor: semantic.success.main,
      },
    },
  },

  MuiCircularProgress: {
    styleOverrides: {
      root: {
        color: primary[500],
      },
    },
  },

  MuiSkeleton: {
    styleOverrides: {
      root: {
        backgroundColor: neutral[200],
      },
      rectangular: {
        borderRadius: radii.DEFAULT,
      },
      rounded: {
        borderRadius: radii.DEFAULT,
      },
    },
  },

  MuiBadge: {
    styleOverrides: {
      badge: {
        fontWeight: 600,
        fontSize: '0.7rem',
        minWidth: 18,
        height: 18,
        padding: '0 4px',
      },
      colorPrimary: {
        backgroundColor: primary[500],
      },
      colorError: {
        backgroundColor: semantic.error.main,
      },
      dot: {
        minWidth: 8,
        height: 8,
        borderRadius: '50%',
      },
    },
  },

  MuiAvatar: {
    styleOverrides: {
      root: {
        backgroundColor: neutral[300],
        color: neutral[700],
        fontWeight: 600,
        fontSize: '0.875rem',
      },
      colorDefault: {
        backgroundColor: primary[100],
        color: primary[700],
      },
    },
  },

  MuiAvatarGroup: {
    styleOverrides: {
      root: {
        '& .MuiAvatar-root': {
          borderColor: '#FFFFFF',
          borderWidth: 2,
        },
      },
    },
  },
};

export default feedbackOverrides;
