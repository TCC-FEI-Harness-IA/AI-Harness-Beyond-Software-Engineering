import { cx } from '@/components/cx'
import { TASK_STATUS_LABEL, TASK_STATUS_TONE } from '@/domain/enums/taskStatus'
import { formatDuration, formatTokens } from '@/domain/services/formatters'
import type { TaskLaneView } from '@/domain/services/graphLayout'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import { Badge } from '@/components/primitives/Badge'
import { Tag } from '@/components/primitives/Tag'
import { AttemptDot } from '@/components/timeline/AttemptDot'
import styles from './TaskLane.module.css'

export interface TaskLaneProps {
  lane: TaskLaneView
  isLive: boolean
  onStepSelect: (step: ThinkingStep) => void
}

/**
 * ② Uma faixa por tarefa — o loop de execução aberto (README, FASE 06, seção 5). Cada passo é
 * um `AttemptDot`; tentativas além da primeira ganham uma chave visual, para que o ciclo
 * B.1 ⇄ B.2 do paper fique legível sem precisar abrir o detalhe de cada passo.
 */
export function TaskLane({ lane, isLive, onStepSelect }: TaskLaneProps): JSX.Element {
  const lastStepId = lane.steps[lane.steps.length - 1]?.step.id
  const isDiscarded = lane.status === 'discarded'

  return (
    <li
      className={cx(styles.lane, isDiscarded && styles.discarded)}
      aria-label={isDiscarded ? `${lane.id}: tarefa descartada — orçamento da sessão esgotado` : undefined}
    >
      <div className={styles.header}>
        <Tag>{lane.id}</Tag>
        <span className={styles.title}>{lane.title ?? 'Tarefa'}</span>
        <Badge tone={TASK_STATUS_TONE[lane.status]}>{TASK_STATUS_LABEL[lane.status]}</Badge>
        {lane.origin === 'C2' ? <Badge tone="warning">Planejada em C.2</Badge> : null}
        <span className={styles.stats}>
          {formatTokens(lane.tokens)} tk · {formatDuration(lane.inferenceTimeMs)}
        </span>
      </div>

      <div className={styles.track}>
        {lane.steps.map((entry, index) => {
          const previous = lane.steps[index - 1]
          const opensNewAttempt =
            entry.attemptIndex > 1 && (previous === undefined || previous.attemptIndex !== entry.attemptIndex)

          return (
            <span key={entry.step.id} className={styles.stepWrapper}>
              {opensNewAttempt ? (
                <span className={styles.attemptTag} aria-hidden="true">
                  tentativa {entry.attemptIndex}
                </span>
              ) : null}
              <AttemptDot step={entry.step} isLatest={isLive && entry.step.id === lastStepId} onSelect={onStepSelect} />
            </span>
          )
        })}
      </div>
    </li>
  )
}
