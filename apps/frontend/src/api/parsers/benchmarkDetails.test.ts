import { describe, expect, it } from 'vitest'
import { parseBenchmarkDetails } from './benchmarkDetails'

describe('BenchmarkDetails', () => {
  it('sessões antigas ou comuns recebem false e demais campos nulos', () => {
    for (const raw of [undefined, null, {}]) {
      const { is_banchmark, ...rest } = parseBenchmarkDetails(raw)
      expect(is_banchmark).toBe(false)
      expect(Object.values(rest).every((value) => value === null)).toBe(true)
    }
  })

  it('preserva resultados corretos e errados, modo, falha e duração', () => {
    const result = parseBenchmarkDetails({
      is_banchmark: true, question_name: 'Q1', inference_mode: 'ralph', run_id: 'r1',
      is_correct: false, duration_seconds: 3.5, error: 'limite', selected_alternative: 'B',
    })
    expect(result.is_correct).toBe(false)
    expect(result.inference_mode).toBe('ralph')
    expect(result.duration_seconds).toBe(3.5)
    expect(result.error).toBe('limite')
  })

  it.each([[], 'invalid', { is_banchmark: 'false' }, { inference_mode: 'outro' },
    { is_correct: 1 }, { duration_seconds: 'um' }])('recusa dados inválidos: %j', (raw) => {
    expect(() => parseBenchmarkDetails(raw)).toThrow()
  })
})
