import type { ReactNode } from 'react'
import { TopBar } from '@/components/layout/TopBar'
import styles from './AppShell.module.css'

export interface AppShellProps {
  children: ReactNode
  sidebar?: ReactNode
}

/**
 * Casca de página usada por todas as telas: barra superior fixa + área de conteúdo
 * que rola. Quando `sidebar` é passado (histórico, FASE 07), o conteúdo vira um grid
 * de duas colunas.
 */
export function AppShell({ children, sidebar }: AppShellProps): JSX.Element {
  return (
    <div className={styles.shell}>
      <TopBar />
      {sidebar ? (
        <main className={styles.mainWithSidebar}>
          <aside className={styles.sidebar} aria-label="Barra lateral">
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
