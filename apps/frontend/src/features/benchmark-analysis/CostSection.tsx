import { useMemo } from 'react'
import { type AnalysisGroup, type AnalysisRecord, costByOutcome } from '@/domain/services/benchmarkAnalysis'
import { CostBenefitChart, OutcomeTokensChart } from './charts/CostCharts'
import chartStyles from './charts/charts.module.css'
import styles from './BenchmarkAnalysis.module.css'

/** Custo do Ralph: onde ele gasta (por desfecho) e se o gasto rende acertos (por execução). */
export function CostSection({
  records,
  executions,
}: {
  records: readonly AnalysisRecord[]
  executions: readonly AnalysisGroup[]
}): JSX.Element {
  const costs = useMemo(() => costByOutcome(records), [records])
  return (
    <section className={styles.section} aria-labelledby="analysis-cost-title">
      <div>
        <h2 id="analysis-cost-title" className={styles.sectionTitle}>
          Custo
        </h2>
        <p className={styles.sectionHint}>
          Se o Ralph gasta mais tokens justamente nas questões que corrige, o loop está trabalhando onde importa;
          se gasta mais nas que piora, o esforço extra está levando a respostas erradas.
        </p>
      </div>
      <div className={chartStyles.chartsGrid}>
        <div className={chartStyles.chartCard}>
          <OutcomeTokensChart costs={costs} flow="ralph" />
        </div>
        <div className={chartStyles.chartCard}>
          <OutcomeTokensChart costs={costs} flow="simple" />
        </div>
        <div className={chartStyles.chartCard}>
          <CostBenefitChart groups={executions} />
        </div>
      </div>
    </section>
  )
}
