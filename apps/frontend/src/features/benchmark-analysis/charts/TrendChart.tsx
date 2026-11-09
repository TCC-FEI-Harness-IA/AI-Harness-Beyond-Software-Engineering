import { type AnalysisGroup, formatPp } from '@/domain/services/benchmarkAnalysis'
import { formatPercent } from '@/domain/services/formatters'
import { ChartFrame, ChartLegend, TooltipBody } from './ChartFrame'
import { clipLabel, linearScale, niceTicks } from './scales'
import styles from './charts.module.css'

const MARGIN = { top: 12, right: 72, bottom: 40, left: 44 }
const HEIGHT = 240
/** Distância vertical mínima entre os rótulos de ponta; abaixo dela a legenda basta. */
const LABEL_CLEARANCE = 14

export interface TrendChartProps {
  title: string
  description: string
  /** Grupos já na ordem natural da dimensão (faixa, nível, quartil). */
  groups: readonly AnalysisGroup[]
  lowN: number
}

/** Acurácia dos dois fluxos ao longo de uma dimensão ordenada: onde as linhas se afastam, o Ralph muda o jogo. */
export function TrendChart({ title, description, groups, lowN }: TrendChartProps): JSX.Element {
  const legend = (
    <ChartLegend
      items={[
        { label: 'Inferência simples', swatchClass: styles.swatchSimple },
        { label: 'Ralph Loop', swatchClass: styles.swatchRalph },
      ]}
    />
  )
  return (
    <ChartFrame title={title} description={description} legend={legend}>
      {({ width, showTooltip, hideTooltip }) => {
        const plotRight = width - MARGIN.right
        const plotBottom = HEIGHT - MARGIN.bottom
        const lowest = Math.min(...groups.flatMap((group) => [group.summary.simpleAccuracy, group.summary.ralphAccuracy]))
        const nice = niceTicks(Math.max(0, lowest * 100 - 5), 100, 4)
        const ticks = nice.ticks.filter((tick) => tick <= 100)
        const y = linearScale([nice.domain[0], 100], [plotBottom, MARGIN.top])
        const band = (plotRight - MARGIN.left) / Math.max(1, groups.length)
        const x = (index: number): number => MARGIN.left + band * (index + 0.5)
        const path = (accessor: (group: AnalysisGroup) => number): string =>
          groups.map((group, index) => `${index === 0 ? 'M' : 'L'}${x(index)},${y(accessor(group) * 100)}`).join(' ')
        const last = groups[groups.length - 1]
        const lastIndex = groups.length - 1
        const simpleEnd = last ? y(last.summary.simpleAccuracy * 100) : 0
        const ralphEnd = last ? y(last.summary.ralphAccuracy * 100) : 0
        const labelEnds = last !== undefined && Math.abs(simpleEnd - ralphEnd) >= LABEL_CLEARANCE
        const maxChars = Math.max(6, Math.floor(band / 6.5))

        return (
          <svg width={width} height={HEIGHT} role="img" aria-label={`${title}: gráfico de linhas`}>
            {ticks.map((tick) => (
              <g key={tick}>
                <line className={styles.grid} x1={MARGIN.left} x2={plotRight} y1={y(tick)} y2={y(tick)} />
                <text className={styles.tick} x={MARGIN.left - 6} y={y(tick) + 3} textAnchor="end">
                  {tick}%
                </text>
              </g>
            ))}
            <line className={styles.axis} x1={MARGIN.left} x2={plotRight} y1={plotBottom} y2={plotBottom} />
            <path className={`${styles.line} ${styles.strokeSimple}`} d={path((group) => group.summary.simpleAccuracy)} />
            <path className={`${styles.line} ${styles.strokeRalph}`} d={path((group) => group.summary.ralphAccuracy)} />
            {groups.map((group, index) => {
              const s = group.summary
              const tooltip = (
                <TooltipBody
                  title={group.label}
                  rows={[
                    ['Pares', String(s.n)],
                    ['Simples', formatPercent(s.simpleAccuracy)],
                    ['Ralph', formatPercent(s.ralphAccuracy)],
                    ['Δ', formatPp(s.delta)],
                    ['Corrige / piora', `${s.recoveries} / ${s.regressions}`],
                  ]}
                />
              )
              return (
                <g key={group.key}>
                  <rect
                    className={styles.hit}
                    x={x(index) - band / 2}
                    y={MARGIN.top}
                    width={band}
                    height={plotBottom - MARGIN.top}
                    tabIndex={0}
                    aria-label={`${group.label}: simples ${formatPercent(s.simpleAccuracy)}, Ralph ${formatPercent(s.ralphAccuracy)}`}
                    onMouseMove={(event) => showTooltip(event, tooltip)}
                    onFocus={(event) => showTooltip(event, tooltip)}
                    onBlur={hideTooltip}
                  />
                  <g pointerEvents="none" className={s.n < lowN ? styles.faded : undefined}>
                    <circle className={`${styles.dot} ${styles.fillSimple}`} cx={x(index)} cy={y(s.simpleAccuracy * 100)} r={5} />
                    <circle className={`${styles.dot} ${styles.fillRalph}`} cx={x(index)} cy={y(s.ralphAccuracy * 100)} r={5} />
                  </g>
                  <text className={styles.label} x={x(index)} y={plotBottom + 14} textAnchor="middle" pointerEvents="none">
                    {clipLabel(group.label, maxChars)}
                  </text>
                  <text className={styles.tick} x={x(index)} y={plotBottom + 27} textAnchor="middle" pointerEvents="none">
                    n={s.n}
                  </text>
                </g>
              )
            })}
            {labelEnds ? (
              <g pointerEvents="none">
                <text className={styles.value} x={x(lastIndex) + 10} y={simpleEnd + 3}>
                  Simples
                </text>
                <text className={styles.value} x={x(lastIndex) + 10} y={ralphEnd + 3}>
                  Ralph
                </text>
              </g>
            ) : null}
          </svg>
        )
      }}
    </ChartFrame>
  )
}
