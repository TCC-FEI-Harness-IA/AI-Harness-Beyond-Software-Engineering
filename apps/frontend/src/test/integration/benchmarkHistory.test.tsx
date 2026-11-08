import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const path = new URL(url).pathname
    if (path.endsWith('/alias') && init?.method === 'PUT') {
      const id = decodeURIComponent(path.split('/').at(-2) ?? '')
      const battery = batteries.find((item) => item.id === id)
      if (!battery) return respond({ detail: 'não encontrada' }, 404)
      battery.alias = (JSON.parse(String(init.body)) as { alias: string | null }).alias
      return respond(battery)
    }
    if (path === '/v1/benchmark/questions') return respond({ question_ids: ['Q1', 'Q2', 'Q3'], max_parallel_limit: 4, max_tokens_limit: 32000 })
    if (path === '/v1/benchmark/sessions') return respond({ benchmark_sessions: batteries })
    if (path.startsWith('/v1/benchmark/sessions/')) {
      const battery = batteries.find((item) => item.id === decodeURIComponent(path.split('/').at(-1) ?? ''))
      return battery ? respond(battery) : respond({ detail: 'não encontrada' }, 404)
    }
    if (path === '/v1/models') return respond({ models: [] })
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

function storeMaxTokens(maxTokens: number): void {
  window.localStorage.setItem(
    'tcc.runConfig',
    JSON.stringify({ modelName: 'openai/gpt-4o-mini', maxTokens, temperature: 0.3, provider: 'open_router' }),
  )
}

beforeEach(() => {
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  window.localStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  Reflect.deleteProperty(URL, 'createObjectURL')
  Reflect.deleteProperty(URL, 'revokeObjectURL')
})

