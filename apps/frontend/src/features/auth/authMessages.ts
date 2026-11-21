// Mensagens das telas de conta — o texto vem do servidor quando ele o explica.
import { AppError } from '@/api/errors/AppError'
import { HttpError } from '@/api/errors/HttpError'

export function authErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof HttpError && error.detail) return error.detail
  return error instanceof AppError ? error.userMessage : fallback
}

/** Só aceita voltar para caminhos do próprio app (nada de redirecionar para outro site). */
export function safeNext(raw: string | null): string {
  return raw !== null && raw.startsWith('/') && !raw.startsWith('//') ? raw : '/'
}
