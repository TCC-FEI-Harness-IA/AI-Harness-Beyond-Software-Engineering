import { FinalAnswerCard } from '@/components/chat/FinalAnswerCard'
import { MessageStats } from '@/components/chat/MessageStats'
import { Badge } from '@/components/primitives/Badge'
import { Card } from '@/components/primitives/Card'
import { RUN_STATUS_LABEL, RUN_STATUS_TONE } from '@/domain/enums/runStatus'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import type { ThinkingRun } from '@/domain/types/thinkingRun'
import styles from './RunSummaryPanel.module.css'

export interface RunSummaryPanelProps {
  run: ThinkingRun
}

function runStatsView(run: ThinkingRun): MessageStatsView {
  return {
    modelName: run.modelName,
    tokensInput: null,
    tokensOutput: null,
    totalTokens: run.totals.totalTokens,
    inferenceTimeMs: run.totals.inferenceTimeMs,
    contextId: null,
    contextSize: null,
    timestamp: null,
    llmCalls: run.totals.llmCalls,
    taskCount: run.totals.taskCount,
    attemptCount: run.totals.attemptCount,
    contextCount: run.totals.contextCount,
  }
}

/**
 * ④ Resumo — sempre visível no rodapé do Modo Gráfico (README, FASE 06, seção 7). A resposta
 * final é destacada nos dois modos, não é privilégio do Modo Chat: quando `run.finalAnswer`
 * existe, o mesmo `<FinalAnswerCard />` da FASE 05 aparece aqui também.
 */
export function RunSummaryPanel({ run }: RunSummaryPanelProps): JSX.Element {
  return (
    <div className={styles.wrapper}>
      {run.finalAnswer ? (
        <FinalAnswerCard content={run.finalAnswer} stats={runStatsView(run)} degradations={run.degradations} />
      ) : null}

      <Card padding="md" elevation="flat" className={styles.summary}>
        <div className={styles.header}>
          <span className={styles.title}>Resumo da execução</span>
          <Badge tone={RUN_STATUS_TONE[run.status]}>{RUN_STATUS_LABEL[run.status]}</Badge>
        </div>
        <MessageStats stats={runStatsView(run)} layout="panel" />
      </Card>
    </div>
  )
}
