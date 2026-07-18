import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base so the built deck works when opened from any static host
// or a subpath (GitHub Pages, an internal wiki, a local file server).
export default defineConfig({
  base: './',
  plugins: [react()],
});
