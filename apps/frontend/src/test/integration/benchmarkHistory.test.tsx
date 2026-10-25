import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import direct from '@/test/fixtures/session-direct-completed.json'
import ralph from '@/test/fixtures/session-a1-completed-with-a3.json'
import type { BenchmarkDetails } from '@/domain/types/benchmarkDetails'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { AppRouter } from '@/router/AppRouter'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { FakeWebSocket } from '@/test/doubles/FakeWebSocket'
import { benchmarkSession, completedBenchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'

const details: BenchmarkDetails = {
  is_banchmark: true, question_name: 'Q1', corret_answer: 'A) um', providade_answer: 'RESPOSTA_FINAL: A',
  inference_mode: 'simple', run_id: 'bench_1', expected_alternative: 'A', selected_alternative: 'A',
  is_correct: true, duration_seconds: 1, error: null,
}
const childSessions = [
  { ...direct, id: 'sess_q1_simple', user_question: 'Enunciado Q1', benchmark_details: details },
  { ...ralph, id: 'sess_q1_ralph', benchmark_details: { ...details, inference_mode: 'ralph' } },
  { ...direct, id: 'sess_q2_simple', benchmark_details: { ...details, question_name: 'Q2', is_correct: false } },
  { ...ralph, id: 'sess_q2_ralph', benchmark_details: { ...details, question_name: 'Q2', inference_mode: 'ralph' } },
]
const normal = { ...direct, id: 'sess_normal', user_question: 'Pergunta normal da API' }

function renderApp(path: string): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider><RunConfigProvider><ViewModeProvider>
        <AppRouter />
      </ViewModeProvider></RunConfigProvider></ThemeProvider>
    </MemoryRouter>,
  )
}

function respond(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve({ status, text: () => Promise.resolve(JSON.stringify(body)) } as Response)
}

