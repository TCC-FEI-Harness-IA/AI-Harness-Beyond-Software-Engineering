import { useEffect, useMemo, useRef, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { cx } from '@/components/cx'
import { formatTokens } from '@/domain/services/formatters'
import { buildContextSeries } from '@/domain/services/graphLayout'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import styles from './ContextMeter.module.css'

export interface ContextMeterProps {
  steps: ThinkingStep[]
}

const STORAGE_KEY = 'tcc.contextMeter.collapsed'
const CONTEXT_ID_VISIBLE_CHARS = 7

// localStorage pode lançar em janela privada — o painel só perde a memória de estado, nunca
// deixa de funcionar (mesma tolerância de `ThemeContext`).
function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function persistCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
  } catch {
    // Acesso bloqueado — segue sem persistir.
  }
}

function linePath(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) return ''
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${100 - point.y}`).join(' ')
}

/**
 * ③ Janela de contexto — o painel que prova o *Fresh Context* (README, FASE 06, seção 6). A
 * série `context_size` despenca a zero a cada `reset` (a serra dentada); `total_tokens` é
 * monotônica. Todo cálculo de ponto vem de `graphLayout.buildContextSeries`, testável sem DOM;
 * este componente só desenha o `viewBox` normalizado.
 */
export function ContextMeter({ steps }: ContextMeterProps): JSX.Element {
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const series = useMemo(() => buildContextSeries(steps), [steps])

  useEffect(() => {
    persistCollapsed(collapsed)
  }, [collapsed])

  const contextPath = linePath(series.points.map((point) => ({ x: point.xPercent, y: point.contextYPercent })))
  const totalPath = linePath(series.points.map((point) => ({ x: point.xPercent, y: point.totalYPercent })))

  const totalAccumulated = series.points[series.points.length - 1]?.totalTokens ?? 0
  const ariaLabel = `Gráfico da janela de contexto: ${series.resetIndices.length} reinicializações de contexto, pico de ${formatTokens(series.maxContextSize)} tokens na janela e total acumulado de ${formatTokens(totalAccumulated)} tokens na sessão.`

  function handleMove(event: ReactMouseEvent<SVGSVGElement>): void {
    const svg = svgRef.current
    if (!svg || series.points.length === 0) return
    const rect = svg.getBoundingClientRect()
    const ratio = rect.width === 0 ? 0 : (event.clientX - rect.left) / rect.width
    const index = Math.round(ratio * (series.points.length - 1))
    setHoverIndex(Math.min(Math.max(index, 0), series.points.length - 1))
  }

  const hoverPoint = hoverIndex !== null ? series.points[hoverIndex] : null

  return (
    <div className={styles.wrapper}>
      <button
        type="button"
        className={styles.toggle}
        onClick={() => setCollapsed((value) => !value)}
        aria-expanded={!collapsed}
      >
        <span className={cx(styles.chevron, !collapsed && styles.chevronOpen)} aria-hidden="true">
          ▸
        </span>
        Janela de contexto
      </button>

      {!collapsed ? (
        <div className={styles.body}>
          {series.points.length > 0 ? (
            <>
              <svg
                ref={svgRef}
                className={styles.chart}
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                role="img"
                aria-label={ariaLabel}
                onMouseMove={handleMove}
                onMouseLeave={() => setHoverIndex(null)}
              >
                <path className={styles.area} d={`${contextPath} L 100 100 L 0 100 Z`} />
                <path className={styles.lineTotal} d={totalPath} />
                <path className={styles.lineContext} d={contextPath} />
                {series.resetIndices.map((index) => {
                  const point = series.points[index]
                  if (!point) return null
                  return (
                    <line
                      key={point.stepId}
                      className={styles.resetMark}
                      x1={point.xPercent}
                      x2={point.xPercent}
                      y1="0"
                      y2="100"
                    />
                  )
                })}
                {hoverPoint ? (
                  <line className={styles.hoverGuide} x1={hoverPoint.xPercent} x2={hoverPoint.xPercent} y1="0" y2="100" />
                ) : null}
              </svg>

              <p className={styles.tooltip} aria-live="polite">
                {hoverPoint
                  ? `${hoverPoint.taskId} · contexto ${formatTokens(hoverPoint.contextSize)} tokens · total ${formatTokens(hoverPoint.totalTokens)} tokens · ${hoverPoint.contextId.slice(0, CONTEXT_ID_VISIBLE_CHARS)}`
                  : 'Passe o mouse sobre o gráfico para ver os valores de cada passo.'}
              </p>
            </>
          ) : (
            <p className={styles.tooltip}>Nenhum passo ainda.</p>
          )}

          <p className={styles.caption}>
            O contexto é reinicializado a cada tarefa (Fresh Context); o consumo acumulado da sessão continua
            crescendo.
          </p>
        </div>
      ) : null}
    </div>
  )
}
