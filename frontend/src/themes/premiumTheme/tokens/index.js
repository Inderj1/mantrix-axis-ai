/**
 * Design Tokens Index
 * Centralized export for all design tokens
 */

export { colorTokens, primary, secondary, semantic, neutral, premium, chart, overlay } from './colors';
export { shadowTokens, standard as shadows, colored as coloredShadows, glass as glassShadows, focus as focusShadows, muiShadows } from './shadows';
export { transitionTokens, duration, easing, preset as transitionPresets, muiTransitions } from './transitions';

// Border radius tokens
export const radii = {
  none: 0,
  xs: 2,
  sm: 4,
  md: 6,
  DEFAULT: 8,
  lg: 12,
  xl: 16,
  '2xl': 20,
  '3xl': 24,
  full: 9999,
  // Semantic aliases
  button: 8,
  input: 8,
  card: 12,
  dialog: 16,
  chip: 6,
  avatar: 9999,
  tooltip: 6,
};

// Spacing scale (base unit: 4px)
export const spacing = {
  base: 4,
  0: 0,
  0.5: 2,
  1: 4,
  1.5: 6,
  2: 8,
  2.5: 10,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
  20: 80,
  24: 96,
};
