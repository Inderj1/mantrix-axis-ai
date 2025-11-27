/**
 * ActiveFilterPills - Display active cross-chart filters as chips
 */
import React from 'react';
import { Stack, Chip, Button, Typography, Box } from '@mui/material';
import { FilterAlt as FilterIcon, Undo as UndoIcon, Redo as RedoIcon } from '@mui/icons-material';
import { useFilterBus, useCanUndo, useCanRedo } from '../../stores/filterEventBus';

const ActiveFilterPills = () => {
  const {
    activeFilters,
    clearFilter,
    clearAllFilters,
    undoFilter,
    redoFilter
  } = useFilterBus();

  const canUndo = useCanUndo();
  const canRedo = useCanRedo();

  const filterEntries = Object.entries(activeFilters);

  if (filterEntries.length === 0) {
    return null;
  }

  // Format filter value for display
  const formatValue = (value) => {
    if (typeof value === 'object' && value !== null) {
      if (value.start && value.end) {
        return `${value.start} - ${value.end}`;
      } else if (value.start) {
        return `>= ${value.start}`;
      } else if (value.end) {
        return `<= ${value.end}`;
      }
    }
    if (Array.isArray(value)) {
      return value.length > 2
        ? `${value.slice(0, 2).join(', ')}...`
        : value.join(', ');
    }
    return String(value);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        p: 1,
        backgroundColor: 'action.hover',
        borderRadius: 1
      }}
    >
      <FilterIcon fontSize="small" color="primary" />

      <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
        Active filters:
      </Typography>

      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
        {filterEntries.map(([dimension, value]) => (
          <Chip
            key={dimension}
            label={`${dimension}: ${formatValue(value)}`}
            size="small"
            color="primary"
            variant="outlined"
            onDelete={() => clearFilter(dimension)}
            sx={{ height: 24 }}
          />
        ))}
      </Stack>

      {/* Undo/Redo */}
      <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5 }}>
        <Button
          size="small"
          disabled={!canUndo}
          onClick={undoFilter}
          startIcon={<UndoIcon fontSize="small" />}
          sx={{ minWidth: 'auto', px: 1 }}
        >
          Undo
        </Button>
        <Button
          size="small"
          disabled={!canRedo}
          onClick={redoFilter}
          startIcon={<RedoIcon fontSize="small" />}
          sx={{ minWidth: 'auto', px: 1 }}
        >
          Redo
        </Button>
      </Box>

      {/* Clear all */}
      {filterEntries.length > 1 && (
        <Button
          size="small"
          color="secondary"
          onClick={clearAllFilters}
          sx={{ ml: 1 }}
        >
          Clear All
        </Button>
      )}
    </Box>
  );
};

export default ActiveFilterPills;
