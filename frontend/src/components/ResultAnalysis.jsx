import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  Button,
  IconButton,
  Tooltip,
  Grid,
  Skeleton,
  useTheme,
  alpha,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  CheckCircleOutline as InsightCheckIcon,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  LightbulbOutlined as RecommendationIcon,
  HelpOutline as QuestionIcon,
  ArrowForward as ArrowIcon,
  InfoOutlined as InfoIcon,
} from '@mui/icons-material';

// Loading skeleton component
const LoadingSkeleton = () => {
  const theme = useTheme();

  return (
    <Box>
      {/* Header skeleton */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <Skeleton variant="circular" width={36} height={36} />
        <Box sx={{ flex: 1 }}>
          <Skeleton variant="text" width={120} height={28} />
          <Skeleton variant="text" width={100} height={16} />
        </Box>
        <Skeleton variant="rounded" width={80} height={32} />
      </Box>

      {/* Summary card skeleton */}
      <Skeleton
        variant="rectangular"
        height={100}
        sx={{ borderRadius: 2, mb: 3 }}
      />

      {/* Two-column grid skeleton */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Skeleton variant="rectangular" height={180} sx={{ borderRadius: 2 }} />
        </Grid>
        <Grid item xs={12} md={6}>
          <Skeleton variant="rectangular" height={180} sx={{ borderRadius: 2 }} />
        </Grid>
      </Grid>

      {/* Recommendations skeleton */}
      <Skeleton
        variant="rectangular"
        height={120}
        sx={{ borderRadius: 2, mb: 3 }}
      />

      {/* Questions skeleton */}
      <Box>
        <Skeleton variant="text" width={140} height={20} sx={{ mb: 2 }} />
        <Stack spacing={1.5}>
          {[1, 2, 3].map((i) => (
            <Skeleton
              key={i}
              variant="rectangular"
              height={52}
              sx={{ borderRadius: 2 }}
            />
          ))}
        </Stack>
      </Box>
    </Box>
  );
};

// Section card component
const SectionCard = ({
  title,
  icon: Icon,
  accentColor,
  items,
  itemIcon: ItemIcon,
  renderItemIcon,
  sectionId,
  onCopy,
  copied,
  numbered = false,
}) => {
  const theme = useTheme();

  if (!items || items.length === 0) return null;

  const formatListForCopy = (list) => list.map((item, i) => `${i + 1}. ${item}`).join('\n');

  return (
    <Paper
      elevation={0}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 2,
        border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
          backgroundColor: alpha(accentColor, 0.04),
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          <Icon sx={{ color: accentColor, fontSize: 18 }} />
          <Typography
            variant="overline"
            sx={{
              color: theme.palette.text.secondary,
              letterSpacing: '0.08em',
              fontWeight: 600,
            }}
          >
            {title}
          </Typography>
          <Chip
            label={items.length}
            size="small"
            sx={{
              height: 20,
              fontSize: '0.7rem',
              fontWeight: 600,
              backgroundColor: alpha(accentColor, 0.1),
              color: accentColor,
            }}
          />
        </Stack>
        <Tooltip title={copied ? 'Copied!' : 'Copy to clipboard'}>
          <IconButton
            size="small"
            onClick={() => onCopy(formatListForCopy(items), sectionId)}
          >
            {copied ? (
              <CheckIcon sx={{ fontSize: 16, color: theme.palette.success.main }} />
            ) : (
              <CopyIcon sx={{ fontSize: 16, color: theme.palette.text.disabled }} />
            )}
          </IconButton>
        </Tooltip>
      </Box>

      {/* Content */}
      <Box sx={{ p: 2, flex: 1 }}>
        <List dense disablePadding>
          {items.map((item, index) => (
            <ListItem key={index} disablePadding sx={{ py: 0.75, alignItems: 'flex-start' }}>
              <ListItemIcon sx={{ minWidth: 28, mt: 0.25 }}>
                {numbered ? (
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: accentColor,
                      width: 20,
                      textAlign: 'center',
                    }}
                  >
                    {index + 1}.
                  </Typography>
                ) : renderItemIcon ? (
                  renderItemIcon(item, index)
                ) : (
                  <ItemIcon sx={{ fontSize: 16, color: accentColor }} />
                )}
              </ListItemIcon>
              <ListItemText
                primary={item}
                primaryTypographyProps={{
                  variant: 'body2',
                  sx: { lineHeight: 1.6, color: theme.palette.text.primary },
                }}
              />
            </ListItem>
          ))}
        </List>
      </Box>
    </Paper>
  );
};

