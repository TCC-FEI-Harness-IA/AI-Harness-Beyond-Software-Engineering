import { afterEach, describe, expect, it, vi } from 'vitest'
import { fakeResponse, fetchCalls, stubBaseEnv } from '@/test/apiTestKit'

const SESSAO = {
  user: { id: 'usr_1', email: 'ana@exemplo.com', role: 'user' },
  session: { expires_at: '2026-11-16T12:00:00+00:00' },
  csrf_token: 'csrf-1',
}

async function importAuthApi() {
  vi.resetModules()
  stubBaseEnv()
  const [authApi, errors, csrf] = await Promise.all([import('./authApi'), import('./errors'), import('./csrfToken')])
  return { ...authApi, ...errors, ...csrf }
}

describe('authApi', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('login devolve conta, fim da sessão e token anti-CSRF', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, SESSAO))
    vi.stubGlobal('fetch', fetchMock)
    const { login } = await importAuthApi()

    const sessao = await login('ana@exemplo.com', 'senha muito boa 1')

    expect(sessao).toEqual({
      user: { id: 'usr_1', email: 'ana@exemplo.com', role: 'user' },
      expiresAt: '2026-11-16T12:00:00+00:00',
      csrfToken: 'csrf-1',
    })
    const [chamada] = fetchCalls(fetchMock)
    expect(chamada?.url).toBe('http://localhost:8000/auth/login')
    expect(chamada?.method).toBe('POST')
    expect(chamada?.body).toEqual({ email: 'ana@exemplo.com', password: 'senha muito boa 1' })
  })

  it('cadastro, sessão atual e logout usam os caminhos do serviço de autenticação', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(fakeResponse(201, { user: SESSAO.user }))
      .mockResolvedValueOnce(fakeResponse(200, SESSAO))
      .mockResolvedValueOnce(fakeResponse(204))
    vi.stubGlobal('fetch', fetchMock)
    const { register, getCurrentSession, logout, setCsrfToken } = await importAuthApi()

    await expect(register('ana@exemplo.com', 'senha muito boa 1')).resolves.toEqual(SESSAO.user)
    await expect(getCurrentSession()).resolves.toMatchObject({ csrfToken: 'csrf-1' })
    setCsrfToken('csrf-1')
    await logout()

    const chamadas = fetchCalls(fetchMock)
    expect(chamadas.map((item) => `${item.method} ${item.url}`)).toEqual([
      'POST http://localhost:8000/auth/register',
      'GET http://localhost:8000/auth/me',
      'POST http://localhost:8000/auth/logout',
    ])
    expect(chamadas[2]?.headers.get('X-CSRF-Token')).toBe('csrf-1')
  })

  it('perfil desconhecido viola o contrato', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(fakeResponse(200, { ...SESSAO, user: { ...SESSAO.user, role: 'root' } })))
    const { getCurrentSession, ContractError } = await importAuthApi()

    await expect(getCurrentSession()).rejects.toBeInstanceOf(ContractError)
  })
})
