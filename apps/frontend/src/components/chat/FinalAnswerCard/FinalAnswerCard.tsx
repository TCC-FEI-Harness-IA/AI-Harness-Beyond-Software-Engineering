import { BUDGET_LIMIT_LABEL, isBudgetLimit } from '@/domain/enums/budgetLimit'
import { PHASE_SHORT_LABEL } from '@/domain/enums/thinkingPhase'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import type { RunDegradation } from '@/domain/types/thinkingRun'
import { Card } from '@/components/primitives/Card'
import { Badge } from '@/components/primitives/Badge'
import { Markdown } from '@/components/markdown/Markdown'
import { MessageStats } from '@/components/chat/MessageStats'
import { cx } from '@/components/cx'
import styles from './FinalAnswerCard.module.css'

export interface FinalAnswerCardProps {
  content: string
  stats?: MessageStatsView
  label?: string
  /** Degradações da execução (README, FASE 05, seção 9) — presentes só quando o Ralph
   * concluiu degradado. Renderizadas como aviso + lista recolhível, nunca como erro. */
  degradations?: RunDegradation[]
}

function limitLabel(limit: string): string {
  return isBudgetLimit(limit) ? BUDGET_LIMIT_LABEL[limit] : limit
}

/**
 * Destaque exigido pelo requisito "resposta final destacada" (README). Tipografia um passo
 * maior que as demais mensagens — a única coisa na tela com esse tratamento, para que o olho
 * vá direto nela ao rolar.
 */
export function FinalAnswerCard({
  content,
  stats,
  label = 'Resposta final',
  degradations = [],
}: FinalAnswerCardProps): JSX.Element {
  const isDegraded = degradations.length > 0

  return (
    <Card padding="lg" elevation="md" className={cx(styles.card, styles.appear)}>
      <div className={styles.header}>
        <Badge tone="accent">{label}</Badge>
        {isDegraded ? <Badge tone="warning">Concluído com degradação</Badge> : null}
      </div>
      <div className={styles.body}>
        <Markdown content={content} variant="block" />
      </div>
      {stats ? (
        <div className={styles.footer}>
          <MessageStats stats={stats} layout="panel" />
        </div>
      ) : null}
      {isDegraded ? (
        <details className={styles.degradations}>
          <summary>Degradações ({degradations.length})</summary>
          <ul>
            {degradations.map((degradation, index) => (
              <li key={`${degradation.limit}:${degradation.taskId ?? 'geral'}:${index}`}>
                <strong>{limitLabel(degradation.limit)}</strong>
                {' · '}
                {PHASE_SHORT_LABEL[degradation.phase]}
                {degradation.description ? ` — ${degradation.description}` : ''}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </Card>
  )
}
