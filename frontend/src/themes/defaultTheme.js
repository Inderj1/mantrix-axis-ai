import { createTheme } from '@mui/material/styles';

// Professional Corporate Theme with Enhanced Typography and Visual Polish
export const defaultTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0A6ED1', // Professional blue
      light: '#4A9EE6',
      dark: '#084C94',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#DF6E0C', // Warm accent orange
      light: '#FF9945',
      dark: '#B85708',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F8FAFB', // Soft light grey
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1A2332', // Deep navy for primary text
      secondary: '#5A6677', // Muted grey for secondary text
    },
    divider: '#E5E9EE',
    action: {
      hover: 'rgba(10, 110, 209, 0.04)',
      selected: 'rgba(10, 110, 209, 0.08)',
    },
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", "Arial", sans-serif',
    fontWeightLight: 300,
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 600,

    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
      lineHeight: 1.2,
      letterSpacing: '-0.02em',
      color: '#1A2332',
    },
    h2: {
      fontWeight: 700,
      fontSize: '2rem',
      lineHeight: 1.3,
      letterSpacing: '-0.01em',
      color: '#1A2332',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.75rem',
      lineHeight: 1.3,
      color: '#1A2332',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.4,
      color: '#1A2332',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.4,
      color: '#1A2332',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
      lineHeight: 1.5,
      color: '#1A2332',
    },
    subtitle1: {
      fontWeight: 500,
      fontSize: '1rem',
      lineHeight: 1.5,
      color: '#1A2332',
    },
    subtitle2: {
      fontWeight: 500,
      fontSize: '0.875rem',
      lineHeight: 1.5,
      color: '#5A6677',
    },
    body1: {
      fontWeight: 400,
      fontSize: '1rem',
      lineHeight: 1.6,
      color: '#1A2332',
    },
    body2: {
      fontWeight: 400,
      fontSize: '0.875rem',
      lineHeight: 1.6,
      color: '#5A6677',
    },
    button: {
      fontWeight: 500,
      fontSize: '0.875rem',
      textTransform: 'none', // Remove uppercase transformation for modern look
      letterSpacing: '0.02em',
    },
    caption: {
      fontWeight: 400,
      fontSize: '0.75rem',
      lineHeight: 1.5,
      color: '#7A8699',
    },
    overline: {
      fontWeight: 600,
      fontSize: '0.75rem',
      lineHeight: 1.5,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: '#7A8699',
    },
  },
  shape: {
    borderRadius: 8, // Slightly rounded for modern corporate feel
  },
  shadows: [
    'none',
    '0px 1px 3px rgba(26, 35, 50, 0.06), 0px 1px 2px rgba(26, 35, 50, 0.04)', // Subtle shadow
    '0px 2px 4px rgba(26, 35, 50, 0.08), 0px 2px 4px rgba(26, 35, 50, 0.04)',
    '0px 4px 8px rgba(26, 35, 50, 0.08), 0px 2px 4px rgba(26, 35, 50, 0.04)',
    '0px 8px 16px rgba(26, 35, 50, 0.10), 0px 4px 8px rgba(26, 35, 50, 0.06)',
    '0px 12px 24px rgba(26, 35, 50, 0.12), 0px 6px 12px rgba(26, 35, 50, 0.08)',
    '0px 16px 32px rgba(26, 35, 50, 0.14), 0px 8px 16px rgba(26, 35, 50, 0.10)',
    '0px 20px 40px rgba(26, 35, 50, 0.16), 0px 10px 20px rgba(26, 35, 50, 0.12)',
    '0px 24px 48px rgba(26, 35, 50, 0.18), 0px 12px 24px rgba(26, 35, 50, 0.14)',
    '0px 28px 56px rgba(26, 35, 50, 0.20), 0px 14px 28px rgba(26, 35, 50, 0.16)',
    // Continue with increasing shadows...
    '0px 32px 64px rgba(26, 35, 50, 0.22), 0px 16px 32px rgba(26, 35, 50, 0.18)',
    '0px 36px 72px rgba(26, 35, 50, 0.24), 0px 18px 36px rgba(26, 35, 50, 0.20)',
    '0px 40px 80px rgba(26, 35, 50, 0.26), 0px 20px 40px rgba(26, 35, 50, 0.22)',
    '0px 44px 88px rgba(26, 35, 50, 0.28), 0px 22px 44px rgba(26, 35, 50, 0.24)',
    '0px 48px 96px rgba(26, 35, 50, 0.30), 0px 24px 48px rgba(26, 35, 50, 0.26)',
    '0px 52px 104px rgba(26, 35, 50, 0.32), 0px 26px 52px rgba(26, 35, 50, 0.28)',
    '0px 56px 112px rgba(26, 35, 50, 0.34), 0px 28px 56px rgba(26, 35, 50, 0.30)',
    '0px 60px 120px rgba(26, 35, 50, 0.36), 0px 30px 60px rgba(26, 35, 50, 0.32)',
    '0px 64px 128px rgba(26, 35, 50, 0.38), 0px 32px 64px rgba(26, 35, 50, 0.34)',
    '0px 68px 136px rgba(26, 35, 50, 0.40), 0px 34px 68px rgba(26, 35, 50, 0.36)',
    '0px 72px 144px rgba(26, 35, 50, 0.42), 0px 36px 72px rgba(26, 35, 50, 0.38)',
    '0px 76px 152px rgba(26, 35, 50, 0.44), 0px 38px 76px rgba(26, 35, 50, 0.40)',
    '0px 80px 160px rgba(26, 35, 50, 0.46), 0px 40px 80px rgba(26, 35, 50, 0.42)',
    '0px 84px 168px rgba(26, 35, 50, 0.48), 0px 42px 84px rgba(26, 35, 50, 0.44)',
    '0px 88px 176px rgba(26, 35, 50, 0.50), 0px 44px 88px rgba(26, 35, 50, 0.46)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
          padding: '8px 20px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(26, 35, 50, 0.08)',
          },
        },
        contained: {
          '&:hover': {
            boxShadow: '0px 4px 8px rgba(26, 35, 50, 0.12)',
          },
        },
        sizeLarge: {
          padding: '12px 28px',
          fontSize: '1rem',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: '1px solid #E5E9EE',
          boxShadow: '0px 1px 3px rgba(26, 35, 50, 0.06)',
          '&:hover': {
            boxShadow: '0px 4px 12px rgba(26, 35, 50, 0.08)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        elevation1: {
          boxShadow: '0px 1px 3px rgba(26, 35, 50, 0.06)',
        },
        elevation2: {
          boxShadow: '0px 2px 4px rgba(26, 35, 50, 0.08)',
        },
        elevation3: {
          boxShadow: '0px 4px 8px rgba(26, 35, 50, 0.10)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          color: '#1A2332',
          backgroundColor: '#F8FAFB',
        },
      },
    },
  },
});