import React, { useMemo, useCallback, Component } from 'react';
import ReactECharts from 'echarts-for-react';
import { useTheme, Box, Alert, Typography, Button } from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';

/**
 * Error Boundary for ECharts to gracefully handle rendering errors
 */
class ChartErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[EChartsVisualization] Chart error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            height: this.props.height || 350,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 2,
            p: 2
          }}
        >
          <Alert severity="warning" sx={{ maxWidth: 400 }}>
            Unable to render chart. Please try refreshing.
          </Alert>
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={() => {
              this.setState({ hasError: false, error: null });
              if (this.props.onRetry) this.props.onRetry();
            }}
          >
            Retry
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}

/**
 * Chart configuration generators for different chart types.
 * Each function takes data and key names, returns ECharts option object.
 */
const CHART_CONFIGS = {
  bar: (data, xKey, yKey, theme) => ({
    xAxis: {
      type: 'category',
      data: data.map(d => d[xKey]),
      axisLabel: {
        rotate: data.length > 10 ? 45 : 0,
        color: theme.palette.text.secondary
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: theme.palette.text.secondary }
    },
    series: [{
      type: 'bar',
      data: data.map(d => d[yKey]),
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: theme.palette.primary.main
      },
      emphasis: {
        itemStyle: { color: theme.palette.primary.dark }
      }
    }]
  }),

  line: (data, xKey, yKey, theme) => ({
    xAxis: {
      type: 'category',
      data: data.map(d => d[xKey]),
      axisLabel: { color: theme.palette.text.secondary }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: theme.palette.text.secondary }
    },
    series: [{
      type: 'line',
      data: data.map(d => d[yKey]),
      smooth: true,
      lineStyle: { color: theme.palette.primary.main, width: 2 },
      itemStyle: { color: theme.palette.primary.main },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: theme.palette.primary.light + '40' },
            { offset: 1, color: theme.palette.primary.light + '05' }
          ]
        }
      }
    }]
  }),

  pie: (data, xKey, yKey, theme) => ({
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '55%'],
      data: data.map((d, i) => ({
        name: d[xKey],
        value: d[yKey],
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
      })),
      label: {
        show: true,
        formatter: '{b}: {d}%',
        color: theme.palette.text.primary
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }),

  donut: (data, xKey, yKey, theme) => ({
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      center: ['50%', '55%'],
      avoidLabelOverlap: true,
      data: data.map((d, i) => ({
        name: d[xKey],
        value: d[yKey],
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
      })),
      label: {
        show: true,
        position: 'outside',
        formatter: '{b}\n{d}%',
        color: theme.palette.text.primary
      },
      labelLine: { show: true },
      emphasis: {
        label: { show: true, fontWeight: 'bold' }
      }
    }]
  }),

  scatter: (data, xKey, yKey, theme) => ({
    xAxis: {
      type: 'value',
      axisLabel: { color: theme.palette.text.secondary }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: theme.palette.text.secondary }
    },
    series: [{
      type: 'scatter',
      data: data.map(d => [d[xKey], d[yKey]]),
      symbolSize: 12,
      itemStyle: { color: theme.palette.primary.main }
    }]
  }),

  area: (data, xKey, yKey, theme) => ({
    xAxis: {
      type: 'category',
      data: data.map(d => d[xKey]),
      boundaryGap: false,
      axisLabel: { color: theme.palette.text.secondary }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: theme.palette.text.secondary }
    },
    series: [{
      type: 'line',
      data: data.map(d => d[yKey]),
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: theme.palette.primary.main + '80' },
            { offset: 1, color: theme.palette.primary.main + '10' }
          ]
        }
      },
      lineStyle: { color: theme.palette.primary.main, width: 2 },
      itemStyle: { color: theme.palette.primary.main }
    }]
  }),

  heatmap: (data, xKey, yKey, valueKey, theme) => {
    const xCategories = [...new Set(data.map(d => d[xKey]))];
    const yCategories = [...new Set(data.map(d => d[yKey]))];
    const values = data.map(d => d[valueKey || Object.keys(d).find(k => k !== xKey && k !== yKey)]);
    const maxValue = Math.max(...values.filter(v => typeof v === 'number'));

    return {
      xAxis: {
        type: 'category',
        data: xCategories,
        axisLabel: { color: theme.palette.text.secondary }
      },
      yAxis: {
        type: 'category',
        data: yCategories,
        axisLabel: { color: theme.palette.text.secondary }
      },
      visualMap: {
        min: 0,
        max: maxValue || 100,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: ['#e0f2fe', '#0284c7', '#0c4a6e']
        }
      },
      series: [{
        type: 'heatmap',
        data: data.map(d => {
          const vKey = valueKey || Object.keys(d).find(k => k !== xKey && k !== yKey);
          return [
            xCategories.indexOf(d[xKey]),
            yCategories.indexOf(d[yKey]),
            d[vKey]
          ];
        }),
        label: { show: true, color: '#fff' }
      }]
    };
  },

  treemap: (data, nameKey, valueKey, theme) => ({
    series: [{
      type: 'treemap',
      data: data.map((d, i) => ({
        name: d[nameKey],
        value: d[valueKey],
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
      })),
      leafDepth: 1,
      label: {
        show: true,
        formatter: '{b}',
        color: '#fff'
      },
      upperLabel: { show: true, height: 30 },
      breadcrumb: { show: false }
    }]
  }),

  funnel: (data, nameKey, valueKey, theme) => ({
    series: [{
      type: 'funnel',
      left: '10%',
      top: 60,
      bottom: 60,
      width: '80%',
      min: 0,
      max: Math.max(...data.map(d => d[valueKey])),
      minSize: '0%',
      maxSize: '100%',
      sort: 'descending',
      gap: 2,
      label: {
        show: true,
        position: 'inside',
        formatter: '{b}: {c}',
        color: '#fff'
      },
      data: data.map((d, i) => ({
        name: d[nameKey],
        value: d[valueKey],
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
      }))
    }]
  }),

  gauge: (data, valueKey, theme) => {
    const value = data[0]?.[valueKey] || 0;
    const isPercentage = valueKey?.toLowerCase().includes('percent') || valueKey?.toLowerCase().includes('rate');

    return {
      series: [{
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: isPercentage ? 100 : Math.ceil(value * 1.2),
        splitNumber: 5,
        radius: '90%',
        center: ['50%', '70%'],
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.3, '#ef4444'],
              [0.7, '#f59e0b'],
              [1, '#22c55e']
            ]
          }
        },
        pointer: {
          itemStyle: { color: theme.palette.text.primary },
          width: 5
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          distance: 25,
          color: theme.palette.text.secondary,
          fontSize: 10
        },
        detail: {
          valueAnimation: true,
          formatter: isPercentage ? '{value}%' : '{value}',
          color: theme.palette.text.primary,
          fontSize: 24,
          fontWeight: 'bold',
          offsetCenter: [0, '20%']
        },
        data: [{ value, name: valueKey }]
      }]
    };
  },

  // Single value display - uses stat card style
  metric: (data, valueKey, theme) => {
    const value = data[0]?.[valueKey] || 0;
    const formattedValue = typeof value === 'number'
      ? value.toLocaleString()
      : value;

    return {
      graphic: {
        elements: [
          {
            type: 'text',
            left: 'center',
            top: '40%',
            style: {
              text: formattedValue,
              fontSize: 48,
              fontWeight: 'bold',
              fill: theme.palette.primary.main,
              textAlign: 'center'
            }
          },
          {
            type: 'text',
            left: 'center',
            top: '65%',
            style: {
              text: valueKey?.replace(/_/g, ' ').toUpperCase() || 'VALUE',
              fontSize: 14,
              fill: theme.palette.text.secondary,
              textAlign: 'center'
            }
          }
        ]
      }
    };
  },

  radar: (data, dimensions, valueKey, theme) => {
    const keys = dimensions || Object.keys(data[0] || {}).filter(k => typeof data[0][k] === 'number');
    const maxValues = keys.map(k => Math.max(...data.map(d => d[k] || 0)));

    return {
      radar: {
        indicator: keys.map((k, i) => ({
          name: k.replace(/_/g, ' '),
          max: maxValues[i] * 1.2 || 100
        })),
        center: ['50%', '55%'],
        radius: '65%'
      },
      series: [{
        type: 'radar',
        data: data.map((row, i) => ({
          value: keys.map(k => row[k] || 0),
          name: row.name || `Series ${i + 1}`,
          areaStyle: { opacity: 0.2 },
          lineStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
          itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        }))
      }]
    };
  },

  sankey: (data, theme) => ({
    series: [{
      type: 'sankey',
      layout: 'none',
      emphasis: { focus: 'adjacency' },
      data: data.nodes || [],
      links: data.links || [],
      lineStyle: { color: 'gradient', curveness: 0.5 },
      label: { color: theme.palette.text.primary }
    }]
  }),

  // Horizontal bar chart
  horizontalBar: (data, xKey, yKey, theme) => ({
    xAxis: {
      type: 'value',
      axisLabel: { color: theme.palette.text.secondary }
    },
    yAxis: {
      type: 'category',
      data: data.map(d => d[xKey]),
      axisLabel: { color: theme.palette.text.secondary }
    },
    series: [{
      type: 'bar',
      data: data.map(d => d[yKey]),
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: theme.palette.primary.main
      }
    }]
  }),

  // Sunburst - hierarchical radial chart
  sunburst: (data, nameKey, valueKey, theme) => {
    // Transform flat data to hierarchical if needed
    const transformToHierarchy = (flatData) => {
      if (flatData.children) return flatData; // Already hierarchical
      return flatData.map((d, i) => ({
        name: d[nameKey] || d.name || `Item ${i + 1}`,
        value: d[valueKey] || d.value || 1,
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
      }));
    };

    return {
      series: [{
        type: 'sunburst',
        data: transformToHierarchy(data),
        radius: [0, '90%'],
        label: {
          rotate: 'radial',
          color: theme.palette.text.primary
        },
        itemStyle: {
          borderRadius: 4,
          borderWidth: 2,
          borderColor: theme.palette.background.paper
        },
        emphasis: {
          focus: 'ancestor'
        }
      }]
    };
  },

  // Boxplot - statistical distribution
  boxplot: (data, categoryKey, valuesKey, theme) => {
    // Expected data format: { categories: ['A', 'B'], values: [[min, Q1, median, Q3, max], ...] }
    // Or array of objects with category and numeric fields
    let categories, boxData;

    if (data.categories && data.values) {
      categories = data.categories;
      boxData = data.values;
    } else {
      // Try to compute boxplot from raw data grouped by category
      categories = [...new Set(data.map(d => d[categoryKey]))];
      boxData = categories.map(() => [0, 25, 50, 75, 100]); // Placeholder
    }

    return {
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { color: theme.palette.text.secondary }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: theme.palette.text.secondary }
      },
      series: [{
        type: 'boxplot',
        data: boxData,
        itemStyle: {
          color: theme.palette.primary.light,
          borderColor: theme.palette.primary.main
        }
      }]
    };
  },

  // Candlestick - financial OHLC data
  candlestick: (data, dateKey, theme) => {
    // Expected: array with date/time and OHLC values
    // Format: [{ date, open, close, low, high }] or [{ date, values: [open, close, low, high] }]
    const dates = data.map(d => d[dateKey] || d.date || d.time);
    const values = data.map(d => {
      if (d.values) return d.values;
      return [d.open, d.close, d.low, d.high];
    });

    return {
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: theme.palette.text.secondary }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { color: theme.palette.text.secondary }
      },
      series: [{
        type: 'candlestick',
        data: values,
        itemStyle: {
          color: '#22c55e',      // Up (bullish)
          color0: '#ef4444',     // Down (bearish)
          borderColor: '#22c55e',
          borderColor0: '#ef4444'
        }
      }]
    };
  },

  // Graph - network/relationship diagram
  graph: (data, theme) => {
    // Expected: { nodes: [{name, value, category}], links: [{source, target, value}] }
    const nodes = data.nodes || data.map((d, i) => ({
      name: d.name || `Node ${i}`,
      value: d.value || 1,
      symbolSize: Math.min(50, Math.max(20, (d.value || 1) / 10))
    }));
    const links = data.links || [];

    return {
      series: [{
        type: 'graph',
        layout: 'force',
        data: nodes.map((n, i) => ({
          ...n,
          itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        })),
        links: links,
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: 'right',
          color: theme.palette.text.primary
        },
        force: {
          repulsion: 200,
          edgeLength: [50, 200]
        },
        lineStyle: {
          color: theme.palette.divider,
          curveness: 0.3
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3 }
        }
      }]
    };
  },

  // Parallel coordinates - high-dimensional data
  parallel: (data, dimensionKeys, theme) => {
    // Detect dimensions from data if not provided
    const dimensions = dimensionKeys || Object.keys(data[0] || {}).filter(
      k => typeof data[0][k] === 'number'
    );

    return {
      parallelAxis: dimensions.map((dim, i) => ({
        dim: i,
        name: dim.replace(/_/g, ' '),
        nameTextStyle: { color: theme.palette.text.secondary }
      })),
      parallel: {
        left: '5%',
        right: '13%',
        parallelAxisDefault: {
          type: 'value',
          axisLine: { lineStyle: { color: theme.palette.divider } },
          axisLabel: { color: theme.palette.text.secondary }
        }
      },
      series: [{
        type: 'parallel',
        lineStyle: {
          width: 2,
          opacity: 0.5
        },
        data: data.map((row, i) => ({
          value: dimensions.map(dim => row[dim]),
          lineStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        }))
      }]
    };
  },

  // ThemeRiver - stacked time series (streamgraph)
  themeRiver: (data, theme) => {
    // Expected format: [[date, value, name], ...] or [{date, value, category}]
    let riverData;
    if (Array.isArray(data[0])) {
      riverData = data;
    } else {
      // Transform object format to array format
      riverData = data.map(d => [
        d.date || d.time,
        d.value || d.amount || 0,
        d.name || d.category || 'Series'
      ]);
    }

    // Get unique names for legend
    const names = [...new Set(riverData.map(d => d[2]))];

    return {
      singleAxis: {
        type: 'time',
        bottom: 30,
        axisLabel: { color: theme.palette.text.secondary }
      },
      legend: {
        data: names,
        bottom: 0,
        textStyle: { color: theme.palette.text.secondary }
      },
      series: [{
        type: 'themeRiver',
        data: riverData,
        label: {
          show: true,
          color: '#fff'
        },
        emphasis: {
          itemStyle: { shadowBlur: 20 }
        }
      }]
    };
  },

  // Calendar heatmap - GitHub-style activity calendar
  calendar: (data, dateKey, valueKey, theme) => {
    // Expected: [{date: '2024-01-01', value: 5}, ...]
    const calendarData = data.map(d => [
      d[dateKey] || d.date,
      d[valueKey] || d.value || d.count || 0
    ]);

    // Determine year range from data
    const dates = calendarData.map(d => new Date(d[0]));
    const years = [...new Set(dates.map(d => d.getFullYear()))];
    const year = years.length > 0 ? Math.max(...years) : new Date().getFullYear();

    const maxValue = Math.max(...calendarData.map(d => d[1]));

    return {
      visualMap: {
        min: 0,
        max: maxValue || 100,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
        }
      },
      calendar: {
        range: year.toString(),
        cellSize: ['auto', 15],
        left: 30,
        right: 30,
        top: 20,
        itemStyle: {
          borderWidth: 2,
          borderColor: theme.palette.background.paper
        },
        dayLabel: { color: theme.palette.text.secondary },
        monthLabel: { color: theme.palette.text.secondary }
      },
      series: [{
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: calendarData
      }]
    };
  },

  // Pictorial bar - bars with custom shapes/icons
  pictorialBar: (data, xKey, yKey, theme) => {
    const symbol = data.symbol || 'rect';

    return {
      xAxis: {
        type: 'category',
        data: data.map(d => d[xKey]),
        axisLabel: { color: theme.palette.text.secondary }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: theme.palette.text.secondary }
      },
      series: [{
        type: 'pictorialBar',
        symbol: symbol,
        symbolRepeat: 'fixed',
        symbolMargin: 2,
        symbolClip: true,
        symbolSize: [20, 10],
        data: data.map((d, i) => ({
          value: d[yKey],
          itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        })),
        label: {
          show: true,
          position: 'top',
          color: theme.palette.text.primary
        }
      }]
    };
  }
};

