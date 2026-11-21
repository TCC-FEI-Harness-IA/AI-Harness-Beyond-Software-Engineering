import { PAIR_OUTCOME_LABEL, type PairedSummary, type PairOutcome } from '@/domain/services/benchmarkAnalysis'
import { formatPercent } from '@/domain/services/formatters'
import { ChartFrame, ChartLegend, TooltipBody } from './ChartFrame'
import styles from './charts.module.css'

const HEIGHT = 220
const NODE_WIDTH = 12
const NODE_GAP = 14
const LABEL_SPACE = 118
/** Faixas com contagem positiva nunca ficam mais finas que isto, para continuarem visíveis. */
const MIN_BAND = 3

const OUTCOME_CLASS: Record<PairOutcome, string | undefined> = {
  both_correct: styles.fillBothCorrect,
  ralph_recovers: styles.fillRecovers,
  ralph_regresses: styles.fillRegresses,
  both_wrong: styles.fillBothWrong,
}

const SWATCH_CLASS: Record<PairOutcome, string | undefined> = {
  both_correct: styles.swatchBothCorrect,
  ralph_recovers: styles.swatchRecovers,
  ralph_regresses: styles.swatchRegresses,
  both_wrong: styles.swatchBothWrong,
}

interface Band {
  outcome: PairOutcome
  count: number
  thickness: number
  /** Topo da faixa na coluna da inferência simples e na do Ralph. */
  fromY: number
  toY: number
}

/**
 * Posiciona as quatro faixas: à esquerda, simples acerta (em cima) e erra; à direita, Ralph acerta e
 * erra. As faixas que cruzam o meio são exatamente as que o Ralph corrige e as que piora.
 */
export function layoutOutcomeFlow(s: PairedSummary, height: number): { bands: Band[]; nodes: Record<'simpleRight' | 'simpleWrong' | 'ralphRight' | 'ralphWrong', { y: number; height: number }> } {
  const available = height - NODE_GAP
  const thick = (count: number): number => (count === 0 ? 0 : Math.max(MIN_BAND, (count / Math.max(1, s.n)) * available))
  const t = {
    both_correct: thick(s.bothCorrect),
    ralph_regresses: thick(s.regressions),
    ralph_recovers: thick(s.recoveries),
    both_wrong: thick(s.bothWrong),
  }
  const simpleRight = t.both_correct + t.ralph_regresses
  const ralphRight = t.both_correct + t.ralph_recovers
  const simpleWrongTop = simpleRight + NODE_GAP
  const ralphWrongTop = ralphRight + NODE_GAP
  const bands: Band[] = [
    { outcome: 'both_correct', count: s.bothCorrect, thickness: t.both_correct, fromY: 0, toY: 0 },
    { outcome: 'ralph_regresses', count: s.regressions, thickness: t.ralph_regresses, fromY: t.both_correct, toY: ralphWrongTop },
    { outcome: 'ralph_recovers', count: s.recoveries, thickness: t.ralph_recovers, fromY: simpleWrongTop, toY: t.both_correct },
    {
      outcome: 'both_wrong',
      count: s.bothWrong,
      thickness: t.both_wrong,
      fromY: simpleWrongTop + t.ralph_recovers,
      toY: ralphWrongTop + t.ralph_regresses,
    },
  ]
  return {
    bands,
    nodes: {
      simpleRight: { y: 0, height: simpleRight },
      simpleWrong: { y: simpleWrongTop, height: t.ralph_recovers + t.both_wrong },
      ralphRight: { y: 0, height: ralphRight },
      ralphWrong: { y: ralphWrongTop, height: t.ralph_regresses + t.both_wrong },
    },
  }
}

function bandPath(x0: number, x1: number, fromY: number, toY: number, thickness: number): string {
  const mid = (x0 + x1) / 2
  return [
    `M${x0},${fromY}`,
    `C${mid},${fromY} ${mid},${toY} ${x1},${toY}`,
    `V${toY + thickness}`,
    `C${mid},${toY + thickness} ${mid},${fromY + thickness} ${x0},${fromY + thickness}`,
    'Z',
  ].join(' ')
}

