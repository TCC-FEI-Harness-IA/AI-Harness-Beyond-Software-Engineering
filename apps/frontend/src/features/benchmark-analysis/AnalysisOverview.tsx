import { Badge } from '@/components/primitives/Badge'
import {
  type AnalysisExclusions,
  type AnalysisGroup,
  formatMultiplier,
  formatPp,
  formatPValue,
  PAIR_OUTCOME_LABEL,
  type PairedSummary,
  type PairOutcome,
  verdict,
} from '@/domain/services/benchmarkAnalysis'
import { formatDuration, formatPercent, formatTokens } from '@/domain/services/formatters'
import styles from './BenchmarkAnalysis.module.css'

const rate = (value: number | null): string => (value === null ? '—' : formatPercent(value))
const signed = (value: number): string => `${value > 0 ? '+' : ''}${value}`

function Kpi({ label, value, detail }: { label: string; value: string; detail?: string }): JSX.Element {
  return (
    <div className={styles.kpi}>
      <span className={styles.kpiLabel}>{label}</span>
      <span className={styles.kpiValue}>{value}</span>
      {detail ? <span className={styles.kpiDetail}>{detail}</span> : null}
    </div>
  )
}

function groupList(groups: readonly AnalysisGroup[]): string {
  return groups.map((group) => `${group.label} (${formatPp(group.summary.delta)}, n=${group.summary.n})`).join('; ')
}

export interface RankedHighlight {
  /** Nome da dimensão no texto: "matéria", "área". */
  dimension: string
  /** Grupos ordenados por Δ, já filtrados por tamanho mínimo. */
  groups: readonly AnalysisGroup[]
}

function Highlights({ dimension, groups }: RankedHighlight): JSX.Element {
  const gains = groups.filter((group) => group.summary.delta > 0).slice(0, 3)
  const losses = groups.filter((group) => group.summary.delta < 0).reverse().slice(0, 3)
  return (
    <>
      {gains.length > 0 ? <li>Maior ganho do Ralph por {dimension}: {groupList(gains)}.</li> : null}
      {losses.length > 0 ? <li>Maior perda do Ralph por {dimension}: {groupList(losses)}.</li> : null}
    </>
  )
}

function ExecutiveSummary({
  summary: s,
  highlights,
  exclusions,
}: {
  summary: PairedSummary
  highlights: readonly RankedHighlight[]
  exclusions: AnalysisExclusions
}): JSX.Element {
  const simpleErrors = s.recoveries + s.bothWrong
  return (
    <ul className={styles.summaryText} aria-label="Resumo executivo">
      <li>
        Em <strong>{s.n}</strong> questões pareadas, o Ralph Loop acertou{' '}
        <strong>{formatPercent(s.ralphAccuracy)}</strong> contra <strong>{formatPercent(s.simpleAccuracy)}</strong>{' '}
        da inferência simples — <strong>{formatPp(s.delta)}</strong> ({verdict(s).label}; McNemar p ={' '}
        {formatPValue(s.mcnemarPValue)}).
      </li>
      <li>
        Quando a inferência simples errou ({simpleErrors} questões), o Ralph acertou <strong>{s.recoveries}</strong> (
        {rate(s.recoveryRate)}). Quando a simples acertou ({s.bothCorrect + s.regressions}), o Ralph errou{' '}
        <strong>{s.regressions}</strong> ({rate(s.regressionRate)}). Saldo: <strong>{signed(s.netGain)}</strong>{' '}
        questões.
      </li>
      <li>
        O Ralph consumiu <strong>{formatMultiplier(s.tokenMultiplier)}</strong> os tokens da simples (
        {formatTokens(s.ralphTokens)} × {formatTokens(s.simpleTokens)})
        {s.extraTokensPerNetGain === null
          ? ' sem ganho líquido de acertos.'
          : `, cerca de ${formatTokens(Math.round(s.extraTokensPerNetGain))} tokens extras por acerto líquido.`}
      </li>
      {highlights.map((highlight) => (
        <Highlights key={highlight.dimension} {...highlight} />
      ))}
      {exclusions.unpaired + exclusions.failures > 0 ? (
        <li className={styles.muted}>
          Fora da análise: {exclusions.unpaired} questões sem os dois fluxos concluídos
          {exclusions.failures > 0 ? ` e ${exclusions.failures} com falha técnica` : ''}.
        </li>
      ) : null}
    </ul>
  )
}

const SEGMENTS: ReadonlyArray<{ outcome: PairOutcome; className: string | undefined; color: string }> = [
  { outcome: 'both_correct', className: styles.segBothCorrect, color: 'var(--outcome-both-correct)' },
  { outcome: 'ralph_recovers', className: styles.segRecovers, color: 'var(--outcome-recovers)' },
  { outcome: 'ralph_regresses', className: styles.segRegresses, color: 'var(--outcome-regresses)' },
  { outcome: 'both_wrong', className: styles.segBothWrong, color: 'var(--outcome-both-wrong)' },
]

function outcomeCount(s: PairedSummary, outcome: PairOutcome): number {
  switch (outcome) {
    case 'both_correct':
      return s.bothCorrect
    case 'ralph_recovers':
      return s.recoveries
    case 'ralph_regresses':
      return s.regressions
    case 'both_wrong':
      return s.bothWrong
  }
}

