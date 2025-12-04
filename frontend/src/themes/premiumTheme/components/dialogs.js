/**
 * Dialog Component Overrides
 * Premium dialog styling with glass effects and refined shadows
 */

import { neutral, primary } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { radii } from '../tokens';
import { dialogGradients } from '../effects/gradients';

export const dialogOverrides = {
  MuiDialog: {
    defaultProps: {
      TransitionProps: {
        timeout: { enter: 250, exit: 200 },
      },
    },
    styleOverrides: {
      root: {
        // Premium backdrop with blur
        '& .MuiBackdrop-root': {
          backgroundColor: 'rgba(26, 35, 50, 0.4)',
          backdropFilter: 'blur(4px)',
          WebkitBackdropFilter: 'blur(4px)',
        },
      },
      paper: {
        borderRadius: radii.dialog,
        boxShadow: shadowTokens.standard.dialog,
        border: '1px solid rgba(229, 233, 238, 0.5)',
        backgroundImage: 'none',
        overflow: 'hidden',
      },
      paperWidthXs: {
        maxWidth: 360,
      },
      paperWidthSm: {
        maxWidth: 480,
      },
      paperWidthMd: {
        maxWidth: 640,
      },
      paperWidthLg: {
        maxWidth: 900,
      },
      paperWidthXl: {
        maxWidth: 1200,
      },
      paperFullScreen: {
        borderRadius: 0,
      },
    },
  },

  MuiDialogTitle: {
    styleOverrides: {
      root: {
        padding: '20px 24px',
        fontSize: '1.25rem',
        fontWeight: 600,
        color: neutral[900],
        borderBottom: `1px solid ${neutral[300]}`,
        background: dialogGradients.header,
      },
    },
  },

  MuiDialogContent: {
    styleOverrides: {
      root: {
        padding: '24px',
        '&:first-of-type': {
          paddingTop: 24,
        },
      },
      dividers: {
        borderTop: `1px solid ${neutral[300]}`,
        borderBottom: `1px solid ${neutral[300]}`,
        padding: '24px',
      },
    },
  },

  MuiDialogContentText: {
    styleOverrides: {
      root: {
        color: neutral[700],
        fontSize: '0.9375rem',
        lineHeight: 1.6,
      },
    },
  },

  MuiDialogActions: {
    styleOverrides: {
      root: {
        padding: '16px 24px',
        borderTop: `1px solid ${neutral[300]}`,
        background: dialogGradients.footer,
        gap: 8,
        '& > :not(:first-of-type)': {
          marginLeft: 0,
        },
      },
      spacing: {
        '& > :not(:first-of-type)': {
          marginLeft: 0,
        },
      },
    },
  },

  // Modal backdrop (for non-dialog modals)
  MuiModal: {
    styleOverrides: {
      backdrop: {
        backgroundColor: 'rgba(26, 35, 50, 0.4)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
      },
    },
  },
};

export default dialogOverrides;
