// Token anti-CSRF da sessão atual (padrão "synchronizer token"): vem do serviço de autenticação
// (`/auth/me` e login), fica só em memória e acompanha toda escrita no header `X-CSRF-Token`.
// Não é a credencial de sessão (essa fica num cookie HttpOnly que o JavaScript não lê).

let token: string | null = null

export function setCsrfToken(value: string): void {
  token = value
}

export function getCsrfToken(): string | null {
  return token
}

export function clearCsrfToken(): void {
  token = null
}
