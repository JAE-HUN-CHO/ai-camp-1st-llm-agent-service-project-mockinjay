import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Keep production environment validation strict while giving unit tests a
  // deterministic, local adapter configuration. Never hard-code these values
  // into a production bundle.
  ...(mode === 'test' ? {
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://localhost:8000'),
      'import.meta.env.VITE_APP_NAME': JSON.stringify('CareGuide'),
      'import.meta.env.VITE_APP_ENV': JSON.stringify('development'),
    },
  } : {}),
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        '**/types',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
}));
