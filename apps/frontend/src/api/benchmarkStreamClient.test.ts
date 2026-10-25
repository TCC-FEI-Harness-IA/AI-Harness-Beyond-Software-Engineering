import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { benchmarkSession } from '@/test/fixtures/benchmarkSession'
import { FakeWebSocket } from '../test/doubles/FakeWebSocket'
import type { BenchmarkRunInput } from '../domain/types/benchmarkSession'
import { WebSocketError } from './errors/WebSocketError'
import { type BenchmarkStreamHandlers, openBenchmarkStream } from './benchmarkStreamClient'

const PAYLOAD: BenchmarkRunInput = {
  question_count: 2,
  max_parallel: 1,
  llm_model_config: {
    provider: 'open_router',
    provider_config: { model_name: 'vendor/modelo', endpoint: null },
    max_tokens: 100,
    temperature: 0.3,
  },
}

type MockedHandlers = { [Key in keyof BenchmarkStreamHandlers]: Mock<BenchmarkStreamHandlers[Key]> }

function handlers(): MockedHandlers {
  return {
    onSession: vi.fn(),
    onErrorFrame: vi.fn(),
    onClose: vi.fn(),
    onFailure: vi.fn(),
    onFrameWarning: vi.fn(),
  }
}

beforeEach(() => {
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
  vi.spyOn(console, 'warn').mockImplementation(() => undefined)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('openBenchmarkStream', () => {
  it('envia a abertura uma única vez e entrega os frames da bateria', () => {
    const spy = handlers()
    openBenchmarkStream(PAYLOAD, spy)
    const socket = FakeWebSocket.latest()

    socket.emitOpen()
    socket.emitOpen()
    socket.emitMessage({ type: 'progress', benchmark_session: benchmarkSession() })
    socket.emitMessage({
      type: 'result',
      benchmark_session: benchmarkSession({ status: 'completed' }),
    })
    socket.emitClose(1000)

    expect(socket.url).toBe('ws://localhost:8000/v1/benchmark/run')
    expect(socket.sentFrames).toEqual([JSON.stringify(PAYLOAD)])
    expect(spy.onSession.mock.calls.map((call) => call[1])).toEqual([false, true])
    expect(spy.onClose).toHaveBeenCalledWith(1000)
    expect(spy.onFailure).not.toHaveBeenCalled()
  })

  it('entrega o frame de recusa e falha pelo código de fechamento', () => {
    const spy = handlers()
    openBenchmarkStream(PAYLOAD, spy)
    const socket = FakeWebSocket.latest()

    socket.emitOpen()
    socket.emitMessage({ type: 'error', content: 'recusado' })
    socket.emitError()
    socket.emitClose(1003)
    socket.emitClose(1003)

    expect(spy.onErrorFrame).toHaveBeenCalledWith('recusado')
    expect(spy.onClose).toHaveBeenCalledTimes(1)
    const failure = spy.onFailure.mock.calls[0]?.[0] as WebSocketError
    expect(failure).toBeInstanceOf(WebSocketError)
    expect(failure.code).toBe(1003)
  })

  it('descarta frames ilegíveis sem encerrar a conexão', () => {
    const spy = handlers()
    openBenchmarkStream(PAYLOAD, spy)
    const socket = FakeWebSocket.latest()

    socket.emitMessage('{não é json')
    socket.emitMessage({ type: 'progress', benchmark_session: {} })

    expect(spy.onFrameWarning).toHaveBeenCalledTimes(2)
    expect(spy.onClose).not.toHaveBeenCalled()
  })

  it('falha quando a conexão não abre a tempo', () => {
    vi.useFakeTimers()
    const spy = handlers()
    openBenchmarkStream(PAYLOAD, spy)
    const socket = FakeWebSocket.latest()

    vi.advanceTimersByTime(5000)
    socket.emitOpen()

    expect(spy.onFailure).toHaveBeenCalledTimes(1)
    expect(socket.closeCalls).toEqual([undefined])
    expect(socket.sentFrames).toEqual([])
  })

  it('fechar pelo cliente encerra com 1000 e ignora eventos posteriores', () => {
    vi.useFakeTimers()
    const spy = handlers()
    const handle = openBenchmarkStream(PAYLOAD, spy)
    const socket = FakeWebSocket.latest()

    handle.close()
    handle.close()
    socket.emitMessage({ type: 'progress', benchmark_session: benchmarkSession() })
    vi.advanceTimersByTime(5000)

    expect(socket.closeCalls).toEqual([1000])
    expect(spy.onSession).not.toHaveBeenCalled()
    expect(spy.onFailure).not.toHaveBeenCalled()
  })
})
