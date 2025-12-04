/**
 * Card Component Overrides
 * Premium card styling with variants and interactive states
 */

import { neutral, primary } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { transitionTokens } from '../tokens/transitions';
import { radii } from '../tokens';

export const cardOverrides = {
  MuiCard: {
    defaultProps: {
      elevation: 0,
    },
    styleOverrides: {
      root: ({ ownerState }) => ({
        borderRadius: radii.card,
        transition: transitionTokens.preset.card,
        backgroundImage: 'none',

        // Default (elevation) variant
        ...(ownerState.variant === 'elevation' && {
          border: '1px solid transparent',
          boxShadow: shadowTokens.standard.sm,
          '&:hover': {
            boxShadow: shadowTokens.standard.lg,
            transform: 'translateY(-2px)',
          },
        }),

        // Outlined variant
        ...(ownerState.variant === 'outlined' && {
          border: `1px solid ${neutral[300]}`,
          boxShadow: 'none',
          '&:hover': {
            borderColor: primary[300],
            boxShadow: `0 0 0 1px ${primary[100]}`,
          },
        }),
      }),
    },
  },

  MuiCardHeader: {
    styleOverrides: {
      root: {
        padding: '16px 20px',
        borderBottom: `1px solid ${neutral[200]}`,
      },
      title: {
        fontSize: '1rem',
        fontWeight: 600,
        color: neutral[900],
      },
      subheader: {
        fontSize: '0.875rem',
        color: neutral[600],
        marginTop: 2,
      },
      action: {
        marginTop: 0,
        marginRight: 0,
      },
    },
  },

  MuiCardContent: {
    styleOverrides: {
      root: {
        padding: '20px',
        '&:last-child': {
          paddingBottom: 20,
        },
      },
    },
  },

  MuiCardActions: {
    styleOverrides: {
      root: {
        padding: '12px 20px',
        borderTop: `1px solid ${neutral[200]}`,
        justifyContent: 'flex-end',
        gap: 8,
      },
      spacing: {
        '& > :not(:first-of-type)': {
          marginLeft: 0,
        },
      },
    },
  },

  MuiCardMedia: {
    styleOverrides: {
      root: {
        borderRadius: `${radii.card}px ${radii.card}px 0 0`,
      },
    },
  },

  MuiCardActionArea: {
    styleOverrides: {
      root: {
        transition: transitionTokens.preset.card,
        '&:hover': {
          backgroundColor: 'transparent',
          '& .MuiCardActionArea-focusHighlight': {
            opacity: 0.04,
          },
        },
      },
      focusHighlight: {
        backgroundColor: primary[500],
      },
    },
  },

  // Paper (used for cards and surfaces)
  MuiPaper: {
    defaultProps: {
      elevation: 0,
    },
    styleOverrides: {
      root: {
        backgroundImage: 'none',
      },
      rounded: {
        borderRadius: radii.DEFAULT,
      },
      elevation0: {
        boxShadow: 'none',
      },
      elevation1: {
        boxShadow: shadowTokens.standard.xs,
      },
      elevation2: {
        boxShadow: shadowTokens.standard.sm,
      },
      elevation3: {
        boxShadow: shadowTokens.standard.md,
      },
      elevation4: {
        boxShadow: shadowTokens.standard.lg,
      },
      elevation6: {
        boxShadow: shadowTokens.standard.xl,
      },
      elevation8: {
        boxShadow: shadowTokens.standard['2xl'],
      },
      elevation12: {
        boxShadow: shadowTokens.standard['3xl'],
      },
      elevation16: {
        boxShadow: shadowTokens.standard.dialog,
      },
      elevation24: {
        boxShadow: shadowTokens.standard.dialog,
      },
      outlined: {
        border: `1px solid ${neutral[300]}`,
      },
    },
  },
};

// Additional card style presets for use in components
export const cardPresets = {
  // Interactive clickable card
  interactive: {
    cursor: 'pointer',
    transition: transitionTokens.preset.card,
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: shadowTokens.standard.xl,
      borderColor: `${primary[200]}`,
    },
    '&:active': {
      transform: 'translateY(-2px)',
      boxShadow: shadowTokens.standard.md,
    },
  },

  // Glass effect card
  glass: {
    background: 'rgba(255, 255, 255, 0.72)',
    backdropFilter: 'blur(12px) saturate(180%)',
    WebkitBackdropFilter: 'blur(12px) saturate(180%)',
    border: '1px solid rgba(255, 255, 255, 0.5)',
    boxShadow: shadowTokens.glass.light,
  },

  // Elevated feature card
  featured: {
    boxShadow: shadowTokens.standard.lg,
    border: 'none',
    '&:hover': {
      boxShadow: shadowTokens.standard['2xl'],
      transform: 'translateY(-4px)',
    },
  },

  // Subtle/flat card
  subtle: {
    backgroundColor: neutral[50],
    border: `1px solid ${neutral[200]}`,
    boxShadow: 'none',
    '&:hover': {
      backgroundColor: neutral[100],
    },
  },
};

export default cardOverrides;
