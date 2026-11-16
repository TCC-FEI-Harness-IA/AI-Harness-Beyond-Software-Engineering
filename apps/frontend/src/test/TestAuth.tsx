// Sessão autenticada (com chave válida) para testes de telas que assumem um usuário logado.
import type { ReactNode } from 'react'
import { AuthProvider } from '@/state/AuthContext'
import { CREDENCIAL_VALIDA, fakeAuthApi, SESSAO_ANA } from './renderWithAuth'

export function TestAuth({ children }: { children: ReactNode }): JSX.Element {
  return (
    <AuthProvider api={fakeAuthApi()} initialState={{ session: SESSAO_ANA, credential: CREDENCIAL_VALIDA }}>
      {children}
    </AuthProvider>
  )
}
