import { useEffect } from 'react'
import { ChatScroller } from '@/components/chat/ChatScroller'
import { FinalAnswerCard } from '@/components/chat/FinalAnswerCard'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '@/domain/enums/taskLabels'
import { THINKING_PHASE } from '@/domain/enums/thinkingPhase'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import type { ThinkingRun, ThinkingStep } from '@/domain/types/thinkingRun'
import { ThinkingStepMessage, thinkingStepAnchorId } from './ThinkingStepMessage'
import styles from './RalphChatMode.module.css'

export interface RalphChatModeProps {
  run: ThinkingRun
  isLive: boolean
  isStreaming?: boolean
  onRetry?: () => void
  /** Id do passo para o qual rolar — aciona a "âncora" que o Modo Gráfico pede em "Ver no Modo
   * Chat" (README, FASE 06, seção 7). `null`/ausente não rola nada. */
  scrollToStepId?: string | null
  onScrolledToStep?: () => void
}

interface StepGroup {
  key: string
  taskId: string | null
  steps: ThinkingStep[]
}

// A resposta final (C.3) não vira bolha — vira o `FinalAnswerCard` no fim da lista
// (README, FASE 05, seção 9).
function isFinalAnswerStep(step: ThinkingStep): boolean {
  return step.phase === THINKING_PHASE.C3 && step.subtype === EVENT_SUBTYPE.COMPILE
}

function groupingKey(step: ThinkingStep): string {
  return step.taskId === TASK_LABEL_SETUP || step.taskId === TASK_LABEL_SYNTHESIS ? '' : step.taskId
}

// Agrupa passos consecutivos da mesma tarefa — o espaçamento (não uma caixa) é o que separa
// visualmente um grupo do outro (README, seção 8.1; FASE 05, seção 9).
function groupSteps(steps: ThinkingStep[]): StepGroup[] {
  const groups: StepGroup[] = []
  for (const step of steps) {
    const key = groupingKey(step)
    const last = groups[groups.length - 1]
    if (last && last.key === key) {
      last.steps.push(step)
    } else {
      groups.push({ key, taskId: key === '' ? null : key, steps: [step] })
    }
  }
  return groups
}

function runTotalsAsStats(run: ThinkingRun): MessageStatsView {
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
 * Modo Chat do Ralph (README, FASE 05, seção 9): cada passo do fluxo de pensamento vira uma
 * mensagem no estilo do chat comum, agrupada por tarefa, com a resposta final destacada no
 * fim. Apresentação pura — recebe o `ThinkingRun` já pronto, não conhece rede nem reducer.
 */
export function RalphChatMode({
  run,
  isLive,
  isStreaming = false,
  onRetry,
  scrollToStepId = null,
  onScrolledToStep,
}: RalphChatModeProps): JSX.Element {
  const timelineSteps = run.steps.filter((step) => !isFinalAnswerStep(step))
  const groups = groupSteps(timelineSteps)
  const lastStepId = timelineSteps[timelineSteps.length - 1]?.id
  const isConnecting = isStreaming && timelineSteps.length === 0

  useEffect(() => {
    if (!scrollToStepId) return
    const element = document.getElementById(thinkingStepAnchorId(scrollToStepId))
    element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    onScrolledToStep?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrollToStepId])

  return (
    <ChatScroller contentKey={run.steps.length} isLive={isLive}>
      <MessageBubble role="user" content={run.question} />

      <div className={styles.groups}>
        {groups.map((group) => (
          <div key={`${group.key || 'geral'}:${group.steps[0]?.id ?? ''}`} className={styles.group}>
            {group.taskId ? <p className={styles.groupLabel}>{group.taskId}</p> : null}
            <div className={styles.groupSteps}>
              {group.steps.map((step) => (
                <ThinkingStepMessage
                  key={step.id}
                  step={step}
                  modelName={run.modelName}
                  animateIn={isLive && step.id === lastStepId}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {run.finalAnswer ? (
        <FinalAnswerCard content={run.finalAnswer} stats={runTotalsAsStats(run)} degradations={run.degradations} />
      ) : null}

      {isConnecting ? (
        <div className={styles.connecting} role="status" aria-live="polite">
          <p>Conectando ao servidor…</p>
          <Skeleton lines={3} />
        </div>
      ) : isStreaming ? (
        <TypingIndicator />
      ) : null}

      {run.error ? <ErrorState error={run.error} {...(onRetry ? { onRetry } : {})} /> : null}
    </ChatScroller>
  )
}