describe('Benchmark como funcionalidade da aplicação', () => {
  it('seleciona várias questões da mesma bateria, acompanha o lote e recarrega os resultados', async () => {
    const user = userEvent.setup()
    const session = completedBenchmarkSession()
    session.questions[0]!.ralph = outcome({ mode: 'ralph', is_correct: false, error: 'Falha no provedor' })
    const backend = mockBackend([session])
    renderApp('/benchmark/bench_1')

    await user.click(await screen.findByRole('checkbox', { name: 'Selecionar todas as questões com erro ou falha' }))
    await user.click(screen.getByRole('button', { name: 'Executar novamente selecionadas (2)' }))
    const socket = FakeWebSocket.latest()
    expect(socket.url).toBe('ws://localhost:8000/v1/benchmark/sessions/bench_1/questions/rerun')
    act(() => socket.emitOpen())
    expect(JSON.parse(socket.sentFrames[0]!)).toEqual({ question_ids: ['Q1', 'Q2'] })

    const running = {
      ...session,
      questions: session.questions.map((question, index) => ({
        ...question, current_mode: index === 0 ? 'ralph' as const : 'simple' as const,
      })),
    }
    emit(socket, 'progress', running)
    expect(await screen.findByText('Ao vivo')).toBeInTheDocument()
    expect(screen.getAllByText('Executando')).toHaveLength(2)
    await user.click(screen.getByRole('link', { name: '← BenchMark · Vestibulares' }))
    const monitor = await screen.findByRole('article', { name: 'Bateria atual' })
    expect(within(monitor).getByRole('heading', { name: 'Reexecução de 2 questões' })).toBeInTheDocument()
    expect(within(monitor).getByText('Reexecutando')).toBeInTheDocument()
    expect(within(monitor).getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()

    const finished = completedBenchmarkSession()
    finished.questions[1]!.simple = outcome({ session_id: 'sess_q2_simple_nova' })
    backend.batteries[0] = finished
    emit(socket, 'result', finished)
    act(() => socket.emitClose(1000))
    expect(within(monitor).getByRole('button', { name: 'Fechar' })).toBeInTheDocument()
    await user.click(within(monitor).getByRole('link', { name: 'Ver detalhes' }))
    await screen.findByRole('heading', { name: /Bateria de/, level: 1 })
    expect(screen.queryByText('Ao vivo')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Executar novamente selecionadas/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir sessão Simples de Q2' })).toHaveAttribute(
      'href', '/benchmark/bench_1/sessao/sess_q2_simple_nova',
    )
  })

  it('alterna para MMLU, configura o protocolo e persiste a identificação no histórico', async () => {
    const user = userEvent.setup()
    const backend = mockBackend()
    const original = backend.fetchMock.getMockImplementation()!
    backend.fetchMock.mockImplementation((url: string) => {
      if (new URL(url).searchParams.get('benchmark') === 'mmlu') return respond({
        question_ids: ['M1', 'M2', 'M3', 'M4', 'M5'], max_parallel_limit: 4, max_tokens_limit: 32000,
        benchmark: { ...benchmarkSession().benchmark, dataset: 'mmlu', revision: 'fixed-revision' },
        subjects: [{ id: 'college_physics', question_count: 2 }, { id: 'history', question_count: 3 }],
      })
      return original(url)
    })
    renderApp('/benchmark')
    await screen.findByRole('button', { name: 'Iniciar bateria' })
    await user.click(screen.getByRole('tab', { name: 'MMLU' }))
    expect(screen.getByRole('tab', { name: 'MMLU' })).toHaveAttribute('aria-selected', 'true')
    const protocol = await screen.findByRole('combobox', { name: 'Protocolo MMLU' })
    expect(protocol).toHaveValue('5')
    await user.selectOptions(protocol, '0')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Disciplina' }), 'college_physics')
    expect(screen.getByRole('spinbutton', { name: /Quantidade de questões/ })).toHaveValue(2)
    const seed = screen.getByRole('spinbutton', { name: /Semente da amostra/ })
    await user.clear(seed)
    await user.type(seed, '123')
    await user.click(screen.getByRole('button', { name: 'Iniciar bateria' }))
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    expect(JSON.parse(socket.sentFrames[0] ?? '{}')).toMatchObject({
      benchmark: 'mmlu', few_shot: 0, subjects: ['college_physics'], sample_seed: 123, question_count: 2,
    })
    expect(screen.getByRole('button', { name: 'Iniciar bateria' })).toBeDisabled()
    const session = completedBenchmarkSession()
    session.benchmark = {
      dataset: 'mmlu', revision: 'fixed-revision', protocol: 'generative_0shot', split: 'test',
      few_shot: 0, subjects: ['college_physics'], sample_seed: 123,
    }
    backend.batteries.push(session)
    emit(socket, 'result', session)
    act(() => socket.emitClose(1000))
    const list = await screen.findByRole('list')
    expect(await within(list).findByText('MMLU · generativo · 0-shot')).toBeInTheDocument()
    await user.click(within(list).getByRole('link'))
    expect(await screen.findByText('fixed-revision')).toBeInTheDocument()
    expect(screen.getByText(/Semente 123/)).toBeInTheDocument()
  })

  it('permite escolher a quantidade de cada disciplina do MMLU, de zero ao máximo', async () => {
    const user = userEvent.setup()
    const backend = mockBackend()
    const original = backend.fetchMock.getMockImplementation()!
    backend.fetchMock.mockImplementation((url: string) => {
      if (new URL(url).searchParams.get('benchmark') === 'mmlu') return respond({
        question_ids: ['M1', 'M2', 'M3', 'M4', 'M5'], max_parallel_limit: 4, max_tokens_limit: 32000,
        benchmark: { ...benchmarkSession().benchmark, dataset: 'mmlu', revision: 'fixed-revision' },
        subjects: [{ id: 'college_physics', question_count: 2 }, { id: 'history', question_count: 3 }],
      })
      return original(url)
    })
    renderApp('/benchmark?benchmark=mmlu')
    const mode = await screen.findByRole('combobox', { name: 'Seleção de questões' })
    await user.selectOptions(mode, 'subject')
    expect(screen.queryByRole('combobox', { name: 'Disciplina' })).not.toBeInTheDocument()
    expect(screen.queryByRole('spinbutton', { name: /Quantidade de questões/ })).not.toBeInTheDocument()
    const submit = screen.getByRole('button', { name: 'Iniciar bateria' })
    expect(submit).toBeDisabled()
    const history = screen.getByRole('spinbutton', { name: /history/ })
    expect(history).toHaveAttribute('max', '3')
    fireEvent.change(history, { target: { value: '9' } })
    fireEvent.blur(history)
    expect(history).toHaveValue(3)
    await user.type(screen.getByRole('spinbutton', { name: /college physics/ }), '{Control>}a{/Control}1')
    expect(screen.getByRole('status')).toHaveTextContent('Total da bateria: 4 questões.')
    await user.click(submit)
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    expect(JSON.parse(socket.sentFrames[0] ?? '{}')).toMatchObject({
      benchmark: 'mmlu', subjects: [], question_count: 4,
      subject_counts: { college_physics: 1, history: 3 },
    })
  })

  it.each([
    ['diamond', 'Diamond', 198],
    ['main', 'Main', 448],
    ['extended', 'Extended', 546],
  ] as const)(
    'executa GPQA %s e preserva a variante no histórico',
    async (subset, label, count) => {
      const user = userEvent.setup()
      const backend = mockBackend()
      const original = backend.fetchMock.getMockImplementation()!
      backend.fetchMock.mockImplementation((url: string) => {
        if (new URL(url).searchParams.get('benchmark') === 'gpqa') {
          const variant = (new URL(url).searchParams.get('gpqa_subset') ?? 'diamond') as
            'diamond' | 'main' | 'extended'
          const total = { diamond: 198, main: 448, extended: 546 }[variant]!
          return respond({
            question_ids: Array.from({ length: total }, (_, i) => `GPQA_${variant}_${i}`),
            max_parallel_limit: 4,
            max_tokens_limit: 32000,
            benchmark: {
              ...benchmarkSession().benchmark,
              dataset: 'gpqa',
              split: variant,
              revision: 'fixed-revision',
            },
            subjects: [
              { id: 'physics', question_count: 2 },
              { id: 'chemistry', question_count: total - 2 },
            ],
          })
        }
        return original(url)
      })
      renderApp('/benchmark')
      await screen.findByRole('button', { name: 'Iniciar bateria' })
      await user.click(screen.getByRole('tab', { name: 'GPQA' }))
      await screen.findByText(/GPQA Diamond: 198 questões/)
      await user.selectOptions(screen.getByRole('combobox', { name: /Variante GPQA/ }), subset)
      await screen.findByText(new RegExp(`GPQA ${label}: ${count} questões`))
      expect(screen.getByRole('spinbutton', { name: /Quantidade de questões/ })).toHaveValue(count)
      expect(screen.queryByRole('combobox', { name: 'Protocolo MMLU' })).not.toBeInTheDocument()
      await user.selectOptions(screen.getByRole('combobox', { name: 'Disciplina' }), 'physics')
      expect(screen.getByRole('spinbutton', { name: /Quantidade de questões/ })).toHaveValue(2)
      const seed = screen.getByRole('spinbutton', { name: /Semente da amostra/ })
      await user.clear(seed)
      await user.type(seed, '123')
      await user.click(screen.getByRole('button', { name: 'Iniciar bateria' }))
      const socket = FakeWebSocket.latest()
      act(() => socket.emitOpen())
      expect(JSON.parse(socket.sentFrames[0] ?? '{}')).toMatchObject({
        benchmark: 'gpqa',
        gpqa_subset: subset,
        few_shot: 0,
        subjects: ['physics'],
        sample_seed: 123,
        question_count: 2,
      })
      expect(screen.getByRole('button', { name: 'Iniciar bateria' })).toBeDisabled()
      expect(screen.getByRole('combobox', { name: /Variante GPQA/ })).toBeDisabled()
      const session = completedBenchmarkSession()
      session.benchmark = {
        dataset: 'gpqa',
        revision: 'fixed-revision',
        protocol: 'generative_0shot',
        split: subset,
        few_shot: 0,
        subjects: ['physics'],
        sample_seed: 123,
      }
      backend.batteries.push(session)
      emit(socket, 'result', session)
      act(() => socket.emitClose(1000))
      const list = await screen.findByRole('list')
      expect(
        await within(list).findByText(`GPQA ${label} · generativo · 0-shot`),
      ).toBeInTheDocument()
      await user.click(within(list).getByRole('link'))
      expect(await screen.findByText('fixed-revision')).toBeInTheDocument()
      expect(screen.getByText(/Semente 123/)).toBeInTheDocument()
    },
  )

  it('volta aos vestibulares e mantém o contrato anterior de execução', async () => {
    const user = userEvent.setup()
    mockBackend()
    renderApp('/benchmark')
    await screen.findByRole('button', { name: 'Iniciar bateria' })
    await user.click(screen.getByRole('tab', { name: 'MMLU' }))
    await screen.findByRole('combobox', { name: 'Protocolo MMLU' })
    await user.click(screen.getByRole('tab', { name: 'Vestibulares' }))
    await user.click(await screen.findByRole('button', { name: 'Iniciar bateria' }))
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    expect(JSON.parse(socket.sentFrames[0] ?? '{}')).not.toHaveProperty('few_shot')
    expect(screen.queryByRole('combobox', { name: 'Protocolo MMLU' })).not.toBeInTheDocument()
  })

  it('inicia uma bateria, monitora o progresso ao vivo e lista a bateria ao terminar', async () => {
    const user = userEvent.setup()
    const backend = mockBackend()
    renderApp('/')

    await user.click(screen.getByRole('link', { name: 'BenchMark' }))
    expect(await screen.findByRole('heading', { name: 'BenchMark', level: 1 })).toBeInTheDocument()
    expect(await screen.findByText('Nenhuma bateria de Vestibulares executada ainda')).toBeInTheDocument()

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

  it('impede iniciar quando o máximo de tokens passa do limite do servidor', async () => {
    const user = userEvent.setup()
    mockBackend()
    storeMaxTokens(10_000_000)
    renderApp('/benchmark')

    const start = await screen.findByRole('button', { name: 'Iniciar bateria' })
    expect(screen.getByRole('alert')).toHaveTextContent('passa do limite de 32.000 por sessão')
    expect(start).toBeDisabled()

    // Contornar o botão desabilitado (envio direto do formulário) também não abre a conexão.
    fireEvent.submit(screen.getByRole('form', { name: 'Nova bateria de benchmark' }))
    expect(FakeWebSocket.instances).toHaveLength(0)

    const tokens = screen.getByRole('spinbutton', { name: /Máximo de tokens/ })
    await user.clear(tokens)
    await user.type(tokens, '4000')

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(start).toBeEnabled()
    await user.click(start)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it.each([
    [32_000, true],
    [32_001, false],
  ])('o limite de tokens é inclusivo: %i tokens, iniciar permitido = %s', async (maxTokens, allowed) => {
    mockBackend()
    storeMaxTokens(maxTokens)
    renderApp('/benchmark')

    const start = await screen.findByRole('button', { name: 'Iniciar bateria' })

    expect(start).toHaveProperty('disabled', !allowed)
    expect(screen.queryByRole('alert') === null).toBe(allowed)
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
    expect(await screen.findByText('Nenhuma bateria de Vestibulares executada ainda')).toBeInTheDocument()
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

  it('adiciona, edita e remove o alias, preservando-o ao navegar pela listagem', async () => {
    const user = userEvent.setup()
    const { fetchMock } = mockBackend([completedBenchmarkSession()])
    renderApp('/benchmark/bench_1')

    await user.click(await screen.findByRole('button', { name: 'Adicionar alias' }))
    const input = screen.getByRole('textbox', { name: 'Alias da bateria' })
    expect(input).toHaveFocus()
    expect(input).toHaveAttribute('maxlength', '120')
    await user.type(input, '  Comparação GPT  ')
    await user.click(screen.getByRole('button', { name: 'Salvar alias' }))
    expect(await screen.findByRole('heading', { name: 'Comparação GPT' })).toBeInTheDocument()
    const putCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
    expect(putCall?.[0]).toBe('http://localhost:8000/v1/benchmark/sessions/bench_1/alias')
    expect(JSON.parse(String(putCall?.[1]?.body))).toEqual({ alias: 'Comparação GPT' })

    await user.click(screen.getByRole('link', { name: '← BenchMark · Vestibulares' }))
    const list = await screen.findByRole('list', { name: 'Baterias de Vestibulares' })
    await user.click(within(list).getByRole('link', { name: /Comparação GPT/ }))
    expect(await screen.findByRole('heading', { name: 'Comparação GPT' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Editar alias' }))
    await user.clear(screen.getByRole('textbox', { name: 'Alias da bateria' }))
    await user.type(screen.getByRole('textbox', { name: 'Alias da bateria' }), 'Teste de temperatura')
    await user.click(screen.getByRole('button', { name: 'Salvar alias' }))
    expect(await screen.findByRole('heading', { name: 'Teste de temperatura' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Editar alias' }))
    await user.clear(screen.getByRole('textbox', { name: 'Alias da bateria' }))
    await user.click(screen.getByRole('button', { name: 'Salvar alias' }))
    expect(await screen.findByRole('heading', { name: /Bateria de/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Adicionar alias' })).toBeInTheDocument()
  })

  it('cancelar a edição do alias mantém o título salvo', async () => {
    const user = userEvent.setup()
    const battery = { ...completedBenchmarkSession(), alias: 'Título salvo' }
    const { fetchMock } = mockBackend([battery])
    renderApp('/benchmark/bench_1')
    await user.click(await screen.findByRole('button', { name: 'Editar alias' }))
    await user.type(screen.getByRole('textbox', { name: 'Alias da bateria' }), ' alterado')
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('heading', { name: 'Título salvo' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false)
  })

  it('uma falha ao salvar mantém o texto para tentar novamente', async () => {
    const user = userEvent.setup()
    const { fetchMock } = mockBackend([completedBenchmarkSession()])
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation((url, init) =>
      init?.method === 'PUT' ? respond({ detail: 'Mongo indisponível' }, 500) : original(url, init),
    )
    renderApp('/benchmark/bench_1')
    await user.click(await screen.findByRole('button', { name: 'Adicionar alias' }))
    await user.type(screen.getByRole('textbox', { name: 'Alias da bateria' }), 'Meu teste')
    await user.click(screen.getByRole('button', { name: 'Salvar alias' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível salvar o alias')
    expect(screen.getByRole('textbox', { name: 'Alias da bateria' })).toHaveValue('Meu teste')
    expect(screen.getByRole('heading', { name: /Bateria de/ })).toBeInTheDocument()
    fetchMock.mockImplementation(original)
    await user.click(screen.getByRole('button', { name: 'Salvar alias' }))
    expect(await screen.findByRole('heading', { name: 'Meu teste' })).toBeInTheDocument()
  })

  it('bateria em execução não oferece edição de alias', async () => {
    mockBackend([benchmarkSession()])
    renderApp('/benchmark/bench_1')
    expect(await screen.findByRole('heading', { name: /Bateria de/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Adicionar alias' })).not.toBeInTheDocument()
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


function mockVestibularSubjects() {
  const backend = mockBackend()
  const original = backend.fetchMock.getMockImplementation()!
  const subjects = [
    { id: 'BIOLOGIA', question_count: 30 },
    { id: 'FILOSOFIA_SOCIOLOGIA', question_count: 30 },
    { id: 'FISICA', question_count: 50 },
    { id: 'GEOGRAFIA', question_count: 30 },
    { id: 'HISTORIA', question_count: 30 },
    { id: 'MATEMATICA', question_count: 50 },
    { id: 'QUIMICA', question_count: 50 },
  ]
  backend.fetchMock.mockImplementation((url: string) => {
    if (new URL(url).pathname === '/v1/benchmark/questions') return respond({
      subjects,
      question_ids: subjects.flatMap((subject) =>
        Array.from({ length: subject.question_count }, (_, index) => `${subject.id}_${index}`)),
      max_parallel_limit: 4,
      max_tokens_limit: 32000,
    })
    return original(url)
  })
  return backend
}

describe('Vestibulares por matéria', () => {
  it('calcula o total e envia somente a distribuição escolhida', async () => {
    const user = userEvent.setup()
    mockVestibularSubjects()
    renderApp('/benchmark')
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Seleção de questões' }), 'subject')
    const submit = screen.getByRole('button', { name: 'Iniciar bateria' })
    expect(submit).toBeDisabled()
    expect(screen.queryByRole('spinbutton', { name: /Quantidade de questões/ })).not.toBeInTheDocument()
    expect(screen.getByRole('spinbutton', { name: /Filosofia e Sociologia/ })).toHaveAttribute('max', '30')
    const biology = screen.getByRole('spinbutton', { name: /Biologia/ })
    const math = screen.getByRole('spinbutton', { name: /Matemática/ })
    await user.clear(biology)
    await user.type(biology, '1')
    expect(screen.getByRole('status')).toHaveTextContent('Total da bateria: 1 questão.')
    await user.clear(math)
    await user.type(math, '2')
    expect(screen.getByRole('status')).toHaveTextContent('Total da bateria: 3 questões.')
    expect(submit).toBeEnabled()
    await user.click(submit)
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    expect(JSON.parse(socket.sentFrames[0] ?? '{}')).toMatchObject({
      question_count: 3,
      subject_counts: {
        BIOLOGIA: 1, FILOSOFIA_SOCIOLOGIA: 0, FISICA: 0, GEOGRAFIA: 0,
        HISTORIA: 0, MATEMATICA: 2, QUIMICA: 0,
      },
    })
    expect(biology).toBeDisabled()
    expect(math).toBeDisabled()
  })

  it('limita cada matéria e preserva as escolhas ao alternar os modos', async () => {
    const user = userEvent.setup()
    mockVestibularSubjects()
    renderApp('/benchmark')
    const mode = await screen.findByRole('combobox', { name: 'Seleção de questões' })
    await user.selectOptions(mode, 'subject')
    const history = screen.getByRole('spinbutton', { name: /História/ })
    fireEvent.change(history, { target: { value: '80' } })
    fireEvent.blur(history)
    expect(history).toHaveValue(30)
    fireEvent.change(history, { target: { value: '-3' } })
    fireEvent.blur(history)
    expect(history).toHaveValue(0)
    fireEvent.change(history, { target: { value: '2.8' } })
    fireEvent.blur(history)
    expect(history).toHaveValue(2)
    await user.selectOptions(mode, 'total')
    expect(screen.getByRole('spinbutton', { name: /Quantidade de questões/ })).toHaveValue(270)
    await user.selectOptions(mode, 'subject')
    expect(screen.getByRole('spinbutton', { name: /História/ })).toHaveValue(2)
    expect(screen.getByRole('status')).toHaveTextContent('Total da bateria: 2 questões.')
  })

  it('mostra a distribuição persistida no detalhe da bateria', async () => {
    const stored: BenchmarkSessionDocument = {
      ...completedBenchmarkSession(),
      question_count: 3,
      questions: [
        questionRun({ question_id: 'BIO1', subject: 'BIOLOGIA' }),
        questionRun({ question_id: 'MAT1', subject: 'MATEMATICA' }),
        questionRun({ question_id: 'MAT2', subject: 'MATEMATICA' }),
      ],
    }
    mockBackend([stored])
    renderApp(`/benchmark/${stored.id}`)
    expect(await screen.findByLabelText('Questões por matéria')).toHaveTextContent('Biologia: 1 · Matemática: 2')
  })
})

describe('Abas do BenchMark', () => {
  it('cada aba lista só as baterias do seu benchmark e o detalhe volta para a aba de origem', async () => {
    const user = userEvent.setup()
    const mmlu = { ...completedBenchmarkSession(), id: 'bench_2' }
    mmlu.benchmark = { ...mmlu.benchmark, dataset: 'mmlu', revision: 'fixed-revision', sample_seed: 42 }
    mockBackend([completedBenchmarkSession(), mmlu])
    renderApp('/benchmark')

    const vestibular = await screen.findByRole('list', { name: 'Baterias de Vestibulares' })
    expect(within(vestibular).getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/benchmark/bench_1',
    ])

    screen.getByRole('tab', { name: 'Vestibulares' }).focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'MMLU' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel', { name: 'MMLU' })).toBeInTheDocument()
    const mmluList = await screen.findByRole('list', { name: 'Baterias de MMLU' })
    expect(within(mmluList).getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/benchmark/bench_2',
    ])

    await user.click(screen.getByRole('tab', { name: 'GPQA' }))
    expect(await screen.findByText('Nenhuma bateria de GPQA executada ainda')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: /Variante GPQA/ })).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'MMLU' }))
    expect(screen.queryByRole('combobox', { name: /Variante GPQA/ })).not.toBeInTheDocument()
    await user.click(within(await screen.findByRole('list', { name: 'Baterias de MMLU' })).getByRole('link'))
    const back = await screen.findByRole('link', { name: '← BenchMark · MMLU' })
    expect(back).toHaveAttribute('href', '/benchmark?benchmark=mmlu')
    await user.click(back)
    expect(await screen.findByRole('tab', { name: 'MMLU' })).toHaveAttribute('aria-selected', 'true')
  })

  it('a bateria em execução aparece só na aba do seu benchmark', async () => {
    const user = userEvent.setup()
    mockBackend()
    renderApp('/benchmark')

    await user.click(await screen.findByRole('button', { name: 'Iniciar bateria' }))
    const socket = FakeWebSocket.latest()
    act(() => socket.emitOpen())
    emit(socket, 'progress', benchmarkSession())
    expect(screen.getByRole('article', { name: 'Bateria atual' })).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'GPQA' }))
    expect(screen.queryByRole('article', { name: 'Bateria atual' })).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Uma bateria de Vestibulares está em execução')
    expect(await screen.findByRole('button', { name: 'Iniciar bateria' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Acompanhar' }))
    expect(screen.getByRole('tab', { name: 'Vestibulares' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('article', { name: 'Bateria atual' })).toBeInTheDocument()
  })
})

describe('Exportação e importação de bateria completa', () => {
  it('importa o ZIP, abre a bateria importada e oferece exportá-la de novo', async () => {
    const user = userEvent.setup()
    const backend = mockBackend()
    const original = backend.fetchMock.getMockImplementation()!
    const imported = { ...completedBenchmarkSession(), id: 'bench_importada', alias: 'Bateria importada' }
    backend.fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (new URL(url).pathname === '/v1/benchmark/sessions/import' && init?.method === 'POST') {
        backend.batteries.push(imported)
        return respond(imported, 201)
      }
      return original(url, init)
    })
    renderApp('/benchmark')

    await user.upload(
      await screen.findByLabelText('Arquivo ZIP da sessão'),
      new File(['PK'], 'bateria.zip', { type: 'application/zip' }),
    )

    expect(await screen.findByRole('heading', { name: 'Bateria importada' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exportar sessão completa' })).toBeEnabled()
    const importCall = backend.fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(importCall?.[1]?.headers).toEqual({ 'Content-Type': 'application/zip' })
  })
})
