// Slot de barra lateral do `AppShell` (README, FASE 07, seção 6). O `AppShell` é montado uma
// única vez, acima do roteador (regra de reuso 8 — nenhuma tela inventa o próprio cabeçalho);
// para que só a tela de detalhe do histórico tenha barra lateral, a própria tela "registra" o
// que deve aparecer ali, e o `AppRouter` lê esse registro para preencher a prop `sidebar` do
// `AppShell`. Toda outra tela nunca registra nada, e a barra lateral simplesmente não existe.

import type { ReactNode } from 'react'
import { createContext, useContext, useEffect, useMemo, useState } from 'react'

interface SidebarSlotContextValue {
  sidebar: ReactNode
  setSidebar: (node: ReactNode) => void
}

const SidebarSlotContext = createContext<SidebarSlotContextValue | undefined>(undefined)

interface SidebarSlotProviderProps {
  children: ReactNode
}

export function SidebarSlotProvider({ children }: SidebarSlotProviderProps): JSX.Element {
  const [sidebar, setSidebar] = useState<ReactNode>(null)
  const value = useMemo<SidebarSlotContextValue>(() => ({ sidebar, setSidebar }), [sidebar])

  return <SidebarSlotContext.Provider value={value}>{children}</SidebarSlotContext.Provider>
}

function useSidebarSlotContext(): SidebarSlotContextValue {
  const context = useContext(SidebarSlotContext)
  if (!context) {
    throw new Error('useRegisterSidebar/useSidebarSlotValue precisam de um SidebarSlotProvider')
  }
  return context
}

/** Lido pelo `AppRouter`, logo acima do `AppShell`. */
export function useSidebarSlotValue(): ReactNode {
  return useSidebarSlotContext().sidebar
}

/**
 * Registra `node` como o conteúdo da barra lateral enquanto a tela chamadora está montada
 * (`HistoryDetailPage`, FASE 07). Passe `null` para telas sem barra lateral — é o valor padrão,
 * então a maioria das telas nunca precisa chamar este hook.
 */
export function useRegisterSidebar(node: ReactNode): void {
  const { setSidebar } = useSidebarSlotContext()

  useEffect(() => {
    setSidebar(node)
    return () => setSidebar(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node])
}
