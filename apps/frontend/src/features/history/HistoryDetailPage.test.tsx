import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as sessionApi from '@/api/sessionApi'
import type * as SessionApiModule from '@/api/sessionApi'
import { AppShell } from '@/components/layout/AppShell'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import { ROUTES } from '@/router/routes'
import { BenchmarkRunProvider } from '@/state/BenchmarkRunContext'
import { SidebarSlotProvider, useSidebarSlotValue } from '@/state/SidebarSlotContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { HistoryDetailPage } from './HistoryDetailPage'

vi.mock('@/api/sessionApi', async () => {
  const actual = await vi.importActual<typeof SessionApiModule>('@/api/sessionApi')
  return { ...actual, listSessionIds: vi.fn(), getSession: vi.fn() }
})

const listSessionIdsMock = sessionApi.listSessionIds as Mock
const getSessionMock = sessionApi.getSession as Mock

function buildRalphDocument(id: string): SessionDocument {
  return {
    id,
    user_question: 'Quais são os números primos entre 0 e 20?',
    flow: 'A1',
    model_name: 'openai/gpt-4o-mini',
    max_tokens: 1200,
    temperature: 0.3,
    status: 'completed',
    created_at: '2026-09-11T23:18:06.000000+00:00',
    updated_at: '2026-09-11T23:18:07.000000+00:00',
    final_answer: 'Os números primos são 2, 3, 5, 7...',
    totals: {
      total_messages: 3,
      total_llm_calls: 1,
      tokens_input: 10,
      tokens_output: 20,
      total_tokens: 30,
      inference_time_ms: 500,
      wall_time_ms: 600,
    },
    messages: [
      {
        id: 'msg_0',
        order: 0,
        timestamp: '2026-09-11T23:18:06.100000+00:00',
        phase: 'A1',
        source: 'user',
        content: 'Quais são os números primos entre 0 e 20?',
        task_id: null,
        context_id: null,
        tokens_input: 0,
        tokens_output: 0,
        total_tokens: 0,
        inference_time_ms: 0,
        model_name: null,
      },
      {
        id: 'msg_1',
        order: 1,
        timestamp: '2026-09-11T23:18:06.200000+00:00',
        phase: 'A1',
        source: 'llm_agent',
        content: '## Critérios de aceite gerais\n\n- `AC1`: usar português',
        task_id: null,
        context_id: 'ctx_1',
        tokens_input: 10,
        tokens_output: 20,
        total_tokens: 30,
        inference_time_ms: 500,
        model_name: 'openai/gpt-4o-mini',
      },
    ],
    degradations: [],
  }
}

function buildDirectDocument(id: string): SessionDocument {
  return {
    id,
    user_question: 'Me conte uma piada',
    flow: 'DIRECT',
    model_name: 'openai/gpt-4o-mini',
    max_tokens: 1000,
    temperature: 0.3,
    status: 'completed',
    created_at: '2026-09-11T23:18:06.000000+00:00',
    updated_at: '2026-09-11T23:18:07.000000+00:00',
    final_answer: 'Por que...',
    totals: {
      total_messages: 2,
      total_llm_calls: 1,
      tokens_input: 5,
      tokens_output: 10,
      total_tokens: 15,
      inference_time_ms: 300,
      wall_time_ms: 300,
    },
    messages: [
      {
        id: 'msg_0',
        order: 0,
        timestamp: '2026-09-11T23:18:06.100000+00:00',
        phase: 'DIRECT',
        source: 'user',
        content: 'Me conte uma piada',
        task_id: null,
        context_id: null,
        tokens_input: 0,
        tokens_output: 0,
        total_tokens: 0,
        inference_time_ms: 0,
        model_name: null,
      },
      {
        id: 'msg_1',
        order: 1,
        timestamp: '2026-09-11T23:18:06.200000+00:00',
        phase: 'DIRECT',
        source: 'llm_agent',
        content: 'Por que...',
        task_id: null,
        context_id: null,
        tokens_input: 5,
        tokens_output: 10,
        total_tokens: 15,
        inference_time_ms: 300,
        model_name: 'openai/gpt-4o-mini',
      },
    ],
    degradations: [],
  }
}

