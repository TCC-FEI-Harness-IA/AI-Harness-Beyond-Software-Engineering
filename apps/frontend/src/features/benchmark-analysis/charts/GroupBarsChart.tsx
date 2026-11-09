import type { ReactNode } from 'react'
import { type AnalysisGroup, formatPp, formatPValue } from '@/domain/services/benchmarkAnalysis'
import { formatPercent } from '@/domain/services/formatters'
import { ChartFrame, ChartLegend, type ChartRenderApi, TooltipBody } from './ChartFrame'
import { approxTextWidth, clipLabel, linearScale, niceTicks, symmetricDomain } from './scales'
import styles from './charts.module.css'

export type GroupChartMode = 'delta' | 'accuracy' | 'counts'

const AXIS_HEIGHT = 20
const ROW_HEIGHT = 24
const BAR_THICKNESS = 12
const VALUE_GUTTER = 64
const RADIUS = 4

/** Barra horizontal com a ponta de dados arredondada e a base reta (no eixo). */
export function horizontalBar(base: number, tip: number, y: number, height: number): string {
  const direction = tip >= base ? 1 : -1
  const length = Math.abs(tip - base)
  const r = Math.min(RADIUS, length, height / 2)
  const end = tip - direction * r
  return [
    `M${base},${y}`,
    `H${end}`,
    `Q${tip},${y} ${tip},${y + r}`,
    `V${y + height - r}`,
    `Q${tip},${y + height} ${end},${y + height}`,
    `H${base}`,
    'Z',
  ].join(' ')
}

function groupTooltip(group: AnalysisGroup): ReactNode {
  const s = group.summary
  return (
    <TooltipBody
      title={group.label}
      rows={[
        ['Pares', String(s.n)],
        ['Simples', formatPercent(s.simpleAccuracy)],
        ['Ralph', formatPercent(s.ralphAccuracy)],
        ['Δ', formatPp(s.delta)],
        ['Ralph corrige', String(s.recoveries)],
        ['Ralph piora', String(s.regressions)],
        ['p (McNemar)', formatPValue(s.mcnemarPValue)],
      ]}
    />
  )
}

const LEGENDS: Record<GroupChartMode, ReadonlyArray<{ label: string; swatchClass: string | undefined }>> = {
  delta: [
    { label: 'Ralph melhor', swatchClass: styles.swatchRalph },
    { label: 'Simples melhor', swatchClass: styles.swatchSimple },
  ],
  accuracy: [
    { label: 'Inferência simples', swatchClass: styles.swatchSimple },
    { label: 'Ralph Loop', swatchClass: styles.swatchRalph },
  ],
  counts: [
    { label: 'Ralph piora (simples acertou, Ralph errou)', swatchClass: styles.swatchRegresses },
    { label: 'Ralph corrige (simples errou, Ralph acertou)', swatchClass: styles.swatchRecovers },
  ],
}

const DESCRIPTIONS: Record<GroupChartMode, string> = {
  delta: 'Diferença de acurácia (Ralph − simples) em pontos percentuais. À direita do zero, o Ralph acerta mais.',
  accuracy: 'Acurácia de cada fluxo no mesmo eixo (ampliado para mostrar a diferença); a haste liga os dois fluxos.',
  counts: 'Questões que o Ralph piora (à esquerda) e corrige (à direita); o saldo líquido fica na ponta.',
}

export interface GroupBarsChartProps {
  title: string
  groups: readonly AnalysisGroup[]
  mode: GroupChartMode
  /** Grupos com menos pares que isto aparecem esmaecidos. */
  lowN: number
}

/** Uma linha por grupo, com uma das três leituras da comparação pareada. */
export function GroupBarsChart({ title, groups, mode, lowN }: GroupBarsChartProps): JSX.Element {
  return (
    <ChartFrame title={title} description={DESCRIPTIONS[mode]} legend={<ChartLegend items={LEGENDS[mode]} />}>
      {(api) => <GroupBarsSvg api={api} groups={groups} mode={mode} lowN={lowN} title={title} />}
    </ChartFrame>
  )
}

