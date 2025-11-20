import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    // 禁用自动刷新，避免与 WebSocket 冲突
    hmr: {
      overlay: true
    }
  }
})

