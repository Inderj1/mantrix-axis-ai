import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Collapse,
  IconButton,
  useTheme,
  alpha,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Summarize as SummaryIcon,
  Lightbulb as InsightIcon,
  Storage as DataIcon,
  TrendingUp as TrendIcon,
} from '@mui/icons-material';

// Map section titles to icons
const getSectionIcon = (title) => {
  const titleLower = title.toLowerCase();
  if (titleLower.includes('summary') || titleLower.includes('overview')) return SummaryIcon;
  if (titleLower.includes('finding') || titleLower.includes('insight') || titleLower.includes('key')) return InsightIcon;
  if (titleLower.includes('data') || titleLower.includes('source') || titleLower.includes('table')) return DataIcon;
  if (titleLower.includes('trend') || titleLower.includes('analysis')) return TrendIcon;
  return null;
};

// Parse and format content
const formatContent = (content, theme) => {
  if (!content) return null;

  // Split by blank lines for paragraphs
  const paragraphs = content.split(/\n\n+/);
  const elements = [];

  paragraphs.forEach((para, pIdx) => {
    const lines = para.split('\n');

    lines.forEach((line, lIdx) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      // Check for headers
      const h1Match = trimmed.match(/^#\s+(.+)$/);
      const h2Match = trimmed.match(/^##\s+(.+)$/);
      const h3Match = trimmed.match(/^###\s+(.+)$/);
      const h4Match = trimmed.match(/^####\s+(.+)$/);

      // Check for list items
      const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/);
      const numberedMatch = trimmed.match(/^(\d+)[.)]\s+(.+)$/);

      if (h1Match || h2Match) {
        const title = h1Match ? h1Match[1] : h2Match[1];
        const Icon = getSectionIcon(title);
        elements.push(
          <Box
            key={`h-${pIdx}-${lIdx}`}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              mt: elements.length > 0 ? 3 : 0,
              mb: 1.5,
              pb: 1,
              borderBottom: `2px solid ${alpha(theme.palette.primary.main, 0.2)}`,
            }}
          >
            {Icon && (
              <Box
                sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '8px',
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Icon sx={{ fontSize: 16, color: theme.palette.primary.main }} />
              </Box>
            )}
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 600,
                color: theme.palette.text.primary,
                fontSize: '1rem',
              }}
            >
              {formatInlineStyles(title)}
            </Typography>
          </Box>
        );
      } else if (h3Match || h4Match) {
        const title = h3Match ? h3Match[1] : h4Match[1];
        elements.push(
          <Typography
            key={`h3-${pIdx}-${lIdx}`}
            variant="subtitle2"
            sx={{
              fontWeight: 600,
              color: theme.palette.text.primary,
              mt: 2,
              mb: 1,
              pl: 1,
              borderLeft: `3px solid ${theme.palette.primary.main}`,
            }}
          >
            {formatInlineStyles(title)}
          </Typography>
        );
      } else if (bulletMatch) {
        elements.push(
          <Box
            key={`bullet-${pIdx}-${lIdx}`}
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1.5,
              pl: 1,
              py: 0.5,
            }}
          >
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                bgcolor: theme.palette.primary.main,
                mt: 1,
                flexShrink: 0,
              }}
            />
            <Typography
              variant="body2"
              sx={{
                color: theme.palette.text.primary,
                lineHeight: 1.7,
              }}
            >
              {formatInlineStyles(bulletMatch[1])}
            </Typography>
          </Box>
        );
      } else if (numberedMatch) {
        elements.push(
          <Box
            key={`num-${pIdx}-${lIdx}`}
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1.5,
              pl: 1,
              py: 0.5,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                fontWeight: 600,
                color: theme.palette.primary.main,
                minWidth: 20,
              }}
            >
              {numberedMatch[1]}.
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: theme.palette.text.primary,
                lineHeight: 1.7,
              }}
            >
              {formatInlineStyles(numberedMatch[2])}
            </Typography>
          </Box>
        );
      } else {
        // Regular paragraph
        elements.push(
          <Typography
            key={`p-${pIdx}-${lIdx}`}
            variant="body2"
            sx={{
              color: theme.palette.text.primary,
              lineHeight: 1.8,
              mb: 1,
            }}
          >
            {formatInlineStyles(trimmed)}
          </Typography>
        );
      }
    });
  });

  return elements;
};

// Format inline styles (bold, numbers, etc.)
const formatInlineStyles = (text) => {
  if (!text) return text;

  // Split by bold markers and process
  const parts = [];
  let remaining = text;
  let key = 0;

  // Process **bold** and *italic*
  const boldRegex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = boldRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <span key={key++}>{text.slice(lastIndex, match.index)}</span>
      );
    }
    parts.push(
      <strong key={key++} style={{ fontWeight: 600 }}>
        {match[1]}
      </strong>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(<span key={key++}>{text.slice(lastIndex)}</span>);
  }

  return parts.length > 0 ? parts : text;
};

const AIExplanation = ({ content, maxHeight = 400, collapsible = true }) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(true);

  const formattedContent = useMemo(
    () => formatContent(content, theme),
    [content, theme]
  );

  if (!content) return null;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 2,
        bgcolor: alpha(theme.palette.background.paper, 0.6),
        border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
        mb: 3,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: expanded ? 2 : 0,
          cursor: collapsible ? 'pointer' : 'default',
        }}
        onClick={() => collapsible && setExpanded(!expanded)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: '10px',
              bgcolor: theme.palette.primary.main,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <AIIcon sx={{ color: 'white', fontSize: 18 }} />
          </Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            AI Analysis
          </Typography>
        </Box>
        {collapsible && (
          <IconButton size="small">
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        )}
      </Box>

      {/* Content */}
      <Collapse in={expanded}>
        <Box
          sx={{
            maxHeight: maxHeight,
            overflow: 'auto',
            pr: 1,
            '&::-webkit-scrollbar': {
              width: 6,
            },
            '&::-webkit-scrollbar-thumb': {
              bgcolor: alpha(theme.palette.text.secondary, 0.2),
              borderRadius: 3,
            },
          }}
        >
          {formattedContent}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default AIExplanation;
