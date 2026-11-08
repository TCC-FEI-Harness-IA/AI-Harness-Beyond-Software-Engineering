import { Button } from '@/components/primitives/Button'
import styles from './ErrorState.module.css'

// Forma estrutural mínima de um erro exibível — não importa `AppError` de `src/api/errors`
// (regra 3/critério 9 do README: componentes não importam de src/api). Como `AppError`
// estende `Error` e tem `userMessage`, qualquer instância real passa aqui por tipagem
// estrutural, sem acoplar o componente à camada de rede.
export interface DisplayableError {
  userMessage: string
  message?: string
}

export interface ErrorStateProps {
  error: DisplayableError
  onRetry?: () => void
}

/** Estado "erro" de uma tela que carrega dados — mensagem legível, técnica recolhida. */
export function ErrorState({ error, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <div className={styles.container}>
      <svg
        className={styles.icon}
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v5" strokeLinecap="round" />
        <circle cx="12" cy="16" r="0.5" fill="currentColor" />
      </svg>
      <p className={styles.message}>{error.userMessage}</p>
      {error.message ? (
        <details className={styles.details}>
          <summary>Detalhe técnico</summary>
          <p className={styles.technical}>{error.message}</p>
        </details>
      ) : null}
      {onRetry ? (
        <Button variant="secondary" size="sm" className={styles.retry} onClick={onRetry}>
          Tentar de novo
        </Button>
      ) : null}
    </div>
  )
}
