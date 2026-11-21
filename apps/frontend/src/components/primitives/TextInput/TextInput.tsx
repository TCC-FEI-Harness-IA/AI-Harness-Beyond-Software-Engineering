import { forwardRef } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { cx } from '@/components/cx'
import styles from './TextInput.module.css'

export interface TextInputProps extends Omit<ComponentPropsWithoutRef<'input'>, 'size'> {
  size?: 'sm' | 'md'
}

/**
 * Campo de uma linha — texto, número ou busca. Mesma altura, raio e foco do `Select` e do
 * `Button`, para que controles lado a lado fiquem alinhados.
 */
export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { size = 'md', className, ...rest },
  ref,
) {
  return <input ref={ref} className={cx(styles.control, styles[size], className)} {...rest} />
})
