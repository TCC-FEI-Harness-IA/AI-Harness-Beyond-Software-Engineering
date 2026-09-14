import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Alias '@' resolvido via URL global (evita depender de '@types/node' para 'node:url').
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': new URL('./src', import.meta.url).pathname },
  },
  server: { port: 5173 },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
