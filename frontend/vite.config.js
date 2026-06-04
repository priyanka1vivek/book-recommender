import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite configuration — tells the development server how to run.
// The proxy section is critical: instead of the frontend calling
// http://localhost:8000 directly (which can cause CORS issues),
// it calls /api/... and Vite silently forwards those requests to the
// backend. The frontend never has to know the backend's port.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      // Any request starting with /api gets forwarded to the FastAPI backend.
      // Example: frontend calls /api/recommend/vibe
      //          Vite forwards to http://localhost:8000/recommend/vibe
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
