import { type FocusEvent, type MouseEvent, type ReactNode, type RefObject, useCallback, useLayoutEffect, useRef, useState } from 'react'
import styles from './charts.module.css'

/** Largura usada antes da primeira medição (e no jsdom, que não mede layout). */
export const FALLBACK_WIDTH = 720

export type TooltipTrigger = MouseEvent<Element> | FocusEvent<Element>

export interface ChartRenderApi {
  width: number
  showTooltip: (event: TooltipTrigger, content: ReactNode) => void
  hideTooltip: () => void
}

interface TooltipState {
  x: number
  y: number
  content: ReactNode
}

function useMeasuredWidth(): [RefObject<HTMLDivElement>, number] {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(FALLBACK_WIDTH)
  useLayoutEffect(() => {
    const element = ref.current
    if (element === null) return undefined
    const measure = (): void => {
      const measured = element.clientWidth
      if (measured > 0) setWidth(measured)
    }
    measure()
    if (typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, width]
}

export interface ChartFrameProps {
  title: string
  /** Uma frase sobre como ler o gráfico. */
  description?: string
  legend?: ReactNode
  children: (api: ChartRenderApi) => ReactNode
}

/**
 * Moldura comum dos gráficos: título, legenda, largura responsiva e a dica flutuante que cada marca
 * abre ao receber o mouse ou o foco do teclado.
 */
export function ChartFrame({ title, description, legend, children }: ChartFrameProps): JSX.Element {
  const [plotRef, width] = useMeasuredWidth()
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)

  const showTooltip = useCallback((event: TooltipTrigger, content: ReactNode) => {
    const container = plotRef.current
    if (container === null) return
    const box = container.getBoundingClientRect()
    const target = (event.currentTarget as Element).getBoundingClientRect()
    const fromPointer = 'clientX' in event && event.clientX !== 0
    const x = fromPointer ? event.clientX - box.left : target.left + target.width / 2 - box.left
    const y = fromPointer ? event.clientY - box.top : target.top - box.top
    setTooltip({ x, y, content })
  }, [plotRef])
  const hideTooltip = useCallback(() => setTooltip(null), [])

  return (
    <figure className={styles.frame}>
      <figcaption className={styles.caption}>
        <span className={styles.title}>{title}</span>
        {description ? <span className={styles.description}>{description}</span> : null}
      </figcaption>
      {legend}
      <div ref={plotRef} className={styles.plot} onMouseLeave={hideTooltip}>
        {children({ width, showTooltip, hideTooltip })}
        {tooltip ? (
          <div
            className={styles.tooltip}
            role="tooltip"
            style={{
              left: Math.min(Math.max(tooltip.x, 90), Math.max(90, width - 90)),
              top: tooltip.y,
            }}
          >
            {tooltip.content}
          </div>
        ) : null}
      </div>
    </figure>
  )
}

/** Legenda de séries: amostra de cor ao lado de um rótulo em cor de texto. */
export function ChartLegend({ items }: { items: ReadonlyArray<{ label: string; swatchClass: string | undefined }> }): JSX.Element {
  return (
    <ul className={styles.legend} aria-label="Legenda">
      {items.map((item) => (
        <li key={item.label}>
          <span className={`${styles.swatch} ${item.swatchClass ?? ''}`} aria-hidden="true" />
          {item.label}
        </li>
      ))}
    </ul>
  )
}

/** Conteúdo padronizado da dica: título e linhas "rótulo: valor". */
export function TooltipBody({ title, rows }: { title: string; rows: ReadonlyArray<[string, string]> }): JSX.Element {
  return (
    <>
      <strong className={styles.tooltipTitle}>{title}</strong>
      {rows.map(([label, value]) => (
        <span key={label} className={styles.tooltipRow}>
          <span>{label}</span>
          <span>{value}</span>
        </span>
      ))}
    </>
  )
}
