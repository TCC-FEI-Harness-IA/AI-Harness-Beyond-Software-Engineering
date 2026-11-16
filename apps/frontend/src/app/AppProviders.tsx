import type { ReactNode } from 'react'
import { type AuthApi, type AuthInitialState, AuthProvider, useAuth } from '@/state/AuthContext'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { UserScope } from '@/state/UserScope'
import { ViewModeProvider } from '@/state/ViewModeContext'

function ScopedRunConfig({ children }: { children: ReactNode }): JSX.Element {
  const auth = useAuth()
  return <RunConfigProvider enabled={auth.status === 'authenticated'}>{children}</RunConfigProvider>
}

export interface AppProvidersProps {
  children: ReactNode
  authApi?: AuthApi
  initialAuth?: AuthInitialState
}

/** Pilha de providers do app (também usada pelos testes de integração). */
export function AppProviders({ children, authApi, initialAuth }: AppProvidersProps): JSX.Element {
  return (
    <ThemeProvider>
      <AuthProvider {...(authApi ? { api: authApi } : {})} {...(initialAuth ? { initialState: initialAuth } : {})}>
        <UserScope>
          <ScopedRunConfig>
            <ViewModeProvider>{children}</ViewModeProvider>
          </ScopedRunConfig>
        </UserScope>
      </AuthProvider>
    </ThemeProvider>
  )
}
