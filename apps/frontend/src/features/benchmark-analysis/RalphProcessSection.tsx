import { Button } from '@/components/primitives/Button'
import type { AnalysisRecord } from '@/domain/services/benchmarkAnalysis'
import {
  groupByProcess,
  PROCESS_DIMENSION_LABEL,
  type ProcessDimension,
} from '@/domain/services/ralphProcessMetrics'
import type { RalphProcessMetricsState } from '@/hooks/useRalphProcessMetrics'
import { BreakdownTable } from './BreakdownTable'
import styles from './BenchmarkAnalysis.module.css'

const DIMENSIONS: ReadonlyArray<{ dimension: ProcessDimension; hint: string }> = [
  {
    dimension: 'taskCount',
    hint: 'Quantas tarefas o plano aprovado teve — a complexidade que o próprio Ralph enxergou na questão.',
  },
  {
    dimension: 'verificationFailures',
    hint: 'Retentativas forçadas pela verificação B.2: mostra se o loop de correção recupera ou só encarece.',
  },
  {
    dimension: 'planRejections',
    hint: 'Planos recusados pelo validador A.3 antes da execução.',
  },
]

export interface RalphProcessSectionProps {
  records: readonly AnalysisRecord[]
  process: RalphProcessMetricsState
}

/** Quebras pela complexidade observada no processo do Ralph; exige carregar as sessões Ralph. */
export function RalphProcessSection({ records, process }: RalphProcessSectionProps): JSX.Element {
  return (
    <section className={styles.section} aria-labelledby="analysis-process-title">
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="analysis-process-title" className={styles.sectionTitle}>
            Complexidade pelo processo do Ralph
          </h2>
          <p className={styles.sectionHint}>
            Lê a sessão Ralph de cada questão (tarefas, verificações e planos reprovados). Uma requisição por
            questão — pode levar alguns segundos em baterias grandes.
          </p>
        </div>
        {process.enabled ? (
          <span className={styles.progress} role="status">
            {process.running ? 'Carregando sessões… ' : ''}
            {process.loaded}/{process.total} sessões
            {process.failed > 0 ? ` · ${process.failed} falharam` : ''}
          </span>
        ) : (
          <Button size="sm" variant="secondary" onClick={process.load} disabled={process.total === 0}>
            Carregar métricas do processo ({process.total} sessões)
          </Button>
        )}
      </div>
      {process.enabled
        ? DIMENSIONS.map(({ dimension, hint }) => (
            <BreakdownTable
              key={dimension}
              id={`analysis-process-${dimension}`}
              title={PROCESS_DIMENSION_LABEL[dimension]}
              hint={hint}
              groups={groupByProcess(records, dimension, process.metrics)}
              ordinal
            />
          ))
        : null}
    </section>
  )
}
