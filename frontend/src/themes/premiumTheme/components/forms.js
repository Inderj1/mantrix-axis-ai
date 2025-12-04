/**
 * Form Component Overrides
 * Premium form styling with focus glow and refined borders
 */

import { neutral, primary, semantic } from '../tokens/colors';
import { shadowTokens } from '../tokens/shadows';
import { transitionTokens } from '../tokens/transitions';
import { radii } from '../tokens';

export const formOverrides = {
  MuiTextField: {
    defaultProps: {
      variant: 'outlined',
      size: 'medium',
    },
    styleOverrides: {
      root: {
        '& .MuiOutlinedInput-root': {
          borderRadius: radii.input,
          backgroundColor: '#FFFFFF',
          transition: transitionTokens.preset.input,

          '& fieldset': {
            borderColor: neutral[400],
            borderWidth: 1,
            transition: transitionTokens.preset.input,
          },

          '&:hover fieldset': {
            borderColor: primary[400],
          },

          '&.Mui-focused fieldset': {
            borderColor: primary[500],
            borderWidth: 2,
            boxShadow: '0 0 0 3px rgba(10, 110, 209, 0.1)',
          },

          '&.Mui-error fieldset': {
            borderColor: semantic.error.main,
            boxShadow: '0 0 0 3px rgba(187, 0, 0, 0.1)',
          },

          '&.Mui-disabled': {
            backgroundColor: neutral[100],
            '& fieldset': {
              borderColor: neutral[300],
            },
          },
        },

        '& .MuiInputBase-input': {
          padding: '12px 14px',
          fontSize: '0.9375rem',
          '&::placeholder': {
            color: neutral[500],
            opacity: 1,
          },
        },
      },
    },
  },

  MuiInputLabel: {
    styleOverrides: {
      root: {
        color: neutral[600],
        fontSize: '0.875rem',
        fontWeight: 500,
        '&.Mui-focused': {
          color: primary[500],
          fontWeight: 600,
        },
        '&.Mui-error': {
          color: semantic.error.main,
        },
        '&.Mui-disabled': {
          color: neutral[500],
        },
      },
      outlined: {
        transform: 'translate(14px, 14px) scale(1)',
        '&.MuiInputLabel-shrink': {
          transform: 'translate(14px, -9px) scale(0.75)',
          backgroundColor: '#FFFFFF',
          padding: '0 4px',
        },
      },
    },
  },

  MuiSelect: {
    defaultProps: {
      variant: 'outlined',
    },
    styleOverrides: {
      root: {
        borderRadius: radii.input,
      },
      select: {
        padding: '12px 14px',
        paddingRight: '32px !important',
        fontSize: '0.9375rem',
        '&:focus': {
          backgroundColor: 'transparent',
        },
      },
      icon: {
        color: neutral[600],
        right: 12,
        transition: transitionTokens.preset.iconRotate,
      },
      iconOpen: {
        transform: 'rotate(180deg)',
      },
    },
  },

  MuiMenu: {
    styleOverrides: {
      paper: {
        borderRadius: radii.lg,
        marginTop: 4,
        boxShadow: shadowTokens.standard.xl,
        border: `1px solid ${neutral[300]}`,
      },
      list: {
        padding: 8,
      },
    },
  },

  MuiMenuItem: {
    styleOverrides: {
      root: {
        borderRadius: radii.md,
        margin: '2px 0',
        padding: '10px 12px',
        fontSize: '0.9375rem',
        transition: transitionTokens.preset.color,
        '&:hover': {
          backgroundColor: `${primary[50]}`,
        },
        '&.Mui-selected': {
          backgroundColor: `${primary[50]}`,
          fontWeight: 500,
          '&:hover': {
            backgroundColor: `${primary[100]}`,
          },
        },
        '&.Mui-focusVisible': {
          backgroundColor: `${primary[50]}`,
        },
      },
    },
  },

  MuiFormHelperText: {
    styleOverrides: {
      root: {
        fontSize: '0.75rem',
        marginTop: 6,
        marginLeft: 2,
        color: neutral[600],
        '&.Mui-error': {
          color: semantic.error.main,
        },
      },
    },
  },

  MuiFormControlLabel: {
    styleOverrides: {
      root: {
        marginLeft: -8,
        '& .MuiTypography-root': {
          fontSize: '0.9375rem',
          color: neutral[800],
        },
      },
    },
  },

  MuiSwitch: {
    styleOverrides: {
      root: {
        width: 48,
        height: 28,
        padding: 0,
      },
      switchBase: {
        padding: 2,
        transition: transitionTokens.preset.transform,
        '&.Mui-checked': {
          transform: 'translateX(20px)',
          '& + .MuiSwitch-track': {
            backgroundColor: primary[500],
            opacity: 1,
          },
          '& .MuiSwitch-thumb': {
            backgroundColor: '#FFFFFF',
          },
        },
        '&.Mui-disabled': {
          '& + .MuiSwitch-track': {
            opacity: 0.5,
          },
        },
      },
      thumb: {
        width: 24,
        height: 24,
        boxShadow: shadowTokens.standard.sm,
        backgroundColor: '#FFFFFF',
      },
      track: {
        borderRadius: 14,
        backgroundColor: neutral[400],
        opacity: 1,
        transition: transitionTokens.preset.color,
      },
    },
  },

  MuiCheckbox: {
    styleOverrides: {
      root: {
        padding: 8,
        color: neutral[500],
        transition: transitionTokens.preset.color,
        '&:hover': {
          backgroundColor: `${primary[50]}`,
        },
        '&.Mui-checked': {
          color: primary[500],
        },
        '&.Mui-disabled': {
          color: neutral[400],
        },
      },
    },
  },

  MuiRadio: {
    styleOverrides: {
      root: {
        padding: 8,
        color: neutral[500],
        transition: transitionTokens.preset.color,
        '&:hover': {
          backgroundColor: `${primary[50]}`,
        },
        '&.Mui-checked': {
          color: primary[500],
        },
      },
    },
  },

  MuiAccordion: {
    styleOverrides: {
      root: {
        borderRadius: `${radii.lg}px !important`,
        border: `1px solid ${neutral[300]}`,
        boxShadow: 'none',
        overflow: 'hidden',

        '&:before': {
          display: 'none',
        },

        '&.Mui-expanded': {
          margin: 0,
          boxShadow: shadowTokens.standard.md,
        },

        '& + .MuiAccordion-root': {
          marginTop: 8,
        },
      },
    },
  },

  MuiAccordionSummary: {
    styleOverrides: {
      root: {
        minHeight: 56,
        padding: '0 20px',
        backgroundColor: neutral[50],
        borderBottom: '1px solid transparent',
        transition: transitionTokens.preset.color,

        '&:hover': {
          backgroundColor: neutral[200],
        },

        '&.Mui-expanded': {
          minHeight: 56,
          backgroundColor: '#FFFFFF',
          borderBottom: `1px solid ${neutral[300]}`,
        },
      },
      content: {
        margin: '16px 0',
        '&.Mui-expanded': {
          margin: '16px 0',
        },
      },
      expandIconWrapper: {
        color: neutral[600],
        transition: transitionTokens.preset.iconRotate,
        '&.Mui-expanded': {
          transform: 'rotate(180deg)',
        },
      },
    },
  },

  MuiAccordionDetails: {
    styleOverrides: {
      root: {
        padding: '20px',
        backgroundColor: '#FFFFFF',
      },
    },
  },

  MuiAutocomplete: {
    styleOverrides: {
      paper: {
        borderRadius: radii.lg,
        boxShadow: shadowTokens.standard.xl,
        border: `1px solid ${neutral[300]}`,
      },
      listbox: {
        padding: 8,
      },
      option: {
        borderRadius: radii.md,
        margin: '2px 8px',
        padding: '10px 12px',
        '&:hover': {
          backgroundColor: `${primary[50]}`,
        },
        '&[aria-selected="true"]': {
          backgroundColor: `${primary[50]}`,
        },
      },
    },
  },
};

export default formOverrides;
