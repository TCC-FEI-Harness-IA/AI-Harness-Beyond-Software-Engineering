import styles from './TypingIndicator.module.css'

/** Três pontos pulsando — usado enquanto se espera a primeira resposta ou entre eventos do Ralph. */
export function TypingIndicator(): JSX.Element {
  return (
    <span className={styles.dots} role="status" aria-label="Gerando resposta">
      <span className={styles.dot} aria-hidden="true" />
      <span className={styles.dot} aria-hidden="true" />
      <span className={styles.dot} aria-hidden="true" />
    </span>
  )
}
