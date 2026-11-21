import { type ChangeEvent, useRef } from 'react'
import type { AppError } from '@/api/errors/AppError'
import { HttpError } from '@/api/errors/HttpError'
import { Button } from '@/components/primitives/Button'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { useBenchmarkSessionImport } from '@/hooks/useBenchmarkSessionImport'
import styles from './BenchmarkRalphErrorsExport.module.css'

/** O backend explica no `detail` por que recusou o arquivo (ZIP inválido, bateria já existente…). */
function failureMessage(error: AppError): string {
  return error instanceof HttpError && error.detail ? error.detail : error.userMessage
}

/**
 * Importa uma bateria a partir do ZIP gerado por "Exportar sessão completa". A importação nunca
 * sobrescreve: se a bateria (ou alguma das suas sessões) já existe, o servidor recusa.
 */
export function BenchmarkSessionImport({
  onImported,
}: {
  onImported?: (session: BenchmarkSessionDocument) => void
}): JSX.Element {
  const importer = useBenchmarkSessionImport(onImported)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0]
    // Limpa a escolha para que o mesmo arquivo possa ser enviado de novo depois de um erro.
    event.target.value = ''
    if (file) importer.start(file)
  }

  return (
    <div className={styles.container}>
      <div className={styles.row}>
        <Button
          variant="secondary"
          loading={importer.isImporting}
          disabled={importer.isImporting}
          aria-describedby="session-import-hint"
          onClick={() => inputRef.current?.click()}
        >
          Importar sessão
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".zip,application/zip"
          hidden
          aria-label="Arquivo ZIP da sessão"
          onChange={handleChange}
        />
        <p id="session-import-hint" className={styles.hint}>
          Envie o ZIP gerado por “Exportar sessão completa”.
        </p>
      </div>
      {importer.isImporting ? (
        <p className={styles.status} role="status">
          Importando a sessão…
        </p>
      ) : null}
      {importer.imported ? (
        <p className={styles.status} role="status">
          Sessão importada.
        </p>
      ) : null}
      {importer.error ? (
        <p className={styles.error} role="alert">
          Não foi possível importar a sessão. {failureMessage(importer.error)}
        </p>
      ) : null}
    </div>
  )
}
