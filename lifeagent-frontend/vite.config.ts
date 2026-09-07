import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发期 API 地址：FastAPI 通过 Docker Compose 暴露在宿主机 8080 端口。
// 走代理而不是直连 8080，可以让浏览器始终只与 5173 通信，避免跨域。
// 代理不做路径重写：/api/v1/xxx 原样转发到 http://localhost:8080/api/v1/xxx。
const API_TARGET = 'http://localhost:8080'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: 'localhost',
    port: 5173,
    proxy: {
      '/api/v1': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
