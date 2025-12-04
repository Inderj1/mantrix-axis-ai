/**
 * Gradient Presets
 * Premium gradient effects for Corporate Premium theme
 */

import { primary, secondary, neutral, premium as premiumColors } from '../tokens/colors';

// Primary brand gradients
export const primaryGradients = {
  default: `linear-gradient(135deg, ${primary[500]} 0%, ${primary[600]} 100%)`,
  subtle: `linear-gradient(135deg, ${primary[50]} 0%, ${primary[100]} 100%)`,
  vibrant: `linear-gradient(135deg, ${primary[400]} 0%, ${primary[700]} 100%)`,
  vertical: `linear-gradient(180deg, ${primary[500]} 0%, ${primary[700]} 100%)`,
};

// Secondary/accent gradients
export const accentGradients = {
  warm: `linear-gradient(135deg, ${secondary[400]} 0%, ${secondary[600]} 100%)`,
  warmSubtle: `linear-gradient(135deg, ${secondary[50]} 0%, ${secondary[100]} 100%)`,
};

// Premium metallic gradients
export const metallicGradients = {
  gold: `linear-gradient(135deg, ${premiumColors.goldLight} 0%, ${premiumColors.gold} 50%, ${premiumColors.goldLight} 100%)`,
  silver: `linear-gradient(135deg, #FFFFFF 0%, ${premiumColors.silver} 50%, #FFFFFF 100%)`,
  platinum: `linear-gradient(135deg, #FAFAFA 0%, ${premiumColors.platinum} 50%, #FAFAFA 100%)`,
};

// Surface gradients (subtle depth)
export const surfaceGradients = {
  card: `linear-gradient(180deg, #FFFFFF 0%, #FAFBFC 100%)`,
  cardHover: `linear-gradient(180deg, #FFFFFF 0%, #F5F7F9 100%)`,
  elevated: `linear-gradient(180deg, #FFFFFF 0%, ${neutral[100]} 100%)`,
  paper: `linear-gradient(135deg, #FFFFFF 0%, #FAFBFC 50%, #FFFFFF 100%)`,
  subtle: `linear-gradient(180deg, ${neutral[50]} 0%, ${neutral[100]} 100%)`,
};

// Header/hero gradients
export const heroGradients = {
  primary: `linear-gradient(135deg, ${primary[600]} 0%, ${primary[800]} 100%)`,
  corporate: `linear-gradient(135deg, #354A5F 0%, #1A2332 100%)`,
  dark: `linear-gradient(135deg, ${neutral[800]} 0%, ${neutral[900]} 100%)`,
};

// Dialog header/footer gradients
export const dialogGradients = {
  header: `linear-gradient(180deg, #FFFFFF 0%, #F8FAFB 100%)`,
  footer: `linear-gradient(180deg, #F8FAFB 0%, #FFFFFF 100%)`,
};

// Button gradients
export const buttonGradients = {
  primary: `linear-gradient(135deg, ${primary[500]} 0%, ${primary[600]} 100%)`,
  primaryHover: `linear-gradient(135deg, ${primary[600]} 0%, ${primary[700]} 100%)`,
  secondary: `linear-gradient(135deg, ${secondary[500]} 0%, ${secondary[600]} 100%)`,
  success: `linear-gradient(135deg, #107E3E 0%, #0B5A2C 100%)`,
  danger: `linear-gradient(135deg, #BB0000 0%, #8C0000 100%)`,
};

// Shimmer effect gradient (for loading states)
export const shimmer = `linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.4) 50%, transparent 100%)`;

// Overlay gradients
export const overlayGradients = {
  fadeTop: `linear-gradient(180deg, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0) 100%)`,
  fadeBottom: `linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 1) 100%)`,
  fadeLeft: `linear-gradient(90deg, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0) 100%)`,
  fadeRight: `linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 1) 100%)`,
  scrim: `linear-gradient(180deg, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.6) 100%)`,
};

/**
 * Create custom linear gradient
 * @param {number} angle - Gradient angle in degrees
 * @param {Array<[string, number]>} stops - Array of [color, position] tuples
 * @returns {string} CSS gradient string
 */
export const createGradient = (angle, ...stops) =>
  `linear-gradient(${angle}deg, ${stops.map(([color, position]) => `${color} ${position}%`).join(', ')})`;

// Export all gradient presets
export const gradients = {
  primary: primaryGradients,
  accent: accentGradients,
  metallic: metallicGradients,
  surface: surfaceGradients,
  hero: heroGradients,
  dialog: dialogGradients,
  button: buttonGradients,
  shimmer,
  overlay: overlayGradients,
  createGradient,
};

export default gradients;
