import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/run-scraper': { target: 'http://localhost:8000', changeOrigin: true },
      '/results': { target: 'http://localhost:8000', changeOrigin: true },
      '/jobs': { target: 'http://localhost:8000', changeOrigin: true },
      '/fix-images': { target: 'http://localhost:8000', changeOrigin: true },
      '/upload-csv': { target: 'http://localhost:8000', changeOrigin: true },
      '/process-csv': { target: 'http://localhost:8000', changeOrigin: true },
      '/processed': { target: 'http://localhost:8000', changeOrigin: true },
      '/static': { target: 'http://localhost:8000', changeOrigin: true }
    }
  }
});
