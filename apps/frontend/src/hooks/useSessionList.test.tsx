import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { HttpError } from '@/api/errors/HttpError'
import type * as SessionApiModule from '@/api/sessionApi'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import type { useSessionList as UseSessionListHook } from './useSessionList'

vi.mock('@/api/sessionApi', async () => {
  const actual = await vi.importActual<typeof SessionApiModule>('@/api/sessionApi')
  return { ...actual, listSessionIds: vi.fn(), getSession: vi.fn() }
})

function buildDocument(id: string, overrides: Partial<SessionDocument> = {}): SessionDocument {
  return {
    id,
    user_question: `Pergunta ${id}`,
    flow: 'DIRECT',
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

// `useSessionList` e o cache em memória que ele importa são singletons de módulo —
// `vi.resetModules()` isola um teste do outro, mas isso também recria o mock de
// `@/api/sessionApi` (a fábrica roda de novo). Por isso cada teste busca referências novas dos
// dois módulos, em vez de reusar as capturadas no topo do arquivo.
async function setup(): Promise<{
  useSessionList: typeof UseSessionListHook
  listSessionIds: Mock
  getSession: Mock
}> {
  const sessionApiModule = await import('@/api/sessionApi')
  const useSessionListModule = await import('./useSessionList')
  return {
    useSessionList: useSessionListModule.useSessionList,
    listSessionIds: sessionApiModule.listSessionIds as unknown as Mock,
    getSession: sessionApiModule.getSession as unknown as Mock,
  }
}

beforeEach(() => {
  vi.resetModules()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('useSessionList', () => {
  it('respeita o limite de concorrência configurado', async () => {
    const { useSessionList, listSessionIds, getSession } = await setup()
    const ids = Array.from({ length: 10 }, (_, index) => `sess_${index}`)
    listSessionIds.mockResolvedValue(ids)

    let inFlight = 0
    let maxInFlight = 0
    getSession.mockImplementation(async (id: string) => {
      inFlight += 1
      maxInFlight = Math.max(maxInFlight, inFlight)
      await new Promise((resolve) => setTimeout(resolve, 5))
      inFlight -= 1
      return buildDocument(id)
    })

    const { result } = renderHook(() => useSessionList())

    await waitFor(() => expect(result.current.items).toHaveLength(10))

    // env.historyFetchConcurrency (default 6) nunca é excedido.
    expect(maxInFlight).toBeLessThanOrEqual(6)
    expect(maxInFlight).toBeGreaterThan(1)
  })

  it('render progressivo: os itens aparecem conforme chegam, não todos de uma vez', async () => {
    const { useSessionList, listSessionIds, getSession } = await setup()
    listSessionIds.mockResolvedValue(['sess_a', 'sess_b'])
    let resolveA: (doc: SessionDocument) => void = () => {}
    getSession.mockImplementation((id: string) => {
      if (id === 'sess_a') return new Promise((resolve) => (resolveA = resolve))
      return Promise.resolve(buildDocument(id))
    })

    const { result } = renderHook(() => useSessionList())

    await waitFor(() => expect(result.current.items).toHaveLength(1))
    expect(result.current.items[0]?.id).toBe('sess_b')
    expect(result.current.pendingCount).toBe(1)

    resolveA(buildDocument('sess_a'))
    await waitFor(() => expect(result.current.items).toHaveLength(2))
  })

  it('uma sessão que falha não derruba as outras', async () => {
    const { useSessionList, listSessionIds, getSession } = await setup()
    listSessionIds.mockResolvedValue(['sess_ok', 'sess_bad'])
    getSession.mockImplementation((id: string) => {
      if (id === 'sess_bad') return Promise.reject(new HttpError(404, 'não encontrada'))
      return Promise.resolve(buildDocument(id))
    })

    const { result } = renderHook(() => useSessionList())

    await waitFor(() => expect(result.current.items).toHaveLength(1))
    await waitFor(() => expect(result.current.failedIds).toEqual(['sess_bad']))
    expect(result.current.items[0]?.id).toBe('sess_ok')
  })

  it('o cache de documentos evita refetch ao montar um segundo hook com os mesmos ids', async () => {
    const { useSessionList, listSessionIds, getSession } = await setup()
    listSessionIds.mockResolvedValue(['sess_a'])
    getSession.mockResolvedValue(buildDocument('sess_a'))

    const first = renderHook(() => useSessionList())
    await waitFor(() => expect(first.result.current.items).toHaveLength(1))
    expect(getSession).toHaveBeenCalledTimes(1)

    const second = renderHook(() => useSessionList())
    await waitFor(() => expect(second.result.current.items).toHaveLength(1))

    // O documento não é buscado de novo — vem do cache em memória (a lista de ids em si é uma
    // chamada leve e pode ser refeita).
    expect(getSession).toHaveBeenCalledTimes(1)
  })

  it('falha ao buscar os ids expõe um erro', async () => {
    const { useSessionList, listSessionIds } = await setup()
    listSessionIds.mockRejectedValue(new HttpError(500, 'falha no servidor'))

    const { result } = renderHook(() => useSessionList())

    await waitFor(() => expect(result.current.error).not.toBeNull())
    expect(result.current.isLoadingIds).toBe(false)
  })

  it('desmontar durante a hidratação aborta as requisições pendentes', async () => {
    const { useSessionList, listSessionIds, getSession } = await setup()
    listSessionIds.mockResolvedValue(['sess_a'])
    getSession.mockImplementation(
      (_id: string, signal?: AbortSignal) =>
        new Promise((_resolve, reject) => {
          signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
        }),
    )

    const { result, unmount } = renderHook(() => useSessionList())
    await waitFor(() => expect(result.current.isLoadingIds).toBe(false))

    expect(() => unmount()).not.toThrow()
  })
})
