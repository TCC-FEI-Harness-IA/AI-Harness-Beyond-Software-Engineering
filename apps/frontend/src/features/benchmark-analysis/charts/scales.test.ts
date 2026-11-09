import { describe, expect, it } from 'vitest'
import { clipLabel, linearScale, niceStep, niceTicks, placePointLabels, symmetricDomain } from './scales'

describe('escalas', () => {
  it('linearScale interpola e centraliza um domínio vazio', () => {
    const scale = linearScale([0, 10], [100, 200])
    expect(scale(5)).toBe(150)
    expect(linearScale([3, 3], [0, 10])(3)).toBe(5)
  })

  it('niceStep escolhe passos 1, 2, 2,5, 5 e 10', () => {
    expect(niceStep(0, 4)).toBe(1)
    expect(niceStep(4, 4)).toBe(1)
    expect(niceStep(8, 4)).toBe(2)
    expect(niceStep(10, 4)).toBe(2.5)
    expect(niceStep(16, 4)).toBe(5)
    expect(niceStep(28, 4)).toBe(10)
  })

  it('niceTicks estende o domínio até ticks redondos', () => {
    expect(niceTicks(83, 100, 4)).toEqual({ domain: [80, 100], ticks: [80, 85, 90, 95, 100] })
    expect(niceTicks(0, 0.3, 3).ticks).toEqual([0, 0.1, 0.2, 0.3])
  })

  it('symmetricDomain respeita o mínimo e cobre o maior valor absoluto', () => {
    expect(symmetricDomain([1, -2], 5)).toEqual({ domain: [-5, 5], ticks: [-5, -2.5, 0, 2.5, 5] })
    expect(symmetricDomain([-17], 5).domain).toEqual([-20, 20])
  })

  it('clipLabel corta com reticências', () => {
    expect(clipLabel('curto', 10)).toBe('curto')
    expect(clipLabel('um rótulo comprido', 6)).toBe('um ró…')
  })

  it('placePointLabels evita sobreposição e as bordas', () => {
    const placed = placePointLabels(
      [
        { x: 100, y: 100, text: 'primeiro' },
        { x: 104, y: 102, text: 'segundo' },
        { x: 300, y: 100, text: 'no limite' },
      ],
      { left: 0, right: 320 },
    )
    expect(placed[0]).toEqual({ x: 109, y: 92, anchor: 'start' })
    expect(placed[1]).toBeNull()
    expect(placed[2]).toEqual({ x: 291, y: 92, anchor: 'end' })
    expect(placePointLabels([{ x: 5, y: 5, text: 'sem espaço nenhum' }], { left: 0, right: 40 })).toEqual([null])
  })
})
