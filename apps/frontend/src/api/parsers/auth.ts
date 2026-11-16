// `unknown` → contratos do serviço de autenticação e da credencial OpenRouter.

import type { AuthSessionView, AuthUser, CredentialState, CredentialStatus, UserRole } from '@/domain/types/auth'
import { ContractError } from '../errors/ContractError'
import { optionalString, requireObject, requireString } from './primitives'

const ROLES: readonly UserRole[] = ['user', 'admin']
const CREDENTIAL_STATES: readonly CredentialState[] = ['missing', 'valid', 'invalid']

export function parseAuthUser(raw: unknown, path = 'user'): AuthUser {
  const source = requireObject(raw, path)
  const role = requireString(source, 'role', `${path}.role`)
  if (!(ROLES as readonly string[]).includes(role)) {
    throw new ContractError(`campo "${path}.role" desconhecido: ${role}`)
  }
  return {
    id: requireString(source, 'id', `${path}.id`),
    email: requireString(source, 'email', `${path}.email`),
    role: role as UserRole,
  }
}

export function parseRegisterResponse(raw: unknown): AuthUser {
  return parseAuthUser(requireObject(raw, 'resposta')['user'])
}

export function parseAuthSession(raw: unknown): AuthSessionView {
  const source = requireObject(raw, 'resposta')
  const session = requireObject(source['session'], 'session')
  return {
    user: parseAuthUser(source['user']),
    expiresAt: requireString(session, 'expires_at', 'session.expires_at'),
    csrfToken: requireString(source, 'csrf_token', 'csrf_token'),
  }
}

export function parseCredentialStatus(raw: unknown): CredentialStatus {
  const source = requireObject(raw, 'credencial')
  const status = requireString(source, 'status', 'status')
  if (!(CREDENTIAL_STATES as readonly string[]).includes(status)) {
    throw new ContractError(`campo "status" desconhecido: ${status}`)
  }
  return {
    status: status as CredentialState,
    available: source['available'] === true,
    expiresAt: optionalString(source, 'expires_at', 'expires_at'),
  }
}
