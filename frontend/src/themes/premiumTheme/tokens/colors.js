/**
 * Corporate Premium Color Design Tokens
 * Based on SAP Fiori palette with enhanced depth and premium accents
 */

// Primary brand colors - refined from SAP Fiori
export const primary = {
  50: '#E8F4FC',
  100: '#B8DDF5',
  200: '#88C6EE',
  300: '#58AFE7',
  400: '#2898E0',
  500: '#0A6ED1',  // Main primary (sapBlue)
  600: '#0854A0',  // Dark primary
  700: '#064378',
  800: '#043250',
  900: '#022128',
};

// Secondary accent colors (warm)
export const secondary = {
  50: '#FFF4E6',
  100: '#FFE0B8',
  200: '#FFCC8A',
  300: '#FFB85C',
  400: '#FFA42E',
  500: '#DF6E0C',  // sapCritical - warm accent
  600: '#B85708',
  700: '#914006',
  800: '#6A2904',
  900: '#431202',
};

// Semantic colors
export const semantic = {
  success: {
    light: '#E8F5ED',
    main: '#107E3E',
    dark: '#0B5A2C',
    contrastText: '#FFFFFF',
  },
  warning: {
    light: '#FFF3E0',
    main: '#DF6E0C',
    dark: '#B85708',
    contrastText: '#FFFFFF',
  },
  error: {
    light: '#FFEBEE',
    main: '#BB0000',
    dark: '#8C0000',
    contrastText: '#FFFFFF',
  },
  info: {
    light: '#E3F2FD',
    main: '#0A6ED1',
    dark: '#0854A0',
    contrastText: '#FFFFFF',
  },
};

// Neutral palette - Corporate grays
export const neutral = {
  0: '#FFFFFF',
  50: '#FAFBFC',
  100: '#F5F7F9',
  200: '#EEF1F4',
  300: '#E5E9EE',
  400: '#D1D7DE',
  500: '#A0A7B0',
  600: '#7A8699',
  700: '#5A6677',
  800: '#3A4455',
  900: '#1A2332',
  1000: '#0D1117',
};

// Premium accent colors (for subtle highlights)
export const premium = {
  gold: '#C9A962',
  goldLight: '#F5EDD6',
  silver: '#B8C5D0',
  silverLight: '#E8EDF2',
  platinum: '#E5E4E2',
};

// Chart colors (preserved from sapFiori)
export const chart = [
  '#5899DA', '#E8743B', '#19A979', '#ED4A7B',
  '#945ECF', '#13A4B4', '#525DF4', '#BF3989',
  '#6C8893', '#EE6868'
];

// Overlay and transparency values
export const overlay = {
  light: 'rgba(255, 255, 255, 0.8)',
  dark: 'rgba(26, 35, 50, 0.6)',
  glass: 'rgba(255, 255, 255, 0.72)',
  frost: 'rgba(255, 255, 255, 0.85)',
  backdrop: 'rgba(26, 35, 50, 0.4)',
};

// Export all color tokens
export const colorTokens = {
  primary,
  secondary,
  semantic,
  neutral,
  premium,
  chart,
  overlay,
};

export default colorTokens;
