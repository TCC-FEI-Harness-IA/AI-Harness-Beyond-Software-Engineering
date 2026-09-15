import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { HttpError } from '@/api/errors/HttpError'
import type * as SessionApiModule from '@/api/sessionApi'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import type { useSession as UseSessionHook } from './useSession'

vi.mock('@/api/sessionApi', async () => {
  const actual = await vi.importActual<typeof SessionApiModule>('@/api/sessionApi')
  return { ...actual, getSession: vi.fn() }
})

function buildDocument(id: string): SessionDocument {
  return {
    id,
    user_question: 'Pergunta',
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
  }
}

async function setup(): Promise<{ useSession: typeof UseSessionHook; getSession: Mock }> {
  const sessionApiModule = await import('@/api/sessionApi')
  const useSessionModule = await import('./useSession')
  return {
    useSession: useSessionModule.useSession,
    getSession: sessionApiModule.getSession as unknown as Mock,
  }
}

beforeEach(() => {
  vi.resetModules()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('useSession', () => {
  it('busca a sessão e expõe status success', async () => {
    const { useSession, getSession } = await setup()
    getSession.mockResolvedValue(buildDocument('sess_a'))

    const { result } = renderHook(() => useSession('sess_a'))
    expect(result.current.state.status).toBe('loading')

    await waitFor(() => expect(result.current.state.status).toBe('success'))
  })

  it('erro vira status error', async () => {
    const { useSession, getSession } = await setup()
    getSession.mockRejectedValue(new HttpError(404, 'não encontrada'))

    const { result } = renderHook(() => useSession('sess_missing'))

    await waitFor(() => expect(result.current.state.status).toBe('error'))
  })

  it('uma segunda montagem para o mesmo id não refaz a requisição (cache)', async () => {
    const { useSession, getSession } = await setup()
    getSession.mockResolvedValue(buildDocument('sess_a'))

    const first = renderHook(() => useSession('sess_a'))
    await waitFor(() => expect(first.result.current.state.status).toBe('success'))
    expect(getSession).toHaveBeenCalledTimes(1)

    const second = renderHook(() => useSession('sess_a'))
    expect(second.result.current.state.status).toBe('success')
    expect(getSession).toHaveBeenCalledTimes(1)
  })

  it('reload força uma nova busca, ignorando o cache', async () => {
    const { useSession, getSession } = await setup()
    getSession.mockResolvedValue(buildDocument('sess_a'))

    const { result } = renderHook(() => useSession('sess_a'))
    await waitFor(() => expect(result.current.state.status).toBe('success'))
    expect(getSession).toHaveBeenCalledTimes(1)

    act(() => {
      result.current.reload()
    })
    await waitFor(() => expect(getSession).toHaveBeenCalledTimes(2))
  })
})
