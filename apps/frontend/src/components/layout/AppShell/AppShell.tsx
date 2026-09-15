import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { TopBar } from '@/components/layout/TopBar'
import { cx } from '@/components/cx'
import styles from './AppShell.module.css'

export interface AppShellProps {
  children: ReactNode
  sidebar?: ReactNode
}

/**
 * Casca de página usada por todas as telas: barra superior fixa + área de conteúdo
 * que rola. Quando `sidebar` é passado (histórico, FASE 07), o conteúdo vira um grid
 * de duas colunas; abaixo de 1024px a barra lateral vira uma gaveta sobreposta, aberta
 * pelo botão que a `TopBar` mostra só quando existe barra lateral (README, seção 6).
 */
export function AppShell({ children, sidebar }: AppShellProps): JSX.Element {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const asideRef = useRef<HTMLElement>(null)

  // Fecha a gaveta sempre que a tela deixa de ter barra lateral (troca de rota) — evita que
  // ela reabra "fantasma" numa tela sem `sidebar`.
  useEffect(() => {
    if (!sidebar) setIsDrawerOpen(false)
  }, [sidebar])

  useEffect(() => {
    if (!isDrawerOpen) return
    asideRef.current?.querySelector<HTMLElement>('a, button')?.focus()
  }, [isDrawerOpen])

  function handleDrawerKeyDown(event: KeyboardEvent<HTMLElement>): void {
    if (event.key !== 'Escape') return
    setIsDrawerOpen(false)
  }

  return (
    <div className={styles.shell}>
      <TopBar {...(sidebar ? { onToggleSidebar: () => setIsDrawerOpen((open) => !open) } : {})} />
      {sidebar ? (
        <main className={styles.mainWithSidebar}>
          {isDrawerOpen ? (
            <button
              type="button"
              className={styles.scrim}
              aria-label="Fechar barra lateral"
              onClick={() => setIsDrawerOpen(false)}
            />
          ) : null}
          <aside
            ref={asideRef}
            className={cx(styles.sidebar, isDrawerOpen && styles.sidebarOpen)}
            aria-label="Barra lateral"
            onKeyDown={handleDrawerKeyDown}
          >
            {sidebar}
          </aside>
          <div>{children}</div>
        </main>
      ) : (
        <main className={styles.main}>{children}</main>
      )}
    </div>
  )
}
