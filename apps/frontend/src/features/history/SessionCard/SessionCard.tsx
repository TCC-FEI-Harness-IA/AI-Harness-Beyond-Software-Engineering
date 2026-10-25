import type { SessionSource } from '@/domain/types/sessionSource'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/primitives/Badge'
import { Card } from '@/components/primitives/Card'
import { SESSION_STATUS, SESSION_STATUS_LABEL, SESSION_STATUS_TONE } from '@/domain/enums/sessionStatus'
import { formatRelative, formatTokens } from '@/domain/services/formatters'
import type { SessionSummaryView } from '@/domain/types/sessionSummaryView'
import { buildHistoryDetailPath } from '@/router/routes'
import { RALPH_FLOW_ICON, SIMPLE_FLOW_ICON } from '../flowIcons'
import styles from './SessionCard.module.css'

export interface SessionCardProps {
  source?: SessionSource
  session: SessionSummaryView
}

/**
 * Cartão de uma sessão na lista de histórico (README, FASE 07, seção 5). O resumo é sempre o
 * input do usuário, truncado por `env.historySummaryMaxChars` — o texto completo fica no
 * `title` do link, acessível via tooltip nativo.
 */
export function SessionCard({ session, source = 'history' }: SessionCardProps): JSX.Element {
  const isRalph = session.flow === 'ralph'
  const benchmark = session.benchmarkDetails

  return (
    <Card as="li" className={styles.card}>
      <Link to={buildHistoryDetailPath(session.id, source)} className={styles.link} title={session.fullQuestion}>
        <div className={styles.header}>
          <Badge tone={isRalph ? 'accent' : 'neutral'} icon={isRalph ? RALPH_FLOW_ICON : SIMPLE_FLOW_ICON}>
            {isRalph ? 'Ralph' : 'Simples'}
          </Badge>
          {session.status !== SESSION_STATUS.COMPLETED ? (
            <Badge tone={SESSION_STATUS_TONE[session.status]}>{SESSION_STATUS_LABEL[session.status]}</Badge>
          ) : null}
        </div>

        {benchmark?.is_banchmark ? (
          <>
            <p className={styles.question}>{benchmark.question_name}</p>
            <p className={styles.meta}>
              {benchmark.is_correct === null ? 'Avaliação pendente' : benchmark.is_correct ? 'Certo' : 'Errado'}
              {' · '}Gabarito: {benchmark.expected_alternative ?? '—'}
              {' · '}Resposta: {benchmark.selected_alternative ?? '—'}
            </p>
          </>
        ) : null}
        <p className={styles.question}>{session.question}</p>

        <p className={styles.meta}>
          <span>{formatRelative(session.createdAt)}</span>
          <span>{formatTokens(session.totalTokens)} tokens</span>
          <span>{session.messageCount} msgs</span>
        </p>
      </Link>
    </Card>
  )
}
