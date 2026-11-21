import { afterEach, describe, expect, it, vi } from 'vitest'
import { getBackendLimits } from './limitsApi'

afterEach(() => vi.unstubAllGlobals())

describe('getBackendLimits', () => {
  it('busca o limite de tokens por sessão do backend', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      text: () => Promise.resolve(JSON.stringify({ max_tokens_limit: 64000 })),
    })
    vi.stubGlobal('fetch', fetchMock)

    expect(await getBackendLimits()).toEqual({ max_tokens_limit: 64000 })
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/v1/limits')
  })
})
