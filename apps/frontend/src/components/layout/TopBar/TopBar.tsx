import { Link } from 'react-router-dom'
import ralphImage from '@/assets/ralph_image.png'
import { ROUTES } from '@/router/routes'
import { ThemeToggle } from './ThemeToggle'
import styles from './TopBar.module.css'

export interface TopBarProps {
  /** Só preenchido pelo `AppShell` quando a tela atual tem barra lateral (histórico, FASE 07).
   * Abaixo de 1024px a barra vira gaveta, e este botão é o único jeito de abri-la — em telas
   * largas ele nem aparece (a barra lateral já está sempre visível). */
  onToggleSidebar?: () => void
}

/**
 * Barra superior fixa e translúcida, presente em todas as telas. À esquerda, o nome do
 * app (ícone do projeto + nome) leva à home (com o botão de abrir a barra lateral, quando existe, logo antes); ao
 * centro fica o slot do interruptor de modo (FASE 05); à direita, o link de histórico e o
 * alternador de tema.
 */
export function TopBar({ onToggleSidebar }: TopBarProps): JSX.Element {
  return (
    <header className={styles.topbar}>
      <div className={styles.leading}>
        {onToggleSidebar ? (
          <button
            type="button"
            className={styles.sidebarToggle}
            aria-label="Abrir barra lateral"
            onClick={onToggleSidebar}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        ) : null}
        <Link to={ROUTES.home} className={styles.brand}>
          <img className={styles.brandIcon} src={ralphImage} alt="" />
          TCC Harness
        </Link>
      </div>
      <div className={styles.center} />
      <nav className={styles.actions} aria-label="Ações principais">
        <Link to={ROUTES.history} className={styles.historyLink}>
          Histórico
        </Link>
        <Link to={ROUTES.benchmark} className={styles.historyLink}>
          BenchMark
        </Link>
        <ThemeToggle />
      </nav>
    </header>
  )
}