/** Backend simulado: `batteries` é mutável, para simular a bateria gravada ao terminar. */
function mockBackend(batteries: BenchmarkSessionDocument[] = []) {
  const documents = [...childSessions, normal]
  const fetchMock = vi.fn((url: string) => {
    const path = new URL(url).pathname
    if (path === '/v1/benchmark/questions') return respond({ question_ids: ['Q1', 'Q2', 'Q3'], max_parallel_limit: 4 })
    if (path === '/v1/benchmark/sessions') return respond({ benchmark_sessions: batteries })
    if (path.startsWith('/v1/benchmark/sessions/')) {
      const battery = batteries.find((item) => item.id === decodeURIComponent(path.split('/').at(-1) ?? ''))
      return battery ? respond(battery) : respond({ detail: 'não encontrada' }, 404)
    }
    if (path === '/v1/sessions') return respond({ session_ids: documents.map((document) => document.id) })
    const document = documents.find((item) => item.id === decodeURIComponent(path.split('/').at(-1) ?? ''))
    return document ? respond(document) : respond({ detail: 'não encontrada' }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, batteries }
}

function emit(socket: FakeWebSocket, type: 'progress' | 'result', session: BenchmarkSessionDocument): void {
  act(() => socket.emitMessage({ type, benchmark_session: session }))
}

beforeEach(() => {
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  Reflect.deleteProperty(URL, 'createObjectURL')
  Reflect.deleteProperty(URL, 'revokeObjectURL')
})

describe('Benchmark como funcionalidade da aplicação', () => {
  it('inicia uma bateria, monitora o progresso ao vivo e lista a bateria ao terminar', async () => {
    const user = userEvent.setup()
    const backend = mockBackend()
    renderApp('/')

    await user.click(screen.getByRole('link', { name: 'BenchMark' }))
    expect(await screen.findByRole('heading', { name: 'BenchMark', level: 1 })).toBeInTheDocument()
    expect(await screen.findByText('Nenhuma bateria executada ainda')).toBeInTheDocument()

    const quantity = await screen.findByRole('spinbutton', { name: /Quantidade de questões/ })
    expect(quantity).toHaveValue(3)
    await user.clear(quantity)
    await user.type(quantity, '2')
    const parallel = screen.getByRole('spinbutton', { name: /Questões em paralelo/ })
    expect(parallel).toHaveValue(4)
    await user.clear(parallel)
    await user.type(parallel, '1')
    expect(screen.getByText(/As 2 primeiras de 3 disponíveis/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Iniciar bateria' }))

    const socket = FakeWebSocket.latest()
    expect(socket.url).toBe('ws://localhost:8000/v1/benchmark/run')
    act(() => socket.emitOpen())
    expect(JSON.parse(socket.sentFrames[0] ?? '{}')).toEqual({
      question_count: 2,
      max_parallel: 1,
      llm_model_config: {
        provider: 'open_router',
        provider_config: { model_name: 'openai/gpt-4o-mini', endpoint: null },
        max_tokens: 1200,
        temperature: 0.3,
      },
    })
    expect(screen.getByRole('button', { name: 'Iniciar bateria' })).toBeDisabled()

    emit(socket, 'progress', benchmarkSession({
      wall_time_ms: 2500,
      total_tokens: 42,
      progress: { total: 2, pending: 1, running: 1, finished: 0, interrupted: 0 },
      questions: [
        questionRun({ question_id: 'Q1', status: 'running', current_mode: 'ralph', current_tokens: 32, total_tokens: 42,
          simple: outcome() }),
        questionRun({ question_id: 'Q2', expected_alternative: 'B' }),
      ],
    }))

    const monitor = screen.getByRole('article', { name: 'Bateria atual' })
    expect(within(monitor).getAllByText('Em execução')).toHaveLength(2)
    expect(within(monitor).getByText('2,5 s')).toBeInTheDocument()
    // Consumo total da bateria (contador) e da questão em execução (tabela).
    expect(within(monitor).getAllByText('42')).toHaveLength(2)
    expect(within(monitor).getByRole('progressbar')).toHaveAttribute('aria-valuetext', '0 de 2 questões encerradas')
    expect(within(monitor).getByText('Executando')).toBeInTheDocument()
    expect(within(monitor).getByRole('link', { name: 'Abrir sessão Simples de Q1' })).toHaveAttribute(
      'href', '/benchmark/bench_1/sessao/sess_q1_simple',
    )

    const done = completedBenchmarkSession()
    backend.batteries.push(done)
    emit(socket, 'result', done)
    act(() => socket.emitClose(1000))

    expect(within(monitor).getByText('Concluída', { selector: 'span' })).toBeInTheDocument()
    expect(within(monitor).getByRole('button', { name: 'Fechar' })).toBeInTheDocument()
    const list = await screen.findByRole('list')
    const card = await within(list).findByRole('link', { name: /Simples 1\/2 \(50%\)/ })
    expect(card).toHaveAttribute('href', '/benchmark/bench_1')
    expect(within(card).getByText('Ralph 2/2 (100%)')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Iniciar bateria' })).toBeEnabled()

    await user.click(within(monitor).getByRole('button', { name: 'Fechar' }))
    expect(screen.queryByRole('article', { name: 'Bateria atual' })).not.toBeInTheDocument()
  })

  it('mantém a bateria em execução ao navegar e mostra o detalhe ao vivo', async () => {
    const user = userEvent.setup()
    mockBackend()
    renderApp('/benchmark')

    await user.click(await screen.findByRole('button', { name: 'Iniciar bateria' }))
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    emit(socket, 'progress', benchmarkSession())

    await user.click(screen.getByRole('link', { name: 'Histórico' }))
    expect(await screen.findByRole('heading', { name: 'Histórico' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'BenchMark' }))
    const monitor = await screen.findByRole('article', { name: 'Bateria atual' })
    expect(socket.closeCalls).toEqual([])

    await user.click(within(monitor).getByRole('link', { name: 'Ver detalhes' }))
    expect(await screen.findByText('Ao vivo')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Questões da bateria' })).toBeInTheDocument()
  })

  it('cancelar fecha a conexão e marca a bateria como cancelada', async () => {
    const user = userEvent.setup()
    mockBackend()
    renderApp('/benchmark')

    await user.click(await screen.findByRole('button', { name: 'Iniciar bateria' }))
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    emit(socket, 'progress', benchmarkSession())
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(socket.closeCalls).toEqual([1000])
    expect(screen.getByText('Cancelada')).toBeInTheDocument()
    expect(screen.getByText(/questões em execução foram interrompidas/)).toBeInTheDocument()
  })

  it('mostra a recusa do servidor quando os parâmetros não são aceitos', async () => {
    const user = userEvent.setup()
    mockBackend()
    renderApp('/benchmark')

    await user.click(await screen.findByRole('button', { name: 'Iniciar bateria' }))
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    act(() => socket.emitMessage({ type: 'error', content: 'question_count deve estar entre 1 e 3. Valor: 9.' }))
    act(() => socket.emitClose(1003))

    expect(screen.getByRole('alert')).toHaveTextContent('question_count deve estar entre 1 e 3. Valor: 9.')
    expect(screen.getByRole('button', { name: 'Iniciar bateria' })).toBeEnabled()
    // O fim da tentativa recarrega a lista de baterias.
    expect(await screen.findByText('Nenhuma bateria executada ainda')).toBeInTheDocument()
  })

  it('o detalhe da bateria compara os fluxos e abre as sessões de cada questão', async () => {
    const user = userEvent.setup()
    mockBackend([completedBenchmarkSession()])
    renderApp('/benchmark/bench_1')

    expect(await screen.findByRole('heading', { name: /Bateria de/ })).toBeInTheDocument()
    const summary = screen.getByRole('table', { name: 'Comparativo entre os fluxos' })
    expect(within(summary).getByRole('row', { name: /Acurácia/ })).toHaveTextContent('50%100%')
    const questions = screen.getByRole('table', { name: 'Questões da bateria' })
    expect(within(questions).getByText('Errado (C)')).toBeInTheDocument()

    await user.click(within(questions).getByRole('link', { name: 'Abrir sessão Simples de Q1' }))
    expect(await screen.findByLabelText('Histórico de mensagens')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Q1 · Simples' })).toBeInTheDocument()
    expect(screen.getByText(/Gabarito: A\) um/)).toBeInTheDocument()
    const sidebar = screen.getByRole('navigation', { name: 'Conversas' })
    await waitFor(() => expect(within(sidebar).getAllByRole('link')).toHaveLength(4))
    expect(within(sidebar).getByRole('link', { name: 'Q2 · Ralph' })).toHaveAttribute(
      'href', '/benchmark/bench_1/sessao/sess_q2_ralph',
    )

    await user.click(screen.getByRole('link', { name: '← Voltar à bateria' }))
    expect(await screen.findByRole('heading', { name: /Bateria de/ })).toBeInTheDocument()
  })

  it('o detalhe de uma bateria encerrada exporta os erros do Ralph Loop em ZIP', async () => {
    const user = userEvent.setup()
    const battery = completedBenchmarkSession()
    battery.questions[1]!.ralph = outcome({ mode: 'ralph', session_id: 'sess_q2_ralph', is_correct: false })
    const { fetchMock } = mockBackend([battery])
    const original = fetchMock.getMockImplementation()!
    const download = vi.fn()
    const exportCalls: string[] = []
    fetchMock.mockImplementation((url: string) => {
      if (!url.endsWith('/ralph-loop-errors/export')) return original(url)
      exportCalls.push(new URL(url).pathname)
      return Promise.resolve({ status: 200, blob: () => Promise.resolve(new Blob(['PK'])) } as Response)
    })
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:zip', revokeObjectURL: vi.fn() }))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      download(this.download)
    })
    renderApp('/benchmark/bench_1')

    await user.click(await screen.findByRole('button', { name: 'Exportar erros do Ralph Loop' }))

    await waitFor(() =>
      expect(download).toHaveBeenCalledWith('benchmark-session-bench_1-ralph-loop-errors.zip'),
    )
    expect(exportCalls).toEqual(['/v1/benchmark/sessions/bench_1/ralph-loop-errors/export'])
  })

  it('o detalhe de uma bateria sem erros no Ralph Loop não oferece o download', async () => {
    mockBackend([completedBenchmarkSession()])
    renderApp('/benchmark/bench_1')

    expect(await screen.findByRole('button', { name: 'Exportar erros do Ralph Loop' })).toBeDisabled()
    expect(screen.getByText(/Nenhuma questão errou no Ralph Loop/)).toBeInTheDocument()
  })

  it('bateria inexistente mostra o estado de não encontrada', async () => {
    mockBackend()
    renderApp('/benchmark/bench_9')

    expect(await screen.findByText('Esta bateria não existe')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Voltar ao BenchMark' })).toHaveAttribute('href', '/benchmark')
  })

  it('recusa um chat comum aberto pela URL de sessão de bateria', async () => {
    const user = userEvent.setup()
    mockBackend([completedBenchmarkSession()])
    renderApp('/benchmark/bench_1/sessao/sess_normal')

    expect(await screen.findByText('Esta conversa não existe mais')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Voltar à bateria' }))
    expect(await screen.findByRole('heading', { name: /Bateria de/ })).toBeInTheDocument()
  })

  it('o Histórico normal exclui as sessões de benchmark', async () => {
    mockBackend()
    renderApp('/historico')

    const list = await screen.findByRole('list')
    expect(await within(list).findByRole('link', { name: /Pergunta normal da API/ })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText(/carregando/)).not.toBeInTheDocument())
    expect(within(list).getAllByRole('link')).toHaveLength(1)
  })
})
