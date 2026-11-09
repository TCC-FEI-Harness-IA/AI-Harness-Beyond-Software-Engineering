// Geometria dos gráficos da análise: escalas lineares, ticks "redondos" e corte de rótulos. Sem
// biblioteca de gráficos — tudo vira SVG simples nos componentes ao lado.

export type Scale = (value: number) => number

export function linearScale(domain: readonly [number, number], range: readonly [number, number]): Scale {
  const [d0, d1] = domain
  const [r0, r1] = range
  const span = d1 - d0
  return (value) => (span === 0 ? (r0 + r1) / 2 : r0 + ((value - d0) / span) * (r1 - r0))
}

/** Passo 1, 2, 2,5 ou 5 × 10ⁿ que gera por volta de `count` intervalos. */
export function niceStep(span: number, count: number): number {
  if (span <= 0) return 1
  const raw = span / count
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const normalized = raw / magnitude
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10
  return factor * magnitude
}

/** Ticks redondos cobrindo `[min, max]`; o domínio devolvido é estendido até o primeiro e o último tick. */
export function niceTicks(min: number, max: number, count = 4): { domain: [number, number]; ticks: number[] } {
  const step = niceStep(max - min, count)
  const start = Math.floor(min / step) * step
  const end = Math.ceil(max / step) * step
  const ticks: number[] = []
  // Arredondamento contra o acúmulo de erro de ponto flutuante (0,1 + 0,2…).
  for (let value = start; value <= end + step / 2; value += step) ticks.push(Math.round(value * 1e9) / 1e9)
  return { domain: [start, end], ticks }
}

/** Domínio simétrico em torno de zero (barras divergentes), nunca menor que `minimum`. */
export function symmetricDomain(values: readonly number[], minimum: number): { domain: [number, number]; ticks: number[] } {
  const extent = Math.max(minimum, ...values.map(Math.abs))
  const { domain } = niceTicks(0, extent, 2)
  const top = domain[1]
  return { domain: [-top, top], ticks: [-top, -top / 2, 0, top / 2, top] }
}

/** Corta o rótulo para caber em `maxChars`, com reticências. */
export function clipLabel(label: string, maxChars: number): string {
  return label.length <= maxChars ? label : `${label.slice(0, Math.max(1, maxChars - 1))}…`
}

/** Largura aproximada de texto de 11–12px, para posicionar rótulos sem medir no DOM. */
export function approxTextWidth(text: string, fontSize = 11): number {
  return text.length * fontSize * 0.58
}

export interface Box {
  x: number
  y: number
  width: number
  height: number
}

function overlaps(a: Box, b: Box): boolean {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
}

/**
 * Posiciona rótulos de pontos sem sobreposição: tenta à direita e depois à esquerda do ponto; quem
 * não couber fica sem rótulo (a dica e a tabela continuam mostrando o valor).
 */
export function placePointLabels(
  points: ReadonlyArray<{ x: number; y: number; text: string }>,
  bounds: { left: number; right: number },
  fontSize = 10,
): Array<{ x: number; y: number; anchor: 'start' | 'end' } | null> {
  const placed: Box[] = points.map((point) => ({ x: point.x - 7, y: point.y - 7, width: 14, height: 14 }))
  return points.map((point) => {
    const width = approxTextWidth(point.text, fontSize)
    const y = point.y - 8
    const candidates: Array<{ box: Box; x: number; anchor: 'start' | 'end' }> = [
      { box: { x: point.x + 9, y: y - fontSize, width, height: fontSize + 2 }, x: point.x + 9, anchor: 'start' },
      { box: { x: point.x - 9 - width, y: y - fontSize, width, height: fontSize + 2 }, x: point.x - 9, anchor: 'end' },
    ]
    const fit = candidates.find(
      ({ box }) => box.x >= bounds.left && box.x + box.width <= bounds.right && !placed.some((other) => overlaps(box, other)),
    )
    if (fit === undefined) return null
    placed.push(fit.box)
    return { x: fit.x, y, anchor: fit.anchor }
  })
}
