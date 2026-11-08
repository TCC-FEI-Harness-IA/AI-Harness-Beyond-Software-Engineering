import { describe, expect, it } from 'vitest'
import {
  benchmarkDatasetLabel,
  benchmarkLabel,
  benchmarkSubjectLabel,
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

  it('um identificador fora da lista, vindo de dados antigos, é exibido como veio', () => {
    expect(benchmarkDatasetLabel('desconhecido' as Parameters<typeof benchmarkDatasetLabel>[0])).toBe('desconhecido')
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
