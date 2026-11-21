import type { BenchmarkDetails } from '@/domain/types/benchmarkDetails'
import { ContractError } from '../errors/ContractError'
import { optionalString, requireNumber, requireObject } from './primitives'

export function parseBenchmarkDetails(raw: unknown): BenchmarkDetails {
  const obj = raw == null ? {} : requireObject(raw, 'benchmark_details')
  const flag = obj.is_banchmark ?? false
  if (typeof flag !== 'boolean') throw new ContractError('is_banchmark deve ser booleano')
  const mode = optionalString(obj, 'inference_mode', 'benchmark_details.inference_mode')
  if (mode !== null && mode !== 'simple' && mode !== 'ralph') {
    throw new ContractError('inference_mode inválido')
  }
  const correct = obj.is_correct ?? null
  if (correct !== null && typeof correct !== 'boolean') throw new ContractError('is_correct inválido')
  return {
    is_banchmark: flag,
    question_name: optionalString(obj, 'question_name', 'benchmark_details.question_name'),
    corret_answer: optionalString(obj, 'corret_answer', 'benchmark_details.corret_answer'),
    providade_answer: optionalString(obj, 'providade_answer', 'benchmark_details.providade_answer'),
    inference_mode: mode,
    run_id: optionalString(obj, 'run_id', 'benchmark_details.run_id'),
    expected_alternative: optionalString(obj, 'expected_alternative', 'benchmark_details.expected_alternative'),
    selected_alternative: optionalString(obj, 'selected_alternative', 'benchmark_details.selected_alternative'),
    is_correct: correct,
    duration_seconds: obj.duration_seconds == null ? null : requireNumber(obj, 'duration_seconds', 'benchmark_details.duration_seconds'),
    error: optionalString(obj, 'error', 'benchmark_details.error'),
  }
}
