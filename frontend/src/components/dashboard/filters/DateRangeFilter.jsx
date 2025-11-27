/**
 * DateRangeFilter - Date range filter for dashboard widgets
 *
 * Features:
 * - Quick presets (Today, Last 7 days, Last 30 days, etc.)
 * - Custom date range picker
 * - Publishes to filter event bus for cross-chart filtering
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  ButtonGroup,
  Popover,
  TextField,
  IconButton,
  Chip,
  Divider
} from '@mui/material';
import {
  DateRange as DateRangeIcon,
  Close as CloseIcon,
  Today as TodayIcon,
  CalendarMonth as CalendarIcon
} from '@mui/icons-material';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { useFilterBus } from '../../../stores/filterEventBus';

// Preset date ranges
const PRESETS = [
  { label: 'Today', value: 'today', getDates: () => ({ start: new Date(), end: new Date() }) },
  {
    label: 'Yesterday',
    value: 'yesterday',
    getDates: () => {
      const d = new Date();
      d.setDate(d.getDate() - 1);
      return { start: d, end: d };
    }
  },
  {
    label: 'Last 7 days',
    value: 'last7',
    getDates: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      return { start, end };
    }
  },
  {
    label: 'Last 30 days',
    value: 'last30',
    getDates: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 30);
      return { start, end };
    }
  },
  {
    label: 'This Month',
    value: 'thisMonth',
    getDates: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      return { start, end };
    }
  },
  {
    label: 'Last Month',
    value: 'lastMonth',
    getDates: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth(), 0);
      return { start, end };
    }
  },
  {
    label: 'This Quarter',
    value: 'thisQuarter',
    getDates: () => {
      const now = new Date();
      const quarter = Math.floor(now.getMonth() / 3);
      const start = new Date(now.getFullYear(), quarter * 3, 1);
      const end = new Date(now.getFullYear(), quarter * 3 + 3, 0);
      return { start, end };
    }
  },
  {
    label: 'This Year',
    value: 'thisYear',
    getDates: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), 0, 1);
      const end = new Date(now.getFullYear(), 11, 31);
      return { start, end };
    }
  },
  {
    label: 'Last Year',
    value: 'lastYear',
    getDates: () => {
      const now = new Date();
      const start = new Date(now.getFullYear() - 1, 0, 1);
      const end = new Date(now.getFullYear() - 1, 11, 31);
      return { start, end };
    }
  }
];

const DateRangeFilter = ({
  dimension = 'date',
  title = 'Date Range',
  compact = false,
  showPresets = true,
  initialPreset = null,
  onFilterChange
}) => {
  const { publishFilter, clearFilter, activeFilters } = useFilterBus();

  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState(initialPreset);
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [customMode, setCustomMode] = useState(false);

  // Restore filter from active filters on mount
  useEffect(() => {
    const existing = activeFilters[dimension];
    if (existing?.type === 'dateRange') {
      setStartDate(new Date(existing.value.start));
      setEndDate(new Date(existing.value.end));
      setSelectedPreset(existing.preset || null);
    }
  }, []);

  // Format date for display
  const formatDate = (date) => {
    if (!date) return '';
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Handle preset selection
  const handlePresetSelect = (preset) => {
    const dates = preset.getDates();
    setStartDate(dates.start);
    setEndDate(dates.end);
    setSelectedPreset(preset.value);
    setCustomMode(false);

    // Publish to filter bus
    const filterValue = {
      type: 'dateRange',
      preset: preset.value,
      value: {
        start: dates.start.toISOString(),
        end: dates.end.toISOString()
      },
      label: preset.label
    };
    publishFilter(dimension, filterValue);

    if (onFilterChange) {
      onFilterChange(filterValue);
    }

    setAnchorEl(null);
  };

  // Handle custom date apply
  const handleApplyCustom = () => {
    if (!startDate || !endDate) return;

    setSelectedPreset(null);

    const filterValue = {
      type: 'dateRange',
      preset: null,
      value: {
        start: startDate.toISOString(),
        end: endDate.toISOString()
      },
      label: `${formatDate(startDate)} - ${formatDate(endDate)}`
    };
    publishFilter(dimension, filterValue);

    if (onFilterChange) {
      onFilterChange(filterValue);
    }

    setAnchorEl(null);
  };

  // Handle clear
  const handleClear = () => {
    setStartDate(null);
    setEndDate(null);
    setSelectedPreset(null);
    clearFilter(dimension);

    if (onFilterChange) {
      onFilterChange(null);
    }
  };

  // Get current display label
  const getDisplayLabel = () => {
    if (selectedPreset) {
      const preset = PRESETS.find(p => p.value === selectedPreset);
      return preset?.label || selectedPreset;
    }
    if (startDate && endDate) {
      return `${formatDate(startDate)} - ${formatDate(endDate)}`;
    }
    return 'Select date range';
  };

  const hasFilter = startDate && endDate;
  const open = Boolean(anchorEl);

  // Compact mode - just a button
  if (compact) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Chip
          icon={<DateRangeIcon />}
          label={getDisplayLabel()}
          onClick={(e) => setAnchorEl(e.currentTarget)}
          onDelete={hasFilter ? handleClear : undefined}
          color={hasFilter ? 'primary' : 'default'}
          variant={hasFilter ? 'filled' : 'outlined'}
          sx={{ cursor: 'pointer' }}
        />

        <Popover
          open={open}
          anchorEl={anchorEl}
          onClose={() => setAnchorEl(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        >
          <FilterContent
            showPresets={showPresets}
            customMode={customMode}
            setCustomMode={setCustomMode}
            startDate={startDate}
            setStartDate={setStartDate}
            endDate={endDate}
            setEndDate={setEndDate}
            selectedPreset={selectedPreset}
            handlePresetSelect={handlePresetSelect}
            handleApplyCustom={handleApplyCustom}
          />
        </Popover>
      </Box>
    );
  }

  // Full mode - card with header
  return (
    <Paper
      elevation={1}
      sx={{
        p: 2,
        borderRadius: 2,
        border: hasFilter ? '2px solid' : '1px solid',
        borderColor: hasFilter ? 'primary.main' : 'divider'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CalendarIcon color="primary" />
          <Typography variant="subtitle1" fontWeight={600}>
            {title}
          </Typography>
        </Box>
        {hasFilter && (
          <IconButton size="small" onClick={handleClear}>
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
      </Box>

      {/* Quick Presets */}
      {showPresets && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Quick Select
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {PRESETS.slice(0, 6).map((preset) => (
              <Chip
                key={preset.value}
                label={preset.label}
                size="small"
                onClick={() => handlePresetSelect(preset)}
                color={selectedPreset === preset.value ? 'primary' : 'default'}
                variant={selectedPreset === preset.value ? 'filled' : 'outlined'}
                sx={{ fontSize: '0.75rem' }}
              />
            ))}
          </Box>
        </Box>
      )}

      <Divider sx={{ my: 1.5 }} />

      {/* Custom Date Range */}
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
        Custom Range
      </Typography>

      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
          <DatePicker
            label="Start Date"
            value={startDate}
            onChange={setStartDate}
            slotProps={{
              textField: {
                size: 'small',
                fullWidth: true,
                sx: { '& .MuiInputBase-input': { fontSize: '0.85rem' } }
              }
            }}
          />
          <DatePicker
            label="End Date"
            value={endDate}
            onChange={setEndDate}
            minDate={startDate}
            slotProps={{
              textField: {
                size: 'small',
                fullWidth: true,
                sx: { '& .MuiInputBase-input': { fontSize: '0.85rem' } }
              }
            }}
          />
        </Box>
      </LocalizationProvider>

      <Button
        variant="contained"
        size="small"
        fullWidth
        onClick={handleApplyCustom}
        disabled={!startDate || !endDate}
      >
        Apply Range
      </Button>
    </Paper>
  );
};

