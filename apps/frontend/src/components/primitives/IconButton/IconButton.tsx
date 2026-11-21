import { forwardRef } from 'react'
import type { ComponentPropsWithoutRef, ReactNode } from 'react'
import { Spinner } from '@/components/primitives/Spinner'
import { cx } from '@/components/cx'
import styles from './IconButton.module.css'

export interface IconButtonProps extends Omit<ComponentPropsWithoutRef<'button'>, 'aria-label'> {
  /** Obrigatório — o botão só mostra um ícone, então precisa de um rótulo acessível próprio. */
  'aria-label': string
  icon: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

/** Botão quadrado só com ícone. Mesmas variantes do `Button`, com `aria-label` forçado no tipo. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, variant = 'secondary', size = 'md', loading = false, disabled, className, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={cx(styles.button, styles[variant], styles[size], className)}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      <span className={cx(styles.icon, loading && styles.iconHidden)}>{icon}</span>
      {loading ? (
        <span className={styles.spinnerOverlay} aria-hidden="true">
          <Spinner size="sm" label="Carregando" />
        </span>
      ) : null}
    </button>
  )
})
