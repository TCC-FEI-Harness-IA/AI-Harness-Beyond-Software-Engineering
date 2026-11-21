import { StatItem } from '@/components/primitives/StatItem'
import { benchmarkCompletion } from '@/domain/services/benchmarkView'
import { formatDuration, formatTokens } from '@/domain/services/formatters'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import styles from './BenchmarkProgressStats.module.css'

/** Contadores da fila, consumo de tokens, tempo de execução e a barra de progresso da bateria. */
export function BenchmarkProgressStats({
  session,
}: {
  session: BenchmarkSessionDocument
}): JSX.Element {
  const { progress } = session
  const completion = benchmarkCompletion(progress)

  return (
    <div className={styles.wrapper}>
      <div className={styles.stats}>
        <StatItem layout="panel" label="Pendentes" value={String(progress.pending)} />
        <StatItem
          layout="panel"
          label="Em execução"
          value={String(progress.running)}
          tone="accent"
        />
        <StatItem
          layout="panel"
          label="Encerradas"
          value={String(progress.finished)}
          tone="success"
        />
        {progress.interrupted > 0 ? (
          <StatItem
            layout="panel"
            label="Interrompidas"
            value={String(progress.interrupted)}
            tone="warning"
          />
        ) : null}
        <StatItem layout="panel" label="Tokens" value={formatTokens(session.total_tokens)} />
        <StatItem
          layout="panel"
          label="Tempo de execução"
          value={formatDuration(session.wall_time_ms)}
        />
      </div>
      <div
        className={styles.track}
        role="progressbar"
        aria-label="Progresso da bateria"
        aria-valuemin={0}
        aria-valuemax={progress.total}
        aria-valuenow={progress.finished + progress.interrupted}
        aria-valuetext={`${progress.finished} de ${progress.total} questões encerradas`}
      >
        <div className={styles.fill} style={{ width: `${completion * 100}%` }} />
      </div>
    </div>
  )
}
