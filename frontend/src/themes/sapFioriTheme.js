import { createTheme } from '@mui/material/styles';

// SAP Fiori 3 Color Palette
const sapColors = {
  // Primary Blues
  sapBlue: '#0a6ed1',
  sapDarkBlue: '#0854a0',
  sapLightBlue: '#1873b4',
  
  // Semantic Colors
  sapPositive: '#107e3e',
  sapCritical: '#df6e0c',
  sapNegative: '#bb0000',
  sapInformation: '#0a6ed1',
  sapNeutral: '#6a6d70',
  
  // Shell Colors
  sapShellHeader: '#354a5f',
  sapShellNavigation: '#fff',
  
  // Background Colors
  sapBackgroundLight: '#f7f7f7',
  sapBackgroundMedium: '#eff1f2',
  sapBackgroundDark: '#edeff0',
  
  // Text Colors - Enhanced for better readability
  sapTextColor: '#1A2332',
  sapTextColorLight: '#5A6677',
  sapTextColorMuted: '#7A8699',
  sapTextColorInverted: '#fff',
  
  // Chart Colors (for AI dashboards)
  sapChart1: '#5899da',
  sapChart2: '#e8743b',
  sapChart3: '#19a979',
  sapChart4: '#ed4a7b',
  sapChart5: '#945ecf',
  sapChart6: '#13a4b4',
  sapChart7: '#525df4',
  sapChart8: '#bf3989',
  sapChart9: '#6c8893',
  sapChart10: '#ee6868',
};

// Professional Corporate Typography
const sapTypography = {
  fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
  fontSize: 14,
  fontWeightLight: 300,
  fontWeightRegular: 400,
  fontWeightMedium: 500,
  fontWeightBold: 600,

  // Headers - More professional with better weights
  h1: {
    fontSize: '2.5rem', // 40px
    fontWeight: 700,
    lineHeight: 1.2,
    letterSpacing: '-0.02em',
    color: '#1A2332',
  },
  h2: {
    fontSize: '2rem', // 32px
    fontWeight: 700,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
    color: '#1A2332',
  },
  h3: {
    fontSize: '1.75rem', // 28px
    fontWeight: 600,
    lineHeight: 1.3,
    color: '#1A2332',
  },
  h4: {
    fontSize: '1.5rem', // 24px
    fontWeight: 600,
    lineHeight: 1.4,
    color: '#1A2332',
  },
  h5: {
    fontSize: '1.25rem', // 20px
    fontWeight: 600,
    lineHeight: 1.4,
    color: '#1A2332',
  },
  h6: {
    fontSize: '1rem', // 16px
    fontWeight: 600,
    lineHeight: 1.5,
    color: '#1A2332',
  },

  // Subtitles
  subtitle1: {
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: 1.5,
    color: '#1A2332',
  },
  subtitle2: {
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: 1.5,
    color: '#5A6677',
  },

  // Body
  body1: {
    fontSize: '1rem', // 16px - increased for better readability
    fontWeight: 400,
    lineHeight: 1.6,
    color: '#32363a',
  },
  body2: {
    fontSize: '0.875rem', // 14px
    fontWeight: 400,
    lineHeight: 1.6,
    color: '#5A6677',
  },

  // Other
  button: {
    fontSize: '0.875rem',
    fontWeight: 500,
    textTransform: 'none',
    letterSpacing: '0.02em',
  },
  caption: {
    fontSize: '0.75rem', // 12px
    fontWeight: 400,
    lineHeight: 1.5,
    color: '#7A8699',
  },
  overline: {
    fontSize: '0.75rem',
    fontWeight: 600,
    lineHeight: 1.5,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#7A8699',
  },
};

