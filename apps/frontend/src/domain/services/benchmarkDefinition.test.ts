import { describe, expect, it } from 'vitest'
import { benchmarkLabel, benchmarkSubjectLabel, LEGACY_BENCHMARK } from './benchmarkDefinition'

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
})

it.each([
  ['diamond', 'Diamond'],
  ['main', 'Main'],
  ['extended', 'Extended'],
])('identifica GPQA %s', (split, label) => {
  expect(benchmarkLabel({ ...LEGACY_BENCHMARK, dataset: 'gpqa', split })).toBe(
    `GPQA ${label} · generativo · 0-shot`,
  )
})

it.each([
  ['HISTORIA', 'História'],
  ['GEOGRAFIA', 'Geografia'],
  ['FILOSOFIA_SOCIOLOGIA', 'Filosofia e Sociologia'],
  ['BIOLOGIA', 'Biologia'],
  ['MATEMATICA', 'Matemática'],
  ['QUIMICA', 'Química'],
  ['FISICA', 'Física'],
  ['college_physics', 'college physics'],
])('apresenta o nome da matéria %s', (id, label) => {
  expect(benchmarkSubjectLabel(id)).toBe(label)
})
