import type { ReactNode } from 'react'
import type { Tone } from '@/domain/enums/tone'
import { cx } from '@/components/cx'
import styles from './StatItem.module.css'

const TONE_CLASS: Partial<Record<Tone, string | undefined>> = {
  accent: styles.toneAccent,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  danger: styles.toneDanger,
  context: styles.toneContext,
}

export interface StatItemProps {
  label: string
  value: string
  tone?: Tone
  icon?: ReactNode
  title?: string
  /** 'inline' = rótulo e valor na mesma linha; 'panel' = rótulo acima do valor. */
  layout?: 'inline' | 'panel'
}

/** Unidade atômica das estatísticas — a peça que `MessageStats` repete. */
export function StatItem({
  label,
  value,
  tone = 'neutral',
  icon,
  title,
  layout = 'inline',
}: StatItemProps): JSX.Element {
  const toneClass = TONE_CLASS[tone]
  return (
    <span className={cx(layout === 'panel' ? styles.panel : styles.item, toneClass)} title={title}>
      {layout === 'inline' ? (
        <>
          {icon ? (
            <span className={styles.icon} aria-hidden="true">
              {icon}
            </span>
          ) : null}
          <span className={styles.label}>{label}</span>
          <span className={styles.value}>{value}</span>
        </>
      ) : (
        <>
          <span className={styles.label}>{label}</span>
          <span className={styles.value}>
            {icon ? (
              <span className={styles.icon} aria-hidden="true">
                {icon}
              </span>
            ) : null}
            {value}
          </span>
        </>
      )}
    </span>
  )
}
