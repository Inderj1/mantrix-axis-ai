/**
 * MultiSelectFilter - Multi-value dimension filter for dashboard widgets
 *
 * Features:
 * - Search/filter values
 * - Select all / clear all
 * - Show selected count
 * - Publishes to filter event bus for cross-chart filtering
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Checkbox,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Button,
  IconButton,
  Chip,
  Popover,
  InputAdornment,
  CircularProgress,
  Badge
} from '@mui/material';
import {
  Search as SearchIcon,
  Close as CloseIcon,
  FilterList as FilterIcon,
  CheckBox as CheckBoxIcon,
  CheckBoxOutlineBlank as CheckBoxOutlineBlankIcon,
  IndeterminateCheckBox as IndeterminateCheckBoxIcon
} from '@mui/icons-material';
import { useFilterBus } from '../../../stores/filterEventBus';

const MultiSelectFilter = ({
  dimension,
  title,
  values = [],
  isLoading = false,
  compact = false,
  maxHeight = 300,
  onFilterChange,
  fetchValues
}) => {
  const { publishFilter, clearFilter, activeFilters } = useFilterBus();

  const [anchorEl, setAnchorEl] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedValues, setSelectedValues] = useState(new Set());
  const [localValues, setLocalValues] = useState(values);
  const [loading, setLoading] = useState(isLoading);

  // Initialize from active filters
  useEffect(() => {
    const existing = activeFilters[dimension];
    if (existing?.type === 'multiSelect' && existing.value) {
      setSelectedValues(new Set(existing.value));
    }
  }, [dimension]);

  // Update local values when prop changes
  useEffect(() => {
    setLocalValues(values);
  }, [values]);

  // Fetch values on open if fetcher provided
  useEffect(() => {
    if (anchorEl && fetchValues && localValues.length === 0) {
      setLoading(true);
      fetchValues(dimension)
        .then((data) => {
          setLocalValues(data);
        })
        .catch((err) => {
          console.error('Failed to fetch filter values:', err);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [anchorEl, fetchValues, dimension, localValues.length]);

  // Filter values based on search
  const filteredValues = useMemo(() => {
    if (!searchTerm) return localValues;
    const term = searchTerm.toLowerCase();
    return localValues.filter((v) =>
      String(v).toLowerCase().includes(term)
    );
  }, [localValues, searchTerm]);

  // Handle value toggle
  const handleToggle = (value) => {
    const newSelected = new Set(selectedValues);
    if (newSelected.has(value)) {
      newSelected.delete(value);
    } else {
      newSelected.add(value);
    }
    setSelectedValues(newSelected);
  };

  // Handle select all (filtered)
  const handleSelectAll = () => {
    const newSelected = new Set(selectedValues);
    filteredValues.forEach((v) => newSelected.add(v));
    setSelectedValues(newSelected);
  };

  // Handle clear all (filtered)
  const handleClearAll = () => {
    if (searchTerm) {
      // Only clear filtered values
      const newSelected = new Set(selectedValues);
      filteredValues.forEach((v) => newSelected.delete(v));
      setSelectedValues(newSelected);
    } else {
      setSelectedValues(new Set());
    }
  };

  // Apply filter
  const handleApply = () => {
    const valuesArray = Array.from(selectedValues);

    if (valuesArray.length === 0) {
      clearFilter(dimension);
      if (onFilterChange) {
        onFilterChange(null);
      }
    } else {
      const filterValue = {
        type: 'multiSelect',
        value: valuesArray,
        label: valuesArray.length === 1
          ? String(valuesArray[0])
          : `${valuesArray.length} selected`
      };
      publishFilter(dimension, filterValue);

      if (onFilterChange) {
        onFilterChange(filterValue);
      }
    }

    setAnchorEl(null);
  };

  // Handle clear
  const handleClear = () => {
    setSelectedValues(new Set());
    clearFilter(dimension);

    if (onFilterChange) {
      onFilterChange(null);
    }
  };

  // Get display label
  const getDisplayLabel = () => {
    if (selectedValues.size === 0) return `Select ${title || dimension}`;
    if (selectedValues.size === 1) return String(Array.from(selectedValues)[0]);
    return `${selectedValues.size} selected`;
  };

  const hasFilter = selectedValues.size > 0;
  const open = Boolean(anchorEl);

  // Determine checkbox state for select all
  const allFilteredSelected = filteredValues.every((v) => selectedValues.has(v));
  const someFilteredSelected = filteredValues.some((v) => selectedValues.has(v));

  // Compact mode - just a chip
  if (compact) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Badge
          badgeContent={hasFilter ? selectedValues.size : 0}
          color="primary"
          invisible={!hasFilter}
        >
          <Chip
            icon={<FilterIcon />}
            label={title || dimension}
            onClick={(e) => setAnchorEl(e.currentTarget)}
            onDelete={hasFilter ? handleClear : undefined}
            color={hasFilter ? 'primary' : 'default'}
            variant={hasFilter ? 'filled' : 'outlined'}
            sx={{ cursor: 'pointer' }}
          />
        </Badge>

        <Popover
          open={open}
          anchorEl={anchorEl}
          onClose={() => setAnchorEl(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        >
          <FilterContent
            title={title}
            dimension={dimension}
            loading={loading}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            filteredValues={filteredValues}
            selectedValues={selectedValues}
            handleToggle={handleToggle}
            handleSelectAll={handleSelectAll}
            handleClearAll={handleClearAll}
            handleApply={handleApply}
            maxHeight={maxHeight}
            allFilteredSelected={allFilteredSelected}
            someFilteredSelected={someFilteredSelected}
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
          <FilterIcon color="primary" />
          <Typography variant="subtitle1" fontWeight={600}>
            {title || dimension}
          </Typography>
          {hasFilter && (
            <Chip
              label={selectedValues.size}
              size="small"
              color="primary"
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
          )}
        </Box>
        {hasFilter && (
          <IconButton size="small" onClick={handleClear}>
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
      </Box>

      {/* Search */}
      <TextField
        size="small"
        fullWidth
        placeholder={`Search ${title || dimension}...`}
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
          endAdornment: searchTerm && (
            <InputAdornment position="end">
              <IconButton size="small" onClick={() => setSearchTerm('')}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          )
        }}
        sx={{ mb: 1 }}
      />

      {/* Select All / Clear All */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Button
          size="small"
          onClick={handleSelectAll}
          disabled={allFilteredSelected}
          sx={{ fontSize: '0.75rem', textTransform: 'none' }}
        >
          Select All
        </Button>
        <Button
          size="small"
          onClick={handleClearAll}
          disabled={!someFilteredSelected}
          sx={{ fontSize: '0.75rem', textTransform: 'none' }}
        >
          Clear All
        </Button>
      </Box>

      {/* Values List */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
          <CircularProgress size={24} />
        </Box>
      ) : (
        <List
          dense
          sx={{
            maxHeight,
            overflow: 'auto',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            bgcolor: 'background.default'
          }}
        >
          {filteredValues.length === 0 ? (
            <ListItem>
              <ListItemText
                primary="No values found"
                primaryTypographyProps={{
                  color: 'text.secondary',
                  fontSize: '0.85rem',
                  textAlign: 'center'
                }}
              />
            </ListItem>
          ) : (
            filteredValues.map((value) => (
              <ListItem key={value} disablePadding>
                <ListItemButton
                  dense
                  onClick={() => handleToggle(value)}
                  sx={{ py: 0.5 }}
                >
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <Checkbox
                      edge="start"
                      checked={selectedValues.has(value)}
                      tabIndex={-1}
                      disableRipple
                      size="small"
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={String(value)}
                    primaryTypographyProps={{
                      fontSize: '0.85rem',
                      noWrap: true
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))
          )}
        </List>
      )}

      {/* Apply Button */}
      <Button
        variant="contained"
        size="small"
        fullWidth
        onClick={handleApply}
        sx={{ mt: 1.5 }}
      >
        Apply Filter
      </Button>
    </Paper>
  );
};

