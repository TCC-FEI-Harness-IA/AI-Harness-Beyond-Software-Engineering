import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { benchmarkSession } from '@/test/fixtures/benchmarkSession'
import { FakeWebSocket } from '@/test/doubles/FakeWebSocket'
import { BenchmarkRunProvider, useBenchmarkRun } from './BenchmarkRunContext'

const CONFIG = {
  modelName: 'vendor/modelo',
  provider: 'open_router' as const,
  maxTokens: 100,
  temperature: 0.3,
}

let current: ReturnType<typeof useBenchmarkRun>

function Probe(): JSX.Element {
  current = useBenchmarkRun()
  return <span data-testid="phase">{current.phase}</span>
}

function renderProvider() {
  return render(
    <BenchmarkRunProvider>
      <Probe />
    </BenchmarkRunProvider>,
  )
}

function start(questionCount = 2): void {
  act(() => current.start({ questionCount, maxParallel: 1, config: CONFIG }))
}

beforeEach(() => {
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => vi.unstubAllGlobals())

describe('BenchmarkRunProvider', () => {
  it('parâmetros inválidos viram erro sem abrir conexão', () => {
    renderProvider()

    start(0)

    expect(screen.getByTestId('phase')).toHaveTextContent('error')
    expect(current.rejection).toContain('O servidor respondeu em um formato inesperado')
    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('só uma bateria por vez: um segundo início é ignorado', () => {
    renderProvider()

    start()
    start()

    expect(FakeWebSocket.instances).toHaveLength(1)
    expect(current.isActive).toBe(true)
    expect(current.phase).toBe('connecting')
    expect(current.benchmark).toBe('vestibular')
  })

  it('fechamento 1011 depois do resultado preserva o desfecho', () => {
    renderProvider()
    start()
    const socket = FakeWebSocket.latest()

    act(() => socket.emitMessage({ type: 'progress', benchmark_session: benchmarkSession() }))
    expect(current.phase).toBe('running')
    act(() =>
      socket.emitMessage({
        type: 'result',
        benchmark_session: benchmarkSession({ status: 'failed' }),
      }),
    )
    act(() => socket.emitClose(1011))

    expect(current.phase).toBe('finished')
    expect(current.error).toBeNull()
    expect(current.finishedCount).toBe(1)
  })

  it('queda da conexão no meio vira erro e libera um novo início', () => {
    renderProvider()
    start()
    const socket = FakeWebSocket.latest()

    act(() => socket.emitMessage({ type: 'progress', benchmark_session: benchmarkSession() }))
    act(() => socket.emitClose(1006))

    expect(current.phase).toBe('error')
    expect(current.rejection).toBe('A conexão com o servidor foi encerrada de forma inesperada.')
    expect(current.session?.id).toBe('bench_1')
    start()
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('dispensar só funciona sem bateria ativa e cancelar sem bateria não faz nada', () => {
    renderProvider()

    act(() => current.cancel())
    expect(current.phase).toBe('idle')

    start()
    act(() => current.dismiss())
    expect(current.phase).toBe('connecting')

    act(() => current.cancel())
    expect(current.phase).toBe('cancelled')
    act(() => current.dismiss())
    expect(current.phase).toBe('idle')
    expect(current.finishedCount).toBe(1)
  })

  it('desmontar o provider fecha a conexão aberta', () => {
    const { unmount } = renderProvider()
    start()

    unmount()

    expect(FakeWebSocket.latest().closeCalls).toEqual([1000])
  })

  it('reexecuta uma questão pela rota da questão e termina com o documento atualizado', () => {
    renderProvider()

    act(() => current.rerun('bench_1', 'Q2', 'mmlu'))
    const socket = FakeWebSocket.latest()

    expect(socket.url).toBe('ws://localhost:8000/v1/benchmark/sessions/bench_1/questions/Q2/rerun')
    expect(current.phase).toBe('connecting')
    expect(current.rerunQuestionIds).toEqual(['Q2'])
    expect(current.benchmark).toBe('mmlu')
    expect(current.isActive).toBe(true)
    act(() => socket.emitOpen())
    expect(socket.sentFrames).toEqual([])
    act(() =>
      socket.emitMessage({
        type: 'progress',
        benchmark_session: benchmarkSession({ status: 'completed' }),
      }),
    )
    expect(current.phase).toBe('running')
    act(() =>
      socket.emitMessage({
        type: 'result',
        benchmark_session: benchmarkSession({ status: 'completed' }),
      }),
    )
    act(() => socket.emitClose(1000))

    expect(current.phase).toBe('finished')
    expect(current.finishedCount).toBe(1)
    expect(current.rerunQuestionIds).toEqual(['Q2'])
    act(() => current.dismiss())
    expect(current.rerunQuestionIds).toEqual([])
    expect(current.benchmark).toBeNull()
  })

  it('não reexecuta enquanto há bateria ou reexecução ativa', () => {
    renderProvider()
    start()

    act(() => current.rerun('bench_1', 'Q1', 'vestibular'))

    expect(FakeWebSocket.instances).toHaveLength(1)
    expect(current.rerunQuestionIds).toEqual([])
  })

  it('reexecução recusada pelo servidor vira erro com a mensagem do servidor', () => {
    renderProvider()
    act(() => current.rerun('bench_1', 'Q1', 'vestibular'))
    const socket = FakeWebSocket.latest()

    act(() => socket.emitMessage({ type: 'error', content: 'Q1 não tem fluxo errado' }))
    act(() => socket.emitClose(1003))

    expect(current.phase).toBe('error')
    expect(current.rejection).toBe('Q1 não tem fluxo errado')
    expect(current.finishedCount).toBe(1)
    act(() => current.rerun('bench_1', 'Q1', 'vestibular'))
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('usar fora do provider é um erro de programação', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)

    expect(() => render(<Probe />)).toThrow('BenchmarkRunProvider')
  })

  it('reexecuta um lote numa única conexão e atualiza as consultas uma vez ao concluir', () => {
    renderProvider()
    act(() => current.rerun('bench_1', ['Q1', 'Q2'], 'mmlu'))
    const socket = FakeWebSocket.latest()

    expect(socket.url).toBe('ws://localhost:8000/v1/benchmark/sessions/bench_1/questions/rerun')
    expect(current.rerunQuestionIds).toEqual(['Q1', 'Q2'])
    expect(current.benchmark).toBe('mmlu')
    act(() => socket.emitOpen())
    expect(socket.sentFrames).toEqual([JSON.stringify({ question_ids: ['Q1', 'Q2'] })])
    act(() => current.rerun('bench_1', ['Q3'], 'mmlu'))
    expect(FakeWebSocket.instances).toHaveLength(1)

    act(() => socket.emitMessage({ type: 'result', benchmark_session: benchmarkSession({ status: 'completed' }) }))
    act(() => socket.emitClose(1000))
    expect(current.phase).toBe('finished')
    expect(current.finishedCount).toBe(1)
    expect(current.session?.id).toBe('bench_1')
    act(() => current.dismiss())
    expect(current.rerunQuestionIds).toEqual([])
  })

  it('cancelar o lote fecha a conexão e permite reexecutar uma nova seleção', () => {
    renderProvider()
    act(() => current.rerun('bench_1', ['Q1', 'Q2'], 'vestibular'))
    const socket = FakeWebSocket.latest()
    act(() => current.cancel())
    expect(socket.closeCalls).toEqual([1000])
    expect(current.phase).toBe('cancelled')
    expect(current.finishedCount).toBe(1)
    act(() => current.rerun('bench_1', ['Q2'], 'vestibular'))
    expect(FakeWebSocket.instances).toHaveLength(2)
    expect(current.rerunQuestionIds).toEqual(['Q2'])
  })

  it('ignora lotes vazios sem abrir conexão', () => {
    renderProvider()
    act(() => current.rerun('bench_1', [], 'vestibular'))
    expect(current.phase).toBe('idle')
    expect(FakeWebSocket.instances).toHaveLength(0)
  })
})
