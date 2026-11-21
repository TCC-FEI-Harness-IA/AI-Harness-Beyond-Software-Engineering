import { cx } from '@/components/cx'
import styles from './Spinner.module.css'

export interface SpinnerProps {
  size?: 'sm' | 'md'
  /** Rótulo acessível — o spinner nunca ocupa a tela inteira, então precisa dizer o que espera. */
  label?: string
}

/**
 * Indicador de carregamento em anel, usado dentro de botões e em áreas pequenas — nunca como
 * spinner de página inteira (regra 13 do README: estado de carregamento é skeleton).
 */
export function Spinner({ size = 'md', label = 'Carregando' }: SpinnerProps): JSX.Element {
  return (
    <svg
      className={cx(styles.spinner, styles[size])}
      viewBox="0 0 24 24"
      fill="none"
      role="status"
      aria-label={label}
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeOpacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
