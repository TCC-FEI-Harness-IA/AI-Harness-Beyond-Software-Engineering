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
    if (event.key === 'Escape') {
      setIsDrawerOpen(false)
      return
    }
    // Prende o foco dentro da gaveta enquanto ela estiver aberta (README, seção 8/FASE 08 § 3.2):
    // no limite do ciclo de Tab, volta para a outra ponta em vez de escapar para o resto da página.
    if (event.key !== 'Tab' || !isDrawerOpen) return
    const focusable = asideRef.current?.querySelectorAll<HTMLElement>('a, button')
    if (!focusable || focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (!first || !last) return
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <div className={styles.shell}>
      <a href="#main-content" className={styles.skipLink}>
        Pular para o conteúdo
      </a>
      <TopBar {...(sidebar ? { onToggleSidebar: () => setIsDrawerOpen((open) => !open) } : {})} />
      {sidebar ? (
        <main id="main-content" className={styles.mainWithSidebar} tabIndex={-1}>
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
        <main id="main-content" className={styles.main} tabIndex={-1}>
          {children}
        </main>
      )}
    </div>
  )
}
