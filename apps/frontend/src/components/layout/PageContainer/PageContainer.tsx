import type { ReactNode } from 'react'
import styles from './PageContainer.module.css'

export interface PageContainerProps {
  children: ReactNode
  width?: 'content' | 'wide' | 'full'
}

/** Coluna central compartilhada por todas as telas, com largura máxima configurável. */
export function PageContainer({ children, width = 'content' }: PageContainerProps): JSX.Element {
  return <div className={`${styles.container} ${styles[width]}`}>{children}</div>
}
