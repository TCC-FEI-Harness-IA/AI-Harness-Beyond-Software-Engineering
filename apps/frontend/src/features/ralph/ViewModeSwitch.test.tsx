import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { FakeWebSocket } from '@/test/doubles/FakeWebSocket'
import { RalphPage } from './RalphPage'

function renderPage(): void {
  render(
    <MemoryRouter
      initialEntries={[{ pathname: '/chat/ralph', state: { question: 'pergunta', autoStart: true } }]}
    >
      <RunConfigProvider>
        <ViewModeProvider>
          <RalphPage />
        </ViewModeProvider>
      </RunConfigProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ViewModeSwitch', () => {
  it('alternar troca o modo montado', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(screen.getByText('Nenhum passo ainda')).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /Chat/ }))

    expect(screen.queryByText('Nenhum passo ainda')).not.toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Mensagem do usuário' })).toHaveTextContent('pergunta')
  })

  it('a escolha persiste em localStorage', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('radio', { name: /Chat/ }))

    expect(window.localStorage.getItem('tcc.viewMode')).toBe('chat')
  })

  it('o atalho de teclado (⌘/Ctrl + \\) alterna o modo', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.keyboard('{Control>}\\{/Control}')

    expect(window.localStorage.getItem('tcc.viewMode')).toBe('chat')
    expect(screen.getByRole('group', { name: 'Mensagem do usuário' })).toHaveTextContent('pergunta')
  })

  it('o stream não é reiniciado ao alternar de modo', async () => {
    const user = userEvent.setup()
    renderPage()
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
    })

    await user.click(screen.getByRole('radio', { name: /Chat/ }))
    await user.click(screen.getByRole('radio', { name: /Gráfico/ }))

    expect(socket.closeCalls).toHaveLength(0)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })
})
