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
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/index.ts',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/test/**',
        'src/features/dev/**',
      ],
      // Limiares mínimos por camada (README, FASE 08, seção 6.1) — a regressão falha o comando.
      thresholds: {
        'src/domain/services/**': { statements: 100, branches: 100, functions: 100, lines: 100 },
        'src/api/**': { statements: 90, branches: 90, functions: 90, lines: 90 },
        'src/hooks/**': { statements: 85, branches: 85, functions: 85, lines: 85 },
        'src/components/**': { statements: 70, branches: 70, functions: 70, lines: 70 },
        'src/features/**': { statements: 70, branches: 70, functions: 70, lines: 70 },
      },
    },
  },
})
