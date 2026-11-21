import type {
  BenchmarkDatasetId,
  BenchmarkDefinition,
  GPQASubset,
} from '@/domain/types/benchmarkSession'

export const GPQA_SUBSET_LABELS: Record<GPQASubset, string> = {
  diamond: 'Diamond',
  main: 'Main',
  extended: 'Extended',
}

export const LEGACY_BENCHMARK: BenchmarkDefinition = {
  dataset: 'vestibular',
  revision: 'vestibular-v1',
  protocol: 'generative_0shot',
  split: 'test',
  few_shot: 0,
  subjects: [],
  sample_seed: null,
}

export function benchmarkLabel(benchmark: BenchmarkDefinition): string {
  if (benchmark.dataset === 'gpqa') {
    return `GPQA ${GPQA_SUBSET_LABELS[benchmark.split as GPQASubset]} · generativo · 0-shot`
  }
  return benchmark.dataset === 'mmlu'
    ? `MMLU · generativo · ${benchmark.few_shot}-shot`
    : 'Vestibulares'
}

const VESTIBULAR_SUBJECT_LABELS: Record<string, string> = {
  HISTORIA: 'História',
  GEOGRAFIA: 'Geografia',
  FILOSOFIA_SOCIOLOGIA: 'Filosofia e Sociologia',
  BIOLOGIA: 'Biologia',
  MATEMATICA: 'Matemática',
  QUIMICA: 'Química',
  FISICA: 'Física',
}

export function benchmarkSubjectLabel(subject: string): string {
  return VESTIBULAR_SUBJECT_LABELS[subject] ?? subject.replaceAll('_', ' ')
}

/** Benchmarks disponíveis, na ordem das abas da página do BenchMark. */
export const BENCHMARK_DATASETS: ReadonlyArray<{
  id: BenchmarkDatasetId
  label: string
  description: string
}> = [
  {
    id: 'vestibular',
    label: 'Vestibulares',
    description: 'Questões de vestibulares brasileiros, em português, na ordem do dataset.',
  },
  {
    id: 'mmlu',
    label: 'MMLU',
    description: 'MMLU em inglês, com quatro alternativas e protocolo 0-shot ou 5-shot.',
  },
  {
    id: 'gpqa',
    label: 'GPQA',
    description:
      'Biologia, química e física em nível de pós-graduação, em inglês, nas variantes Diamond, ' +
      'Main e Extended.',
  },
]

export function isBenchmarkDatasetId(value: string | null): value is BenchmarkDatasetId {
  return BENCHMARK_DATASETS.some((dataset) => dataset.id === value)
}

export function benchmarkDatasetLabel(benchmark: BenchmarkDatasetId): string {
  return BENCHMARK_DATASETS.find((dataset) => dataset.id === benchmark)?.label ?? benchmark
}
