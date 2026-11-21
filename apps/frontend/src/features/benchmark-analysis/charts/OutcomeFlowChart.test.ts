import { describe, expect, it } from 'vitest'
import { summarizePairs } from '@/domain/services/benchmarkAnalysis'
import { layoutOutcomeFlow } from './OutcomeFlowChart'

describe('layoutOutcomeFlow', () => {
  it('empilha as faixas sem lacunas e dá espessura mínima às pequenas', () => {
    const summary = { ...summarizePairs([]), n: 100, bothCorrect: 90, regressions: 1, recoveries: 4, bothWrong: 5 }
    const { bands, nodes } = layoutOutcomeFlow(summary, 214)
    const [bothCorrect, regress, recover, bothWrong] = bands
    expect(bothCorrect?.thickness).toBeCloseTo(180)
    expect(regress?.thickness).toBe(3)
    expect(regress?.fromY).toBeCloseTo(180)
    expect(recover?.toY).toBeCloseTo(180)
    expect(nodes.simpleRight.height).toBeCloseTo(183)
    expect(nodes.simpleWrong.y).toBeCloseTo(197)
    expect(bothWrong?.fromY).toBeCloseTo(nodes.simpleWrong.y + (recover?.thickness ?? 0))
    expect(nodes.ralphWrong.height).toBeCloseTo(3 + 10)
  })

  it('não desenha faixa para desfecho vazio', () => {
    const { bands } = layoutOutcomeFlow({ ...summarizePairs([]), n: 2, bothCorrect: 2 }, 100)
    expect(bands.filter((band) => band.thickness > 0)).toHaveLength(1)
  })
})