// Mantrix theme colors
const CHART_COLORS = [
  '#6366f1', // Indigo
  '#22c55e', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Purple
  '#06b6d4', // Cyan
  '#ec4899', // Pink
  '#14b8a6', // Teal
  '#f97316', // Orange
  '#84cc16'  // Lime
];

// Helper to detect ID/key columns that should be treated as categorical even if numeric
const isIdColumn = (columnName) => {
  const idPatterns = [
    /_sk$/i,           // Surrogate key (data warehouse pattern)
    /_id$/i,           // ID suffix
    /_key$/i,          // Key suffix
    /^id$/i,           // Just "id"
    /_pk$/i,           // Primary key
    /_fk$/i,           // Foreign key
    /_code$/i,         // Code columns (often categorical)
    /customer_?id/i,   // Common patterns
    /product_?id/i,
    /store_?id/i,
    /item_?id/i,
    /order_?id/i,
    /ticket_?number/i,
    /hdemo_?sk/i,      // Household demo surrogate key
    /cdemo_?sk/i,      // Customer demo surrogate key
    /addr_?sk/i,       // Address surrogate key
    /promo_?sk/i,      // Promotion surrogate key
  ];
  return idPatterns.some(pattern => pattern.test(columnName));
};

// Helper to detect metric/value columns (actual numbers to aggregate/visualize)
const isMetricColumn = (columnName, value) => {
  if (typeof value !== 'number') return false;
  if (isIdColumn(columnName)) return false;

  // Common metric patterns
  const metricPatterns = [
    /price/i, /cost/i, /amount/i, /total/i, /sum/i,
    /revenue/i, /sales/i, /profit/i, /margin/i,
    /quantity/i, /qty/i, /count/i, /num/i,
    /rate/i, /percent/i, /ratio/i, /avg/i,
    /weight/i, /size/i, /length/i, /width/i, /height/i
  ];
  return metricPatterns.some(pattern => pattern.test(columnName));
};

