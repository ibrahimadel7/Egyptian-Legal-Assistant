import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendProxy = env.BACKEND_PROXY_URL || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      proxy: {
        '/api': { target: backendProxy, changeOrigin: true },
        '/health': { target: backendProxy, changeOrigin: true },
      },
    },
    test: { environment: 'jsdom', setupFiles: './src/testSetup.ts' },
  };
});
