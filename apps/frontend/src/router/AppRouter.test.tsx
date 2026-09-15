import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { AppRouter } from './AppRouter'
import { buildHistoryDetailPath } from './routes'

function renderAt(path: string, enableDevRoute = false): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider>
        <RunConfigProvider>
          <AppRouter enableDevRoute={enableDevRoute} />
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
    expect(screen.getByRole('heading', { name: 'Ralph Loop Adaptado' })).toBeInTheDocument()
  })

  it('renderiza o Histórico em /historico', () => {
    renderAt('/historico')
    expect(screen.getByRole('heading', { name: 'Histórico' })).toBeInTheDocument()
  })

  it('renderiza o detalhe do histórico com o sessionId da URL', () => {
    renderAt('/historico/sess_ab12cd34ef56')
    expect(screen.getByText('Sessão: sess_ab12cd34ef56')).toBeInTheDocument()
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
