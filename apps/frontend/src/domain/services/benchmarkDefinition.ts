import type { BenchmarkDefinition, GPQASubset } from '@/domain/types/benchmarkSession'

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
