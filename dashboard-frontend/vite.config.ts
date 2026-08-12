import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// during development, the vite dev server proxies api/ws calls to the fastapi
// backend (second_brain/dashboard/server.py) running on port 8420 - in production
// the backend serves this project's built static output directly, no proxy needed
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8420',
      '/ws': {
        target: 'ws://127.0.0.1:8420',
        ws: true,
      },
    },
  },
})
