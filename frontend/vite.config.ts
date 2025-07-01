import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts: [
      'localhost',
      '54.211.160.83',
      '.ngrok.io',
      '.ngrok-free.app',
      'back-agent.com',
      '*.back-agent.com',
      '*.trycloudflare.com'
    ],
    hmr: false, // Disable HMR for stability
    proxy: {
      '/api': {
        target: 'https://api.back-agent.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/ws': {
        target: 'wss://api.back-agent.com',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist'
  }
})
