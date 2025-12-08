import React from 'react';
import {
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  LinearProgress,
  Paper,
  Collapse,
  IconButton,
  Chip,
  useTheme,
  alpha,
  Fade,
  Skeleton,
  Button,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as PendingIcon,
  AutoAwesome as AIIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Code as CodeIcon,
  Lightbulb as TipIcon,
  Psychology as ThinkingIcon,
  Schema as SchemaIcon,
  EditNote as WriteIcon,
  PlayArrow as ExecuteIcon,
  DataObject as DataIcon,
  Verified as ValidateIcon,
  QuestionAnswer as ContextIcon,
  HourglassTop as LongRunningIcon,
  Notifications as NotificationsIcon,
  NotificationsActive as NotificationsActiveIcon,
} from '@mui/icons-material';

// Progress phases with user-friendly messaging and icons
const PHASES = [
  { id: 'understanding', label: 'Analyzing your question', detail: 'Parsing natural language query', icon: ThinkingIcon, color: '#7C3AED' },
  { id: 'context', label: 'Loading conversation context', detail: 'Retrieving previous messages', icon: ContextIcon, color: '#2563EB' },
  { id: 'schema', label: 'Searching tables & columns', detail: 'Analyzing database schema', icon: SchemaIcon, color: '#0891B2' },
  { id: 'generating', label: 'AI writing SQL query', detail: 'Generating optimized query', icon: WriteIcon, color: '#7C3AED' },
  { id: 'validating', label: 'Validating query syntax', detail: 'Checking for errors', icon: ValidateIcon, color: '#059669' },
  { id: 'executing', label: 'Running query on database', detail: 'Executing SQL', icon: ExecuteIcon, color: '#DC2626' },
  { id: 'long_running', label: 'Processing large dataset', detail: 'This may take several minutes', icon: LongRunningIcon, color: '#F59E0B' },
  { id: 'background', label: 'Running in background', detail: 'You will be notified when complete', icon: NotificationsActiveIcon, color: '#10B981' },
  { id: 'processing', label: 'Processing results', detail: 'Formatting data', icon: DataIcon, color: '#EA580C' },
];

// Tips to show during wait times
const TIPS = [
  'Try asking follow-up questions to drill deeper into your data',
  'You can ask "show me this by region" to add grouping',
  'Use natural language like "top 10" or "last month" for filters',
  'Ask "compare this to last year" for trend analysis',
  'You can export results to CSV or Excel after the query completes',
];

