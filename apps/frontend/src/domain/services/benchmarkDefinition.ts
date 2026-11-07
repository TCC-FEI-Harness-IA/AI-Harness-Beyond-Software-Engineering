import type { BenchmarkDatasetId, BenchmarkDefinition } from '@/domain/types/benchmarkSession'

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
  if (benchmark.dataset === 'gpqa') return 'GPQA Diamond · generativo · 0-shot'
  return benchmark.dataset === 'mmlu'
    ? `MMLU · generativo · ${benchmark.few_shot}-shot`
    : 'Vestibulares'
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
    description: 'GPQA Diamond: biologia, química e física em nível de pós-graduação, em inglês.',
  },
]

export function isBenchmarkDatasetId(value: string | null): value is BenchmarkDatasetId {
  return BENCHMARK_DATASETS.some((dataset) => dataset.id === value)
}

export function benchmarkDatasetLabel(benchmark: BenchmarkDatasetId): string {
  return BENCHMARK_DATASETS.find((dataset) => dataset.id === benchmark)?.label ?? benchmark
}