/**
 * Auto-detect the best chart type based on data shape and characteristics.
 * This provides smart defaults when LLM returns 'auto' or makes suboptimal choices.
 */
const detectChartType = (data) => {
  if (!data || data.length === 0) return 'bar';

  // Network/graph data has nodes and links
  if (data.nodes && data.links) return 'sankey';

  const firstRow = data[0] || {};
  const keys = Object.keys(firstRow);

  // Enhanced type detection - separates IDs from actual metrics
  const idKeys = keys.filter(k => isIdColumn(k) && typeof firstRow[k] === 'number');
  const metricKeys = keys.filter(k => isMetricColumn(k, firstRow[k]));
  const stringKeys = keys.filter(k => typeof firstRow[k] === 'string');
  const numericKeys = keys.filter(k => typeof firstRow[k] === 'number' && !isIdColumn(k));

  // Treat ID columns as categorical for chart selection
  const categoricalKeys = [...stringKeys, ...idKeys];

  // 1. SINGLE ROW → metric or gauge (NEVER bar!)
  if (data.length === 1) {
    const valueKeys = metricKeys.length > 0 ? metricKeys : numericKeys;
    if (valueKeys.length === 1) return 'metric';
    if (valueKeys.length <= 5) return 'gauge';
    return 'radar'; // Multiple metrics → radar
  }

  // 2. TIME SERIES detection
  const timePatterns = ['date', 'time', 'month', 'year', 'quarter', 'week', 'day', 'period'];
  const hasTimeKey = keys.some(k =>
    timePatterns.some(p => k.toLowerCase().includes(p))
  );

  if (hasTimeKey) {
    // Check if it looks like daily data over a year → calendar
    if (data.length > 100 && data.length <= 366) {
      const dateKey = keys.find(k => k.toLowerCase().includes('date'));
      if (dateKey) return 'calendar';
    }
    // Multiple series flowing over time → themeRiver
    if (categoricalKeys.length >= 2 && (metricKeys.length >= 1 || numericKeys.length >= 1)) {
      return 'themeRiver';
    }
    // Regular time series → line (default for time data)
    return 'line';
  }

  // 3. SMALL CATEGORICAL (≤6 rows) → pie/donut
  // Use categoricalKeys (strings + IDs) for detection
  if (data.length <= 6 && categoricalKeys.length >= 1) {
    const valueKeys = metricKeys.length > 0 ? metricKeys : numericKeys;
    if (valueKeys.length >= 1) {
      // Check if values look like percentages (sum to ~100)
      const firstValueKey = valueKeys[0];
      const total = data.reduce((sum, row) => sum + (row[firstValueKey] || 0), 0);
      if (total >= 95 && total <= 105) return 'donut'; // Percentages → donut with total
      return 'pie';
    }
  }

  // 4. MEDIUM CATEGORICAL (7-12 rows) → donut
  if (data.length >= 7 && data.length <= 12 && categoricalKeys.length >= 1) {
    const valueKeys = metricKeys.length > 0 ? metricKeys : numericKeys;
    if (valueKeys.length >= 1) return 'donut';
  }

  // 5. LONG LABELS → horizontalBar
  if (categoricalKeys.length > 0) {
    const labelKey = categoricalKeys[0];
    const avgLabelLength = data.reduce((sum, row) => sum + String(row[labelKey] || '').length, 0) / data.length;
    if (avgLabelLength > 15) return 'horizontalBar';
  }

  // 6. MULTI-DIMENSIONAL (many numeric/metric columns) → radar or parallel
  const valueKeys = metricKeys.length > 0 ? metricKeys : numericKeys;
  if (valueKeys.length >= 5) {
    if (data.length <= 10) return 'radar';
    return 'parallel';
  }

  // 7. SCATTER detection (two numeric value columns, many rows)
  if (valueKeys.length === 2 && data.length > 10) {
    return 'scatter';
  }

  // 8. FUNNEL detection (sequential stages with decreasing values)
  if (data.length >= 3 && data.length <= 8 && valueKeys.length === 1) {
    const values = data.map(row => row[valueKeys[0]]);
    const isDecreasing = values.every((v, i) => i === 0 || v <= values[i - 1]);
    if (isDecreasing) return 'funnel';
  }

  // 9. MATRIX detection (looks like row x column data)
  // If there are 2+ categorical columns and 1+ value, might be heatmap
  if (categoricalKeys.length >= 2 && valueKeys.length >= 1) {
    const col1Values = new Set(data.map(row => row[categoricalKeys[0]]));
    const col2Values = new Set(data.map(row => row[categoricalKeys[1]]));
    if (col1Values.size * col2Values.size === data.length) {
      return 'heatmap';
    }
  }

  // 10. MANY ROWS with ID columns → treemap for better visualization
  if (data.length > 12 && idKeys.length > 0 && valueKeys.length >= 1) {
    return 'treemap';
  }

  // 11. Mostly ID columns → horizontalBar for readability
  if (idKeys.length >= keys.length / 2 && valueKeys.length >= 1) {
    return 'horizontalBar';
  }

  // 12. DEFAULT → bar for categorical comparisons
  return 'bar';
};

