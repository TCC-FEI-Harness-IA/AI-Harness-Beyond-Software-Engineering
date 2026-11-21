import {
  type AnalysisGroup,
  formatMultiplier,
  formatPp,
  type OutcomeCost,
  PAIR_OUTCOME_LABEL,
} from '@/domain/services/benchmarkAnalysis'
import { formatCompactTokens, formatDuration, formatTokens } from '@/domain/services/formatters'
import { ChartFrame, TooltipBody } from './ChartFrame'
import { horizontalBar } from './GroupBarsChart'
import { clipLabel, linearScale, niceTicks, placePointLabels, symmetricDomain } from './scales'
import styles from './charts.module.css'

const ROW = 30
const BAR = 14
const LABEL_WIDTH = 104
const TOP = 20

/**
 * Tokens médios por desfecho do par, um painel por fluxo (escalas diferentes, nunca no mesmo eixo):
 * mostra se o Ralph gasta mais justamente nas questões que corrige ou que piora.
 */
export function OutcomeTokensChart({ costs, flow }: { costs: readonly OutcomeCost[]; flow: 'simple' | 'ralph' }): JSX.Element {
  const isRalph = flow === 'ralph'
  const value = (cost: OutcomeCost): number => (isRalph ? cost.ralphMeanTokens : cost.simpleMeanTokens)
  const title = isRalph ? 'Tokens médios do Ralph por desfecho' : 'Tokens médios da simples por desfecho'
  return (
    <ChartFrame title={title} description="Média por questão em cada desfecho do par.">
      {({ width, showTooltip, hideTooltip }) => {
        const right = width - 64
        const { domain, ticks } = niceTicks(0, Math.max(1, ...costs.map(value)), 3)
        const x = linearScale(domain, [LABEL_WIDTH + 8, right])
        const height = TOP + costs.length * ROW
        return (
          <svg width={width} height={height} role="img" aria-label={title}>
            {ticks.map((tick) => (
              <g key={tick}>
                <line className={styles.grid} x1={x(tick)} x2={x(tick)} y1={TOP - 4} y2={height} />
                <text className={styles.tick} x={x(tick)} y={10} textAnchor="middle">
                  {formatCompactTokens(tick)}
                </text>
              </g>
            ))}
            {costs.map((cost, index) => {
              const middle = TOP + index * ROW + ROW / 2
              const mean = value(cost)
              const tooltip = (
                <TooltipBody
                  title={PAIR_OUTCOME_LABEL[cost.outcome]}
                  rows={[
                    ['Questões', String(cost.count)],
                    ['Tokens médios', formatTokens(Math.round(mean))],
                    ...(isRalph ? ([['Tempo médio', formatDuration(cost.ralphMeanSeconds * 1000)]] as Array<[string, string]>) : []),
                  ]}
                />
              )
              return (
                <g key={cost.outcome} className={cost.count === 0 ? styles.faded : undefined}>
                  <rect
                    className={styles.hit}
                    x={0}
                    y={middle - ROW / 2}
                    width={width}
                    height={ROW}
                    tabIndex={0}
                    aria-label={`${PAIR_OUTCOME_LABEL[cost.outcome]}: ${formatTokens(Math.round(mean))} tokens`}
                    onMouseMove={(event) => showTooltip(event, tooltip)}
                    onFocus={(event) => showTooltip(event, tooltip)}
                    onBlur={hideTooltip}
                  />
                  <g pointerEvents="none">
                    <text className={styles.label} x={LABEL_WIDTH} y={middle + 4} textAnchor="end">
                      {PAIR_OUTCOME_LABEL[cost.outcome]}
                    </text>
                    {mean > 0 ? (
                      <path
                        className={isRalph ? styles.fillRalph : styles.fillSimple}
                        d={horizontalBar(x(0), x(mean), middle - BAR / 2, BAR)}
                      />
                    ) : null}
                    <text className={styles.value} x={x(mean) + 6} y={middle + 3}>
                      {cost.count === 0 ? '—' : formatCompactTokens(mean)}
                    </text>
                  </g>
                </g>
              )
            })}
          </svg>
        )
      }}
    </ChartFrame>
  )
}