// Follow-up question button
const FollowUpQuestionButton = ({ question, onClick, index }) => {
  const theme = useTheme();

  return (
    <Paper
      onClick={() => onClick(question)}
      elevation={0}
      sx={{
        p: 2,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        cursor: 'pointer',
        borderRadius: 2,
        border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
        backgroundColor: theme.palette.background.paper,
        transition: 'all 0.2s ease',
        '&:hover': {
          borderColor: theme.palette.primary.main,
          backgroundColor: alpha(theme.palette.primary.main, 0.04),
          transform: 'translateX(4px)',
          '& .arrow-icon': {
            transform: 'translateX(4px)',
            color: theme.palette.primary.main,
          },
        },
      }}
      role="button"
      tabIndex={0}
      onKeyPress={(e) => e.key === 'Enter' && onClick(question)}
    >
      <QuestionIcon
        sx={{
          color: theme.palette.primary.main,
          fontSize: 20,
          flexShrink: 0,
        }}
      />
      <Typography
        variant="body2"
        sx={{
          flex: 1,
          color: theme.palette.text.primary,
          fontWeight: 500,
          lineHeight: 1.5,
        }}
      >
        {question}
      </Typography>
      <ArrowIcon
        className="arrow-icon"
        sx={{
          color: theme.palette.text.disabled,
          fontSize: 18,
          transition: 'all 0.2s ease',
          flexShrink: 0,
        }}
      />
    </Paper>
  );
};

// Get trend icon based on text content
const getTrendIcon = (trendText, theme) => {
  const text = trendText.toLowerCase();

  if (text.includes('increase') || text.includes('growth') || text.includes('up') ||
      text.includes('rising') || text.includes('improve') || text.includes('higher')) {
    return <TrendingUp sx={{ fontSize: 16, color: theme.palette.success.main }} />;
  }

  if (text.includes('decrease') || text.includes('decline') || text.includes('down') ||
      text.includes('falling') || text.includes('drop') || text.includes('lower')) {
    return <TrendingDown sx={{ fontSize: 16, color: theme.palette.error.main }} />;
  }

  return <TrendingFlat sx={{ fontSize: 16, color: theme.palette.info.main }} />;
};

