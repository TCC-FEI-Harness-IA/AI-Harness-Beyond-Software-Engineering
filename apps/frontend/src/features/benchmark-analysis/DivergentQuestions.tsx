import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/primitives/Badge'
import { SegmentedControl } from '@/components/primitives/SegmentedControl'
import { type AnalysisRecord, PAIR_OUTCOME_LABEL, type PairOutcome } from '@/domain/services/benchmarkAnalysis'
import { benchmarkSubjectLabel } from '@/domain/services/benchmarkDefinition'
import { formatTokens } from '@/domain/services/formatters'
import type { BenchmarkFlowOutcome } from '@/domain/types/benchmarkSession'
import { buildBenchmarkChildSessionPath } from '@/router/routes'
import styles from './BenchmarkAnalysis.module.css'

const FILTERS: ReadonlyArray<{ value: PairOutcome; label: string }> = [
  { value: 'ralph_recovers', label: PAIR_OUTCOME_LABEL.ralph_recovers },
  { value: 'ralph_regresses', label: PAIR_OUTCOME_LABEL.ralph_regresses },
  { value: 'both_wrong', label: PAIR_OUTCOME_LABEL.both_wrong },
]

const PAGE_SIZE = 50

function FlowAnswer({
  benchmarkSessionId,
  outcome,
}: {
  benchmarkSessionId: string
  outcome: BenchmarkFlowOutcome
}): JSX.Element {
  const label = `${outcome.selected_alternative ?? '—'}${outcome.error !== null ? ' · falha' : ''}`
  return outcome.session_id === null ? (
    <span>{label}</span>
  ) : (
    <Link
      className={styles.link}
      to={buildBenchmarkChildSessionPath(benchmarkSessionId, outcome.session_id)}
      title={outcome.error ?? 'Abrir a sessão'}
    >
      {label}
    </Link>
  )
}

/** Questões em que os fluxos divergem (ou ambos erram) — material para a análise qualitativa. */
export function DivergentQuestions({ records }: { records: readonly AnalysisRecord[] }): JSX.Element {
  const [filter, setFilter] = useState<PairOutcome>('ralph_recovers')
  const [limit, setLimit] = useState(PAGE_SIZE)
  const counts = useMemo(() => {
    const result: Record<PairOutcome, number> = { both_correct: 0, ralph_recovers: 0, ralph_regresses: 0, both_wrong: 0 }
    for (const record of records) result[record.outcome] += 1
    return result
  }, [records])
  const visible = useMemo(() => records.filter((record) => record.outcome === filter), [records, filter])

  return (
    <section className={styles.section} aria-labelledby="analysis-divergent-title">
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="analysis-divergent-title" className={styles.sectionTitle}>
            Questões para análise qualitativa
          </h2>
          <p className={styles.sectionHint}>
            Abra a sessão de cada fluxo para ver onde o plano, a verificação ou a síntese do Ralph mudaram o resultado.
          </p>
        </div>
        <SegmentedControl
          ariaLabel="Desfecho das questões listadas"
          size="sm"
          options={FILTERS.map((option) => ({ ...option, label: `${option.label} (${counts[option.value]})` }))}
          value={filter}
          onChange={(value) => {
            setFilter(value)
            setLimit(PAGE_SIZE)
          }}
        />
      </div>
      <div className={styles.tableWrapper}>
        <table className={styles.table} aria-label="Questões divergentes">
          <thead>
            <tr>
              <th scope="col">Questão</th>
              <th scope="col" className={styles.left}>
                Execução
              </th>
              <th scope="col" className={styles.left}>
                Matéria
              </th>
              <th scope="col" className={styles.left}>
                Gabarito
              </th>
              <th scope="col" className={styles.left}>
                Simples
              </th>
              <th scope="col" className={styles.left}>
                Ralph
              </th>
              <th scope="col">Tokens simples</th>
              <th scope="col">Tokens Ralph</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={8} className={styles.muted}>
                  Nenhuma questão com este desfecho.
                </td>
              </tr>
            ) : (
              visible.slice(0, limit).map((record) => (
                <tr key={record.key}>
                  <td className={styles.mono}>{record.questionId}</td>
                  <td className={styles.left}>
                    <span className={styles.groupLabel} title={record.executionLabel}>
                      {record.executionLabel}
                    </span>
                  </td>
                  <td className={styles.left}>{record.subject === null ? '—' : benchmarkSubjectLabel(record.subject)}</td>
                  <td className={styles.left}>
                    <Badge>{record.expected}</Badge>
                  </td>
                  <td className={styles.left}>
                    <FlowAnswer benchmarkSessionId={record.benchmarkSessionId} outcome={record.simple} />
                  </td>
                  <td className={styles.left}>
                    <FlowAnswer benchmarkSessionId={record.benchmarkSessionId} outcome={record.ralph} />
                  </td>
                  <td>{formatTokens(record.simple.total_tokens)}</td>
                  <td>{formatTokens(record.ralph.total_tokens)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {visible.length > limit ? (
        <button type="button" className={`${styles.sortButton} ${styles.link}`} onClick={() => setLimit(limit + PAGE_SIZE)}>
          Mostrar mais ({visible.length - limit} restantes)
        </button>
      ) : null}
    </section>
  )
}
