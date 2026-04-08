import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: "0.0.0.0",
    allowedHosts: [
      "jae.local"
    ],
    proxy: {
      '/api': 'http://jae.local:8000',
      '/ws': {
        target: 'ws://jae.local:8000',
        ws: true,
      },
    },
  },
})
