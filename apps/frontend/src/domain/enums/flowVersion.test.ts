import { describe, expect, it } from 'vitest'
import { FLOW_VERSION, isFlowVersion } from './flowVersion'

describe('FLOW_VERSION', () => {
  it('declara a versão antiga (A.3 = aprendizados) e a atual (A.3 = validação, A.4 = aprendizados)', () => {
    expect(FLOW_VERSION.LEGACY).toBe(1)
    expect(FLOW_VERSION.VALIDATED_PLANNING).toBe(2)
  })

  it('só reconhece os inteiros das versões conhecidas', () => {
    expect(isFlowVersion(1)).toBe(true)
    expect(isFlowVersion(2)).toBe(true)
    for (const value of [0, 3, '2', null, undefined, 2.5, true]) {
      expect(isFlowVersion(value)).toBe(false)
    }
  })
})
