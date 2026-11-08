import type { ReactElement } from 'react'
import styles from './Tooltip.module.css'

export interface TooltipProps {
  content: string
  children: ReactElement
}

/**
 * Dica leve em CSS puro (`::before`/`::after`), sem lib de posicionamento. Aparece em
 * hover/foco com atraso de 400ms. Envolve um único filho focável.
 */
export function Tooltip({ content, children }: TooltipProps): JSX.Element {
  return (
    <span className={styles.wrapper} data-tooltip={content}>
      {children}
    </span>
  )
}
