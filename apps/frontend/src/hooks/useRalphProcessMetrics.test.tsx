import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { NetworkError } from '@/api/errors/NetworkError'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import { getSession } from '@/api/sessionApi'
import { clearRalphProcessMetricsCache, useRalphProcessMetrics } from './useRalphProcessMetrics'

vi.mock('@/api/sessionApi', () => ({ getSession: vi.fn() }))

const getSessionMock = getSession as unknown as Mock

function ralphDocument(id: string, tasks: string[]): SessionDocument {
  return {
    id,
    user_question: 'Q',
    flow: 'A1',
    flow_version: 2,
    model_name: 'm',
    max_tokens: 1,
    temperature: 0,
    status: 'completed',
    created_at: '',
    updated_at: '',
    final_answer: null,
    totals: {
      total_messages: 0,
      total_llm_calls: 3,
      tokens_input: 0,
      tokens_output: 0,
      total_tokens: 0,
      inference_time_ms: 0,
      wall_time_ms: 0,
    },
    messages: tasks.map((task, order) => ({
      id: `${id}-${order}`,
      order,
      timestamp: '',
      phase: 'B1',
      source: 'llm_agent',
      content: '',
      task_id: task,
      context_id: null,
      tokens_input: 0,
      tokens_output: 0,
      total_tokens: 0,
      inference_time_ms: 0,
      model_name: null,
      subtype: 'reasoning',
    })) as SessionDocument['messages'],
    degradations: [],
  }
}

afterEach(() => {
  clearRalphProcessMetricsCache()
  getSessionMock.mockReset()
})

describe('useRalphProcessMetrics', () => {
  it('só busca depois de load, conta falhas e reaproveita o cache', async () => {
    getSessionMock.mockImplementation((id: string) =>
      id === 'bad' ? Promise.reject(new NetworkError('offline')) : Promise.resolve(ralphDocument(id, ['T1', 'T2'])),
    )
    const { result, rerender } = renderHook(({ ids }) => useRalphProcessMetrics(ids), {
      initialProps: { ids: ['r1', 'bad'] },
    })
    expect(result.current).toMatchObject({ enabled: false, loaded: 0, total: 2 })
    expect(getSessionMock).not.toHaveBeenCalled()

    act(() => result.current.load())
    await waitFor(() => expect(result.current.running).toBe(false))
    expect(result.current).toMatchObject({ enabled: true, loaded: 1, failed: 1 })
    expect(result.current.metrics.get('r1')?.taskCount).toBe(2)

    rerender({ ids: ['r1'] })
    await waitFor(() => expect(result.current.loaded).toBe(1))
    expect(result.current.running).toBe(false)
    expect(getSessionMock).toHaveBeenCalledTimes(2)

    const second = renderHook(() => useRalphProcessMetrics(['r1']))
    expect(second.result.current.loaded).toBe(1)
  })

  it('aborta as buscas pendentes ao desmontar', async () => {
    let signal: AbortSignal | undefined
    getSessionMock.mockImplementation(
      (_id: string, abort: AbortSignal) =>
        new Promise((_resolve, reject) => {
          signal = abort
          abort.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
        }),
    )
    const { result, unmount } = renderHook(() => useRalphProcessMetrics(['r1']))
    act(() => result.current.load())
    await waitFor(() => expect(signal).toBeDefined())
    unmount()
    expect(signal?.aborted).toBe(true)
  })
})