const MARGIN = { top: 26, right: 24, bottom: 36, left: 52 }
const SCATTER_HEIGHT = 260
const MAX_DIRECT_LABELS = 8

/** Custo × benefício por grupo (execução): quantas vezes mais tokens o Ralph gasta e quanto isso rende em acurácia. */
export function CostBenefitChart({ groups }: { groups: readonly AnalysisGroup[] }): JSX.Element {
  const points = groups.filter((group) => group.summary.tokenMultiplier !== null)
  return (
    <ChartFrame
      title="Custo × benefício por execução"
      description="Eixo horizontal: tokens do Ralph ÷ tokens da simples. Vertical: ganho de acurácia em p.p. Acima da linha zero o Ralph compensa em acertos."
    >
      {({ width, showTooltip, hideTooltip }) => {
        const right = width - MARGIN.right
        const bottom = SCATTER_HEIGHT - MARGIN.bottom
        const xTicks = niceTicks(0, Math.max(1, ...points.map((group) => group.summary.tokenMultiplier as number)), 4)
        const yAxis = symmetricDomain(points.map((group) => group.summary.delta * 100), 5)
        const x = linearScale(xTicks.domain, [MARGIN.left, right])
        const y = linearScale(yAxis.domain, [bottom, MARGIN.top])
        const positions = points.map((group) => ({
          x: x(group.summary.tokenMultiplier as number),
          y: y(group.summary.delta * 100),
          text: clipLabel(group.label, 24),
        }))
        const labels =
          points.length <= MAX_DIRECT_LABELS ? placePointLabels(positions, { left: MARGIN.left, right: width }) : []
        return (
          <svg width={width} height={SCATTER_HEIGHT} role="img" aria-label="Custo em tokens versus ganho de acurácia por execução">
            {yAxis.ticks.map((tick) => (
              <g key={`y${tick}`}>
                <line className={tick === 0 ? styles.zero : styles.grid} x1={MARGIN.left} x2={right} y1={y(tick)} y2={y(tick)} />
                <text className={styles.tick} x={MARGIN.left - 6} y={y(tick) + 3} textAnchor="end">
                  {`${tick > 0 ? '+' : ''}${Math.round(tick * 10) / 10}`}
                </text>
              </g>
            ))}
            {xTicks.ticks.map((tick) => (
              <text key={`x${tick}`} className={styles.tick} x={x(tick)} y={bottom + 14} textAnchor="middle">
                {tick}×
              </text>
            ))}
            <text className={styles.tick} x={(MARGIN.left + right) / 2} y={SCATTER_HEIGHT - 4} textAnchor="middle">
              tokens Ralph ÷ simples
            </text>
            <text className={styles.tick} x={MARGIN.left - 6} y={10} textAnchor="end">
              Δ p.p.
            </text>
            {points.map((group, index) => {
              const s = group.summary
              const { x: cx, y: cy, text } = positions[index] as { x: number; y: number; text: string }
              const label = labels[index] ?? null
              const tooltip = (
                <TooltipBody
                  title={group.label}
                  rows={[
                    ['Pares', String(s.n)],
                    ['Δ', formatPp(s.delta)],
                    ['Tokens Ralph / simples', formatMultiplier(s.tokenMultiplier)],
                    ['Saldo', `${s.netGain > 0 ? '+' : ''}${s.netGain}`],
                  ]}
                />
              )
              return (
                <g key={group.key}>
                  <circle className={`${styles.dot} ${styles.fillInk}`} cx={cx} cy={cy} r={6} pointerEvents="none" />
                  <circle
                    className={styles.hit}
                    cx={cx}
                    cy={cy}
                    r={12}
                    tabIndex={0}
                    aria-label={`${group.label}: ${formatMultiplier(s.tokenMultiplier)} tokens, Δ ${formatPp(s.delta)}`}
                    onMouseMove={(event) => showTooltip(event, tooltip)}
                    onFocus={(event) => showTooltip(event, tooltip)}
                    onBlur={hideTooltip}
                  />
                  {label !== null ? (
                    <text className={styles.value} x={label.x} y={label.y} textAnchor={label.anchor} pointerEvents="none">
                      {text}
                    </text>
                  ) : null}
                </g>
              )
            })}
          </svg>
        )
      }}
    </ChartFrame>
  )
}
