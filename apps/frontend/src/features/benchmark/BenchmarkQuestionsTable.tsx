import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/primitives/Badge'
import { Button } from '@/components/primitives/Button'
import { BENCHMARK_MODE_LABEL } from '@/domain/enums/benchmarkStatus'
import { BENCHMARK_SESSION_STATUS } from '@/domain/enums/benchmarkStatus'
import { benchmarkFlowCell, isQuestionRerunnable } from '@/domain/services/benchmarkView'
import { formatTokens } from '@/domain/services/formatters'
import type { BenchmarkInferenceMode } from '@/domain/types/benchmarkDetails'
import type {
  BenchmarkQuestionRun,
  BenchmarkSessionDocument,
} from '@/domain/types/benchmarkSession'
import { buildBenchmarkChildSessionPath } from '@/router/routes'
import styles from './BenchmarkQuestionsTable.module.css'

const MODES: readonly BenchmarkInferenceMode[] = ['simple', 'ralph']
const PAGE_SIZE = 100

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
 *
 * Com `onRerun`, as questões encerradas com fluxo errado ou com falha ganham o botão
 * "Executar novamente", que refaz só esses fluxos. Fica desabilitado enquanto `rerunDisabled`
 * (outra bateria ou reexecução em andamento) e ausente enquanto a própria bateria executa.
 * `onRerunMany` habilita seleção múltipla, preservada entre páginas da mesma bateria.
 */
export function BenchmarkQuestionsTable({
  session,
  onRerun,
  onRerunMany,
  rerunDisabled = false,
}: {
  session: BenchmarkSessionDocument
  onRerun?: (questionId: string) => void
  onRerunMany?: (questionIds: string[]) => void
  rerunDisabled?: boolean
}): JSX.Element {
  const [page, setPage] = useState(0)
  const [selection, setSelection] = useState<{ sessionId: string; questionIds: string[] }>({
    sessionId: session.id,
    questionIds: [],
  })
  const canRerun = onRerun !== undefined && session.status !== BENCHMARK_SESSION_STATUS.RUNNING
  const canSelect = onRerunMany !== undefined && session.status !== BENCHMARK_SESSION_STATUS.RUNNING
  const rerunnableIds = canSelect
    ? session.questions.filter(isQuestionRerunnable).map((question) => question.question_id)
    : []
  const selected = new Set(selection.sessionId === session.id ? selection.questionIds : [])
  const selectedIds = rerunnableIds.filter((id) => selected.has(id))
  const allSelected = rerunnableIds.length > 0 && selectedIds.length === rerunnableIds.length

  function toggleQuestion(questionId: string): void {
    setSelection({
      sessionId: session.id,
      questionIds: selectedIds.includes(questionId)
        ? selectedIds.filter((id) => id !== questionId)
        : [...selectedIds, questionId],
    })
  }

  const pageCount = Math.max(1, Math.ceil(session.questions.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount - 1)
  const questions = session.questions.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)
  return (
    <div className={styles.wrapper}>
      {canSelect && rerunnableIds.length > 0 ? (
        <div className={styles.selectionBar}>
          <div>
            <p className={styles.selectionCount} aria-live="polite">
              {selectedIds.length} de {rerunnableIds.length} questões selecionadas
            </p>
            <p className={styles.selectionHint}>
              Selecione questões com erro ou falha. A seleção inclui todas as páginas.
            </p>
          </div>
          <Button
            size="sm"
            disabled={rerunDisabled || selectedIds.length === 0}
            onClick={() => {
              onRerunMany(selectedIds)
              setSelection({ sessionId: session.id, questionIds: [] })
            }}
          >
            Executar novamente selecionadas ({selectedIds.length})
          </Button>
        </div>
      ) : null}
      {pageCount > 1 ? (
        <nav className={styles.pagination} aria-label="Páginas de questões">
          <Button
            size="sm"
            variant="secondary"
            disabled={currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            Anterior
          </Button>
          <span>
            Página {currentPage + 1} de {pageCount}
          </span>
          <Button
            size="sm"
            variant="secondary"
            disabled={currentPage === pageCount - 1}
            onClick={() => setPage(currentPage + 1)}
          >
            Próxima
          </Button>
        </nav>
      ) : null}
      <table className={styles.table} aria-label="Questões da bateria">
        <thead>
          <tr>
            {canSelect ? (
              <th scope="col" className={styles.selectionCell}>
                <input
                  type="checkbox"
                  aria-label="Selecionar todas as questões com erro ou falha"
                  checked={allSelected}
                  ref={(input) => {
                    if (input) input.indeterminate = selectedIds.length > 0 && !allSelected
                  }}
                  disabled={rerunDisabled || rerunnableIds.length === 0}
                  onChange={() => setSelection({
                    sessionId: session.id,
                    questionIds: allSelected ? [] : rerunnableIds,
                  })}
                />
              </th>
            ) : null}
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
            {onRerun ? (
              <th scope="col">
                <span className={styles.srOnly}>Ações</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {questions.map((question) => (
            <tr key={question.question_id}>
              {canSelect ? (
                <td className={styles.selectionCell}>
                  {isQuestionRerunnable(question) ? (
                    <input
                      type="checkbox"
                      aria-label={`Selecionar ${question.question_id} para reexecução`}
                      checked={selected.has(question.question_id)}
                      disabled={rerunDisabled}
                      onChange={() => toggleQuestion(question.question_id)}
                    />
                  ) : null}
                </td>
              ) : null}
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
              {onRerun ? (
                <td>
                  {canRerun && isQuestionRerunnable(question) ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={rerunDisabled}
                      aria-label={`Executar novamente ${question.question_id}`}
                      onClick={() => onRerun(question.question_id)}
                    >
                      Executar novamente
                    </Button>
                  ) : null}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
