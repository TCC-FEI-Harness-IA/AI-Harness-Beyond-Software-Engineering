// Sessão de autenticação e credencial OpenRouter, mantidas como estados separados: estar
// autenticado não basta para executar — `canRunLlm` exige também uma credencial válida. A chave em
// si nunca fica no estado (nem em storage): vai uma vez ao backend e volta como cookie HttpOnly.

import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import * as authApi from '@/api/authApi'
import { onUnauthorized } from '@/api/authEvents'
import * as credentialsApi from '@/api/credentialsApi'
import { clearCsrfToken, setCsrfToken } from '@/api/csrfToken'
import { AppError } from '@/api/errors/AppError'
import { HttpError } from '@/api/errors/HttpError'
import type { AuthSessionView, AuthUser, CredentialStatus } from '@/domain/types/auth'
import { clearSessionCache } from '@/hooks/sessionCache'
import { clearRalphProcessMetricsCache } from '@/hooks/useRalphProcessMetrics'

export interface AuthApi {
  getCurrentSession: (signal?: AbortSignal) => Promise<AuthSessionView>
  login: (email: string, password: string) => Promise<AuthSessionView>
  register: (email: string, password: string) => Promise<AuthUser>
  logout: () => Promise<void>
  getCredentialStatus: (signal?: AbortSignal) => Promise<CredentialStatus>
  saveCredential: (apiKey: string) => Promise<CredentialStatus>
  deleteCredential: () => Promise<void>
}

const DEFAULT_API: AuthApi = {
  getCurrentSession: authApi.getCurrentSession,
  login: authApi.login,
  register: authApi.register,
  logout: authApi.logout,
  getCredentialStatus: credentialsApi.getCredentialStatus,
  saveCredential: credentialsApi.saveCredential,
  deleteCredential: credentialsApi.deleteCredential,
}

export type AuthStatus = 'loading' | 'anonymous' | 'authenticated'
export type CredentialUiStatus = 'unknown' | 'checking' | 'missing' | 'valid' | 'invalid' | 'error'

export interface CredentialUiState {
  status: CredentialUiStatus
  expiresAt: string | null
  /** Motivo da última recusa ou falha, já em texto para o usuário. */
  message: string | null
}

export interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  sessionExpiresAt: string | null
  /** A sessão anterior terminou (expirou ou foi revogada) — mostra o aviso para entrar de novo. */
  expired: boolean
  /** A saída não foi confirmada pelo servidor; a sessão local continua ativa até nova tentativa. */
  logoutError: string | null
  credential: CredentialUiState
  /** Autenticado e com credencial válida: as únicas condições para executar chamadas LLM. */
  canRunLlm: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Envia a chave uma única vez; devolve se a OpenRouter a aceitou. */
  saveApiKey: (apiKey: string) => Promise<boolean>
  removeApiKey: () => Promise<void>
  refreshCredential: () => void
  dismissExpired: () => void
}

const UNKNOWN_CREDENTIAL: CredentialUiState = { status: 'unknown', expiresAt: null, message: null }
const CREDENTIAL_FAILURE = 'Não foi possível consultar a sua chave OpenRouter agora.'

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof HttpError && error.detail) return error.detail
  return error instanceof AppError ? error.userMessage : fallback
}

function fromStatus(status: CredentialStatus): CredentialUiState {
  return { status: status.status, expiresAt: status.expiresAt, message: null }
}

/** Dados da conta anterior não podem aparecer para a próxima: caches de sessões e métricas. */
function clearUserScopedState(): void {
  clearCsrfToken()
  clearSessionCache()
  clearRalphProcessMetricsCache()
}

export interface AuthInitialState {
  session: AuthSessionView
  credential: CredentialStatus
}

export interface AuthProviderProps {
  children: ReactNode
  api?: AuthApi
  /** Sessão já conhecida (testes de telas); sem ela, a sessão é consultada em `/auth/me`. */
  initialState?: AuthInitialState
}

