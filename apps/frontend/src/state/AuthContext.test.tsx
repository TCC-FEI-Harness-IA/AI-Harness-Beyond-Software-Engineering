import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { emitUnauthorized } from '@/api/authEvents'
import { getCsrfToken } from '@/api/csrfToken'
import { HttpError } from '@/api/errors/HttpError'
import type { AuthSessionView, CredentialStatus } from '@/domain/types/auth'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import { getCachedSession, setCachedSession } from '@/hooks/sessionCache'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import { type AuthApi, AuthProvider, useAuth } from './AuthContext'

const SESSAO: AuthSessionView = {
  user: { id: 'usr_ana', email: 'ana@exemplo.com', role: 'user' },
  expiresAt: '2026-11-16T12:00:00+00:00',
  csrfToken: 'csrf-ana',
}
const VALIDA: CredentialStatus = { status: 'valid', available: true, expiresAt: SESSAO.expiresAt }
const AUSENTE: CredentialStatus = { status: 'missing', available: false, expiresAt: null }

function api(overrides: Partial<AuthApi> = {}): AuthApi {
  return {
    getCurrentSession: vi.fn().mockRejectedValue(new HttpError(401, null)),
    login: vi.fn().mockResolvedValue(SESSAO),
    register: vi.fn().mockResolvedValue(SESSAO.user),
    logout: vi.fn().mockResolvedValue(undefined),
    getCredentialStatus: vi.fn().mockResolvedValue(AUSENTE),
    saveCredential: vi.fn().mockResolvedValue(VALIDA),
    deleteCredential: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

let atual: ReturnType<typeof useAuth> | null = null

function Sonda(): JSX.Element {
  atual = useAuth()
  return (
    <p>
      {atual.status}|{atual.user?.email ?? '-'}|{atual.credential.status}|{String(atual.canRunLlm)}|
      {String(atual.expired)}
    </p>
  )
}

function montar(fake: AuthApi): void {
  render(
    <AuthProvider api={fake}>
      <Sonda />
    </AuthProvider>,
  )
}

describe('AuthContext', () => {
  it('visitante: sem sessão, sem credencial e sem execução', async () => {
    montar(api())

    await screen.findByText('anonymous|-|unknown|false|false')
  })

  it('restaura a sessão e o estado da credencial ao abrir o app', async () => {
    montar(api({ getCurrentSession: vi.fn().mockResolvedValue(SESSAO), getCredentialStatus: vi.fn().mockResolvedValue(VALIDA) }))

    await screen.findByText('authenticated|ana@exemplo.com|valid|true|false')
    expect(getCsrfToken()).toBe('csrf-ana')
  })

  it('login com chave recusada mantém a conta autenticada sem liberar execução', async () => {
    const fake = api({ saveCredential: vi.fn().mockRejectedValue(new HttpError(422, 'A OpenRouter recusou a chave informada.')) })
    montar(fake)
    await screen.findByText(/anonymous/)

    await act(async () => {
      await atual?.login('ana@exemplo.com', 'senha muito boa 1')
    })
    let aceita = true
    await act(async () => {
      aceita = (await atual?.saveApiKey('sk-or-v1-ruim')) ?? true
    })

    expect(aceita).toBe(false)
    await screen.findByText('authenticated|ana@exemplo.com|invalid|false|false')
    expect(atual?.credential.message).toMatch(/recusou/)
  })

  it('troca e remove a chave da sessão atual', async () => {
    const fake = api({ getCurrentSession: vi.fn().mockResolvedValue(SESSAO) })
    montar(fake)
    await screen.findByText(/missing/)

    await act(async () => {
      await atual?.saveApiKey('sk-or-v1-boa')
    })
    await screen.findByText(/\|valid\|true/)
    await act(async () => {
      await atual?.removeApiKey()
    })

    await screen.findByText(/\|missing\|false/)
    expect(fake.deleteCredential).toHaveBeenCalledTimes(1)
  })

  it('cadastro cria a conta e entra em seguida', async () => {
    const fake = api()
    montar(fake)
    await screen.findByText(/anonymous/)

    await act(async () => {
      await atual?.register('ana@exemplo.com', 'senha muito boa 1')
    })

    expect(fake.register).toHaveBeenCalledWith('ana@exemplo.com', 'senha muito boa 1')
    expect(fake.login).toHaveBeenCalledWith('ana@exemplo.com', 'senha muito boa 1')
    await screen.findByText(/authenticated\|ana@exemplo.com/)
  })

  it('logout encerra no servidor e limpa caches, token anti-CSRF e estado', async () => {
    const fake = api({ getCurrentSession: vi.fn().mockResolvedValue(SESSAO) })
    montar(fake)
    await screen.findByText(/authenticated/)
    setCachedSession(completedFixture as unknown as SessionDocument)

    await act(async () => {
      await atual?.logout()
    })

    expect(fake.logout).toHaveBeenCalledTimes(1)
    await screen.findByText('anonymous|-|unknown|false|false')
    expect(getCsrfToken()).toBeNull()
    expect(getCachedSession(completedFixture.id)).toBeUndefined()
  })

  it('falha no logout mantém a sessão e permite tentar a revogação novamente', async () => {
    const fake = api({
      getCurrentSession: vi.fn().mockResolvedValue(SESSAO),
      logout: vi.fn().mockRejectedValueOnce(new Error('rede')).mockResolvedValue(undefined),
    })
    montar(fake)
    await screen.findByText(/authenticated/)
    setCachedSession(completedFixture as unknown as SessionDocument)

    await act(async () => {
      await atual?.logout()
    })

    expect(atual?.status).toBe('authenticated')
    expect(atual?.user?.id).toBe('usr_ana')
    expect(getCsrfToken()).toBe('csrf-ana')
    expect(getCachedSession(completedFixture.id)).toBeDefined()
    expect(atual?.logoutError).toMatch(/Não foi possível confirmar/)

    await act(async () => {
      await atual?.logout()
    })

    expect(fake.logout).toHaveBeenCalledTimes(2)
    await screen.findByText(/^anonymous/)
    expect(atual?.logoutError).toBeNull()
    expect(getCsrfToken()).toBeNull()
    expect(getCachedSession(completedFixture.id)).toBeUndefined()
  })

  it('sessão expirada ou revogada volta a visitante e avisa uma vez', async () => {
    montar(api({ getCurrentSession: vi.fn().mockResolvedValue(SESSAO) }))
    await screen.findByText(/authenticated/)

    act(() => emitUnauthorized())

    await screen.findByText('anonymous|-|unknown|false|true')
    act(() => atual?.dismissExpired())
    await screen.findByText('anonymous|-|unknown|false|false')
  })

  it('um 401 de visitante não é tratado como expiração', async () => {
    montar(api())
    await screen.findByText(/anonymous/)

    act(() => emitUnauthorized())

    await waitFor(() => expect(atual?.expired).toBe(false))
  })

  it('falha ao consultar a credencial não libera execução', async () => {
    montar(api({ getCurrentSession: vi.fn().mockResolvedValue(SESSAO), getCredentialStatus: vi.fn().mockRejectedValue(new Error('rede')) }))

    await screen.findByText('authenticated|ana@exemplo.com|error|false|false')
  })

  it('useAuth fora do provider é um erro de programação', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => render(<Sonda />)).toThrow(/AuthProvider/)
  })
})
