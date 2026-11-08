import type { ReactNode } from 'react'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import { StatItem } from '@/components/primitives/StatItem'
import { Tag } from '@/components/primitives/Tag'
import { formatDateTime, formatDuration, formatTokens } from '@/domain/services/formatters'
import styles from './MessageStats.module.css'

export interface MessageStatsProps {
  stats: MessageStatsView
  /** 'inline' = faixa discreta sob a mensagem; 'panel' = grade, no rodapé de uma execução. */
  layout?: 'inline' | 'panel'
}

const CONTEXT_ID_VISIBLE_CHARS = 7

/**
 * Estatísticas de uma mensagem — modelo, tokens, tempo e contexto. É o único componente que
 * renderiza esses dados, no fluxo simples e no Ralph, ao vivo e no histórico (regra de reuso 5).
 * A ordem é sempre modelo → tokens → tempo → contexto; campos `null` somem sem deixar buraco.
 */
export function MessageStats({ stats, layout = 'inline' }: MessageStatsProps): JSX.Element {
  const entries: Array<{ key: string; node: ReactNode }> = []

  if (stats.modelName !== null) {
    entries.push({ key: 'model', node: <StatItem label="Modelo" value={stats.modelName} layout={layout} /> })
  }

  if (stats.tokensInput !== null && stats.tokensOutput !== null) {
    entries.push({
      key: 'tokens-io',
      node: (
        <StatItem
          label="Tokens"
          value={`${formatTokens(stats.tokensInput)} → ${formatTokens(stats.tokensOutput)}`}
          layout={layout}
        />
      ),
    })
  }

  if (stats.totalTokens !== null) {
    entries.push({
      key: 'tokens-total',
      node: <StatItem label="Total" value={`${formatTokens(stats.totalTokens)} tokens`} layout={layout} />,
    })
  }

  if (stats.inferenceTimeMs !== null) {
    entries.push({
      key: 'time',
      node: <StatItem label="Tempo" value={formatDuration(stats.inferenceTimeMs)} layout={layout} />,
    })
  }

  if (stats.contextSize !== null) {
    entries.push({
      key: 'context-size',
      node: (
        <StatItem
          label="Contexto"
          value={`${formatTokens(stats.contextSize)} tokens`}
          tone="context"
          layout={layout}
        />
      ),
    })
  }

  if (stats.contextId !== null) {
    entries.push({
      key: 'context-id',
      node: <Tag title={stats.contextId}>{stats.contextId.slice(0, CONTEXT_ID_VISIBLE_CHARS)}</Tag>,
    })
  }

  if (stats.sessionId !== null && stats.sessionId !== undefined) {
    entries.push({
      key: 'session-id',
      node: (
        <Tag title={`Sessão completa: ${stats.sessionId}`}>
          {stats.sessionId.slice(0, CONTEXT_ID_VISIBLE_CHARS)}
        </Tag>
      ),
    })
  }

  if (stats.llmCalls !== null && stats.llmCalls !== undefined) {
    entries.push({
      key: 'llm-calls',
      node: <StatItem label="Chamadas" value={formatTokens(stats.llmCalls)} layout={layout} />,
    })
  }

  if (stats.taskCount !== null && stats.taskCount !== undefined) {
    entries.push({
      key: 'task-count',
      node: <StatItem label="Tarefas" value={formatTokens(stats.taskCount)} layout={layout} />,
    })
  }

  if (stats.attemptCount !== null && stats.attemptCount !== undefined) {
    entries.push({
      key: 'attempt-count',
      node: <StatItem label="Tentativas" value={formatTokens(stats.attemptCount)} layout={layout} />,
    })
  }

  if (stats.contextCount !== null && stats.contextCount !== undefined) {
    entries.push({
      key: 'context-count',
      node: (
        <StatItem label="Janelas" value={formatTokens(stats.contextCount)} tone="context" layout={layout} />
      ),
    })
  }

  if (stats.timestamp !== null) {
    entries.push({
      key: 'timestamp',
      node: <StatItem label="Quando" value={formatDateTime(stats.timestamp)} layout={layout} />,
    })
  }

  if (layout === 'panel') {
    return (
      <div className={styles.panel}>
        {entries.map((entry) => (
          <span key={entry.key}>{entry.node}</span>
        ))}
      </div>
    )
  }

  return (
    <div className={styles.inline}>
      {entries.map((entry, index) => (
        <span key={entry.key} className={styles.entry}>
          {index > 0 ? <span className={styles.separator}>·</span> : null}
          {entry.node}
        </span>
      ))}
    </div>
  )
}
