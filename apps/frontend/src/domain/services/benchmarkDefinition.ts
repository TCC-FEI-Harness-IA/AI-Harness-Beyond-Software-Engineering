import type { BenchmarkDefinition } from '@/domain/types/benchmarkSession'

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
  return benchmark.dataset === 'mmlu'
    ? `MMLU · generativo · ${benchmark.few_shot}-shot`
    : 'Vestibulares'
}