// Create SAP Fiori Theme
export const sapFioriTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: sapColors.sapBlue,
      dark: sapColors.sapDarkBlue,
      light: sapColors.sapLightBlue,
      contrastText: '#fff',
    },
    secondary: {
      main: sapColors.sapNeutral,
      contrastText: '#fff',
    },
    success: {
      main: sapColors.sapPositive,
      contrastText: '#fff',
    },
    warning: {
      main: sapColors.sapCritical,
      contrastText: '#fff',
    },
    error: {
      main: sapColors.sapNegative,
      contrastText: '#fff',
    },
    info: {
      main: sapColors.sapInformation,
      contrastText: '#fff',
    },
    background: {
      default: sapColors.sapBackgroundLight,
      paper: '#fff',
    },
    text: {
      primary: sapColors.sapTextColor,
      secondary: sapColors.sapTextColorLight,
    },
    divider: 'rgba(0, 0, 0, 0.12)',
  },
  
  typography: sapTypography,
  
  spacing: 4, // Base spacing unit (4px)

  shape: {
    borderRadius: 8, // Modern rounded corners for corporate feel
  },
  
  components: {
    // App Bar (Header)
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: sapColors.sapShellHeader,
          boxShadow: '0 1px 0 0 rgba(0,0,0,0.15)',
        },
      },
    },
    
    // Buttons - Enhanced for better UX
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 20px',
          fontWeight: 500,
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(26, 35, 50, 0.08)',
          },
        },
        contained: {
          '&:hover': {
            backgroundColor: sapColors.sapDarkBlue,
            boxShadow: '0px 4px 8px rgba(26, 35, 50, 0.12)',
          },
        },
        outlined: {
          borderWidth: 1,
          '&:hover': {
            borderWidth: 1,
            backgroundColor: 'rgba(10, 110, 209, 0.04)',
          },
        },
        sizeLarge: {
          padding: '12px 28px',
          fontSize: '1rem',
        },
      },
    },
    
    // Cards - More refined
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
    
    // Paper - Refined shadows
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
    
    // Text Fields - Modern look
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            '& fieldset': {
              borderColor: 'rgba(0,0,0,0.23)',
            },
            '&:hover fieldset': {
              borderColor: sapColors.sapBlue,
            },
          },
        },
      },
    },
    
    // Tabs
    MuiTabs: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(0,0,0,0.12)',
        },
        indicator: {
          height: 3,
          backgroundColor: sapColors.sapBlue,
        },
      },
    },
    
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 400,
          '&.Mui-selected': {
            fontWeight: 600,
          },
        },
      },
    },
    
    // List Items
    MuiListItemButton: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(106, 109, 112, 0.1)',
          },
          '&.Mui-selected': {
            backgroundColor: 'rgba(106, 109, 112, 0.08)',
            '&:hover': {
              backgroundColor: 'rgba(106, 109, 112, 0.12)',
            },
          },
        },
      },
    },

    // Drawer
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: sapColors.sapShellNavigation,
          borderRight: '1px solid rgba(0,0,0,0.12)',
        },
      },
    },
    
    // Alert
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 4,
        },
        standardSuccess: {
          backgroundColor: 'rgba(16, 126, 62, 0.1)',
          color: sapColors.sapPositive,
        },
        standardError: {
          backgroundColor: 'rgba(187, 0, 0, 0.1)',
          color: sapColors.sapNegative,
        },
        standardWarning: {
          backgroundColor: 'rgba(223, 110, 12, 0.1)',
          color: sapColors.sapCritical,
        },
        standardInfo: {
          backgroundColor: 'rgba(10, 110, 209, 0.1)',
          color: sapColors.sapInformation,
        },
      },
    },

    // Table Cells - Better headers
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          color: '#1A2332',
          backgroundColor: '#F8FAFB',
        },
      },
    },

    // Chips - Refined
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
      },
    },
  },
});

// Export color palette for charts
export const sapChartColors = [
  sapColors.sapChart1,
  sapColors.sapChart2,
  sapColors.sapChart3,
  sapColors.sapChart4,
  sapColors.sapChart5,
  sapColors.sapChart6,
  sapColors.sapChart7,
  sapColors.sapChart8,
  sapColors.sapChart9,
  sapColors.sapChart10,
];

// Export individual colors for custom usage
export { sapColors };