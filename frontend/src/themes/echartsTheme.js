/**
 * Custom ECharts theme matching Material UI / Mantrix design system.
 *
 * This theme provides consistent styling across all ECharts visualizations
 * with support for both light and dark modes.
 */

import * as echarts from 'echarts';

// Mantrix brand colors
const MANTRIX_COLORS = [
  '#6366f1', // Indigo (primary)
  '#22c55e', // Green (success)
  '#f59e0b', // Amber (warning)
  '#ef4444', // Red (error)
  '#8b5cf6', // Purple
  '#06b6d4', // Cyan
  '#ec4899', // Pink
  '#14b8a6', // Teal
  '#f97316', // Orange
  '#84cc16', // Lime
  '#3b82f6', // Blue
  '#a855f7'  // Violet
];

// Light theme configuration
export const mantrixLightTheme = {
  color: MANTRIX_COLORS,
  backgroundColor: 'transparent',

  textStyle: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },

  title: {
    textStyle: {
      color: '#1e293b',
      fontWeight: 600,
      fontSize: 16
    },
    subtextStyle: {
      color: '#64748b',
      fontSize: 12
    }
  },

  legend: {
    textStyle: {
      color: '#64748b'
    }
  },

  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.96)',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    textStyle: {
      color: '#334155'
    },
    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);'
  },

  axisPointer: {
    lineStyle: {
      color: '#94a3b8'
    },
    crossStyle: {
      color: '#94a3b8'
    }
  },

  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#e2e8f0'
      }
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      color: '#64748b'
    },
    splitLine: {
      show: false
    }
  },

  valueAxis: {
    axisLine: {
      show: false
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      color: '#64748b'
    },
    splitLine: {
      lineStyle: {
        color: '#f1f5f9',
        type: 'dashed'
      }
    }
  },

  line: {
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: {
      width: 2
    }
  },

  bar: {
    itemStyle: {
      borderRadius: [4, 4, 0, 0]
    }
  },

  pie: {
    itemStyle: {
      borderColor: '#fff',
      borderWidth: 2
    }
  },

  scatter: {
    symbolSize: 10
  },

  gauge: {
    axisLine: {
      lineStyle: {
        width: 15,
        color: [
          [0.3, '#ef4444'],
          [0.7, '#f59e0b'],
          [1, '#22c55e']
        ]
      }
    }
  },

  dataZoom: {
    backgroundColor: 'transparent',
    dataBackgroundColor: '#f1f5f9',
    fillerColor: 'rgba(99, 102, 241, 0.2)',
    handleColor: '#6366f1',
    handleSize: '100%',
    textStyle: {
      color: '#64748b'
    }
  },

  toolbox: {
    iconStyle: {
      borderColor: '#94a3b8'
    },
    emphasis: {
      iconStyle: {
        borderColor: '#6366f1'
      }
    }
  }
};

// Dark theme configuration
export const mantrixDarkTheme = {
  color: MANTRIX_COLORS,
  backgroundColor: 'transparent',

  textStyle: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },

  title: {
    textStyle: {
      color: '#f1f5f9',
      fontWeight: 600,
      fontSize: 16
    },
    subtextStyle: {
      color: '#94a3b8',
      fontSize: 12
    }
  },

  legend: {
    textStyle: {
      color: '#94a3b8'
    }
  },

  tooltip: {
    backgroundColor: 'rgba(30, 41, 59, 0.96)',
    borderColor: '#334155',
    borderWidth: 1,
    textStyle: {
      color: '#f1f5f9'
    },
    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);'
  },

  axisPointer: {
    lineStyle: {
      color: '#475569'
    },
    crossStyle: {
      color: '#475569'
    }
  },

  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#334155'
      }
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      color: '#94a3b8'
    },
    splitLine: {
      show: false
    }
  },

  valueAxis: {
    axisLine: {
      show: false
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      color: '#94a3b8'
    },
    splitLine: {
      lineStyle: {
        color: '#1e293b',
        type: 'dashed'
      }
    }
  },

  line: {
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: {
      width: 2
    }
  },

  bar: {
    itemStyle: {
      borderRadius: [4, 4, 0, 0]
    }
  },

  pie: {
    itemStyle: {
      borderColor: '#1e293b',
      borderWidth: 2
    }
  },

  scatter: {
    symbolSize: 10
  },

  gauge: {
    axisLine: {
      lineStyle: {
        width: 15,
        color: [
          [0.3, '#ef4444'],
          [0.7, '#f59e0b'],
          [1, '#22c55e']
        ]
      }
    }
  },

  dataZoom: {
    backgroundColor: 'transparent',
    dataBackgroundColor: '#1e293b',
    fillerColor: 'rgba(99, 102, 241, 0.3)',
    handleColor: '#6366f1',
    handleSize: '100%',
    textStyle: {
      color: '#94a3b8'
    }
  },

  toolbox: {
    iconStyle: {
      borderColor: '#64748b'
    },
    emphasis: {
      iconStyle: {
        borderColor: '#6366f1'
      }
    }
  }
};

// Register themes with ECharts
echarts.registerTheme('mantrix', mantrixLightTheme);
echarts.registerTheme('mantrix-light', mantrixLightTheme);
echarts.registerTheme('mantrix-dark', mantrixDarkTheme);

/**
 * Get the appropriate theme name based on Material UI palette mode.
 * @param {string} mode - 'light' or 'dark'
 * @returns {string} Theme name to use with ECharts
 */
export const getEChartsTheme = (mode) => {
  return mode === 'dark' ? 'mantrix-dark' : 'mantrix-light';
};

export default {
  mantrixLightTheme,
  mantrixDarkTheme,
  getEChartsTheme
};
