import type { MessageStatsView } from '@/domain/types/messageStatsView'
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
}

/**
 * Destaque exigido pelo requisito "resposta final destacada" (README). Tipografia um passo
 * maior que as demais mensagens — a única coisa na tela com esse tratamento, para que o olho
 * vá direto nela ao rolar.
 */
export function FinalAnswerCard({ content, stats, label = 'Resposta final' }: FinalAnswerCardProps): JSX.Element {
  return (
    <Card padding="lg" elevation="md" className={cx(styles.card, styles.appear)}>
      <div className={styles.header}>
        <Badge tone="accent">{label}</Badge>
      </div>
      <div className={styles.body}>
        <Markdown content={content} variant="block" />
      </div>
      {stats ? (
        <div className={styles.footer}>
          <MessageStats stats={stats} layout="panel" />
        </div>
      ) : null}
    </Card>
  )
}
