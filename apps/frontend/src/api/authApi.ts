// `/auth/*` — cadastro, login, logout e sessão atual. O token de sessão vive num cookie HttpOnly
// definido pelo servidor; o front só recebe a conta, o fim da sessão e o token anti-CSRF.

import type { AuthSessionView, AuthUser } from '../domain/types/auth'
import { authHttpClient } from './httpClient'
import { parseAuthSession, parseRegisterResponse } from './parsers/auth'

export function register(email: string, password: string, signal?: AbortSignal): Promise<AuthUser> {
  return authHttpClient.post('/register', { email, password }, parseRegisterResponse, signal)
}

export function login(email: string, password: string, signal?: AbortSignal): Promise<AuthSessionView> {
  return authHttpClient.post('/login', { email, password }, parseAuthSession, signal)
}

export function getCurrentSession(signal?: AbortSignal): Promise<AuthSessionView> {
  return authHttpClient.get('/me', parseAuthSession, signal)
}

/** Revoga a sessão no servidor e remove os cookies de sessão e de credencial. */
export function logout(signal?: AbortSignal): Promise<void> {
  return authHttpClient.postEmpty('/logout', undefined, signal)
}