/**
 * Auto-detect x and y keys from data.
 * Prioritizes metric columns for y-axis and categorical/ID columns for x-axis.
 */
const detectKeys = (data) => {
  if (!data || data.length === 0) return { xKey: null, yKey: null };

  const firstRow = data[0] || {};
  const keys = Object.keys(firstRow);

  // Filter out internal columns from multi-DB queries
  const filteredKeys = keys.filter(k =>
    !k.startsWith('_') &&
    k !== '_source_connector' &&
    k !== '_row_id'
  );

  // Categorize columns
  const textKeys = filteredKeys.filter(k => typeof firstRow[k] === 'string');
  const idKeys = filteredKeys.filter(k => isIdColumn(k) && typeof firstRow[k] === 'number');
  const metricKeys = filteredKeys.filter(k => isMetricColumn(k, firstRow[k]));
  const numericKeys = filteredKeys.filter(k => typeof firstRow[k] === 'number' && !isIdColumn(k));

  // For x-axis: prefer string keys, then ID keys (categorical)
  // For y-axis: prefer metric keys, then numeric keys (values)
  const categoricalKeys = [...textKeys, ...idKeys];
  const valueKeys = metricKeys.length > 0 ? metricKeys : numericKeys;

  return {
    xKey: categoricalKeys[0] || filteredKeys[0],
    yKey: valueKeys[0] || filteredKeys[1] || filteredKeys[0]
  };
};

