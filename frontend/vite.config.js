import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // In development, forward API calls to Django.
    proxy: { '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8000' },
  },
  test: { environment: 'jsdom' },
})