// Filter content for popover
const FilterContent = ({
  showPresets,
  customMode,
  setCustomMode,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  selectedPreset,
  handlePresetSelect,
  handleApplyCustom
}) => (
  <Box sx={{ p: 2, width: 320 }}>
    {showPresets && !customMode && (
      <>
        <Typography variant="subtitle2" gutterBottom>
          Quick Select
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
          {PRESETS.map((preset) => (
            <Button
              key={preset.value}
              size="small"
              variant={selectedPreset === preset.value ? 'contained' : 'text'}
              onClick={() => handlePresetSelect(preset)}
              sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
            >
              {preset.label}
            </Button>
          ))}
        </Box>
        <Divider sx={{ my: 1 }} />
        <Button
          size="small"
          fullWidth
          onClick={() => setCustomMode(true)}
          startIcon={<CalendarIcon />}
        >
          Custom Range
        </Button>
      </>
    )}

    {(!showPresets || customMode) && (
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {showPresets && (
            <Button
              size="small"
              onClick={() => setCustomMode(false)}
              sx={{ alignSelf: 'flex-start' }}
            >
              Back to Presets
            </Button>
          )}

          <DatePicker
            label="Start Date"
            value={startDate}
            onChange={setStartDate}
            slotProps={{ textField: { size: 'small', fullWidth: true } }}
          />
          <DatePicker
            label="End Date"
            value={endDate}
            onChange={setEndDate}
            minDate={startDate}
            slotProps={{ textField: { size: 'small', fullWidth: true } }}
          />

          <Button
            variant="contained"
            onClick={handleApplyCustom}
            disabled={!startDate || !endDate}
          >
            Apply
          </Button>
        </Box>
      </LocalizationProvider>
    )}
  </Box>
);

export default DateRangeFilter;
