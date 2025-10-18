import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/run-scraper': 'http://localhost:8000',
      '/results': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
      '/fix-images': 'http://localhost:8000',
      '/static': 'http://localhost:8000'
    }
  }
});
