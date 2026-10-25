import { Link } from 'react-router-dom'
import { Badge } from '@/components/primitives/Badge'
import { BENCHMARK_MODE_LABEL } from '@/domain/enums/benchmarkStatus'
import { benchmarkFlowCell } from '@/domain/services/benchmarkView'
import { formatTokens } from '@/domain/services/formatters'
import type { BenchmarkInferenceMode } from '@/domain/types/benchmarkDetails'
import type {
  BenchmarkQuestionRun,
  BenchmarkSessionDocument,
} from '@/domain/types/benchmarkSession'
import { buildBenchmarkChildSessionPath } from '@/router/routes'
import styles from './BenchmarkQuestionsTable.module.css'

const MODES: readonly BenchmarkInferenceMode[] = ['simple', 'ralph']

function FlowCell({
  benchmarkSessionId,
  question,
  mode,
}: {
  benchmarkSessionId: string
  question: BenchmarkQuestionRun
  mode: BenchmarkInferenceMode
}): JSX.Element {
  const cell = benchmarkFlowCell(question, mode)
  const badge = <Badge tone={cell.tone}>{cell.label}</Badge>
  return (
    <td title={cell.detail ?? undefined}>
      {cell.sessionId ? (
        <Link
          to={buildBenchmarkChildSessionPath(benchmarkSessionId, cell.sessionId)}
          className={styles.sessionLink}
          aria-label={`Abrir sessão ${BENCHMARK_MODE_LABEL[mode]} de ${question.question_id}`}
        >
          {badge}
        </Link>
      ) : (
        badge
      )}
    </td>
  )
}

/**
 * Uma linha por questão da bateria, com o desfecho de cada fluxo. Um fluxo encerrado leva ao
 * chat da sua sessão — o mesmo detalhe do histórico, nos modos Chat e Gráfico.
 */
export function BenchmarkQuestionsTable({
  session,
}: {
  session: BenchmarkSessionDocument
}): JSX.Element {
  return (
    <div className={styles.wrapper}>
      <table className={styles.table} aria-label="Questões da bateria">
        <thead>
          <tr>
            <th scope="col">Questão</th>
            <th scope="col">Gabarito</th>
            {MODES.map((mode) => (
              <th scope="col" key={mode}>
                {BENCHMARK_MODE_LABEL[mode]}
              </th>
            ))}
            <th scope="col" className={styles.numeric}>
              Tokens
            </th>
          </tr>
        </thead>
        <tbody>
          {session.questions.map((question) => (
            <tr key={question.question_id}>
              <th scope="row" className={styles.questionName}>
                {question.question_id}
              </th>
              <td>{question.expected_alternative}</td>
              {MODES.map((mode) => (
                <FlowCell
                  key={mode}
                  benchmarkSessionId={session.id}
                  question={question}
                  mode={mode}
                />
              ))}
              <td className={styles.numeric}>{formatTokens(question.total_tokens)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
