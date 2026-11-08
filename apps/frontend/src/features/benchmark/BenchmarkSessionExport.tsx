import { Button } from '@/components/primitives/Button'
import { BENCHMARK_SESSION_STATUS } from '@/domain/enums/benchmarkStatus'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { useBenchmarkSessionExport } from '@/hooks/useBenchmarkSessionExport'
import styles from './BenchmarkRalphErrorsExport.module.css'

function hint(session: BenchmarkSessionDocument): string {
  if (session.status === BENCHMARK_SESSION_STATUS.RUNNING) {
    return 'Disponível quando a bateria terminar.'
  }
  const count = session.question_count
  const questions = count === 1 ? '1 questão' : `${count} questões`
  return `ZIP com a bateria e, para ${questions}, enunciado, resposta esperada e as execuções simples e Ralph Loop.`
}

/**
 * Baixa, em ZIP padronizado, tudo que está atrelado a uma bateria encerrada. O mesmo arquivo pode
 * ser importado de volta na página do BenchMark.
 */
export function BenchmarkSessionExport({
  session,
}: {
  session: BenchmarkSessionDocument
}): JSX.Element {
  const exporter = useBenchmarkSessionExport(session.id)
  const isRunning = session.status === BENCHMARK_SESSION_STATUS.RUNNING

  return (
    <div className={styles.container}>
      <div className={styles.row}>
        <Button
          variant="secondary"
          loading={exporter.isExporting}
          disabled={isRunning || exporter.isExporting}
          aria-describedby="session-export-hint"
          onClick={exporter.start}
        >
          Exportar sessão completa
        </Button>
        <p id="session-export-hint" className={styles.hint}>
          {hint(session)}
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
          Não foi possível exportar a sessão. {exporter.error.userMessage}
        </p>
      ) : null}
    </div>
  )
}
