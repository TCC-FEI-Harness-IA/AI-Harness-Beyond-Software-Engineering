import { forwardRef } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { cx } from '@/components/cx'
import styles from './RangeInput.module.css'

export type RangeInputProps = Omit<ComponentPropsWithoutRef<'input'>, 'type' | 'size'>

/** Controle deslizante — mesma altura de um `TextInput` md, para alinhar em grade com os demais campos. */
export const RangeInput = forwardRef<HTMLInputElement, RangeInputProps>(function RangeInput(
  { className, ...rest },
  ref,
) {
  return <input ref={ref} type="range" className={cx(styles.range, className)} {...rest} />
})
