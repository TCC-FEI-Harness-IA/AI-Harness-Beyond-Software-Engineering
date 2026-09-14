import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@/state/ThemeContext'
import { AppRouter } from './AppRouter'
import { buildHistoryDetailPath } from './routes'

function renderAt(path: string): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider>
        <AppRouter />
      </ThemeProvider>
    </MemoryRouter>,
  )
}

describe('AppRouter', () => {
  it('renderiza a Home em /', () => {
    renderAt('/')
    expect(screen.getByRole('heading', { name: 'Home' })).toBeInTheDocument()
  })

  it('renderiza a Inferência Simples em /chat/simples', () => {
    renderAt('/chat/simples')
    expect(screen.getByRole('heading', { name: 'Inferência Simples' })).toBeInTheDocument()
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
})

describe('buildHistoryDetailPath', () => {
  it('escapa um id com caractere especial', () => {
    expect(buildHistoryDetailPath('sess ab/cd')).toBe('/historico/sess%20ab%2Fcd')
  })
})
