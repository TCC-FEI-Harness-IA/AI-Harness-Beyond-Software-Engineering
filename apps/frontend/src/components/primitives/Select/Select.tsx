import { forwardRef } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { cx } from '@/components/cx'
import controlStyles from '@/components/primitives/TextInput/TextInput.module.css'
import styles from './Select.module.css'

export interface SelectProps extends Omit<ComponentPropsWithoutRef<'select'>, 'size'> {
  size?: 'sm' | 'md'
}

/**
 * Lista de opções — `<select>` nativo (acessível e com teclado de graça) com a mesma aparência
 * do `TextInput`. O chevron é um SVG sobreposto porque `appearance: none` remove o do navegador.
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { size = 'md', className, children, ...rest },
  ref,
) {
  return (
    <span className={styles.wrapper}>
      <select
        ref={ref}
        className={cx(controlStyles.control, controlStyles[size], styles.select, className)}
        {...rest}
      >
        {children}
      </select>
      <svg
        className={styles.chevron}
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 4.5l3 3 3-3" />
      </svg>
    </span>
  )
})
