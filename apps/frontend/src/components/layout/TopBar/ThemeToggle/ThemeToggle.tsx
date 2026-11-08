import type { Theme } from '@/state/ThemeContext'
import { useTheme } from '@/state/ThemeContext'
import styles from './ThemeToggle.module.css'

const THEME_SEQUENCE: readonly Theme[] = ['system', 'light', 'dark']

const THEME_LABEL: Record<Theme, string> = {
  system: 'Sistema',
  light: 'Claro',
  dark: 'Escuro',
}

function nextTheme(current: Theme): Theme {
  const currentIndex = THEME_SEQUENCE.indexOf(current)
  const next = THEME_SEQUENCE[(currentIndex + 1) % THEME_SEQUENCE.length]
  return next ?? 'system'
}

function themeIconPath(theme: Theme): string {
  if (theme === 'light') {
    // Sol
    return 'M12 3v2m0 14v2m9-9h-2M5 12H3m14.95 6.95-1.41-1.41M6.46 6.46 5.05 5.05m12.9 0-1.41 1.41M6.46 17.54l-1.41 1.41M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z'
  }
  if (theme === 'dark') {
    // Lua
    return 'M20 14.5A8.5 8.5 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z'
  }
  // Sistema — círculo meio a meio
  return 'M12 3a9 9 0 1 0 0 18V3Z'
}

/** Botão de três estados (sistema/claro/escuro) — cicla o tema global a cada clique. */
export function ThemeToggle(): JSX.Element {
  const { theme, setTheme } = useTheme()

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={() => setTheme(nextTheme(theme))}
      aria-label={`Tema atual: ${THEME_LABEL[theme]}. Alternar tema.`}
      title={`Tema: ${THEME_LABEL[theme]}`}
    >
      <svg
        className={styles.icon}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d={themeIconPath(theme)} />
      </svg>
    </button>
  )
}