// Sonda o slot registrado por `HistoryDetailPage` e o repassa ao `AppShell`, exatamente como o
// `AppRouter` faz de verdade — sem isso, a barra lateral nunca apareceria neste teste isolado.
function SlotBridge({ children }: { children: React.ReactNode }): JSX.Element {
  const sidebar = useSidebarSlotValue()
  return <AppShell sidebar={sidebar ?? undefined}>{children}</AppShell>
}

function renderDetail(sessionId: string): void {
  render(
    <MemoryRouter initialEntries={[`/historico/${sessionId}`]}>
      <ThemeProvider>
        <ViewModeProvider>
          <BenchmarkRunProvider>
          <SidebarSlotProvider>
            <SlotBridge>
              <Routes>
                <Route path={ROUTES.historyDetail} element={<HistoryDetailPage />} />
              </Routes>
            </SlotBridge>
          </SidebarSlotProvider>
          </BenchmarkRunProvider>
        </ViewModeProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  listSessionIdsMock.mockReset()
  getSessionMock.mockReset()
  listSessionIdsMock.mockResolvedValue([])
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('HistoryDetailPage', () => {
  it('sessão Ralph renderiza o RalphView com o interruptor de modo', async () => {
    getSessionMock.mockResolvedValue(buildRalphDocument('sess_ralph_1'))

    renderDetail('sess_ralph_1')

    expect(await screen.findByRole('radiogroup', { name: /Modo de visualização/i })).toBeInTheDocument()
  })

  it('sessão DIRECT renderiza o SimpleChatView sem o interruptor', async () => {
    getSessionMock.mockResolvedValue(buildDirectDocument('sess_direct_1'))

    renderDetail('sess_direct_1')

    expect(await screen.findByText('Me conte uma piada')).toBeInTheDocument()
    expect(screen.queryByRole('radiogroup', { name: /Modo de visualização/i })).not.toBeInTheDocument()
  })

  it('a barra lateral marca o item ativo com aria-current', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_ralph_2', 'sess_other'])
    getSessionMock.mockImplementation((id: string) =>
      Promise.resolve(id === 'sess_other' ? buildDirectDocument(id) : buildRalphDocument(id)),
    )

    renderDetail('sess_ralph_2')

    const activeLink = await screen.findByRole('link', { current: 'page' })
    expect(activeLink).toHaveAccessibleName(expect.stringContaining('primos'))
  })

  it('trocar de conversa pela barra lateral não desmonta o AppShell', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_ralph_3', 'sess_direct_2'])
    getSessionMock.mockImplementation((id: string) =>
      Promise.resolve(id === 'sess_direct_2' ? buildDirectDocument(id) : buildRalphDocument(id)),
    )
    const user = userEvent.setup()

    renderDetail('sess_ralph_3')
    await screen.findByRole('radiogroup', { name: /Modo de visualização/i })

    const otherLink = await screen.findByRole('link', { name: /Me conte uma piada/ })
    await user.click(otherLink)

    await waitFor(() => expect(screen.getAllByText('Me conte uma piada').length).toBeGreaterThan(0))
    // O `AppShell`/`TopBar` seguem montados — a marca do app continua visível.
    expect(screen.getByRole('link', { name: 'TCC Harness' })).toBeInTheDocument()
  })

  it('404 mostra a mensagem de sessão inexistente e um caminho de volta', async () => {
    const { HttpError } = await import('@/api/errors/HttpError')
    getSessionMock.mockRejectedValue(new HttpError(404, 'não encontrada'))

    renderDetail('sess_inexistente')

    expect(await screen.findByText('Esta conversa não existe mais')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Voltar ao histórico' })).toBeInTheDocument()
  })
})
