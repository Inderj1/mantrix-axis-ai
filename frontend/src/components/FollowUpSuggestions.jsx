import React from 'react';
import { Box, Chip, Stack, Typography, Paper } from '@mui/material';
import { TipsAndUpdates as LightbulbIcon } from '@mui/icons-material';

/**
 * FollowUpSuggestions Component
 *
 * Displays clickable follow-up suggestion chips for copilot functionality.
 * Performance-optimized to render without causing layout shift.
 */
const FollowUpSuggestions = ({ suggestions = [], onSuggestionClick, loading = false }) => {
  // Don't render if no suggestions and not loading
  if (!loading && (!suggestions || suggestions.length === 0)) {
    return null;
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        bgcolor: '#F8FAFB',
        borderRadius: 2,
        border: '1px solid #E5E7EB',
        mt: 2
      }}
    >
      <Stack spacing={1.5}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LightbulbIcon sx={{ fontSize: 18, color: '#6A6D70' }} />
          <Typography
            variant="caption"
            sx={{
              color: '#6A6D70',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}
          >
            Follow-up Questions
          </Typography>
        </Box>

        {/* Suggestion Chips */}
        <Stack
          direction="row"
          spacing={1}
          sx={{
            flexWrap: 'wrap',
            gap: 1
          }}
        >
          {loading ? (
            // Loading state
            <>
              {[1, 2, 3].map((i) => (
                <Chip
                  key={i}
                  label="Loading..."
                  size="small"
                  disabled
                  sx={{
                    bgcolor: '#fff',
                    border: '1px solid #E5E7EB',
                    '&.Mui-disabled': {
                      opacity: 0.6
                    }
                  }}
                />
              ))}
            </>
          ) : (
            suggestions.map((suggestion, index) => (
              <Chip
                key={index}
                label={suggestion}
                onClick={() => onSuggestionClick && onSuggestionClick(suggestion)}
                clickable
                size="small"
                sx={{
                  bgcolor: '#fff',
                  border: '1px solid #E5E7EB',
                  color: '#1A2332',
                  fontWeight: 500,
                  fontSize: '0.8125rem',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: '#0066CC',
                    color: '#fff',
                    borderColor: '#0066CC',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 2px 4px rgba(0,102,204,0.2)'
                  },
                  '&:active': {
                    transform: 'translateY(0)',
                    boxShadow: '0 1px 2px rgba(0,102,204,0.15)'
                  }
                }}
              />
            ))
          )}
        </Stack>

        {/* Helper text */}
        {!loading && suggestions.length > 0 && (
          <Typography
            variant="caption"
            sx={{
              color: '#9CA3AF',
              fontSize: '0.75rem',
              mt: 0.5
            }}
          >
            Click any suggestion to explore further
          </Typography>
        )}
      </Stack>
    </Paper>
  );
};

export default FollowUpSuggestions;
