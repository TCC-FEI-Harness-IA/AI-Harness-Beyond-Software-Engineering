import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AppRouter } from '@/router/AppRouter'
import { ThemeProvider } from '@/state/ThemeContext'
import './styles/reset.css'
import './styles/tokens.css'
import './styles/animations.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Elemento #root não encontrado em index.html')
}

// Tela mínima de erro de configuração — não depende de nenhum outro módulo do app,
// para funcionar mesmo quando o boot falha antes de qualquer render.
function renderConfigError(message: string, root: HTMLElement): void {
  root.innerHTML = `
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 640px; margin: 80px auto; padding: 0 24px; color: #1D1D1F;">
      <h1 style="font-size: 22px; margin-bottom: 12px;">Erro de configuração</h1>
      <p style="line-height: 1.55;">${message}</p>
    </div>
  `
}

async function bootstrap(root: HTMLElement): Promise<void> {
  try {
    // Import dinâmico: se loadEnv() lançar, cai no catch antes de qualquer render. Mantido
    // dinâmico (em vez de um import estático em AppRouter) para que src/config/env não entre
    // no grafo estático do router — só o boot precisa decidir a rota de depuração.
    const { env } = await import('@/config/env')

    createRoot(root).render(
      <StrictMode>
        <BrowserRouter>
          <ThemeProvider>
            <AppRouter enableDevRoute={env.enableDebugPanel} />
          </ThemeProvider>
        </BrowserRouter>
      </StrictMode>,
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Erro desconhecido ao iniciar o app.'
    renderConfigError(message, root)
  }
}

void bootstrap(rootElement)