function OutcomeBar({ summary }: { summary: PairedSummary }): JSX.Element {
  return (
    <div className={styles.section}>
      <div className={styles.outcomeBar} role="img" aria-label="Distribuição dos desfechos pareados">
        {SEGMENTS.map(({ outcome, className }) => {
          const count = outcomeCount(summary, outcome)
          if (count === 0) return null
          return (
            <span
              key={outcome}
              className={`${styles.segment} ${className ?? ''}`}
              style={{ flexGrow: count }}
              title={`${PAIR_OUTCOME_LABEL[outcome]}: ${count} (${formatPercent(count / summary.n)})`}
            />
          )
        })}
      </div>
      <ul className={styles.legend} aria-label="Legenda dos desfechos">
        {SEGMENTS.map(({ outcome, color }) => {
          const count = outcomeCount(summary, outcome)
          return (
            <li key={outcome}>
              <span className={styles.swatch} style={{ background: color }} />
              {PAIR_OUTCOME_LABEL[outcome]}: {count} ({formatPercent(summary.n === 0 ? 0 : count / summary.n)})
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function ContingencyMatrix({ summary: s }: { summary: PairedSummary }): JSX.Element {
  const share = (count: number): string => formatPercent(s.n === 0 ? 0 : count / s.n)
  return (
    <table className={styles.matrix} aria-label="Tabela de contingência Simples × Ralph">
      <thead>
        <tr>
          <td />
          <th scope="col">Ralph acerta</th>
          <th scope="col">Ralph erra</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Simples acerta</th>
          <td className={styles.matrixCell}>
            <strong>{s.bothCorrect}</strong>
            <span>ambos acertam · {share(s.bothCorrect)}</span>
          </td>
          <td className={`${styles.matrixCell} ${styles.cellRegresses}`}>
            <strong>{s.regressions}</strong>
            <span>Ralph piora · {share(s.regressions)}</span>
          </td>
        </tr>
        <tr>
          <th scope="row">Simples erra</th>
          <td className={`${styles.matrixCell} ${styles.cellRecovers}`}>
            <strong>{s.recoveries}</strong>
            <span>Ralph corrige · {share(s.recoveries)}</span>
          </td>
          <td className={styles.matrixCell}>
            <strong>{s.bothWrong}</strong>
            <span>
              ambos erram · {s.bothWrongSameAnswer} c/ mesma alternativa
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  )
}

export interface AnalysisOverviewProps {
  summary: PairedSummary
  /** Destaques do resumo executivo: onde o Ralph mais ganha e mais perde. */
  highlights: readonly RankedHighlight[]
  exclusions: AnalysisExclusions
}

/** Visão geral consolidada da seleção: resumo em texto, indicadores, matriz 2×2 e desfechos. */
export function AnalysisOverview({ summary: s, highlights, exclusions }: AnalysisOverviewProps): JSX.Element {
  const result = verdict(s)
  return (
    <section className={styles.section} aria-labelledby="analysis-overview-title">
      <div className={styles.sectionHeader}>
        <h2 id="analysis-overview-title" className={styles.sectionTitle}>
          Resumo executivo
        </h2>
        <Badge tone={result.tone}>{result.label}</Badge>
      </div>
      <ExecutiveSummary summary={s} highlights={highlights} exclusions={exclusions} />

      <div className={styles.kpis}>
        <Kpi
          label="Acurácia simples"
          value={formatPercent(s.simpleAccuracy)}
          detail={`${s.simpleCorrect}/${s.n} · IC95% ${formatPercent(s.simpleInterval[0])}–${formatPercent(s.simpleInterval[1])}`}
        />
        <Kpi
          label="Acurácia Ralph"
          value={formatPercent(s.ralphAccuracy)}
          detail={`${s.ralphCorrect}/${s.n} · IC95% ${formatPercent(s.ralphInterval[0])}–${formatPercent(s.ralphInterval[1])}`}
        />
        <Kpi label="Diferença" value={formatPp(s.delta)} detail={`McNemar p = ${formatPValue(s.mcnemarPValue)}`} />
        <Kpi
          label="Recuperação"
          value={rate(s.recoveryRate)}
          detail={`${s.recoveries} de ${s.recoveries + s.bothWrong} erros da simples`}
        />
        <Kpi
          label="Regressão"
          value={rate(s.regressionRate)}
          detail={`${s.regressions} de ${s.bothCorrect + s.regressions} acertos da simples`}
        />
        <Kpi label="Redução do erro" value={rate(s.errorReduction)} detail={`Saldo ${signed(s.netGain)} questões`} />
        <Kpi
          label="Tokens Ralph / simples"
          value={formatMultiplier(s.tokenMultiplier)}
          detail={`${formatTokens(s.ralphTokens)} vs ${formatTokens(s.simpleTokens)}`}
        />
        <Kpi
          label="Tempo Ralph / simples"
          value={formatMultiplier(s.simpleSeconds === 0 ? null : s.ralphSeconds / s.simpleSeconds)}
          detail={`${formatDuration(s.ralphSeconds * 1000)} vs ${formatDuration(s.simpleSeconds * 1000)}`}
        />
        <Kpi
          label="Mudou a resposta"
          value={formatPercent(s.n === 0 ? 0 : s.answerChanged / s.n)}
          detail={`${s.answerChanged} questões com alternativa diferente`}
        />
        <Kpi label="Falhas técnicas" value={`${s.simpleFailures} · ${s.ralphFailures}`} detail="simples · Ralph" />
      </div>

      <div className={styles.overviewGrid}>
        <ContingencyMatrix summary={s} />
        <OutcomeBar summary={s} />
      </div>
    </section>
  )
}
