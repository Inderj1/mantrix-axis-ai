/**
 * Corporate Premium Theme
 * Main theme file that assembles all tokens, effects, and component overrides
 */

import { createTheme } from '@mui/material/styles';

// Import tokens
import { colorTokens, primary, secondary, semantic, neutral, chart } from './tokens/colors';
import { shadowTokens, muiShadows } from './tokens/shadows';
import { transitionTokens, muiTransitions } from './tokens/transitions';
import { radii, spacing } from './tokens';

// Import component overrides
import { allComponentOverrides } from './components';

// Typography configuration
const typography = {
  fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
  fontSize: 14,
  fontWeightLight: 300,
  fontWeightRegular: 400,
  fontWeightMedium: 500,
  fontWeightBold: 600,

  h1: {
    fontSize: '2.5rem',
    fontWeight: 700,
    lineHeight: 1.2,
    letterSpacing: '-0.02em',
    color: neutral[900],
  },
  h2: {
    fontSize: '2rem',
    fontWeight: 700,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
    color: neutral[900],
  },
  h3: {
    fontSize: '1.75rem',
    fontWeight: 600,
    lineHeight: 1.3,
    color: neutral[900],
  },
  h4: {
    fontSize: '1.5rem',
    fontWeight: 600,
    lineHeight: 1.4,
    color: neutral[900],
  },
  h5: {
    fontSize: '1.25rem',
    fontWeight: 600,
    lineHeight: 1.4,
    color: neutral[900],
  },
  h6: {
    fontSize: '1rem',
    fontWeight: 600,
    lineHeight: 1.5,
    color: neutral[900],
  },
  subtitle1: {
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: 1.5,
    color: neutral[900],
  },
  subtitle2: {
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: 1.5,
    color: neutral[600],
  },
  body1: {
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: 1.6,
    color: neutral[800],
  },
  body2: {
    fontSize: '0.875rem',
    fontWeight: 400,
    lineHeight: 1.6,
    color: neutral[600],
  },
  button: {
    fontSize: '0.875rem',
    fontWeight: 500,
    textTransform: 'none',
    letterSpacing: '0.02em',
  },
  caption: {
    fontSize: '0.75rem',
    fontWeight: 400,
    lineHeight: 1.5,
    color: neutral[500],
  },
  overline: {
    fontSize: '0.75rem',
    fontWeight: 600,
    lineHeight: 1.5,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: neutral[500],
  },
};

// Create the Corporate Premium Theme
export const premiumTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: primary[500],
      light: primary[300],
      dark: primary[700],
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: secondary[500],
      light: secondary[300],
      dark: secondary[700],
      contrastText: '#FFFFFF',
    },
    success: semantic.success,
    warning: semantic.warning,
    error: semantic.error,
    info: semantic.info,
    background: {
      default: neutral[100],
      paper: '#FFFFFF',
    },
    text: {
      primary: neutral[900],
      secondary: neutral[600],
      disabled: neutral[500],
    },
    divider: neutral[300],
    action: {
      hover: primary[50],
      selected: primary[50],
      disabled: neutral[300],
      disabledBackground: neutral[200],
      focus: primary[100],
    },
    grey: neutral,
  },

  typography,

  spacing: spacing.base,

  shape: {
    borderRadius: radii.DEFAULT,
  },

  shadows: muiShadows,

  transitions: muiTransitions,

  components: {
    ...allComponentOverrides,

    // Global CSS baseline
    MuiCssBaseline: {
      styleOverrides: {
        '*': {
          boxSizing: 'border-box',
        },
        html: {
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale',
        },
        body: {
          backgroundColor: neutral[100],
          color: neutral[900],
        },
        // Scrollbar styling
        '::-webkit-scrollbar': {
          width: 8,
          height: 8,
        },
        '::-webkit-scrollbar-track': {
          backgroundColor: neutral[100],
          borderRadius: 4,
        },
        '::-webkit-scrollbar-thumb': {
          backgroundColor: neutral[400],
          borderRadius: 4,
          '&:hover': {
            backgroundColor: neutral[500],
          },
        },
        // Selection styling
        '::selection': {
          backgroundColor: primary[100],
          color: primary[800],
        },
      },
    },
  },
});

// Re-export tokens and utilities for custom use
export { colorTokens, primary, secondary, semantic, neutral, chart };
export { shadowTokens };
export { transitionTokens };
export { radii, spacing };

// Re-export effects
export { glassmorphism, createGlassEffect } from './effects/glassmorphism';
export { gradients, buttonGradients, surfaceGradients, dialogGradients } from './effects/gradients';
export { interactiveMixins, surfaces } from './effects';

// Re-export component presets
export { cardPresets } from './components/cards';

// Re-export chat styles
export { chatMessageStyles } from './helpers/chatStyles';

// Export chart colors for data visualization
export const chartColors = chart;

export default premiumTheme;
