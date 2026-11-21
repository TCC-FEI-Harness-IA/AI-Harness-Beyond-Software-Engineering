import type { ReactNode } from 'react'
import { cx } from '@/components/cx'
import styles from './Field.module.css'

export interface FieldProps {
  label: ReactNode
  /** Texto auxiliar abaixo do controle. */
  hint?: ReactNode
  /** O controle (TextInput, Select, RangeInput) ou um valor estático quando não há escolha. */
  children: ReactNode
  className?: string
}

/**
 * Rótulo + controle + dica de um campo de formulário. É um `<label>`, então o clique no texto
 * foca o controle e o leitor de tela anuncia o rótulo sem precisar de `id`/`htmlFor`.
 */
export function Field({ label, hint, children, className }: FieldProps): JSX.Element {
  return (
    <label className={cx(styles.field, className)}>
      <span className={styles.label}>{label}</span>
      {children}
      {hint ? <small className={styles.hint}>{hint}</small> : null}
    </label>
  )
}
