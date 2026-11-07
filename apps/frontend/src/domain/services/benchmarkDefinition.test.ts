import { describe, expect, it } from 'vitest'
import {
  benchmarkDatasetLabel,
  benchmarkLabel,
  isBenchmarkDatasetId,
  LEGACY_BENCHMARK,
} from './benchmarkDefinition'

describe('identificação do benchmark', () => {
  it('identifica vestibulares e protocolos MMLU separadamente', () => {
    expect(benchmarkLabel(LEGACY_BENCHMARK)).toBe('Vestibulares')
    expect(benchmarkLabel({ ...LEGACY_BENCHMARK, dataset: 'mmlu' })).toBe(
      'MMLU · generativo · 0-shot',
    )
    expect(
      benchmarkLabel({
        ...LEGACY_BENCHMARK,
        dataset: 'mmlu',
        few_shot: 5,
        protocol: 'generative_5shot',
      }),
    ).toBe('MMLU · generativo · 5-shot')
  })

  it('reconhece só os datasets que têm aba', () => {
    expect(isBenchmarkDatasetId('gpqa')).toBe(true)
    expect(isBenchmarkDatasetId('outro')).toBe(false)
    expect(isBenchmarkDatasetId(null)).toBe(false)
    expect(benchmarkDatasetLabel('vestibular')).toBe('Vestibulares')
  })
})
