import styles from './Divider.module.css'

export interface DividerProps {
  orientation?: 'horizontal' | 'vertical'
}

/** Linha *hairline* de separação — hierarquia por espaço/tipografia primeiro (regra 8.1.2). */
export function Divider({ orientation = 'horizontal' }: DividerProps): JSX.Element {
  return orientation === 'vertical' ? (
    <span role="separator" aria-orientation="vertical" className={styles.vertical} />
  ) : (
    <hr className={styles.horizontal} />
  )
}
