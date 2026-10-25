import { formatDuration, formatPercent, formatTokens } from '@/domain/services/formatters'
import type {
  BenchmarkModeSummary,
  BenchmarkSessionDocument,
} from '@/domain/types/benchmarkSession'
import styles from './BenchmarkSummary.module.css'

const MILLISECONDS_PER_SECOND = 1000

const ROWS: ReadonlyArray<{ label: string; format: (summary: BenchmarkModeSummary) => string }> = [
  { label: 'Executadas', format: (summary) => String(summary.executed) },
  { label: 'Acertos', format: (summary) => String(summary.correct) },
  { label: 'Erros', format: (summary) => String(summary.wrong) },
  { label: 'Falhas (incluídas nos erros)', format: (summary) => String(summary.failures) },
  { label: 'Acurácia', format: (summary) => formatPercent(summary.accuracy) },
  { label: 'Tokens', format: (summary) => formatTokens(summary.total_tokens) },
  {
    label: 'Tempo somado',
    format: (summary) => formatDuration(summary.duration_seconds * MILLISECONDS_PER_SECOND),
  },
]

/** Comparativo lado a lado entre a inferência simples e o Ralph Loop na mesma bateria. */
export function BenchmarkSummary({ session }: { session: BenchmarkSessionDocument }): JSX.Element {
  return (
    <table className={styles.table} aria-label="Comparativo entre os fluxos">
      <thead>
        <tr>
          <th scope="col" />
          <th scope="col">Simples</th>
          <th scope="col">Ralph</th>
        </tr>
      </thead>
      <tbody>
        {ROWS.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td>{row.format(session.summary.simple)}</td>
            <td>{row.format(session.summary.ralph)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