// Filter content for popover
const FilterContent = ({
  title,
  dimension,
  loading,
  searchTerm,
  setSearchTerm,
  filteredValues,
  selectedValues,
  handleToggle,
  handleSelectAll,
  handleClearAll,
  handleApply,
  maxHeight,
  allFilteredSelected,
  someFilteredSelected
}) => (
  <Box sx={{ p: 2, width: 280 }}>
    <Typography variant="subtitle2" gutterBottom>
      {title || dimension}
    </Typography>

    {/* Search */}
    <TextField
      size="small"
      fullWidth
      placeholder="Search..."
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon fontSize="small" />
          </InputAdornment>
        )
      }}
      sx={{ mb: 1 }}
    />

    {/* Select All / Clear */}
    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
      <Button
        size="small"
        onClick={handleSelectAll}
        disabled={allFilteredSelected}
        sx={{ fontSize: '0.7rem', textTransform: 'none', p: 0.5 }}
      >
        Select All
      </Button>
      <Button
        size="small"
        onClick={handleClearAll}
        disabled={!someFilteredSelected}
        sx={{ fontSize: '0.7rem', textTransform: 'none', p: 0.5 }}
      >
        Clear
      </Button>
    </Box>

    {/* Values */}
    {loading ? (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={20} />
      </Box>
    ) : (
      <List
        dense
        sx={{
          maxHeight: maxHeight - 60,
          overflow: 'auto',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1
        }}
      >
        {filteredValues.map((value) => (
          <ListItem key={value} disablePadding>
            <ListItemButton dense onClick={() => handleToggle(value)} sx={{ py: 0.25 }}>
              <ListItemIcon sx={{ minWidth: 28 }}>
                <Checkbox
                  edge="start"
                  checked={selectedValues.has(value)}
                  size="small"
                  sx={{ p: 0.25 }}
                />
              </ListItemIcon>
              <ListItemText
                primary={String(value)}
                primaryTypographyProps={{ fontSize: '0.8rem', noWrap: true }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    )}

    <Button
      variant="contained"
      size="small"
      fullWidth
      onClick={handleApply}
      sx={{ mt: 1.5 }}
    >
      Apply
    </Button>
  </Box>
);

export default MultiSelectFilter;
