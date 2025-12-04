/**
 * Corporate Premium Transition & Animation Tokens
 * Smooth, professional animations for premium feel
 */

// Duration scale
export const duration = {
  instant: '0ms',
  fast: '100ms',
  normal: '200ms',
  moderate: '300ms',
  slow: '400ms',
  slower: '500ms',
  slowest: '700ms',
};

// Easing functions
export const easing = {
  // Standard Material Design easings
  standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
  emphasized: 'cubic-bezier(0.4, 0, 0, 1)',
  decelerate: 'cubic-bezier(0, 0, 0.2, 1)',
  accelerate: 'cubic-bezier(0.4, 0, 1, 1)',

  // Premium smooth easings
  smooth: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  smoothOut: 'cubic-bezier(0.23, 1, 0.32, 1)',

  // Bounce/elastic (use sparingly)
  bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  elastic: 'cubic-bezier(0.68, -0.6, 0.32, 1.6)',

  // Entry/exit
  enter: 'cubic-bezier(0, 0, 0.2, 1)',
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
};

// Pre-composed transitions
export const preset = {
  // Interactive elements
  button: `all ${duration.normal} ${easing.standard}`,
  buttonHover: `transform ${duration.fast} ${easing.standard}, box-shadow ${duration.normal} ${easing.standard}`,

  // Color transitions
  color: `color ${duration.normal} ${easing.standard}, background-color ${duration.normal} ${easing.standard}`,
  backgroundColor: `background-color ${duration.normal} ${easing.standard}`,
  borderColor: `border-color ${duration.normal} ${easing.standard}`,

  // Transform transitions
  transform: `transform ${duration.moderate} ${easing.standard}`,
  transformFast: `transform ${duration.fast} ${easing.standard}`,

  // Elevation/shadow
  elevation: `box-shadow ${duration.moderate} ${easing.standard}`,

  // Expansion
  expand: `max-height ${duration.moderate} ${easing.standard}, opacity ${duration.normal} ${easing.standard}`,

  // Opacity
  fade: `opacity ${duration.normal} ${easing.standard}`,
  fadeSlow: `opacity ${duration.slow} ${easing.standard}`,

  // Premium combined hover effect
  premiumHover: `transform ${duration.normal} ${easing.smooth}, box-shadow ${duration.moderate} ${easing.smooth}, background-color ${duration.normal} ${easing.standard}`,

  // Card interactions
  card: `transform ${duration.normal} ${easing.smoothOut}, box-shadow ${duration.moderate} ${easing.smoothOut}, border-color ${duration.normal} ${easing.standard}`,

  // Form inputs
  input: `border-color ${duration.normal} ${easing.standard}, box-shadow ${duration.normal} ${easing.standard}`,

  // Icon rotation
  iconRotate: `transform ${duration.moderate} ${easing.standard}`,
};

// MUI transitions config (for createTheme)
export const muiTransitions = {
  duration: {
    shortest: 100,
    shorter: 150,
    short: 200,
    standard: 250,
    complex: 350,
    enteringScreen: 225,
    leavingScreen: 195,
  },
  easing: {
    easeInOut: easing.standard,
    easeOut: easing.decelerate,
    easeIn: easing.accelerate,
    sharp: easing.emphasized,
  },
};

// Export all transition tokens
export const transitionTokens = {
  duration,
  easing,
  preset,
  muiTransitions,
};

export default transitionTokens;
