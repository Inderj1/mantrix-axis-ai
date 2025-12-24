import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/superset': {
        target: 'http://localhost:8088',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/superset/, ''),
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React - always needed
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // UI framework - always needed but can load in parallel
          'vendor-mui': ['@mui/material', '@mui/icons-material'],
          // Charting libraries - load on demand
          'vendor-charts': ['recharts', 'echarts', 'echarts-for-react'],
          // Plotly - very heavy, separate chunk
          'vendor-plotly': ['plotly.js', 'react-plotly.js'],
          // Code editor - load on demand
          'vendor-ace': ['react-ace', 'ace-builds'],
          // Data tables - load on demand
          'vendor-data': ['@mui/x-data-grid', '@tanstack/react-table'],
          // Other visualization
          'vendor-visx': ['@visx/axis', '@visx/curve', '@visx/gradient', '@visx/grid', '@visx/group', '@visx/responsive', '@visx/scale', '@visx/shape', '@visx/text', '@visx/tooltip'],
        }
      }
    },
    // Increase chunk size warning limit (we're intentionally creating large vendor chunks)
    chunkSizeWarningLimit: 1000,
  }
})