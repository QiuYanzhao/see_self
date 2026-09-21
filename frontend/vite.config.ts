import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发期 /api 代理到 FastAPI（默认 8080）；生产构建产物由 FastAPI 托管
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
