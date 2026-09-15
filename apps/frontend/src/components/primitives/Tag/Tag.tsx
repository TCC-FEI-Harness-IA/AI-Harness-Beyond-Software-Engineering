import type { ReactNode } from 'react'
import styles from './Tag.module.css'

export interface TagProps {
  children: ReactNode
  /** Texto completo mostrado no tooltip nativo — usado quando `children` está abreviado. */
  title?: string
}

/** Etiqueta monoespaçada para identificadores técnicos (`T1`, `context_id`, nome de modelo). */
export function Tag({ children, title }: TagProps): JSX.Element {
  return (
    <span className={styles.tag} title={title}>
      {children}
    </span>
  )
}
