import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Alias '@' resolvido via URL global (evita depender de '@types/node' para 'node:url').
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': new URL('./src', import.meta.url).pathname },
  },
  build: {
    rollupOptions: {
      output: {
        // A partir da FASE 04, `src/config/env.ts` passou a ser alcançado tanto pelo import
        // dinâmico de `main.tsx` quanto por imports estáticos de módulos que falam com a rede
        // (`httpClient`, `websocketClient`, `RunConfigContext`). Sem isto, o Rollup funde
        // `env.ts` no chunk estático e emite o aviso "dynamic import will not move module into
        // another chunk" — força-o para o próprio chunk para eliminar o aviso.
        manualChunks(id) {
          if (id.includes('/src/config/env.ts')) return 'env'
          return undefined
        },
      },
    },
  },
  server: { port: 5173 },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
