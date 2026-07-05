import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// dev 프록시로 serving(:8080)에 붙는다 — CORS 설정 없이 same-origin처럼 동작.
const SERVING = process.env.SERVING_URL ?? 'http://localhost:8080'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': SERVING,
      '/events': SERVING,
      '/health': SERVING,
    },
  },
  test: {
    environment: 'node',
  },
})
