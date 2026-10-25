import { Button } from '@/components/primitives/Button'
import { benchmarkRalphErrorsExport } from '@/domain/services/benchmarkExport'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { useBenchmarkRalphErrorsExport } from '@/hooks/useBenchmarkRalphErrorsExport'
import styles from './BenchmarkRalphErrorsExport.module.css'

function hint(state: ReturnType<typeof benchmarkRalphErrorsExport>): string {
  switch (state.kind) {
    case 'running':
      return 'Disponível quando a bateria terminar.'
    case 'empty':
      return 'Nenhuma questão errou no Ralph Loop nesta bateria: não há o que exportar.'
    case 'ready':
      return state.count === 1
        ? '1 questão errada no Ralph Loop será exportada.'
        : `${state.count} questões erradas no Ralph Loop serão exportadas.`
  }
}

/**
 * Baixa, em ZIP, as questões erradas no Ralph Loop de uma bateria encerrada. O botão só
 * habilita com a bateria encerrada e ao menos um erro, para nunca baixar um ZIP vazio.
 */
export function BenchmarkRalphErrorsExport({
  session,
}: {
  session: BenchmarkSessionDocument
}): JSX.Element {
  const state = benchmarkRalphErrorsExport(session)
  const exporter = useBenchmarkRalphErrorsExport(session.id)

  return (
    <div className={styles.container}>
      <div className={styles.row}>
        <Button
          variant="secondary"
          loading={exporter.isExporting}
          disabled={state.kind !== 'ready' || exporter.isExporting}
          aria-describedby="ralph-errors-export-hint"
          onClick={exporter.start}
        >
          Exportar erros do Ralph Loop
        </Button>
        <p id="ralph-errors-export-hint" className={styles.hint}>
          {hint(state)}
        </p>
      </div>
      {exporter.isExporting ? (
        <p className={styles.status} role="status">
          Gerando o arquivo ZIP…
        </p>
      ) : null}
      {exporter.isDone ? (
        <p className={styles.status} role="status">
          Arquivo ZIP gerado; o download foi iniciado.
        </p>
      ) : null}
      {exporter.error ? (
        <p className={styles.error} role="alert">
          Não foi possível exportar os erros. {exporter.error.userMessage}
        </p>
      ) : null}
    </div>
  )
}
