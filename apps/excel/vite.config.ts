/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 3000,
    https: process.env.HTTPS === 'true',
  },
  preview: {
    port: 3333,
    https: false,
  },
  build: {
    rollupOptions: {
      input: {
        taskpane: './taskpane.html',
        functions: './src/functions.ts',
      },
      output: {
        entryFileNames: '[name]/[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
});
