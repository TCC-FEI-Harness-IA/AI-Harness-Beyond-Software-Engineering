import { Link } from 'react-router-dom'
import { ROUTES } from '@/router/routes'
import { ThemeToggle } from './ThemeToggle'
import styles from './TopBar.module.css'

/**
 * Barra superior fixa e translúcida, presente em todas as telas. À esquerda, o nome do
 * app leva à home; ao centro fica o slot do interruptor de modo (FASE 05); à direita, o
 * link de histórico e o alternador de tema.
 */
export function TopBar(): JSX.Element {
  return (
    <header className={styles.topbar}>
      <Link to={ROUTES.home} className={styles.brand}>
        TCC Harness
      </Link>
      <div className={styles.center} />
      <nav className={styles.actions} aria-label="Ações principais">
        <Link to={ROUTES.history} className={styles.historyLink}>
          Histórico
        </Link>
        <ThemeToggle />
      </nav>
    </header>
  )
}