export function AuthProvider({ children, api = DEFAULT_API, initialState }: AuthProviderProps): JSX.Element {
  const [status, setStatus] = useState<AuthStatus>(initialState ? 'authenticated' : 'loading')
  const [session, setSession] = useState<AuthSessionView | null>(initialState?.session ?? null)
  const [credential, setCredential] = useState<CredentialUiState>(
    initialState ? fromStatus(initialState.credential) : UNKNOWN_CREDENTIAL,
  )
  const skipBootstrap = useRef(initialState !== undefined)
  if (initialState) setCsrfToken(initialState.session.csrfToken)
  const [expired, setExpired] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)
  const [credentialToken, setCredentialToken] = useState(0)
  const statusRef = useRef<AuthStatus>('loading')
  statusRef.current = status

  const becomeAnonymous = useCallback((wasExpired: boolean) => {
    clearUserScopedState()
    setSession(null)
    setCredential(UNKNOWN_CREDENTIAL)
    setStatus('anonymous')
    setExpired(wasExpired)
    setLogoutError(null)
  }, [])

  const enter = useCallback((view: AuthSessionView) => {
    clearUserScopedState()
    setCsrfToken(view.csrfToken)
    setSession(view)
    setExpired(false)
    setLogoutError(null)
    setStatus('authenticated')
    setCredentialToken((token) => token + 1)
  }, [])

  useEffect(() => {
    if (skipBootstrap.current) return undefined
    const controller = new AbortController()
    api
      .getCurrentSession(controller.signal)
      .then((view) => {
        if (!controller.signal.aborted) enter(view)
      })
      .catch(() => {
        if (!controller.signal.aborted) becomeAnonymous(false)
      })
    return () => controller.abort()
  }, [api, enter, becomeAnonymous])

  useEffect(
    () =>
      onUnauthorized(() => {
        if (statusRef.current === 'authenticated') becomeAnonymous(true)
      }),
    [becomeAnonymous],
  )

  useEffect(() => {
    if (status !== 'authenticated') return undefined
    if (skipBootstrap.current) {
      skipBootstrap.current = false
      return undefined
    }
    const controller = new AbortController()
    setCredential((prev) => ({ ...prev, status: 'checking' }))
    api
      .getCredentialStatus(controller.signal)
      .then((next) => {
        if (!controller.signal.aborted) setCredential(fromStatus(next))
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setCredential({ status: 'error', expiresAt: null, message: errorMessage(error, CREDENTIAL_FAILURE) })
        }
      })
    return () => controller.abort()
  }, [api, status, credentialToken])

  const login = useCallback(
    async (email: string, password: string) => {
      enter(await api.login(email, password))
    },
    [api, enter],
  )

  const register = useCallback(
    async (email: string, password: string) => {
      await api.register(email, password)
      enter(await api.login(email, password))
    },
    [api, enter],
  )

  const logout = useCallback(async () => {
    setLogoutError(null)
    try {
      await api.logout()
    } catch {
      setLogoutError('Não foi possível confirmar sua saída. A sessão pode continuar ativa. Tente novamente.')
      return
    }
    becomeAnonymous(false)
  }, [api, becomeAnonymous])

  const saveApiKey = useCallback(
    async (apiKey: string) => {
      setCredential((prev) => ({ ...prev, status: 'checking', message: null }))
      try {
        setCredential(fromStatus(await api.saveCredential(apiKey)))
        return true
      } catch (error) {
        setCredential({ status: 'invalid', expiresAt: null, message: errorMessage(error, CREDENTIAL_FAILURE) })
        return false
      }
    },
    [api],
  )

  const removeApiKey = useCallback(async () => {
    await api.deleteCredential()
    setCredential({ status: 'missing', expiresAt: null, message: null })
  }, [api])

  const refreshCredential = useCallback(() => setCredentialToken((token) => token + 1), [])
  const dismissExpired = useCallback(() => setExpired(false), [])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: session?.user ?? null,
      sessionExpiresAt: session?.expiresAt ?? null,
      expired,
      logoutError,
      credential,
      canRunLlm: status === 'authenticated' && credential.status === 'valid',
      login,
      register,
      logout,
      saveApiKey,
      removeApiKey,
      refreshCredential,
      dismissExpired,
    }),
    [status, session, expired, logoutError, credential, login, register, logout, saveApiKey, removeApiKey, refreshCredential, dismissExpired],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (value === undefined) throw new Error('useAuth precisa estar dentro de <AuthProvider>.')
  return value
}
