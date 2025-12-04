/**
 * Component Overrides Index
 * Centralized export for all MUI component overrides
 */

export { dialogOverrides } from './dialogs';
export { formOverrides } from './forms';
export { tableOverrides } from './tables';
export { cardOverrides, cardPresets } from './cards';
export { buttonOverrides } from './buttons';
export { navigationOverrides } from './navigation';
export { feedbackOverrides } from './feedback';

// Combined overrides for easy importing
import { dialogOverrides } from './dialogs';
import { formOverrides } from './forms';
import { tableOverrides } from './tables';
import { cardOverrides } from './cards';
import { buttonOverrides } from './buttons';
import { navigationOverrides } from './navigation';
import { feedbackOverrides } from './feedback';

export const allComponentOverrides = {
  ...dialogOverrides,
  ...formOverrides,
  ...tableOverrides,
  ...cardOverrides,
  ...buttonOverrides,
  ...navigationOverrides,
  ...feedbackOverrides,
};
