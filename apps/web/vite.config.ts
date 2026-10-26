import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { apiPort, webPort } from './serverPorts';

export default defineConfig({
  plugins: [react()],
  server: { port: webPort, strictPort: true, proxy: { '/api': {
    target: `http://127.0.0.1:${apiPort}`, rewrite: path => path.replace(/^\/api/, ''),
  } } },
});
