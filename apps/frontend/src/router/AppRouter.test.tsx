import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type * as SessionApiModule from '@/api/sessionApi'
import { HttpError } from '@/api/errors/HttpError'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { AppRouter } from './AppRouter'
import { buildHistoryDetailPath } from './routes'

// As telas de histórico buscam sessões de verdade — para este smoke test de roteamento, uma
// lista vazia é suficiente e evita qualquer chamada de rede real.
vi.mock('@/api/sessionApi', async () => {
  const actual = await vi.importActual<typeof SessionApiModule>('@/api/sessionApi')
  return {
    ...actual,
    listSessionIds: vi.fn().mockResolvedValue([]),
    getSession: vi.fn().mockRejectedValue(new HttpError(404, 'não encontrada')),
  }
})

function renderAt(path: string, enableDevRoute = false): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider>
        <RunConfigProvider>
          <ViewModeProvider>
            <AppRouter enableDevRoute={enableDevRoute} />
          </ViewModeProvider>
        </RunConfigProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('AppRouter', () => {
  it('renderiza a Home em /', () => {
    renderAt('/')
    expect(screen.getByRole('heading', { name: 'Harness de IA' })).toBeInTheDocument()
  })

  it('renderiza a Inferência Simples em /chat/simples', () => {
    renderAt('/chat/simples')
    expect(screen.getByText('Faça uma pergunta para começar')).toBeInTheDocument()
  })

  it('renderiza o Ralph Loop Adaptado em /chat/ralph', () => {
    renderAt('/chat/ralph')
    expect(screen.getByText('Faça uma pergunta para começar')).toBeInTheDocument()
  })

  it('renderiza o Histórico em /historico', async () => {
    renderAt('/historico')
    expect(await screen.findByRole('heading', { name: 'Histórico' })).toBeInTheDocument()
  })

  it('renderiza o detalhe do histórico com o sessionId da URL', async () => {
    renderAt('/historico/sess_ab12cd34ef56')
    expect(await screen.findByText('Esta conversa não existe mais')).toBeInTheDocument()
  })

  it('cai na tela de não encontrado para uma rota desconhecida', () => {
    renderAt('/rota/que/nao/existe')
    expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
  })

  it('sem enableDevRoute, /dev/componentes cai em não encontrado', () => {
    renderAt('/dev/componentes')
    expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
  })

  it('com enableDevRoute, /dev/componentes mostra o catálogo', () => {
    renderAt('/dev/componentes', true)
    expect(screen.getByRole('heading', { name: 'Catálogo de componentes' })).toBeInTheDocument()
  })
})

describe('buildHistoryDetailPath', () => {
  it('escapa um id com caractere especial', () => {
    expect(buildHistoryDetailPath('sess ab/cd')).toBe('/historico/sess%20ab%2Fcd')
  })
})