const ResultAnalysis = ({ analysis, loading, onFollowUpClick }) => {
  const theme = useTheme();
  const [copiedSection, setCopiedSection] = useState(null);

  const handleCopy = async (text, sectionId) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(sectionId);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const copyAllInsights = () => {
    const sections = [];

    if (analysis.summary) {
      sections.push('## Executive Summary\n' + analysis.summary);
    }
    if (analysis.key_insights?.length) {
      sections.push('## Key Insights\n' + analysis.key_insights.map((item, i) => `${i + 1}. ${item}`).join('\n'));
    }
    if (analysis.trends?.length) {
      sections.push('## Trends\n' + analysis.trends.map((item, i) => `${i + 1}. ${item}`).join('\n'));
    }
    if (analysis.recommendations?.length) {
      sections.push('## Recommendations\n' + analysis.recommendations.map((item, i) => `${i + 1}. ${item}`).join('\n'));
    }

    handleCopy(sections.join('\n\n'), 'all');
  };

  // Loading state
  if (loading) {
    return <LoadingSkeleton />;
  }

  // Empty state
  if (!analysis) {
    return null;
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: '10px',
              bgcolor: theme.palette.primary.main,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <AIIcon sx={{ color: 'white', fontSize: 20 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600, color: theme.palette.text.primary }}>
              AI Insights
            </Typography>
            <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
              Generated just now
            </Typography>
          </Box>
        </Stack>
        <Button
          size="small"
          variant="outlined"
          startIcon={copiedSection === 'all' ? <CheckIcon /> : <CopyIcon />}
          onClick={copyAllInsights}
          sx={{ textTransform: 'none', borderRadius: 2 }}
        >
          {copiedSection === 'all' ? 'Copied!' : 'Copy All'}
        </Button>
      </Box>

      {/* Executive Summary */}
      {analysis.summary && (
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 3,
            borderRadius: 2,
            borderLeft: `4px solid ${theme.palette.primary.main}`,
            border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
            borderLeftWidth: 4,
            borderLeftColor: theme.palette.primary.main,
            backgroundColor: alpha(theme.palette.primary.main, 0.02),
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
            <Typography
              variant="overline"
              sx={{
                color: theme.palette.text.secondary,
                letterSpacing: '0.08em',
                fontWeight: 600,
              }}
            >
              Executive Summary
            </Typography>
            <Tooltip title={copiedSection === 'summary' ? 'Copied!' : 'Copy'}>
              <IconButton size="small" onClick={() => handleCopy(analysis.summary, 'summary')}>
                {copiedSection === 'summary' ? (
                  <CheckIcon sx={{ fontSize: 16, color: theme.palette.success.main }} />
                ) : (
                  <CopyIcon sx={{ fontSize: 16, color: theme.palette.text.disabled }} />
                )}
              </IconButton>
            </Tooltip>
          </Box>
          <Typography variant="body1" sx={{ lineHeight: 1.7, color: theme.palette.text.primary }}>
            {analysis.summary}
          </Typography>
        </Paper>
      )}

      {/* Key Insights & Trends - Two Column Grid */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {analysis.key_insights?.length > 0 && (
          <Grid item xs={12} md={6}>
            <SectionCard
              title="Key Insights"
              icon={InsightCheckIcon}
              accentColor={theme.palette.success.main}
              items={analysis.key_insights}
              itemIcon={InsightCheckIcon}
              sectionId="insights"
              onCopy={handleCopy}
              copied={copiedSection === 'insights'}
            />
          </Grid>
        )}
        {analysis.trends?.length > 0 && (
          <Grid item xs={12} md={6}>
            <SectionCard
              title="Trends & Patterns"
              icon={TrendingUp}
              accentColor={theme.palette.info.main}
              items={analysis.trends}
              renderItemIcon={(item) => getTrendIcon(item, theme)}
              sectionId="trends"
              onCopy={handleCopy}
              copied={copiedSection === 'trends'}
            />
          </Grid>
        )}
      </Grid>

      {/* Recommendations */}
      {analysis.recommendations?.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <SectionCard
            title="Recommendations"
            icon={RecommendationIcon}
            accentColor={theme.palette.warning.main}
            items={analysis.recommendations}
            numbered
            sectionId="recommendations"
            onCopy={handleCopy}
            copied={copiedSection === 'recommendations'}
          />
        </Box>
      )}

      {/* Follow-up Questions */}
      {analysis.follow_up_questions?.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="overline"
            sx={{
              display: 'block',
              mb: 2,
              color: theme.palette.text.secondary,
              letterSpacing: '0.08em',
              fontWeight: 600,
            }}
          >
            Explore Further
          </Typography>
          <Stack spacing={1.5}>
            {analysis.follow_up_questions.map((question, index) => (
              <FollowUpQuestionButton
                key={index}
                question={question}
                onClick={onFollowUpClick}
                index={index}
              />
            ))}
          </Stack>
        </Box>
      )}

      {/* Data Quality Notes */}
      {analysis.data_quality_notes?.length > 0 && (
        <Alert
          severity="info"
          icon={<InfoIcon />}
          sx={{
            borderRadius: 2,
            '& .MuiAlert-message': { width: '100%' },
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            Data Quality Notes
          </Typography>
          <List dense disablePadding>
            {analysis.data_quality_notes.map((note, index) => (
              <ListItem key={index} disablePadding sx={{ py: 0.25 }}>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                  {'\u2022'} {note}
                </Typography>
              </ListItem>
            ))}
          </List>
        </Alert>
      )}
    </Box>
  );
};

export default ResultAnalysis;
