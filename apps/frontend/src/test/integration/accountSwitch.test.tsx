// Troca de conta no mesmo navegador: nada da conta anterior pode aparecer para a seguinte, e os
// dados pessoais persistidos no servidor voltam no próximo login da mesma conta.
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppProviders } from '@/app/AppProviders'
import type { AuthSessionView } from '@/domain/types/auth'
import { getAllCachedSessions } from '@/hooks/sessionCache'
import { AppRouter } from '@/router/AppRouter'
import { FakeWebSocket } from '@/test/doubles/FakeWebSocket'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import { CREDENCIAL_VALIDA, fakeAuthApi } from '@/test/renderWithAuth'

function sessao(id: string, email: string): AuthSessionView {
  return { user: { id, email, role: 'user' }, expiresAt: '2026-11-16T12:00:00+00:00', csrfToken: `csrf-${id}` }
}

const HISTORICO: Record<string, Array<{ id: string; pergunta: string }>> = {
  usr_ana: [{ id: 'sess_da_ana', pergunta: 'Pergunta secreta da Ana' }],
  usr_bia: [{ id: 'sess_da_bia', pergunta: 'Pergunta da Bia' }],
}

function respond(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve({ status, text: () => Promise.resolve(JSON.stringify(body)) } as Response)
}

beforeEach(() => {
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('troca de conta no mesmo navegador', () => {
  it('limpa histórico, caches e conexões da conta anterior e recupera os dados no novo login', async () => {
    let atual: string | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const path = new URL(url).pathname
        if (path === '/v1/public/benchmarks') return respond({ publications: [] })
        if (atual === null) return respond({ detail: 'Faça login para continuar.' }, 401)
        if (path === '/v1/sessions') return respond({ session_ids: HISTORICO[atual]?.map((item) => item.id) ?? [] })
        const item = HISTORICO[atual]?.find((entry) => path.endsWith(`/${entry.id}`))
        if (item) return respond({ ...completedFixture, id: item.id, user_question: item.pergunta, benchmark_details: null })
        if (path === '/v1/models') return respond({ models: [] })
        if (path === '/v1/limits') return respond({ max_tokens_limit: 100000 })
        return respond({ detail: 'não encontrado' }, 404)
      }),
    )
    const api = fakeAuthApi({
      login: vi.fn(async (email: string) => {
        atual = email.startsWith('ana') ? 'usr_ana' : 'usr_bia'
        return sessao(atual, email)
      }),
      logout: vi.fn(async () => {
        atual = null
      }),
      getCredentialStatus: vi.fn().mockResolvedValue(CREDENCIAL_VALIDA),
    })
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/entrar?next=/historico']}>
        <AppProviders authApi={api}>
          <AppRouter />
        </AppProviders>
      </MemoryRouter>,
    )

    async function entrar(email: string): Promise<void> {
      await user.type(await screen.findByLabelText('E-mail'), email)
      await user.type(screen.getByLabelText('Senha'), 'senha muito boa 1')
      await user.click(screen.getByRole('button', { name: 'Entrar' }))
    }

    await entrar('ana@exemplo.com')
    expect(await screen.findByText('Pergunta secreta da Ana')).toBeInTheDocument()
    const socket = new FakeWebSocket('ws://exemplo')
    expect(getAllCachedSessions().map((item) => item.id)).toContain('sess_da_ana')

    await user.click(screen.getByRole('button', { name: 'Sair' }))
    await waitFor(() => expect(api.logout).toHaveBeenCalled())
    expect(screen.queryByText('Pergunta secreta da Ana')).not.toBeInTheDocument()
    expect(getAllCachedSessions()).toEqual([])
    act(() => socket.emitClose(1000))

    // O convite da página privada volta para o histórico depois do login.
    await user.click((await screen.findAllByRole('link', { name: 'Entrar' })).at(-1) as HTMLElement)
    await entrar('bia@exemplo.com')
    expect(await screen.findByText('Pergunta da Bia')).toBeInTheDocument()
    expect(screen.queryByText('Pergunta secreta da Ana')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sair' }))
    await user.click((await screen.findAllByRole('link', { name: 'Entrar' })).at(-1) as HTMLElement)
    await entrar('ana@exemplo.com')
    expect(await screen.findByText('Pergunta secreta da Ana')).toBeInTheDocument()
    expect(screen.queryByText('Pergunta da Bia')).not.toBeInTheDocument()
  })

  it('uma bateria em andamento é desconectada quando a sessão termina', async () => {
    const { BenchmarkRunProvider, useBenchmarkRun } = await import('@/state/BenchmarkRunContext')
    const { emitUnauthorized } = await import('@/api/authEvents')
    vi.stubGlobal('fetch', vi.fn(() => respond({ publications: [] })))
    let iniciar: (() => void) | null = null
    function Sonda(): null {
      const run = useBenchmarkRun()
      iniciar = () =>
        run.start({
          questionCount: 1,
          maxParallel: 1,
          config: { modelName: 'm', maxTokens: 1000, temperature: 0.3, provider: 'open_router' },
        })
      return null
    }
    render(
      <MemoryRouter>
        <AppProviders
          authApi={fakeAuthApi()}
          initialAuth={{ session: sessao('usr_ana', 'ana@exemplo.com'), credential: CREDENCIAL_VALIDA }}
        >
          <BenchmarkRunProvider>
            <Sonda />
          </BenchmarkRunProvider>
        </AppProviders>
      </MemoryRouter>,
    )
    await waitFor(() => expect(iniciar).not.toBeNull())
    act(() => iniciar?.())
    const socket = FakeWebSocket.latest()

    act(() => emitUnauthorized())

    await waitFor(() => expect(socket.closeCalls.length).toBeGreaterThan(0))
  })
})
