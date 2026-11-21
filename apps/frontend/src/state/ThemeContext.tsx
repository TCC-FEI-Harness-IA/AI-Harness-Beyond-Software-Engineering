import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export type Theme = 'light' | 'dark' | 'system'

interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const STORAGE_KEY = 'tcc.theme'

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

function isTheme(value: string): value is Theme {
  return value === 'light' || value === 'dark' || value === 'system'
}

// localStorage pode lançar em janela privada — o app precisa continuar funcionando
// com o default 'system' nesse caso.
function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored !== null && isTheme(stored)) return stored
  } catch {
    // Acesso bloqueado (janela privada, permissões de site) — segue com o default.
  }
  return 'system'
}

function persistTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Mesma tolerância de leitura: falha em persistir não deve quebrar a troca de tema.
  }
}

interface ThemeProviderProps {
  children: ReactNode
}

// Provider de tema claro/escuro/sistema. A troca é só CSS (atributo data-theme na raiz)
// — nunca re-renderiza a árvore inteira do app por causa de tema.
export function ThemeProvider({ children }: ThemeProviderProps): JSX.Element {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', theme)
    }
  }, [theme])

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next)
    persistTheme(next)
  }, [])

  const value = useMemo<ThemeContextValue>(() => ({ theme, setTheme }), [theme, setTheme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme precisa ser usado dentro de um ThemeProvider')
  }
  return context
}
