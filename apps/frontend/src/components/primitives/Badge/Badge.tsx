import type { ReactNode } from 'react'
import { cx } from '@/components/cx'
import styles from './Badge.module.css'

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'context'

const TONE_CLASS: Record<BadgeTone, string | undefined> = {
  neutral: styles.neutral,
  accent: styles.accent,
  success: styles.success,
  warning: styles.warning,
  danger: styles.danger,
  context: styles.context,
}

export interface BadgeProps {
  children: ReactNode
  tone?: BadgeTone
  icon?: ReactNode
}

/**
 * Pílula de status colorida por `tone` (README, seção 8.3). Cor nunca é o único portador de
 * informação: `children` sempre carrega um rótulo textual, e `icon` reforça o significado
 * quando `tone` não é `neutral`.
 */
export function Badge({ children, tone = 'neutral', icon }: BadgeProps): JSX.Element {
  return (
    <span className={cx(styles.badge, TONE_CLASS[tone])}>
      {icon ? (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      ) : null}
      {children}
    </span>
  )
}