/** Para onde vão as respostas da simples quando o Ralph responde a mesma questão. */
export function OutcomeFlowChart({ summary: s }: { summary: PairedSummary }): JSX.Element {
  const legend = (
    <ChartLegend
      items={(['both_correct', 'ralph_recovers', 'ralph_regresses', 'both_wrong'] as const).map((outcome) => ({
        label: PAIR_OUTCOME_LABEL[outcome],
        swatchClass: SWATCH_CLASS[outcome],
      }))}
    />
  )
  return (
    <ChartFrame
      title="Simples → Ralph"
      description="Cada faixa liga a resposta da inferência simples à do Ralph na mesma questão. As faixas que cruzam são as que o Ralph corrige e as que piora."
      legend={legend}
    >
      {({ width, showTooltip, hideTooltip }) => {
        const { bands, nodes } = layoutOutcomeFlow(s, HEIGHT)
        const total = Math.max(nodes.simpleWrong.y + nodes.simpleWrong.height, nodes.ralphWrong.y + nodes.ralphWrong.height)
        const leftX = LABEL_SPACE
        const rightX = Math.max(leftX + 80, width - LABEL_SPACE - NODE_WIDTH)
        const share = (count: number): string => formatPercent(s.n === 0 ? 0 : count / s.n)
        const nodeLabels: Array<{ key: string; x: number; anchor: 'start' | 'end'; node: { y: number; height: number }; title: string; count: number }> = [
          { key: 'sr', x: leftX - 8, anchor: 'end', node: nodes.simpleRight, title: 'Simples acerta', count: s.simpleCorrect },
          { key: 'sw', x: leftX - 8, anchor: 'end', node: nodes.simpleWrong, title: 'Simples erra', count: s.n - s.simpleCorrect },
          { key: 'rr', x: rightX + NODE_WIDTH + 8, anchor: 'start', node: nodes.ralphRight, title: 'Ralph acerta', count: s.ralphCorrect },
          { key: 'rw', x: rightX + NODE_WIDTH + 8, anchor: 'start', node: nodes.ralphWrong, title: 'Ralph erra', count: s.n - s.ralphCorrect },
        ]
        return (
          <svg width={width} height={total + 20} role="img" aria-label="Fluxo dos desfechos da inferência simples para o Ralph Loop">
            {bands
              .filter((band) => band.count > 0)
              .map((band) => {
                const tooltip = (
                  <TooltipBody
                    title={PAIR_OUTCOME_LABEL[band.outcome]}
                    rows={[
                      ['Questões', String(band.count)],
                      ['Do total', share(band.count)],
                    ]}
                  />
                )
                return (
                  <path
                    key={band.outcome}
                    className={`${styles.band} ${OUTCOME_CLASS[band.outcome] ?? ''}`}
                    d={bandPath(leftX + NODE_WIDTH, rightX, band.fromY, band.toY, band.thickness)}
                    tabIndex={0}
                    aria-label={`${PAIR_OUTCOME_LABEL[band.outcome]}: ${band.count}`}
                    onMouseMove={(event) => showTooltip(event, tooltip)}
                    onFocus={(event) => showTooltip(event, tooltip)}
                    onBlur={hideTooltip}
                  />
                )
              })}
            {nodeLabels.map(({ key, x, anchor, node, title, count }) => (
              <g key={key} pointerEvents="none">
                {node.height > 0 ? (
                  <rect
                    className={styles.fillInk}
                    x={anchor === 'end' ? leftX : rightX}
                    y={node.y}
                    width={NODE_WIDTH}
                    height={node.height}
                    rx={3}
                  />
                ) : null}
                <text className={styles.labelStrong} x={x} y={node.y + Math.max(node.height, 12) / 2} textAnchor={anchor}>
                  {title}
                </text>
                <text className={styles.value} x={x} y={node.y + Math.max(node.height, 12) / 2 + 13} textAnchor={anchor}>
                  {count} · {share(count)}
                </text>
              </g>
            ))}
          </svg>
        )
      }}
    </ChartFrame>
  )
}