/**
 * Filter out internal columns from multi-database queries.
 */
const filterInternalColumns = (data) => {
  if (!Array.isArray(data)) return data;

  return data.map(row => {
    const filtered = {};
    Object.entries(row).forEach(([key, value]) => {
      if (!key.startsWith('_') && key !== '_source_connector' && key !== '_row_id') {
        filtered[key] = value;
      }
    });
    return filtered;
  });
};

/**
 * EChartsVisualization Component
 *
 * A flexible chart component using Apache ECharts that auto-detects
 * the best visualization type based on data characteristics.
 *
 * @param {Object} props
 * @param {Array|Object} props.data - Chart data
 * @param {string} props.chartType - Chart type (auto, bar, line, pie, etc.)
 * @param {string} props.title - Chart title
 * @param {number} props.height - Chart height in pixels
 * @param {Function} props.onChartClick - Click event handler for drill-down
 * @param {Function} props.onBrushSelected - Brush selection handler
 * @param {string} props.xKey - Override x-axis key
 * @param {string} props.yKey - Override y-axis key
 * @param {boolean} props.showToolbox - Show ECharts toolbox
 * @param {boolean} props.showDataZoom - Show data zoom controls
 */
const EChartsVisualization = ({
  data,
  chartType = 'auto',
  title,
  height = 350,
  onChartClick,
  onBrushSelected,
  xKey: propXKey,
  yKey: propYKey,
  showToolbox = true,
  showDataZoom = true
}) => {
  const muiTheme = useTheme();

  const { option, isValid, errorMessage, debugInfo } = useMemo(() => {
    // Validate data
    if (!data) {
      return { isValid: false, errorMessage: 'No data provided' };
    }

    // Handle empty arrays
    if (Array.isArray(data) && data.length === 0) {
      return { isValid: false, errorMessage: 'No data available for visualization' };
    }

    // Filter internal columns
    const cleanData = filterInternalColumns(data);

    // Detect chart type and keys
    const type = chartType === 'auto' ? detectChartType(cleanData) : chartType;
    const { xKey: detectedXKey, yKey: detectedYKey } = detectKeys(cleanData);
    const xKey = propXKey || detectedXKey;
    const yKey = propYKey || detectedYKey;

    // Chart types that don't require x/y keys
    const noKeyTypes = ['metric', 'sankey', 'graph', 'themeRiver', 'parallel'];
    if (!xKey && !yKey && !noKeyTypes.includes(type)) {
      return { isValid: false, errorMessage: 'Unable to determine chart dimensions' };
    }

    // Get chart configuration
    const configFn = CHART_CONFIGS[type] || CHART_CONFIGS.bar;
    let chartConfig;

    try {
      // Handle different chart type signatures
      if (type === 'heatmap') {
        chartConfig = configFn(cleanData, xKey, yKey, null, muiTheme);
      } else if (type === 'radar') {
        chartConfig = configFn(cleanData, null, yKey, muiTheme);
      } else if (type === 'sankey' || type === 'graph' || type === 'themeRiver') {
        chartConfig = configFn(cleanData, muiTheme);
      } else if (type === 'parallel') {
        chartConfig = configFn(cleanData, null, muiTheme);
      } else if (type === 'calendar') {
        chartConfig = configFn(cleanData, xKey, yKey, muiTheme);
      } else if (type === 'candlestick') {
        chartConfig = configFn(cleanData, xKey, muiTheme);
      } else if (type === 'sunburst' || type === 'boxplot') {
        chartConfig = configFn(cleanData, xKey, yKey, muiTheme);
      } else {
        chartConfig = configFn(cleanData, xKey, yKey, muiTheme);
      }
    } catch (err) {
      console.error('Chart config error:', err);
      return { isValid: false, errorMessage: 'Error generating chart configuration' };
    }

    // Build final ECharts option
    const noZoomTypes = ['pie', 'donut', 'gauge', 'metric', 'radar', 'funnel', 'treemap', 'sankey', 'sunburst', 'graph', 'themeRiver', 'calendar'];
    const showZoom = showDataZoom && !noZoomTypes.includes(type) && cleanData.length > 10;
    const noToolboxTypes = ['metric', 'gauge'];
    const noGridTypes = ['pie', 'donut', 'gauge', 'metric', 'radar', 'funnel', 'treemap', 'sankey', 'sunburst', 'graph', 'parallel', 'themeRiver', 'calendar'];
    const itemTriggerTypes = ['pie', 'donut', 'treemap', 'funnel', 'sunburst', 'graph'];

    // Build toolbox only for supported chart types
    // Using minimal configuration to avoid ECharts internal errors
    let toolboxConfig = undefined;
    if (showToolbox && !noToolboxTypes.includes(type)) {
      try {
        toolboxConfig = {
          show: true,
          feature: {
            saveAsImage: {
              show: true,
              type: 'png',
              pixelRatio: 2,
              name: 'chart'
            }
          },
          right: 10,
          top: 5,
          showTitle: true
        };
      } catch (e) {
        console.warn('[EChartsVisualization] Toolbox config error:', e);
        toolboxConfig = undefined;
      }
    }

    const option = {
      // Title
      title: title ? {
        text: title,
        left: 'center',
        textStyle: {
          color: muiTheme.palette.text.primary,
          fontSize: 16,
          fontWeight: 600
        }
      } : undefined,

      // Tooltip
      tooltip: {
        trigger: itemTriggerTypes.includes(type) ? 'item' : 'axis',
        backgroundColor: muiTheme.palette.mode === 'dark'
          ? 'rgba(30, 30, 30, 0.95)'
          : 'rgba(255, 255, 255, 0.95)',
        borderColor: muiTheme.palette.divider,
        textStyle: { color: muiTheme.palette.text.primary },
        confine: true
      },

      // Toolbox
      toolbox: toolboxConfig,

      // Data zoom - only add for chart types that support it
      ...(showZoom ? {
        dataZoom: [
          { type: 'inside', start: 0, end: 100, filterMode: 'filter' },
          { type: 'slider', start: 0, end: 100, bottom: 10, height: 20 }
        ]
      } : {}),

      // Grid (for proper spacing)
      grid: !noGridTypes.includes(type) ? {
        left: '3%',
        right: '4%',
        bottom: showZoom ? 60 : '3%',
        top: title ? 50 : 30,
        containLabel: true
      } : undefined,

      // Legend for pie/donut charts
      legend: ['pie', 'donut'].includes(type) ? {
        orient: 'horizontal',
        bottom: 0,
        textStyle: { color: muiTheme.palette.text.secondary }
      } : undefined,

      // Animation
      animation: true,
      animationDuration: 500,

      // Merge chart-specific config
      ...chartConfig
    };

    // Remove undefined properties to prevent ECharts errors
    const cleanOption = Object.fromEntries(
      Object.entries(option).filter(([_, v]) => v !== undefined)
    );

    // Debug info for troubleshooting
    const debugInfo = {
      detectedType: type,
      xKey,
      yKey,
      dataLength: Array.isArray(cleanData) ? cleanData.length : 0,
      hasToolbox: !!toolboxConfig,
      hasDataZoom: showZoom
    };

    // Log for debugging in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[EChartsVisualization] Chart config:', debugInfo);
    }

    return { isValid: true, option: cleanOption, debugInfo };
  }, [data, chartType, title, muiTheme, propXKey, propYKey, showToolbox, showDataZoom]);

  // Event handlers
  const handleEvents = useMemo(() => ({
    click: (params) => {
      if (onChartClick) {
        onChartClick({
          name: params.name,
          value: params.value,
          dataIndex: params.dataIndex,
          seriesName: params.seriesName,
          data: params.data
        });
      }
    },
    brushSelected: (params) => {
      if (onBrushSelected) {
        onBrushSelected(params);
      }
    }
  }), [onChartClick, onBrushSelected]);

  // Render error state
  if (!isValid) {
    return (
      <Box
        sx={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 1
        }}
      >
        <Alert severity="info" sx={{ maxWidth: 400 }}>
          {errorMessage}
        </Alert>
      </Box>
    );
  }

  // Generate a stable key based on data to help React track changes
  const chartKey = useMemo(() => {
    if (!data) return 'empty';
    if (Array.isArray(data)) {
      // Use first item's values to create a semi-stable key
      const firstItem = data[0];
      const itemHash = firstItem ? Object.values(firstItem).slice(0, 3).join('-') : '';
      return `chart-${chartType}-${data.length}-${itemHash}`;
    }
    return `chart-${chartType}-obj`;
  }, [data, chartType]);

  return (
    <ChartErrorBoundary height={height}>
      <ReactECharts
        key={chartKey}
        option={option}
        style={{ height, width: '100%' }}
        onEvents={handleEvents}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
        lazyUpdate={false}
      />
    </ChartErrorBoundary>
  );
};

export default EChartsVisualization;
