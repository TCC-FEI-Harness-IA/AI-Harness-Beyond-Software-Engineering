// Renderiza telas dentro do `AuthProvider` real, com a API de autenticação substituída por dublês.
import { render, type RenderResult } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { HttpError } from '@/api/errors/HttpError'
import type { AuthSessionView, CredentialStatus } from '@/domain/types/auth'
import { type AuthApi, AuthProvider } from '@/state/AuthContext'
import { ThemeProvider } from '@/state/ThemeContext'

export const SESSAO_ANA: AuthSessionView = {
  user: { id: 'usr_ana', email: 'ana@exemplo.com', role: 'user' },
  expiresAt: '2026-11-16T12:00:00+00:00',
  csrfToken: 'csrf-ana',
}
export const CREDENCIAL_VALIDA: CredentialStatus = { status: 'valid', available: true, expiresAt: SESSAO_ANA.expiresAt }
export const CREDENCIAL_AUSENTE: CredentialStatus = { status: 'missing', available: false, expiresAt: null }

export function fakeAuthApi(overrides: Partial<AuthApi> = {}): AuthApi {
  return {
    getCurrentSession: vi.fn().mockRejectedValue(new HttpError(401, null)),
    login: vi.fn().mockResolvedValue(SESSAO_ANA),
    register: vi.fn().mockResolvedValue(SESSAO_ANA.user),
    logout: vi.fn().mockResolvedValue(undefined),
    getCredentialStatus: vi.fn().mockResolvedValue(CREDENCIAL_AUSENTE),
    saveCredential: vi.fn().mockResolvedValue(CREDENCIAL_VALIDA),
    deleteCredential: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

/** Visitante (padrão) ou usuário autenticado, com ou sem credencial válida. */
export function authApiFor(kind: 'visitor' | 'user' | 'user-with-key'): AuthApi {
  if (kind === 'visitor') return fakeAuthApi()
  return fakeAuthApi({
    getCurrentSession: vi.fn().mockResolvedValue(SESSAO_ANA),
    getCredentialStatus: vi.fn().mockResolvedValue(kind === 'user-with-key' ? CREDENCIAL_VALIDA : CREDENCIAL_AUSENTE),
  })
}

export function renderWithAuth(ui: ReactNode, options: { api?: AuthApi; route?: string } = {}): RenderResult {
  return render(
    <MemoryRouter initialEntries={[options.route ?? '/']}>
      <ThemeProvider>
        <AuthProvider api={options.api ?? fakeAuthApi()}>{ui}</AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}
