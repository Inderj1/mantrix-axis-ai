/**
 * Corporate Premium Shadow Design Tokens
 * Refined shadow system for depth and elevation
 */

// Standard elevation shadows
export const standard = {
  none: 'none',
  xs: '0px 1px 2px rgba(26, 35, 50, 0.04)',
  sm: '0px 1px 3px rgba(26, 35, 50, 0.06), 0px 1px 2px rgba(26, 35, 50, 0.04)',
  md: '0px 2px 4px rgba(26, 35, 50, 0.08), 0px 2px 4px rgba(26, 35, 50, 0.04)',
  lg: '0px 4px 8px rgba(26, 35, 50, 0.08), 0px 2px 4px rgba(26, 35, 50, 0.04)',
  xl: '0px 8px 16px rgba(26, 35, 50, 0.10), 0px 4px 8px rgba(26, 35, 50, 0.06)',
  '2xl': '0px 12px 24px rgba(26, 35, 50, 0.12), 0px 6px 12px rgba(26, 35, 50, 0.08)',
  '3xl': '0px 20px 40px rgba(26, 35, 50, 0.16), 0px 10px 20px rgba(26, 35, 50, 0.12)',
  dialog: '0px 24px 48px rgba(26, 35, 50, 0.18), 0px 12px 24px rgba(26, 35, 50, 0.12)',
};

// Premium colored shadows
export const colored = {
  primary: '0px 4px 14px rgba(10, 110, 209, 0.25)',
  primaryHover: '0px 8px 20px rgba(10, 110, 209, 0.30)',
  primaryLight: '0px 2px 8px rgba(10, 110, 209, 0.15)',
  success: '0px 4px 14px rgba(16, 126, 62, 0.25)',
  warning: '0px 4px 14px rgba(223, 110, 12, 0.25)',
  error: '0px 4px 14px rgba(187, 0, 0, 0.25)',
};

// Glassmorphism shadows
export const glass = {
  light: '0px 8px 32px rgba(26, 35, 50, 0.12), inset 0px 1px 0px rgba(255, 255, 255, 0.6)',
  medium: '0px 12px 40px rgba(26, 35, 50, 0.15), inset 0px 1px 0px rgba(255, 255, 255, 0.4)',
  heavy: '0px 16px 56px rgba(26, 35, 50, 0.20), inset 0px 1px 0px rgba(255, 255, 255, 0.3)',
};

// Inner shadows (for pressed states, inputs)
export const inner = {
  subtle: 'inset 0px 1px 2px rgba(26, 35, 50, 0.06)',
  medium: 'inset 0px 2px 4px rgba(26, 35, 50, 0.10)',
  focus: 'inset 0px 0px 0px 2px rgba(10, 110, 209, 0.20)',
};

// Focus ring shadows
export const focus = {
  primary: '0px 0px 0px 3px rgba(10, 110, 209, 0.24)',
  error: '0px 0px 0px 3px rgba(187, 0, 0, 0.24)',
  success: '0px 0px 0px 3px rgba(16, 126, 62, 0.24)',
};

// MUI shadows array (for theme.shadows)
export const muiShadows = [
  'none',
  standard.xs,
  standard.sm,
  standard.md,
  standard.lg,
  standard.xl,
  standard['2xl'],
  standard['3xl'],
  standard.dialog,
  // Fill remaining slots with progressively stronger shadows
  '0px 5px 10px rgba(26, 35, 50, 0.12)',
  '0px 6px 12px rgba(26, 35, 50, 0.12)',
  '0px 7px 14px rgba(26, 35, 50, 0.14)',
  '0px 8px 16px rgba(26, 35, 50, 0.14)',
  '0px 9px 18px rgba(26, 35, 50, 0.16)',
  '0px 10px 20px rgba(26, 35, 50, 0.16)',
  '0px 11px 22px rgba(26, 35, 50, 0.18)',
  '0px 12px 24px rgba(26, 35, 50, 0.18)',
  '0px 13px 26px rgba(26, 35, 50, 0.20)',
  '0px 14px 28px rgba(26, 35, 50, 0.20)',
  '0px 15px 30px rgba(26, 35, 50, 0.22)',
  '0px 16px 32px rgba(26, 35, 50, 0.22)',
  '0px 17px 34px rgba(26, 35, 50, 0.24)',
  '0px 18px 36px rgba(26, 35, 50, 0.24)',
  '0px 19px 38px rgba(26, 35, 50, 0.26)',
  '0px 20px 40px rgba(26, 35, 50, 0.26)',
];

// Export all shadow tokens
export const shadowTokens = {
  standard,
  colored,
  glass,
  inner,
  focus,
  muiShadows,
};

export default shadowTokens;
