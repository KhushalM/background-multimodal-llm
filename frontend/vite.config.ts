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
      '.ngrok-free.app'
    ],
    hmr: {
      port: 3000,
      host: '4c80-54-211-160-83.ngrok-free.app'
    },
    proxy: {
      '/api': {
        target: 'https://a4c8-54-211-160-83.ngrok-free.app',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/ws': {
        target: 'wss://a4c8-54-211-160-83.ngrok-free.app',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist'
  }
})
