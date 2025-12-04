/**
 * Premium Effects Index
 * Centralized export for all visual effects
 */

export { glassmorphism, light as glassLight, frost as glassFrost, premium as glassPremium, dialogOverlay, createGlassEffect } from './glassmorphism';
export { gradients, primaryGradients, surfaceGradients, buttonGradients, dialogGradients, createGradient } from './gradients';

// Interactive mixins for components
export const interactiveMixins = {
  // Hover lift effect - element rises on hover
  hoverLift: {
    transition: 'transform 200ms cubic-bezier(0.25, 0.1, 0.25, 1), box-shadow 250ms cubic-bezier(0.25, 0.1, 0.25, 1)',
    cursor: 'pointer',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: '0px 8px 16px rgba(26, 35, 50, 0.10)',
    },
    '&:active': {
      transform: 'translateY(0)',
      boxShadow: '0px 2px 4px rgba(26, 35, 50, 0.08)',
    },
  },

  // Subtle scale effect
  hoverScale: {
    transition: 'transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
    '&:hover': {
      transform: 'scale(1.02)',
    },
    '&:active': {
      transform: 'scale(0.98)',
    },
  },

  // Focus ring
  focusRing: {
    '&:focus-visible': {
      outline: 'none',
      boxShadow: '0px 0px 0px 3px rgba(10, 110, 209, 0.24)',
    },
  },

  // Clickable card
  clickableCard: {
    cursor: 'pointer',
    transition: 'transform 200ms cubic-bezier(0.23, 1, 0.32, 1), box-shadow 250ms cubic-bezier(0.23, 1, 0.32, 1), border-color 200ms ease',
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: '0px 12px 24px rgba(26, 35, 50, 0.12)',
      borderColor: 'rgba(10, 110, 209, 0.3)',
    },
    '&:active': {
      transform: 'translateY(-2px)',
      boxShadow: '0px 4px 12px rgba(26, 35, 50, 0.10)',
    },
  },

  // Press effect for buttons
  pressEffect: {
    transition: 'transform 100ms cubic-bezier(0.4, 0, 0.2, 1)',
    '&:active': {
      transform: 'scale(0.97)',
    },
  },
};

// Surface styles for common patterns
export const surfaces = {
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    border: '1px solid #E5E9EE',
    boxShadow: '0px 1px 3px rgba(26, 35, 50, 0.06)',
  },
  cardElevated: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    border: 'none',
    boxShadow: '0px 4px 8px rgba(26, 35, 50, 0.08)',
  },
  paper: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    border: '1px solid #D1D7DE',
  },
  dialog: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    boxShadow: '0px 24px 48px rgba(26, 35, 50, 0.18)',
  },
};
