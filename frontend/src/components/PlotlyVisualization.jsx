import React, { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { Box, Paper, Typography, Grid, Chip, Alert, useTheme, FormControl, Select, MenuItem, InputLabel } from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ShowChart as ShowChartIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { sapChartColors } from '../themes/sapFioriTheme';

/**
 * PlotlyVisualization Component
 *
 * Automatically selects the best chart type for the data and displays it with
 * rich contextual information including data insights and statistics.
 *
 * Props:
 * - data: Array of objects to visualize
 * - title: Chart title
 * - chartType: Override chart type (optional)
 * - enableCrossFilter: Enable cross-chart filtering on click (default: false)
 * - onClick: Callback when chart element is clicked (for cross-filtering)
 * - dimensions: Array of dimension column names (from backend intelligence)
 * - measures: Array of measure column names (from backend intelligence)
 * - drillPaths: Array of drill-down paths (e.g., [['country', 'region', 'city']])
 * - onDrillDown: Callback when drill-down is triggered (dimension, value)
 */
const PlotlyVisualization = ({
  data,
  title = 'Data Visualization',
  chartType: propChartType,
  enableCrossFilter = false,
  onClick,
  dimensions,
  measures,
  drillPaths,
  onDrillDown
}) => {
  const theme = useTheme();
  const [selectedChartType, setSelectedChartType] = useState(propChartType || 'auto');

  // Analyze data and select best visualization
  const analysis = useMemo(() => analyzeData(data, theme, selectedChartType), [data, theme, selectedChartType]);

  if (!data || data.length === 0) {
    return (
      <Alert severity="info">
        No data available for visualization
      </Alert>
    );
  }

  if (!analysis.hasNumericData) {
    return (
      <Alert severity="warning">
        No numeric data available for visualization. Data contains only text columns.
      </Alert>
    );
  }

  const { chartType, traces, layout, insights, statistics } = analysis;

  // Handle chart click for cross-filtering
  const handlePlotClick = (event) => {
    if (!event.points || event.points.length === 0) return;

    const point = event.points[0];

    // Extract dimension and value from the clicked point
    const dimension = dimensions?.[0] || analysis.labelColumn || 'value';
    const value = point.x || point.label || point.text || point.y;

    // Call onClick callback if provided (for cross-filtering)
    if (onClick) {
      onClick(event);
    }

    // Trigger drill-down if enabled and paths available
    if (onDrillDown && drillPaths?.length > 0) {
      onDrillDown(dimension, value);
    }
  };

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        background: 'white',
        borderRadius: 2,
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
      }}
    >
      {/* Chart Type Selector */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel id="chart-type-label">Chart Type</InputLabel>
          <Select
            labelId="chart-type-label"
            id="chart-type-select"
            value={selectedChartType}
            label="Chart Type"
            onChange={(e) => setSelectedChartType(e.target.value)}
          >
            <MenuItem value="auto">🤖 Auto-Select</MenuItem>
            <MenuItem value="bar">📊 Bar Chart</MenuItem>
            <MenuItem value="line">📈 Line Chart</MenuItem>
            <MenuItem value="pie">🥧 Pie Chart</MenuItem>
            <MenuItem value="scatter">⚫ Scatter Plot</MenuItem>
            <MenuItem value="area">📉 Area Chart</MenuItem>
          </Select>
        </FormControl>
        <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
          {selectedChartType === 'auto' ? `Auto-selected: ${chartType}` : 'Manual override active'}
        </Typography>
      </Box>

      {/* Chart Wrapper with Grid Layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '220px 1fr 260px', gap: 3 }}>

        {/* Left Side - Chart Type & Data Info */}
        <Box
          sx={{
            background: theme.palette.background.paper,
            p: 2.5,
            borderRadius: 2,
            borderLeft: `4px solid ${theme.palette.primary.main}`,
            border: `1px solid ${theme.palette.divider}`
          }}
        >
          <Typography variant="h6" sx={{ mb: 2, color: theme.palette.text.primary, fontSize: '1rem' }}>
            📊 Chart Details
          </Typography>

          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mb: 0.5 }}>
              <strong>Chart Type:</strong>
            </Typography>
            <Chip
              label={chartType}
              size="small"
              sx={{
                bgcolor: theme.palette.primary.main,
                color: 'white',
                fontWeight: 600,
                fontSize: '0.75rem'
              }}
            />
          </Box>

          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mb: 0.5 }}>
            <strong>Total Records:</strong>
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.primary, fontWeight: 600 }}>
            {data.length.toLocaleString()}
          </Typography>

          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mb: 0.5 }}>
            <strong>Numeric Columns:</strong>
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.primary, fontWeight: 600 }}>
            {analysis.numericColumns.length}
          </Typography>

          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mb: 0.5 }}>
            <strong>Dimensions:</strong>
          </Typography>
          <Typography variant="body2" sx={{ color: theme.palette.text.primary, fontWeight: 600 }}>
            {Object.keys(data[0]).length} columns
          </Typography>

          {analysis.labelColumn && (
            <>
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mt: 2, mb: 0.5 }}>
                <strong>Primary Axis:</strong>
              </Typography>
              <Typography variant="body2" sx={{ color: theme.palette.text.primary, fontWeight: 600, fontSize: '0.8rem' }}>
                {analysis.labelColumn}
              </Typography>
            </>
          )}

          {analysis.groupColumn && (
            <>
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mt: 2, mb: 0.5 }}>
                <strong>Grouped By:</strong>
              </Typography>
              <Typography variant="body2" sx={{ color: theme.palette.text.primary, fontWeight: 600, fontSize: '0.8rem' }}>
                {analysis.groupColumn}
              </Typography>
            </>
          )}
        </Box>

        {/* Center - Chart */}
        <Box sx={{ minHeight: 500, cursor: enableCrossFilter ? 'pointer' : 'default' }}>
          <Plot
            data={traces}
            layout={{
              ...layout,
              title: {
                text: title,
                font: { size: 18, color: '#333' }
              },
              autosize: true,
              height: 500,
              margin: { t: 80, r: 30, b: 80, l: 80 },
              hovermode: 'closest',
              showlegend: traces.length > 1,
              legend: {
                x: 0.5,
                xanchor: 'center',
                y: -0.2,
                orientation: 'h'
              }
            }}
            onClick={enableCrossFilter ? handlePlotClick : undefined}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d'],
              toImageButtonOptions: {
                format: 'png',
                filename: 'chart_export',
                height: 800,
                width: 1200,
                scale: 2
              }
            }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler={true}
          />
        </Box>

        {/* Right Side - Insights & Description */}
        <Box
          sx={{
            background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.background.default} 100%)`,
            p: 2.5,
            borderRadius: 2,
            borderRight: `4px solid ${theme.palette.success.main}`,
            border: `1px solid ${theme.palette.divider}`
          }}
        >
          <Typography variant="h6" sx={{ mb: 2, color: theme.palette.text.primary, fontSize: '1rem' }}>
            💡 Insights
          </Typography>

          {insights.map((insight, idx) => (
            <Box
              key={idx}
              sx={{
                mb: 2,
                p: 1.5,
                background: theme.palette.background.paper,
                borderRadius: 1,
                fontSize: '0.85rem',
                lineHeight: 1.6,
                color: theme.palette.text.primary,
                border: `1px solid ${theme.palette.divider}`
              }}
            >
              {insight}
            </Box>
          ))}

          <Typography variant="h6" sx={{ mt: 3, mb: 2, color: theme.palette.text.primary, fontSize: '1rem' }}>
            📈 Features
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            <Chip label="🔍 Zoom & Pan" size="small" sx={{ fontSize: '0.7rem' }} />
            <Chip label="📥 Export PNG" size="small" sx={{ fontSize: '0.7rem' }} />
            <Chip label="📊 Hover Data" size="small" sx={{ fontSize: '0.7rem' }} />
            <Chip label="🔄 Interactive" size="small" sx={{ fontSize: '0.7rem' }} />
          </Box>
        </Box>
      </Box>

      {/* Bottom Section - Statistics Summary (Single Line) */}
      <Box
        sx={{
          mt: 3,
          background: theme.palette.background.paper,
          p: 2,
          borderRadius: 2,
          borderBottom: `4px solid ${theme.palette.success.main}`,
          border: `1px solid ${theme.palette.divider}`
        }}
      >
        <Typography variant="subtitle2" sx={{ mb: 1.5, color: theme.palette.text.secondary, fontSize: '0.85rem', fontWeight: 600 }}>
          📊 Statistical Summary
        </Typography>

        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', alignItems: 'center' }}>
          {statistics.map((stat, idx) => (
            <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontSize: '0.75rem' }}>
                {stat.label}:
              </Typography>
              <Typography variant="body2" sx={{ color: theme.palette.text.primary, fontWeight: 700, fontSize: '0.95rem' }}>
                {stat.value}
                {stat.trend === 'up' && <TrendingUpIcon sx={{ ml: 0.3, fontSize: '0.9rem', color: theme.palette.success.main, verticalAlign: 'middle' }} />}
                {stat.trend === 'down' && <TrendingDownIcon sx={{ ml: 0.3, fontSize: '0.9rem', color: theme.palette.error.main, verticalAlign: 'middle' }} />}
              </Typography>
              {idx < statistics.length - 1 && (
                <Typography variant="body2" sx={{ color: theme.palette.divider, mx: 0.5 }}>
                  •
                </Typography>
              )}
            </Box>
          ))}
        </Box>

        {/* Overall Insight */}
        {analysis.overallInsight && (
          <Box
            sx={{
              mt: 2.5,
              p: 2,
              background: theme.palette.background.default,
              borderLeft: `4px solid ${theme.palette.primary.main}`,
              borderRadius: 1,
              border: `1px solid ${theme.palette.divider}`
            }}
          >
            <Typography variant="body2" sx={{ lineHeight: 1.7, color: theme.palette.text.primary }}>
              <InfoIcon sx={{ fontSize: '1rem', mr: 1, verticalAlign: 'middle', color: theme.palette.primary.main }} />
              <strong>Analysis:</strong> {analysis.overallInsight}
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

/**
 * Get display name for chart type
 */
function getChartDisplayName(chartType) {
  const names = {
    'bar': 'Bar Chart',
    'line': 'Line Chart',
    'pie': 'Pie Chart',
    'scatter': 'Scatter Plot',
    'area': 'Area Chart',
    'multi-axis': 'Multi-Axis Chart'
  };
  return names[chartType] || 'Chart';
}

/**
 * Analyze data and determine the best visualization approach
 */
function analyzeData(data, theme, selectedChartType = 'auto') {
  if (!data || data.length === 0) {
    return { hasNumericData: false };
  }

  const keys = Object.keys(data[0]);

  // Identify numeric columns
  const numericColumns = keys.filter(key => {
    return data.every(row => {
      const value = row[key];
      if (value === null || value === undefined || value === '') return true;
      return typeof value === 'number' || !isNaN(parseFloat(String(value).replace(/[$,]/g, '')));
    });
  });

  // Identify categorical/label columns (support multiple categorical dimensions)
  const categoricalColumns = keys.filter(k => !numericColumns.includes(k));
  const labelColumn = categoricalColumns[0] || keys[0];
  const groupColumn = categoricalColumns.length > 1 ? categoricalColumns[1] : null;

  if (numericColumns.length === 0) {
    return { hasNumericData: false };
  }

  // Sanitize data
  const sanitizedData = data.map(row => {
    const sanitized = { ...row };
    numericColumns.forEach(col => {
      if (sanitized[col] !== null && sanitized[col] !== undefined) {
        const parsed = parseFloat(String(sanitized[col]).replace(/[$,]/g, ''));
        if (!isNaN(parsed)) {
          sanitized[col] = parsed;
        }
      }
    });
    return sanitized;
  });

  // Determine chart type - use manual selection or auto-select
  const chartDecision = selectedChartType === 'auto'
    ? selectBestChartType(sanitizedData, labelColumn, numericColumns, groupColumn)
    : { type: selectedChartType, displayName: getChartDisplayName(selectedChartType), reason: 'User selected' };

  // Generate traces based on chart type
  const traces = generateTraces(sanitizedData, labelColumn, numericColumns, chartDecision.type, theme, groupColumn);

  // Generate layout
  const layout = generateLayout(chartDecision.type, labelColumn, numericColumns, theme, groupColumn);

  // Generate insights
  const insights = generateInsights(sanitizedData, labelColumn, numericColumns, chartDecision);

  // Generate statistics
  const statistics = generateStatistics(sanitizedData, numericColumns);

  // Generate overall insight
  const overallInsight = generateOverallInsight(sanitizedData, labelColumn, numericColumns, chartDecision);

  return {
    hasNumericData: true,
    chartType: chartDecision.displayName,
    traces,
    layout,
    insights,
    statistics,
    overallInsight,
    numericColumns,
    labelColumn,
    groupColumn
  };
}

/**
 * Select the best chart type based on data characteristics
 */
function selectBestChartType(data, labelColumn, numericColumns, groupColumn = null) {
  const rowCount = data.length;
  const numericCount = numericColumns.length;
  const uniqueLabels = new Set(data.map(row => row[labelColumn])).size;

  // Check if label column looks like time series
  const isTimeSeries = data.every(row => {
    const label = row[labelColumn];
    return !isNaN(Date.parse(label)) || /^\d{4}/.test(String(label));
  });

  // Decision logic (prioritize categorical breakdowns over scatter plots)
  if (isTimeSeries && rowCount > 5) {
    return { type: 'line', displayName: 'Line Chart (Time Series)', reason: 'Time-based data detected' };
  }

  if (uniqueLabels <= 10 && numericCount === 1 && rowCount <= 10) {
    return { type: 'pie', displayName: 'Pie Chart', reason: 'Few categories, single metric' };
  }

  // Bar chart for categorical breakdowns (small number of categories, multiple metrics)
  if (uniqueLabels <= 20 && rowCount <= 50 && numericCount >= 1) {
    return { type: 'bar', displayName: 'Bar Chart', reason: 'Categorical breakdown with metrics' };
  }

  if (numericCount >= 2 && rowCount <= 100) {
    return { type: 'scatter', displayName: 'Scatter Plot', reason: 'Multiple metrics, correlation analysis' };
  }

  if (rowCount > 20 && numericCount === 1) {
    return { type: 'area', displayName: 'Area Chart', reason: 'Large dataset, trend visualization' };
  }

  if (numericCount > 1 && rowCount <= 50) {
    return { type: 'multi-axis', displayName: 'Multi-Axis Chart', reason: 'Multiple metrics comparison' };
  }

  // Default to bar chart
  return { type: 'bar', displayName: 'Bar Chart', reason: 'General comparison' };
}

/**
 * Generate Plotly traces based on chart type
 */
function generateTraces(data, labelColumn, numericColumns, chartType, theme, groupColumn = null) {
  const colors = sapChartColors;

  // Limit data for better performance
  const limitedData = data.length > 100 ? data.slice(0, 100) : data;

  switch (chartType) {
    case 'pie':
      const pieData = limitedData.slice(0, 10); // Top 10 for pie
      return [{
        type: 'pie',
        labels: pieData.map(row => row[labelColumn]),
        values: pieData.map(row => row[numericColumns[0]]),
        marker: {
          colors: colors
        },
        hovertemplate: '<b>%{label}</b><br>Value: %{value:,.2f}<br>Percentage: %{percent}<extra></extra>',
        textinfo: 'label+percent',
        textposition: 'auto'
      }];

    case 'scatter':
      if (numericColumns.length < 2) {
        return generateTraces(data, labelColumn, numericColumns, 'bar');
      }
      return [{
        type: 'scatter',
        mode: 'markers',
        x: limitedData.map(row => row[numericColumns[0]]),
        y: limitedData.map(row => row[numericColumns[1]]),
        text: limitedData.map(row => row[labelColumn]),
        marker: {
          size: 10,
          color: colors[0],
          opacity: 0.7,
          line: { width: 1, color: 'white' }
        },
        hovertemplate: '<b>%{text}</b><br>' +
          `${numericColumns[0]}: %{x:,.2f}<br>` +
          `${numericColumns[1]}: %{y:,.2f}<extra></extra>`
      }];

    case 'line':
    case 'area':
      return numericColumns.slice(0, 3).map((col, idx) => ({
        type: 'scatter',
        mode: chartType === 'line' ? 'lines+markers' : 'lines',
        fill: chartType === 'area' ? 'tozeroy' : 'none',
        name: col,
        x: limitedData.map(row => row[labelColumn]),
        y: limitedData.map(row => row[col]),
        line: {
          color: colors[idx],
          width: 3
        },
        marker: chartType === 'line' ? { size: 6 } : undefined,
        hovertemplate: `<b>${col}</b><br>%{x}<br>Value: %{y:,.2f}<extra></extra>`
      }));

    case 'multi-axis':
      const traces = [];
      const primaryCol = numericColumns[0];
      const secondaryCol = numericColumns[1];

      traces.push({
        type: 'bar',
        name: primaryCol,
        x: limitedData.map(row => row[labelColumn]),
        y: limitedData.map(row => row[primaryCol]),
        marker: { color: colors[0] },
        yaxis: 'y',
        hovertemplate: `<b>${primaryCol}</b><br>%{x}<br>Value: %{y:,.2f}<extra></extra>`
      });

      traces.push({
        type: 'scatter',
        mode: 'lines+markers',
        name: secondaryCol,
        x: limitedData.map(row => row[labelColumn]),
        y: limitedData.map(row => row[secondaryCol]),
        line: { color: colors[1], width: 3 },
        marker: { size: 8 },
        yaxis: 'y2',
        hovertemplate: `<b>${secondaryCol}</b><br>%{x}<br>Value: %{y:,.2f}<extra></extra>`
      });

      return traces;

    case 'bar':
    default:
      // If we have a groupColumn (e.g., Location), create grouped bars
      if (groupColumn) {
        const primaryMetric = numericColumns[0]; // Use first numeric column
        const groups = [...new Set(limitedData.map(row => row[groupColumn]))];

        return groups.map((group, idx) => {
          const groupData = limitedData.filter(row => row[groupColumn] === group);
          return {
            type: 'bar',
            name: group,
            x: groupData.map(row => row[labelColumn]),
            y: groupData.map(row => row[primaryMetric]),
            marker: {
              color: colors[idx % colors.length],
              line: { width: 1, color: 'white' }
            },
            hovertemplate: `<b>${group}</b><br>%{x}<br>${primaryMetric}: %{y:,.2f}<extra></extra>`
          };
        });
      }

      // Standard bar chart - one trace per numeric column
      return numericColumns.slice(0, 3).map((col, idx) => ({
        type: 'bar',
        name: col,
        x: limitedData.map(row => row[labelColumn]),
        y: limitedData.map(row => row[col]),
        marker: {
          color: colors[idx],
          line: { width: 1, color: 'white' }
        },
        hovertemplate: `<b>${col}</b><br>%{x}<br>Value: %{y:,.2f}<extra></extra>`
      }));
  }
}

/**
 * Generate Plotly layout based on chart type
 */
function generateLayout(chartType, labelColumn, numericColumns, theme, groupColumn = null) {
  const baseLayout = {
    paper_bgcolor: theme?.palette?.background?.paper || 'white',
    plot_bgcolor: theme?.palette?.background?.default || '#f7f7f7',
    font: {
      family: theme?.typography?.fontFamily || '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
      size: 12,
      color: theme?.palette?.text?.primary || '#1A2332'
    }
  };

  if (chartType === 'pie') {
    return {
      ...baseLayout,
      showlegend: true,
      legend: { orientation: 'h', y: -0.2 }
    };
  }

  if (chartType === 'scatter') {
    return {
      ...baseLayout,
      xaxis: {
        title: numericColumns[0] || 'X Axis',
        gridcolor: theme?.palette?.divider || '#e0e0e0',
        showgrid: true
      },
      yaxis: {
        title: numericColumns[1] || 'Y Axis',
        gridcolor: theme?.palette?.divider || '#e0e0e0',
        showgrid: true
      }
    };
  }

  if (chartType === 'multi-axis') {
    return {
      ...baseLayout,
      xaxis: {
        title: labelColumn,
        gridcolor: theme?.palette?.divider || '#e0e0e0'
      },
      yaxis: {
        title: numericColumns[0],
        titlefont: { color: sapChartColors[0] },
        tickfont: { color: sapChartColors[0] },
        gridcolor: theme?.palette?.divider || '#e0e0e0',
        showgrid: true
      },
      yaxis2: {
        title: numericColumns[1],
        titlefont: { color: sapChartColors[1] },
        tickfont: { color: sapChartColors[1] },
        overlaying: 'y',
        side: 'right',
        showgrid: false
      }
    };
  }

  // Default layout for bar, line, area
  // Use the actual metric name for Y-axis (first numeric column if available)
  const yAxisTitle = numericColumns.length > 0 ? numericColumns[0] : 'Value';

  return {
    ...baseLayout,
    xaxis: {
      title: {
        text: labelColumn,
        font: { size: 13, weight: 600 }
      },
      gridcolor: theme?.palette?.divider || '#e0e0e0',
      tickangle: -45,
      tickfont: { size: 11 }
    },
    yaxis: {
      title: {
        text: yAxisTitle,
        font: { size: 13, weight: 600 }
      },
      gridcolor: theme?.palette?.divider || '#e0e0e0',
      showgrid: true,
      tickfont: { size: 11 }
    },
    barmode: chartType === 'bar' && (numericColumns.length > 1 || groupColumn) ? 'group' : undefined,
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.15,
      x: 0.5,
      xanchor: 'center',
      font: { size: 11 }
    }
  };
}

/**
 * Generate concise, chart-focused insights
 */
function generateInsights(data, labelColumn, numericColumns, chartDecision) {
  const insights = [];
  const firstCol = numericColumns[0];
  const values = data.map(row => row[firstCol]).filter(v => v != null);

  if (values.length === 0) {
    insights.push(`No numeric data available`);
    return insights;
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const sorted = [...values].sort((a, b) => a - b);

  // 1. TOP PERFORMER - Most critical insight
  const maxRow = data.find(row => row[firstCol] === max);
  const minRow = data.find(row => row[firstCol] === min);

  if (maxRow && minRow) {
    const gap = ((max - min) / min * 100).toFixed(0);
    insights.push(`🏆 Top: "${maxRow[labelColumn]}" (${formatNumber(max)}) leads by ${gap}%`);
  }

  // 2. VARIABILITY - Only if significant
  const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;
  const stdDev = Math.sqrt(variance);
  const cv = (stdDev / avg) * 100;

  if (cv > 30) {
    insights.push(`⚠️ High variability (${cv.toFixed(0)}%) detected`);
  } else if (cv < 10) {
    insights.push(`✓ Consistent performance (${cv.toFixed(0)}% variation)`);
  }

  // 3. TREND - Only for time series
  if (chartDecision.type === 'line' || chartDecision.type === 'area') {
    const firstHalf = values.slice(0, Math.floor(values.length / 2));
    const secondHalf = values.slice(Math.floor(values.length / 2));
    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
    const trend = ((secondAvg - firstAvg) / firstAvg * 100).toFixed(0);

    if (Math.abs(trend) >= 10) {
      insights.push(`${trend > 0 ? '📈' : '📉'} ${Math.abs(trend)}% ${trend > 0 ? 'growth' : 'decline'} trend`);
    }
  }

  // 4. CALL TO ACTION - Guide to detailed insights
  insights.push(`💡 Click "View Detailed Results" for AI-powered business insights`);

  return insights.slice(0, 4); // Max 4 concise insights
}

/**
 * Generate statistical summary
 */
function generateStatistics(data, numericColumns) {
  const stats = [];
  const firstCol = numericColumns[0];
  const values = data.map(row => row[firstCol]).filter(v => v != null);

  // Total
  const total = values.reduce((a, b) => a + b, 0);
  stats.push({ label: 'Total', value: formatNumber(total) });

  // Average
  const avg = total / values.length;
  stats.push({ label: 'Average', value: formatNumber(avg) });

  // Max
  const max = Math.max(...values);
  stats.push({ label: 'Maximum', value: formatNumber(max), trend: 'up' });

  // Min
  const min = Math.min(...values);
  stats.push({ label: 'Minimum', value: formatNumber(min), trend: 'down' });

  // Std Deviation
  const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;
  const stdDev = Math.sqrt(variance);
  stats.push({ label: 'Std Dev', value: formatNumber(stdDev) });

  // Median
  const sorted = [...values].sort((a, b) => a - b);
  const median = sorted.length % 2 === 0
    ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
    : sorted[Math.floor(sorted.length / 2)];
  stats.push({ label: 'Median', value: formatNumber(median) });

  return stats;
}

/**
 * Generate concise overall insight
 */
function generateOverallInsight(data, labelColumn, numericColumns, chartDecision) {
  const firstCol = numericColumns[0];
  const values = data.map(row => row[firstCol]).filter(v => v != null);

  if (values.length === 0) {
    return `${data.length} records with no numeric data available.`;
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const maxRow = data.find(row => row[firstCol] === max);
  const minRow = data.find(row => row[firstCol] === min);
  const gap = ((max - min) / min * 100).toFixed(0);

  // Calculate top 20% concentration
  const sorted = [...values].sort((a, b) => a - b);
  const top20Percent = Math.ceil(values.length * 0.2);
  const topSum = sorted.slice(-top20Percent).reduce((a, b) => a + b, 0);
  const totalSum = values.reduce((a, b) => a + b, 0);
  const concentration = ((topSum / totalSum) * 100).toFixed(0);

  return `Analyzing ${data.length} records: "${maxRow[labelColumn]}" leads (${formatNumber(max)}) with ${gap}% gap over "${minRow[labelColumn]}" (${formatNumber(min)}). ` +
    `Top 20% accounts for ${concentration}% of total value. For detailed business insights, click "View Detailed Results" above.`;
}

/**
 * Format number for display
 */
function formatNumber(num) {
  if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(2)}K`;
  return num.toFixed(2);
}

export default PlotlyVisualization;
