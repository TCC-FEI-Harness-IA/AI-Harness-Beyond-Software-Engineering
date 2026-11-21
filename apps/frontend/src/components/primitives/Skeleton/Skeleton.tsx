import type { CSSProperties } from 'react'
import styles from './Skeleton.module.css'

export interface SkeletonProps {
  width?: string
  height?: string
  radius?: string
  /** Quando > 1, gera várias barras de larguras levemente diferentes (a última mais curta),
   * simulando uma linha de texto sendo carregada. */
  lines?: number
}

// Larguras decrescentes para as linhas de um bloco de texto simulado — a última é sempre
// mais curta, o que é o detalhe que faz o esqueleto parecer texto de verdade.
const LINE_WIDTHS = ['100%', '96%', '88%', '92%', '70%']

function lineWidth(index: number, total: number): string {
  if (index === total - 1 && total > 1) return '60%'
  return LINE_WIDTHS[index % LINE_WIDTHS.length] ?? '100%'
}

/** Placeholder animado (*shimmer*) para conteúdo em carregamento — nunca um spinner de tela inteira. */
export function Skeleton({
  width = '100%',
  height = '1em',
  radius = 'var(--radius-sm)',
  lines = 1,
}: SkeletonProps): JSX.Element {
  if (lines > 1) {
    return (
      <span className={styles.lines} aria-hidden="true">
        {Array.from({ length: lines }, (_, index) => (
          <span
            key={index}
            className={styles.block}
            style={
              {
                '--sk-width': lineWidth(index, lines),
                '--sk-height': height,
                '--sk-radius': radius,
              } as CSSProperties
            }
          />
        ))}
      </span>
    )
  }

  return (
    <span
      className={styles.block}
      aria-hidden="true"
      style={{ '--sk-width': width, '--sk-height': height, '--sk-radius': radius } as CSSProperties}
    />
  )
}
