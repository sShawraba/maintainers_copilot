import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: './src/widget.jsx',
      name: 'MaintainersCopilotWidget',
      formats: ['iife'],
    },
    rollupOptions: {
      output: {
        dir: 'dist',
        entryFileNames: 'widget.js',
        format: 'iife',
        name: 'MaintainersCopilotWidget',
        globals: {},
      },
    },
    minify: 'terser',
    sourcemap: false,
    target: 'ES2020',
  },
  server: {
    port: 5173,
    open: true,
  },
});
