import { memo } from 'react'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE } from '@/domain/enums/eventType'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '@/domain/enums/taskLabels'
import type { Tone } from '@/domain/enums/tone'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { PhaseTag } from '@/components/chat/PhaseTag'
import { Badge } from '@/components/primitives/Badge'
import { Tag } from '@/components/primitives/Tag'
import styles from './ThinkingStepMessage.module.css'

export interface ThinkingStepMessageProps {
  step: ThinkingStep
  modelName: string | null
  /** Só o último passo ao vivo anima — histórico e passos antigos entram sem transição. */
  animateIn?: boolean
}

const CONTEXT_ID_VISIBLE_CHARS = 7

const SEPARATOR_SUBTYPES: ReadonlySet<string> = new Set([
  EVENT_SUBTYPE.RESET,
  EVENT_SUBTYPE.STORE,
  EVENT_SUBTYPE.EXECUTE,
])

function displayTaskId(taskId: string): string | null {
  return taskId === TASK_LABEL_SETUP || taskId === TASK_LABEL_SYNTHESIS ? null : taskId
}

function buildStats(step: ThinkingStep, modelName: string | null): MessageStatsView {
  return {
    modelName,
    tokensInput: null,
    tokensOutput: null,
    totalTokens: step.totalTokens,
    inferenceTimeMs: step.inferenceTimeMs,
    contextId: step.contextId,
    contextSize: step.contextSize,
    timestamp: step.timestamp,
  }
}

function toneForStep(step: ThinkingStep): Tone {
  if (step.type === EVENT_TYPE.DEGRADED) return 'warning'
  if (step.subtype === EVENT_SUBTYPE.VERIFY_PASS) return 'success'
  if (step.subtype === EVENT_SUBTYPE.VERIFY_FAIL) return 'warning'
  return 'neutral'
}

/**
 * Uma mensagem do Modo Chat do Ralph — a forma varia com o `subtype` do passo (README,
 * FASE 05, seção 9). `reset`/`store`/`execute` são etapas programáticas e viram separador,
 * não bolha, para não competir visualmente com o raciocínio do modelo.
 */
export const ThinkingStepMessage = memo(function ThinkingStepMessage({
  step,
  modelName,
  animateIn = false,
}: ThinkingStepMessageProps): JSX.Element {
  if (SEPARATOR_SUBTYPES.has(step.subtype)) {
    if (step.subtype === EVENT_SUBTYPE.RESET) {
      return (
        <MessageBubble
          role="system"
          content={step.content}
          label={`Contexto reinicializado · ${step.taskId}`}
          header={<Tag tone="context">{step.contextId.slice(0, CONTEXT_ID_VISIBLE_CHARS)}</Tag>}
          animateIn={animateIn}
        />
      )
    }
    return <MessageBubble role="system" content={step.content} animateIn={animateIn} />
  }

  return (
    <MessageBubble
      role="assistant"
      content={step.content}
      tone={toneForStep(step)}
      header={
        <span className={styles.header}>
          <PhaseTag phase={step.phase} subtype={step.subtype} taskId={displayTaskId(step.taskId)} />
          {step.type === EVENT_TYPE.DEGRADED ? <Badge tone="warning">Degradação</Badge> : null}
        </span>
      }
      stats={buildStats(step, modelName)}
      animateIn={animateIn}
    />
  )
})
