// Modo de visualização do Ralph — Gráfico ou Chat (README, FASE 05, seção 8). Vive em Context
// para que o interruptor, a execução ao vivo e o histórico (FASE 07) leiam e alternem o mesmo
// estado, persistido entre telas e sessões do navegador.

import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useMemo, useState } from 'react'

export type ViewMode = 'graph' | 'chat'

interface ViewModeContextValue {
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
  toggleViewMode: () => void
}

const STORAGE_KEY = 'tcc.viewMode'
// O Modo Gráfico é o diferencial do trabalho — é o que deve ser visto primeiro.
const DEFAULT_MODE: ViewMode = 'graph'

const ViewModeContext = createContext<ViewModeContextValue | undefined>(undefined)

function isViewMode(value: string): value is ViewMode {
  return value === 'graph' || value === 'chat'
}

// Mesma tolerância de `ThemeContext`/`RunConfigContext`: localStorage pode lançar em janela
// privada, e o app precisa seguir funcionando com o default nesse caso.
function readStoredViewMode(): ViewMode {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored !== null && isViewMode(stored)) return stored
  } catch {
    // Acesso bloqueado — segue com o default.
  }
  return DEFAULT_MODE
}

function persistViewMode(mode: ViewMode): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    // Mesma tolerância da leitura.
  }
}

interface ViewModeProviderProps {
  children: ReactNode
}

/** Provider do modo de visualização (Gráfico/Chat) do Ralph, ao vivo e no histórico. */
export function ViewModeProvider({ children }: ViewModeProviderProps): JSX.Element {
  const [viewMode, setViewModeState] = useState<ViewMode>(readStoredViewMode)

  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeState(mode)
    persistViewMode(mode)
  }, [])

  const toggleViewMode = useCallback(() => {
    setViewModeState((prev) => {
      const next: ViewMode = prev === 'graph' ? 'chat' : 'graph'
      persistViewMode(next)
      return next
    })
  }, [])

  const value = useMemo<ViewModeContextValue>(
    () => ({ viewMode, setViewMode, toggleViewMode }),
    [viewMode, setViewMode, toggleViewMode],
  )

  return <ViewModeContext.Provider value={value}>{children}</ViewModeContext.Provider>
}

export function useViewMode(): ViewModeContextValue {
  const context = useContext(ViewModeContext)
  if (!context) {
    throw new Error('useViewMode precisa ser usado dentro de um ViewModeProvider')
  }
  return context
}
