/// <reference types="vitest/config" />
import path from 'node:path';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, 'src') },
  },
  // DEMO track: the demo backend from deploy/compose/local/compose.demo.yml.
  server: { host: 'localhost', port: 5173, proxy: { '/api/demo': { target: 'http://127.0.0.1:8000', changeOrigin: false } } },
  preview: { host: 'localhost', port: 4173, proxy: { '/api/demo': { target: 'http://127.0.0.1:8000', changeOrigin: false } } },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
    css: false,
  },
});
