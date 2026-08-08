import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base so a build can be served from any static host or subpath.
export default defineConfig({
  base: './',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    globals: true,
  },
});
