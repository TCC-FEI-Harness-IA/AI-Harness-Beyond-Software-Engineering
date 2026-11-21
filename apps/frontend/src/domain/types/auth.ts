// Contratos do serviço de autenticação e da credencial OpenRouter, já no vocabulário do front.

export type UserRole = 'user' | 'admin'

export interface AuthUser {
  id: string
  email: string
  role: UserRole
}

/** Sessão de autenticação atual. O token da sessão nunca chega aqui: fica num cookie HttpOnly. */
export interface AuthSessionView {
  user: AuthUser
  /** Fim absoluto da sessão (24 h após o login). */
  expiresAt: string
  /** Token anti-CSRF da sessão, enviado em `X-CSRF-Token` nas escritas. */
  csrfToken: string
}

export type CredentialState = 'missing' | 'valid' | 'invalid'

/** Só o estado da credencial; o conteúdo da chave nunca volta do servidor. */
export interface CredentialStatus {
  status: CredentialState
  available: boolean
  expiresAt: string | null
}