const QueryProgress = ({
  currentPhase,
  progress,
  message,
  detail,
  sql,
  error,
  showSql = false,
  onToggleSql,
  isLongRunning = false,
  estimatedMinutes = 0,
  executionId = null,
  onNotifyMe,
  largestTableRows = 0,
}) => {
  const theme = useTheme();
  const [tipIndex, setTipIndex] = React.useState(0);
  const [sqlExpanded, setSqlExpanded] = React.useState(false);

  // Rotate tips every 5 seconds
  React.useEffect(() => {
    const interval = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % TIPS.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Format row count for display
  const formatRowCount = (rows) => {
    if (rows >= 1_000_000_000) {
      return `${(rows / 1_000_000_000).toFixed(1)}B`;
    } else if (rows >= 1_000_000) {
      return `${(rows / 1_000_000).toFixed(1)}M`;
    } else if (rows >= 1_000) {
      return `${(rows / 1_000).toFixed(1)}K`;
    }
    return rows.toString();
  };

  // Get current phase index
  const currentPhaseIndex = PHASES.findIndex((p) => p.id === currentPhase);

  // Handle SQL toggle
  const handleSqlToggle = () => {
    setSqlExpanded(!sqlExpanded);
    if (onToggleSql) onToggleSql(!sqlExpanded);
  };

  return (
    <Paper
      elevation={3}
      sx={{
        p: 3,
        borderRadius: 3,
        bgcolor: 'background.paper',
        border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`,
        maxWidth: 520,
        boxShadow: `0 4px 20px ${alpha(theme.palette.primary.main, 0.1)}`,
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: '12px',
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.3)}`,
          }}
        >
          <AIIcon sx={{ color: 'white', fontSize: 24 }} />
        </Box>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600, color: theme.palette.text.primary, lineHeight: 1.2 }}>
            AI Assistant
          </Typography>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
            Processing your query
          </Typography>
        </Box>
      </Box>

      {/* Progress Steps - Compact horizontal view */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 2, flexWrap: 'wrap' }}>
          {PHASES.map((phase, index) => {
            const isCompleted = index < currentPhaseIndex;
            const isActive = index === currentPhaseIndex;
            const isPending = index > currentPhaseIndex;
            const IconComponent = phase.icon;

            return (
              <React.Fragment key={phase.id}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    py: 0.5,
                    px: 1,
                    borderRadius: '20px',
                    bgcolor: isActive
                      ? alpha(phase.color, 0.1)
                      : isCompleted
                        ? alpha(theme.palette.success.main, 0.1)
                        : 'transparent',
                    border: isActive
                      ? `1px solid ${alpha(phase.color, 0.3)}`
                      : 'none',
                    transition: 'all 0.3s ease',
                  }}
                >
                  <Box
                    sx={{
                      width: 24,
                      height: 24,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      bgcolor: isCompleted
                        ? theme.palette.success.main
                        : isActive
                          ? phase.color
                          : alpha(theme.palette.text.disabled, 0.15),
                      color: isCompleted || isActive ? 'white' : theme.palette.text.disabled,
                      transition: 'all 0.3s ease',
                    }}
                  >
                    {isCompleted ? (
                      <CheckIcon sx={{ fontSize: 14 }} />
                    ) : (
                      <IconComponent sx={{ fontSize: 14 }} />
                    )}
                  </Box>
                  {isActive && (
                    <Typography
                      variant="caption"
                      sx={{
                        fontWeight: 600,
                        color: phase.color,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {phase.label}
                    </Typography>
                  )}
                </Box>
                {index < PHASES.length - 1 && (
                  <Box
                    sx={{
                      width: 12,
                      height: 2,
                      bgcolor: isCompleted
                        ? theme.palette.success.main
                        : alpha(theme.palette.text.disabled, 0.2),
                      borderRadius: 1,
                      transition: 'all 0.3s ease',
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </Box>

        {/* Current phase detail */}
        {currentPhaseIndex >= 0 && currentPhaseIndex < PHASES.length && (
          <Fade in key={currentPhase}>
            <Box
              sx={{
                p: 2,
                bgcolor: alpha(PHASES[currentPhaseIndex].color, 0.05),
                borderRadius: 2,
                border: `1px solid ${alpha(PHASES[currentPhaseIndex].color, 0.15)}`,
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 500,
                  color: theme.palette.text.primary,
                  mb: 0.5,
                }}
              >
                {message || PHASES[currentPhaseIndex].label}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: theme.palette.text.secondary,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                {detail || PHASES[currentPhaseIndex].detail}
                {(currentPhase === 'generating' || currentPhase === 'executing') && (
                  <Box
                    component="span"
                    sx={{
                      display: 'inline-flex',
                      gap: 0.3,
                      ml: 1,
                    }}
                  >
                    {[0, 1, 2].map((i) => (
                      <Box
                        key={i}
                        sx={{
                          width: 4,
                          height: 4,
                          borderRadius: '50%',
                          bgcolor: PHASES[currentPhaseIndex].color,
                          animation: 'pulse 1.4s ease-in-out infinite',
                          animationDelay: `${i * 0.2}s`,
                          '@keyframes pulse': {
                            '0%, 80%, 100%': { opacity: 0.3 },
                            '40%': { opacity: 1 },
                          },
                        }}
                      />
                    ))}
                  </Box>
                )}
              </Typography>
            </Box>
          </Fade>
        )}
      </Box>

      {/* Overall Progress Bar */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="caption" color="text.secondary" fontWeight={500}>
            Progress
          </Typography>
          <Typography variant="caption" sx={{ color: theme.palette.primary.main, fontWeight: 600 }}>
            {progress}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: alpha(theme.palette.primary.main, 0.1),
            '& .MuiLinearProgress-bar': {
              borderRadius: 4,
              background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
            },
          }}
        />
      </Box>

      {/* SQL Preview (collapsible) */}
      {sql && (
        <Box sx={{ mb: 2 }}>
          <Box
            onClick={handleSqlToggle}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              cursor: 'pointer',
              py: 1,
              px: 1.5,
              borderRadius: 2,
              bgcolor: alpha(theme.palette.grey[500], 0.08),
              transition: 'all 0.2s ease',
              '&:hover': {
                bgcolor: alpha(theme.palette.grey[500], 0.12),
              },
            }}
          >
            <CodeIcon sx={{ fontSize: 18, color: theme.palette.text.secondary }} />
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
              {sqlExpanded ? 'Hide Generated SQL' : 'View Generated SQL'}
            </Typography>
            <Chip
              label="SQL"
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                bgcolor: alpha(theme.palette.success.main, 0.1),
                color: theme.palette.success.main,
              }}
            />
            {sqlExpanded ? (
              <ExpandLessIcon sx={{ fontSize: 18, color: theme.palette.text.secondary }} />
            ) : (
              <ExpandMoreIcon sx={{ fontSize: 18, color: theme.palette.text.secondary }} />
            )}
          </Box>
          <Collapse in={sqlExpanded}>
            <Box
              sx={{
                mt: 1,
                p: 2,
                bgcolor: '#1e1e1e',
                borderRadius: 2,
                fontFamily: '"Fira Code", "Monaco", monospace',
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: 200,
                overflow: 'auto',
                color: '#d4d4d4',
                border: `1px solid ${alpha(theme.palette.common.white, 0.1)}`,
              }}
            >
              {sql}
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Background Mode - Query moved to background processing */}
      {currentPhase === 'background' && (
        <Box
          sx={{
            mb: 2,
            p: 2,
            bgcolor: alpha('#10B981', 0.1),
            borderRadius: 2,
            border: `1px solid ${alpha('#10B981', 0.3)}`,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <NotificationsActiveIcon sx={{ color: '#10B981', fontSize: 24 }} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#059669' }}>
                Running in Background
              </Typography>
              <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                {message || 'Query running in background. You will be notified when complete.'}
              </Typography>
            </Box>
            {largestTableRows > 0 && (
              <Chip
                label={`~${formatRowCount(largestTableRows)} rows`}
                size="small"
                sx={{
                  height: 22,
                  fontSize: '0.75rem',
                  bgcolor: alpha('#10B981', 0.15),
                  color: '#059669',
                  fontWeight: 600,
                }}
              />
            )}
          </Box>
          <Typography variant="caption" sx={{ display: 'block', mt: 1.5, color: '#059669' }}>
            You can continue asking other questions. A notification will appear when this query completes.
          </Typography>
        </Box>
      )}

      {/* Long-Running Query Alert - Transitional state before moving to background */}
      {(isLongRunning || currentPhase === 'long_running') && currentPhase !== 'background' && (
        <Box
          sx={{
            mb: 2,
            p: 2,
            bgcolor: alpha('#F59E0B', 0.08),
            borderRadius: 2,
            border: `1px solid ${alpha('#F59E0B', 0.25)}`,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <LongRunningIcon sx={{ color: '#F59E0B', fontSize: 24 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#B45309' }}>
              Large Dataset Detected
            </Typography>
            {largestTableRows > 0 && (
              <Chip
                label={`${formatRowCount(largestTableRows)} rows`}
                size="small"
                sx={{
                  height: 20,
                  fontSize: '0.7rem',
                  bgcolor: alpha('#F59E0B', 0.15),
                  color: '#B45309',
                  fontWeight: 600,
                }}
              />
            )}
          </Box>

          <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 1.5 }}>
            {message || `Scanning a large dataset (~${formatRowCount(largestTableRows)} rows). Moving to background...`}
          </Typography>

          {/* Progress indicator */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={16} sx={{ color: '#F59E0B' }} />
            <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
              Switching to background mode...
            </Typography>
          </Box>
        </Box>
      )}

      {/* Tip Section */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
          p: 1.5,
          bgcolor: alpha(theme.palette.info.main, 0.05),
          borderRadius: 2,
          border: `1px solid ${alpha(theme.palette.info.main, 0.1)}`,
        }}
      >
        <TipIcon sx={{ fontSize: 18, color: theme.palette.info.main, mt: 0.2 }} />
        <Typography
          variant="caption"
          sx={{
            color: theme.palette.text.secondary,
            lineHeight: 1.5,
          }}
        >
          <Box component="span" sx={{ fontWeight: 600, color: theme.palette.info.main }}>
            Tip:
          </Box>{' '}
          {TIPS[tipIndex]}
        </Typography>
      </Box>

      {/* Error Display */}
      {error && (
        <Box
          sx={{
            mt: 2,
            p: 1.5,
            bgcolor: alpha(theme.palette.error.main, 0.05),
            borderRadius: 2,
            border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
          }}
        >
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default QueryProgress;
