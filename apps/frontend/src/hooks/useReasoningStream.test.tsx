import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { RunConfig } from '@/api/messageApi'
import { FakeWebSocket } from '@/test/doubles/FakeWebSocket'
import { useReasoningStream } from './useReasoningStream'

const CONFIG: RunConfig = {
  modelName: 'openai/gpt-4o-mini',
  provider: 'open_router',
  maxTokens: 1000,
  temperature: 0.3,
}

const VALID_EVENT = {
  type: 'thinking',
  subtype: 'reasoning',
  phase: 'B1',
  task: 'T1',
  session_id: 'sess_abc123',
  content: 'conteúdo',
  total_tokens: 10,
  context_window: { context_id: 'ctx_1', context_size: 5 },
  inference_time_ms: 100,
}

beforeEach(() => {
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useReasoningStream', () => {
  it('start envia exatamente um frame no open', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('Quais são todos os números primos entre 0 e 20?')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
    })

    expect(socket.sentFrames).toHaveLength(1)
    expect(result.current.isStreaming).toBe(true)
  })

  it('eventos recebidos atualizam o run', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('pergunta')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
      socket.emitMessage(VALID_EVENT)
    })

    expect(result.current.run.steps).toHaveLength(1)
    expect(result.current.run.steps[0]).toMatchObject({ content: 'conteúdo', subtype: 'reasoning' })
    expect(result.current.run.sessionId).toBe('sess_abc123')
  })

  it('close(1000) leva o run a completed', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('pergunta')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
      socket.emitMessage(VALID_EVENT)
      socket.emitClose(1000)
    })

    expect(result.current.run.status).toBe('completed')
    expect(result.current.isStreaming).toBe(false)
  })

  it('close(1011) leva o run a failed preservando os passos recebidos', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('pergunta')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
      socket.emitMessage(VALID_EVENT)
      socket.emitClose(1011)
    })

    expect(result.current.run.status).toBe('failed')
    expect(result.current.run.error).not.toBeNull()
    expect(result.current.run.steps).toHaveLength(1)
    expect(result.current.isStreaming).toBe(false)
  })

  it('cancel fecha o socket e nenhum evento posterior é processado', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('pergunta')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
      socket.emitMessage(VALID_EVENT)
    })
    expect(result.current.run.steps).toHaveLength(1)

    act(() => {
      result.current.cancel()
    })
    expect(socket.closeCalls).toEqual([1000])
    expect(result.current.isStreaming).toBe(false)

    act(() => {
      socket.emitMessage(VALID_EVENT)
      socket.emitClose(1000)
    })
    expect(result.current.run.steps).toHaveLength(1)
  })

  it('desmontar fecha o socket', () => {
    const { result, unmount } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('pergunta')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
    })

    unmount()

    expect(socket.closeCalls).toEqual([1000])
  })

  it('frame malformado no meio do stream gera um aviso não fatal e os frames seguintes continuam sendo processados', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('pergunta')
    })
    const socket = FakeWebSocket.latest()
    act(() => {
      socket.emitOpen()
      socket.emitMessage('{')
    })

    expect(result.current.run.warning).not.toBeNull()
    expect(result.current.run.status).not.toBe('failed')
    expect(result.current.isStreaming).toBe(true)

    act(() => {
      socket.emitMessage(VALID_EVENT)
    })
    expect(result.current.run.steps).toHaveLength(1)
    expect(result.current.run.warning).toBeNull()
  })

  it('start durante um streaming em andamento é ignorado', () => {
    const { result } = renderHook(() => useReasoningStream(CONFIG))

    act(() => {
      result.current.start('primeira pergunta')
    })
    act(() => {
      result.current.start('segunda pergunta')
    })

    expect(FakeWebSocket.instances).toHaveLength(1)
  })
})
