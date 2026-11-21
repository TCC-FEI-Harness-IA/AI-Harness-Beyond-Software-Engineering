import { afterEach, describe, expect, it, vi } from 'vitest'
import { fakeResponse, fetchCalls, stubBaseEnv } from '@/test/apiTestKit'

async function importCredentialsApi() {
  vi.resetModules()
  stubBaseEnv()
  const [api, errors] = await Promise.all([import('./credentialsApi'), import('./errors')])
  return { ...api, ...errors }
}

describe('credentialsApi', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('envia a chave uma única vez e só recebe de volta o estado da credencial', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      fakeResponse(200, { status: 'valid', available: true, expires_at: '2026-11-16T12:00:00+00:00' }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { saveCredential } = await importCredentialsApi()

    const estado = await saveCredential('sk-or-v1-chave')

    expect(estado).toEqual({ status: 'valid', available: true, expiresAt: '2026-11-16T12:00:00+00:00' })
    expect(JSON.stringify(estado)).not.toContain('sk-or')
    const [chamada] = fetchCalls(fetchMock)
    expect(chamada?.method).toBe('PUT')
    expect(chamada?.url).toBe('http://localhost:8000/v1/credentials/openrouter')
    expect(chamada?.body).toEqual({ api_key: 'sk-or-v1-chave' })
  })

  it('consulta e remove a credencial', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(fakeResponse(200, { status: 'missing', available: false, expires_at: null }))
      .mockResolvedValueOnce(fakeResponse(204))
    vi.stubGlobal('fetch', fetchMock)
    const { getCredentialStatus, deleteCredential } = await importCredentialsApi()

    await expect(getCredentialStatus()).resolves.toEqual({ status: 'missing', available: false, expiresAt: null })
    await deleteCredential()

    expect(fetchCalls(fetchMock)[1]?.method).toBe('DELETE')
  })

  it('estado desconhecido viola o contrato', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(fakeResponse(200, { status: 'talvez', available: true, expires_at: null })))
    const { getCredentialStatus, ContractError } = await importCredentialsApi()

    await expect(getCredentialStatus()).rejects.toBeInstanceOf(ContractError)
  })
})
