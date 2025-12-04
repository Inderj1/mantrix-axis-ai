/**
 * Glassmorphism Effects
 * Premium glass/frosted effects for Corporate Premium theme
 */

import { shadowTokens } from '../tokens/shadows';

// Light glass - for cards on light backgrounds
export const light = {
  background: 'rgba(255, 255, 255, 0.72)',
  backdropFilter: 'blur(12px) saturate(180%)',
  WebkitBackdropFilter: 'blur(12px) saturate(180%)',
  border: '1px solid rgba(255, 255, 255, 0.5)',
  boxShadow: shadowTokens.glass.light,
};

// Frosted glass - more opaque
export const frost = {
  background: 'rgba(255, 255, 255, 0.85)',
  backdropFilter: 'blur(20px) saturate(200%)',
  WebkitBackdropFilter: 'blur(20px) saturate(200%)',
  border: '1px solid rgba(255, 255, 255, 0.6)',
  boxShadow: shadowTokens.glass.medium,
};

// Premium glass - with subtle gradient
export const premium = {
  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0.6) 100%)',
  backdropFilter: 'blur(16px) saturate(180%)',
  WebkitBackdropFilter: 'blur(16px) saturate(180%)',
  border: '1px solid rgba(255, 255, 255, 0.4)',
  boxShadow: shadowTokens.glass.heavy,
};

// Dialog backdrop with blur
export const dialogOverlay = {
  backgroundColor: 'rgba(26, 35, 50, 0.4)',
  backdropFilter: 'blur(8px)',
  WebkitBackdropFilter: 'blur(8px)',
};

// Header/navigation glass
export const header = {
  background: 'rgba(255, 255, 255, 0.92)',
  backdropFilter: 'blur(12px) saturate(150%)',
  WebkitBackdropFilter: 'blur(12px) saturate(150%)',
  borderBottom: '1px solid rgba(229, 233, 238, 0.8)',
};

// Sidebar glass
export const sidebar = {
  background: 'rgba(255, 255, 255, 0.95)',
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  borderRight: '1px solid rgba(229, 233, 238, 0.6)',
};

// Tooltip glass
export const tooltip = {
  background: 'rgba(26, 35, 50, 0.92)',
  backdropFilter: 'blur(8px)',
  WebkitBackdropFilter: 'blur(8px)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
};

/**
 * Create custom glass effect
 * @param {Object} options
 * @param {number} options.opacity - Background opacity (0-1)
 * @param {number} options.blur - Blur amount in pixels
 * @param {number} options.saturation - Saturation percentage
 * @param {number} options.borderOpacity - Border opacity (0-1)
 * @param {string} options.shadowVariant - Shadow variant: 'light' | 'medium' | 'heavy'
 */
export const createGlassEffect = ({
  opacity = 0.72,
  blur = 12,
  saturation = 180,
  borderOpacity = 0.5,
  shadowVariant = 'light',
} = {}) => ({
  background: `rgba(255, 255, 255, ${opacity})`,
  backdropFilter: `blur(${blur}px) saturate(${saturation}%)`,
  WebkitBackdropFilter: `blur(${blur}px) saturate(${saturation}%)`,
  border: `1px solid rgba(255, 255, 255, ${borderOpacity})`,
  boxShadow: shadowTokens.glass[shadowVariant] || shadowTokens.glass.light,
});

// Export all glassmorphism effects
export const glassmorphism = {
  light,
  frost,
  premium,
  dialogOverlay,
  header,
  sidebar,
  tooltip,
  createGlassEffect,
};

export default glassmorphism;