function GroupBarsSvg({
  api,
  groups,
  mode,
  lowN,
  title,
}: {
  api: ChartRenderApi
  groups: readonly AnalysisGroup[]
  mode: GroupChartMode
  lowN: number
  title: string
}): JSX.Element {
  const { width, showTooltip, hideTooltip } = api
  const labelWidth = Math.min(200, Math.max(110, width * 0.3))
  const left = labelWidth + 8
  const right = Math.max(left + 80, width - VALUE_GUTTER)
  const height = AXIS_HEIGHT + groups.length * ROW_HEIGHT + 4
  const maxChars = Math.floor(labelWidth / approxTextWidth('m'))

  let ticks: number[]
  let x: (value: number) => number
  let tickLabel: (value: number) => string
  if (mode === 'delta') {
    const symmetric = symmetricDomain(groups.map((group) => group.summary.delta * 100), 5)
    ticks = symmetric.ticks
    x = linearScale(symmetric.domain, [left, right])
    tickLabel = (value) => `${value > 0 ? '+' : ''}${Math.round(value * 10) / 10}`
  } else if (mode === 'counts') {
    const maximum = Math.max(1, ...groups.map((group) => Math.max(group.summary.recoveries, group.summary.regressions)))
    const nice = niceTicks(0, maximum, 2)
    const top = nice.domain[1]
    ticks = [...nice.ticks.slice(1).map((tick) => -tick).reverse(), ...nice.ticks]
    x = linearScale([-top, top], [left, right])
    tickLabel = (value) => String(Math.abs(value))
  } else {
    const lowest = Math.min(...groups.flatMap((group) => [group.summary.simpleAccuracy, group.summary.ralphAccuracy]))
    const nice = niceTicks(Math.max(0, lowest * 100 - 5), 100, 4)
    ticks = nice.ticks.filter((tick) => tick <= 100)
    x = linearScale([nice.domain[0], 100], [left, right])
    tickLabel = (value) => `${value}%`
  }
  const zero = x(0)

  return (
    <svg width={width} height={height} role="img" aria-label={`${title}: gráfico`}>
      {ticks.map((tick) => (
        <g key={tick}>
          <line className={mode !== 'accuracy' && tick === 0 ? styles.zero : styles.grid} x1={x(tick)} x2={x(tick)} y1={AXIS_HEIGHT - 4} y2={height} />
          <text className={styles.tick} x={x(tick)} y={10} textAnchor="middle">
            {tickLabel(tick)}
          </text>
        </g>
      ))}
      {groups.map((group, index) => {
        const s = group.summary
        const top = AXIS_HEIGHT + index * ROW_HEIGHT
        const middle = top + ROW_HEIGHT / 2
        const barY = middle - BAR_THICKNESS / 2
        let marks: ReactNode
        if (mode === 'delta') {
          const tip = x(s.delta * 100)
          marks = (
            <>
              {s.delta !== 0 ? (
                <path className={s.delta > 0 ? styles.fillRalph : styles.fillSimple} d={horizontalBar(zero, tip, barY, BAR_THICKNESS)} />
              ) : null}
              <text className={styles.value} x={right + 6} y={middle + 3}>
                {formatPp(s.delta)}
              </text>
            </>
          )
        } else if (mode === 'counts') {
          marks = (
            <>
              {s.regressions > 0 ? (
                <path className={styles.fillRegresses} d={horizontalBar(zero - 1, x(-s.regressions), barY, BAR_THICKNESS)} />
              ) : null}
              {s.recoveries > 0 ? (
                <path className={styles.fillRecovers} d={horizontalBar(zero + 1, x(s.recoveries), barY, BAR_THICKNESS)} />
              ) : null}
              <text className={styles.value} x={right + 6} y={middle + 3}>
                {`${s.netGain > 0 ? '+' : ''}${s.netGain} líquido`}
              </text>
            </>
          )
        } else {
          const simpleX = x(s.simpleAccuracy * 100)
          const ralphX = x(s.ralphAccuracy * 100)
          marks = (
            <>
              <line className={styles.crosshair} x1={simpleX} x2={ralphX} y1={middle} y2={middle} />
              <circle className={`${styles.dot} ${styles.fillSimple}`} cx={simpleX} cy={middle} r={5} />
              <circle className={`${styles.dot} ${styles.fillRalph}`} cx={ralphX} cy={middle} r={5} />
              <text className={styles.value} x={right + 6} y={middle + 3}>
                {formatPp(s.delta)}
              </text>
            </>
          )
        }
        return (
          <g key={group.key} className={s.n < lowN ? styles.faded : undefined}>
            <rect
              className={styles.hit}
              x={0}
              y={top}
              width={width}
              height={ROW_HEIGHT}
              tabIndex={0}
              aria-label={`${group.label}: Δ ${formatPp(s.delta)}, n ${s.n}`}
              onMouseMove={(event) => showTooltip(event, groupTooltip(group))}
              onFocus={(event) => showTooltip(event, groupTooltip(group))}
              onBlur={hideTooltip}
            />
            <text className={styles.label} x={labelWidth} y={middle + 4} textAnchor="end" pointerEvents="none">
              {clipLabel(group.label, maxChars)}
            </text>
            <g pointerEvents="none">{marks}</g>
          </g>
        )
      })}
    </svg>
  )
}
