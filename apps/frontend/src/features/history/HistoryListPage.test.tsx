import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as sessionApi from '@/api/sessionApi'
import type * as SessionApiModule from '@/api/sessionApi'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import { ROUTES } from '@/router/routes'
import { HistoryListPage } from './HistoryListPage'

vi.mock('@/api/sessionApi', async () => {
  const actual = await vi.importActual<typeof SessionApiModule>('@/api/sessionApi')
  return { ...actual, listSessionIds: vi.fn(), getSession: vi.fn() }
})

const listSessionIdsMock = sessionApi.listSessionIds as Mock
const getSessionMock = sessionApi.getSession as Mock

function buildDocument(overrides: Partial<SessionDocument> & { id: string }): SessionDocument {
  return {
    user_question: 'Pergunta padrão',
    flow: 'A1',
    model_name: 'openai/gpt-4o-mini',
    max_tokens: 1000,
    temperature: 0.3,
    status: 'completed',
    created_at: '2026-09-11T23:18:06.000000+00:00',
    updated_at: '2026-09-11T23:18:07.000000+00:00',
    final_answer: 'Resposta',
    totals: {
      total_messages: 2,
      total_llm_calls: 1,
      tokens_input: 10,
      tokens_output: 20,
      total_tokens: 30,
      inference_time_ms: 500,
      wall_time_ms: 600,
    },
    messages: [],
    degradations: [],
    ...overrides,
  }
}

function DestinationProbe(): JSX.Element {
  return <div data-testid="destination">Detalhe</div>
}

function renderPage(initialPath = ROUTES.history): void {
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path={ROUTES.history} element={<HistoryListPage />} />
        <Route path={ROUTES.historyDetail} element={<DestinationProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  listSessionIdsMock.mockReset()
  getSessionMock.mockReset()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('HistoryListPage', () => {
  // Ids únicos por teste: o cache em memória de `useSessionList` é um singleton de módulo que
  // sobrevive entre os testes deste arquivo — reusar um id faria o segundo teste enxergar o
  // documento cacheado pelo primeiro em vez de buscar o seu próprio.
  it('mostra os cards com o input do usuário truncado', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_truncate'])
    getSessionMock.mockResolvedValue(
      buildDocument({ id: 'sess_truncate', user_question: 'Quais são todos os números primos entre 0 e 20?' }),
    )

    renderPage()

    expect(await screen.findByText(/Quais são todos os números primos/)).toBeInTheDocument()
  })

  it('clicar num card navega para o detalhe, sem refresh', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_click'])
    getSessionMock.mockResolvedValue(buildDocument({ id: 'sess_click', user_question: 'Pergunta clicável' }))
    const user = userEvent.setup()

    renderPage()

    const link = await screen.findByRole('link', { name: /Pergunta clicável/ })
    await user.click(link)

    expect(await screen.findByTestId('destination')).toBeInTheDocument()
  })

  it('a busca filtra ignorando acentuação e caixa, e fica na URL', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_search_1', 'sess_search_2'])
    getSessionMock.mockImplementation((id: string) =>
      Promise.resolve(
        buildDocument({
          id,
          user_question: id === 'sess_search_1' ? 'Números primos' : 'Piada de programador',
        }),
      ),
    )
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Números primos')
    await user.type(screen.getByRole('searchbox', { name: 'Buscar no histórico' }), 'NUMEROS')

    await waitFor(() => expect(screen.queryByText('Piada de programador')).not.toBeInTheDocument())
    expect(screen.getByText('Números primos')).toBeInTheDocument()
  })

  it('o filtro de fluxo mostra só o fluxo selecionado', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_flow_ralph', 'sess_flow_simples'])
    getSessionMock.mockImplementation((id: string) =>
      Promise.resolve(
        buildDocument({
          id,
          flow: id === 'sess_flow_ralph' ? 'A1' : 'DIRECT',
          user_question: id === 'sess_flow_ralph' ? 'Pergunta Ralph' : 'Pergunta Simples',
        }),
      ),
    )
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Pergunta Ralph')
    await user.click(screen.getByRole('radio', { name: 'Simples' }))

    await waitFor(() => expect(screen.queryByText('Pergunta Ralph')).not.toBeInTheDocument())
    expect(screen.getByText('Pergunta Simples')).toBeInTheDocument()
  })

  it('lista vazia mostra o EmptyState com uma ação de saída', async () => {
    listSessionIdsMock.mockResolvedValue([])

    renderPage()

    expect(await screen.findByText('Nenhuma conversa ainda')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fazer uma pergunta' })).toBeInTheDocument()
  })

  it('busca sem resultado mostra o EmptyState de busca com "Limpar busca"', async () => {
    listSessionIdsMock.mockResolvedValue(['sess_no_match'])
    getSessionMock.mockResolvedValue(buildDocument({ id: 'sess_no_match', user_question: 'Pergunta única' }))
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Pergunta única')
    await user.type(screen.getByRole('searchbox', { name: 'Buscar no histórico' }), 'inexistente')

    expect(await screen.findByText(/Nada encontrado para/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Limpar busca' })).toBeInTheDocument()
  })
})
