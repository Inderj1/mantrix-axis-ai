/**
 * Button Component Overrides
 * Premium button styling with gradients and lift effects
 */

import { neutral, primary, secondary, semantic } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { transitionTokens } from '../tokens/transitions';
import { radii } from '../tokens';
import { buttonGradients } from '../effects/gradients';

export const buttonOverrides = {
  MuiButton: {
    defaultProps: {
      disableElevation: true,
    },
    styleOverrides: {
      root: {
        borderRadius: radii.button,
        fontWeight: 500,
        fontSize: '0.875rem',
        letterSpacing: '0.02em',
        textTransform: 'none',
        padding: '10px 20px',
        transition: transitionTokens.preset.premiumHover,
        '&:focus-visible': {
          outline: 'none',
          boxShadow: shadowTokens.focus.primary,
        },
      },

      // Contained variant - Premium solid style with gradient
      contained: {
        boxShadow: 'none',
        '&:hover': {
          boxShadow: shadowTokens.colored.primary,
          transform: 'translateY(-1px)',
        },
        '&:active': {
          transform: 'translateY(0)',
          boxShadow: shadowTokens.standard.sm,
        },
      },
      containedPrimary: {
        background: buttonGradients.primary,
        '&:hover': {
          background: buttonGradients.primaryHover,
        },
      },
      containedSecondary: {
        background: buttonGradients.secondary,
        '&:hover': {
          background: `linear-gradient(135deg, ${secondary[600]} 0%, ${secondary[700]} 100%)`,
        },
      },
      containedSuccess: {
        background: buttonGradients.success,
        '&:hover': {
          boxShadow: shadowTokens.colored.success,
        },
      },
      containedError: {
        background: buttonGradients.danger,
        '&:hover': {
          boxShadow: shadowTokens.colored.error,
        },
      },

      // Outlined variant - Refined border style
      outlined: {
        borderWidth: 1.5,
        '&:hover': {
          borderWidth: 1.5,
          backgroundColor: primary[50],
          boxShadow: shadowTokens.standard.sm,
        },
      },
      outlinedPrimary: {
        borderColor: primary[500],
        color: primary[500],
        '&:hover': {
          borderColor: primary[600],
          backgroundColor: primary[50],
        },
      },
      outlinedSecondary: {
        borderColor: neutral[400],
        color: neutral[700],
        '&:hover': {
          borderColor: neutral[500],
          backgroundColor: neutral[50],
        },
      },

      // Text variant - Subtle hover
      text: {
        '&:hover': {
          backgroundColor: primary[50],
        },
      },
      textPrimary: {
        color: primary[500],
        '&:hover': {
          backgroundColor: primary[50],
        },
      },
      textSecondary: {
        color: neutral[600],
        '&:hover': {
          backgroundColor: neutral[100],
        },
      },

      // Size variants
      sizeSmall: {
        padding: '6px 14px',
        fontSize: '0.8125rem',
      },
      sizeMedium: {
        padding: '10px 20px',
        fontSize: '0.875rem',
      },
      sizeLarge: {
        padding: '14px 28px',
        fontSize: '1rem',
      },

      // Disabled state
      disabled: {
        backgroundColor: neutral[200],
        color: neutral[500],
      },
    },
  },

  MuiIconButton: {
    styleOverrides: {
      root: {
        borderRadius: radii.DEFAULT,
        transition: transitionTokens.preset.color,
        '&:hover': {
          backgroundColor: primary[50],
        },
        '&:focus-visible': {
          outline: 'none',
          boxShadow: shadowTokens.focus.primary,
        },
      },
      colorPrimary: {
        '&:hover': {
          backgroundColor: primary[100],
        },
      },
      colorSecondary: {
        '&:hover': {
          backgroundColor: neutral[100],
        },
      },
      sizeSmall: {
        padding: 6,
      },
      sizeMedium: {
        padding: 8,
      },
      sizeLarge: {
        padding: 12,
      },
    },
  },

  MuiToggleButton: {
    styleOverrides: {
      root: {
        borderRadius: radii.DEFAULT,
        borderColor: neutral[300],
        textTransform: 'none',
        fontWeight: 500,
        padding: '8px 16px',
        transition: transitionTokens.preset.color,
        '&.Mui-selected': {
          backgroundColor: primary[50],
          borderColor: primary[500],
          color: primary[600],
          '&:hover': {
            backgroundColor: primary[100],
          },
        },
        '&:hover': {
          backgroundColor: neutral[50],
        },
      },
    },
  },

  MuiToggleButtonGroup: {
    styleOverrides: {
      root: {
        borderRadius: radii.DEFAULT,
        backgroundColor: neutral[50],
        padding: 2,
        gap: 2,
      },
      grouped: {
        borderRadius: `${radii.md}px !important`,
        border: 'none !important',
        margin: 0,
        '&:not(:first-of-type)': {
          marginLeft: 0,
        },
      },
    },
  },

  MuiButtonGroup: {
    styleOverrides: {
      root: {
        borderRadius: radii.DEFAULT,
        boxShadow: 'none',
      },
      grouped: {
        borderRadius: 0,
        '&:first-of-type': {
          borderTopLeftRadius: radii.DEFAULT,
          borderBottomLeftRadius: radii.DEFAULT,
        },
        '&:last-of-type': {
          borderTopRightRadius: radii.DEFAULT,
          borderBottomRightRadius: radii.DEFAULT,
        },
        '&:not(:last-of-type)': {
          borderRight: 'none',
        },
      },
    },
  },

  MuiFab: {
    styleOverrides: {
      root: {
        boxShadow: shadowTokens.standard.lg,
        transition: transitionTokens.preset.premiumHover,
        '&:hover': {
          boxShadow: shadowTokens.standard.xl,
          transform: 'scale(1.05)',
        },
        '&:active': {
          transform: 'scale(0.98)',
        },
      },
      primary: {
        background: buttonGradients.primary,
        '&:hover': {
          background: buttonGradients.primaryHover,
        },
      },
    },
  },

  MuiLoadingButton: {
    styleOverrides: {
      root: {
        '&.MuiLoadingButton-loading': {
          color: 'transparent',
        },
      },
      loadingIndicator: {
        color: 'inherit',
      },
    },
  },
};

export default buttonOverrides;
