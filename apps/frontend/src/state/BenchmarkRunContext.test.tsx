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

  it('usar fora do provider é um erro de programação', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)

    expect(() => render(<Probe />)).toThrow('BenchmarkRunProvider')
  })
})
