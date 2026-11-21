import { forwardRef } from 'react'
import type { ComponentPropsWithoutRef, ReactNode } from 'react'
import { Spinner } from '@/components/primitives/Spinner'
import { cx } from '@/components/cx'
import styles from './Button.module.css'

export interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  iconLeft?: ReactNode
  iconRight?: ReactNode
  fullWidth?: boolean
}

/**
 * Botão de ação — a única forma de disparar uma ação primária, secundária, terciária (ghost)
 * ou destrutiva no app. `loading` substitui o `iconLeft` por um spinner sem mudar a largura
 * do botão (o conteúdo original fica invisível, não removido, para não pular o layout).
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    iconLeft,
    iconRight,
    fullWidth = false,
    disabled,
    className,
    children,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={cx(styles.button, styles[variant], styles[size], fullWidth && styles.fullWidth, className)}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      <span className={cx(styles.content, loading && styles.contentHidden)}>
        {iconLeft ? <span className={styles.icon}>{iconLeft}</span> : null}
        {children}
        {iconRight ? <span className={styles.icon}>{iconRight}</span> : null}
      </span>
      {loading ? (
        <span className={styles.spinnerOverlay} aria-hidden="true">
          <Spinner size="sm" label="Carregando" />
        </span>
      ) : null}
    </button>
  )
})
