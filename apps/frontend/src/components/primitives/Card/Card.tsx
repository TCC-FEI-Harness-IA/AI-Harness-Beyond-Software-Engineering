import { forwardRef } from 'react'
import type { ComponentPropsWithoutRef, ElementType, ReactNode } from 'react'
import { cx } from '@/components/cx'
import styles from './Card.module.css'

const ELEVATION_CLASS = {
  flat: styles.elevationFlat,
  sm: styles.elevationSm,
  md: styles.elevationMd,
} as const

const PADDING_CLASS = {
  sm: styles.paddingSm,
  md: styles.paddingMd,
  lg: styles.paddingLg,
} as const

export interface CardProps extends Omit<ComponentPropsWithoutRef<'div'>, 'as'> {
  children: ReactNode
  padding?: 'sm' | 'md' | 'lg'
  elevation?: 'flat' | 'sm' | 'md'
  interactive?: boolean
  as?: 'div' | 'article' | 'li'
}

/** Superfície elevada — base de bolhas, painéis e cartões de resumo em toda a UI. */
export const Card = forwardRef<HTMLElement, CardProps>(function Card(
  { children, padding = 'md', elevation = 'flat', interactive = false, as = 'div', className, ...rest },
  ref,
) {
  const Component = as as ElementType
  return (
    <Component
      ref={ref}
      className={cx(
        styles.card,
        ELEVATION_CLASS[elevation],
        PADDING_CLASS[padding],
        interactive && styles.interactive,
        className,
      )}
      tabIndex={interactive ? 0 : undefined}
      {...rest}
    >
      {children}
    </Component>
  )
})
