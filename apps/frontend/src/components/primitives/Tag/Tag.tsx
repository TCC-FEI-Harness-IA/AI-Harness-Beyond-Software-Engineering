import type { ReactNode } from 'react'
import type { Tone } from '@/domain/enums/tone'
import { cx } from '@/components/cx'
import styles from './Tag.module.css'

const TONE_CLASS: Partial<Record<Tone, string | undefined>> = {
  accent: styles.toneAccent,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  danger: styles.toneDanger,
  context: styles.toneContext,
}

export interface TagProps {
  children: ReactNode
  /** Texto completo mostrado no tooltip nativo — usado quando `children` está abreviado. */
  title?: string
  tone?: Tone
}

/** Etiqueta monoespaçada para identificadores técnicos (`T1`, `context_id`, nome de modelo). */
export function Tag({ children, title, tone = 'neutral' }: TagProps): JSX.Element {
  return (
    <span className={cx(styles.tag, TONE_CLASS[tone])} title={title}>
      {children}
    </span>
  )
}
