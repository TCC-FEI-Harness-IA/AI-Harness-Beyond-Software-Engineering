import { afterEach, describe, expect, it, vi } from 'vitest'
import type * as WebsocketClientModule from './websocketClient'
import { FakeWebSocket } from '../test/doubles/FakeWebSocket'
import type { DefaultInputDTO } from '../domain/types/defaultInput'

const BASE_ENV: Record<string, string> = {
  VITE_API_BASE_URL: 'http://localhost:8000',
  VITE_WS_BASE_URL: 'ws://localhost:8000',
  VITE_API_PREFIX: '/v1',
  VITE_REQUEST_TIMEOUT_MS: '5000',
  VITE_WS_OPEN_TIMEOUT_MS: '5000',
  VITE_DEFAULT_PROVIDER: 'open_router',
  VITE_AVAILABLE_MODELS: 'openai/gpt-4o-mini',
  VITE_DEFAULT_MODEL: 'openai/gpt-4o-mini',
  VITE_DEFAULT_MAX_TOKENS: '1200',
  VITE_DEFAULT_TEMPERATURE: '0.3',
  VITE_HISTORY_FETCH_CONCURRENCY: '6',
  VITE_HISTORY_SUMMARY_MAX_CHARS: '120',
  VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS: '48',
  VITE_ENABLE_DEBUG_PANEL: 'false',
}

function stubEnv(overrides: Record<string, string> = {}): void {
  for (const [key, value] of Object.entries({ ...BASE_ENV, ...overrides })) {
    vi.stubEnv(key, value)
  }
}

async function importWebsocketClient(
  overrides: Record<string, string> = {},
): Promise<typeof WebsocketClientModule> {
  vi.resetModules()
  stubEnv(overrides)
  FakeWebSocket.reset()
  vi.stubGlobal('WebSocket', FakeWebSocket)
  return import('./websocketClient')
}

const PAYLOAD: DefaultInputDTO = {
  message: { user_input: 'Quais são todos os números primos entre 0 e 20?' },
  llm_model_config: {
    provider: 'open_router',
    provider_config: { model_name: 'openai/gpt-4o-mini', endpoint: null },
    max_tokens: 1000,
    temperature: 0.3,
  },
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

function makeHandlers() {
  return {
    onEvent: vi.fn(),
    onErrorFrame: vi.fn(),
    onClose: vi.fn(),
    onFailure: vi.fn(),
  }
}

describe('openReasoningStream', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('envia exatamente um frame de texto no onopen', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    socket.emitOpen()

    expect(socket.sentFrames).toHaveLength(1)
    expect(JSON.parse(socket.sentFrames[0] ?? '')).toEqual(PAYLOAD)
  })

  it('cada mensagem completa vira onEvent', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    socket.emitMessage(VALID_EVENT)

    expect(handlers.onEvent).toHaveBeenCalledWith(VALID_EVENT)
    expect(handlers.onErrorFrame).not.toHaveBeenCalled()
  })

  it('close(1000) chama onClose(1000) e não onFailure', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    socket.emitClose(1000)

    expect(handlers.onClose).toHaveBeenCalledWith(1000)
    expect(handlers.onFailure).not.toHaveBeenCalled()
  })

  it('close(1011) chama onFailure', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    socket.emitClose(1011)

    expect(handlers.onFailure).toHaveBeenCalled()
  })

  it('nenhum handler dispara depois de handle.close()', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    const handle = openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    handle.close()

    expect(socket.closeCalls).toEqual([1000])

    socket.emitMessage(VALID_EVENT)
    socket.emitClose(1011)

    expect(handlers.onEvent).not.toHaveBeenCalled()
    expect(handlers.onClose).not.toHaveBeenCalled()
    expect(handlers.onFailure).not.toHaveBeenCalled()
  })

  it('chamar close() duas vezes é seguro', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    const handle = openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    handle.close()
    handle.close()

    expect(socket.closeCalls).toEqual([1000])
  })

  it('frame malformado vira onFailure e o socket continua aberto', async () => {
    const { openReasoningStream } = await importWebsocketClient()
    const handlers = makeHandlers()
    openReasoningStream(PAYLOAD, handlers)

    const socket = FakeWebSocket.latest()
    socket.emitOpen()
    socket.emitMessage({ isso: 'não é um frame válido' })

    expect(handlers.onFailure).toHaveBeenCalled()
    expect(socket.closeCalls).toHaveLength(0)

    socket.emitMessage(VALID_EVENT)
    expect(handlers.onEvent).toHaveBeenCalledWith(VALID_EVENT)
  })

  it('onopen que não vem dentro do timeout vira onFailure', async () => {
    vi.useFakeTimers()
    const { openReasoningStream } = await importWebsocketClient({ VITE_WS_OPEN_TIMEOUT_MS: '50' })
    const handlers = makeHandlers()
    openReasoningStream(PAYLOAD, handlers)

    await vi.advanceTimersByTimeAsync(60)

    expect(handlers.onFailure).toHaveBeenCalled()
  })
})
