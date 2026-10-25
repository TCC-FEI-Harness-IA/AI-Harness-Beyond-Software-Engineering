// `unknown` → contratos de benchmark (README, FASE 02, seção 5): documento de `BenchmarkSession`,
// listagem, dataset e frames do WebSocket de execução.

import { isBenchmarkQuestionStatus, isBenchmarkSessionStatus } from '@/domain/enums/benchmarkStatus'
import { isModelProvider } from '@/domain/enums/modelProvider'
import type { BenchmarkInferenceMode } from '@/domain/types/benchmarkDetails'
import type {
  BenchmarkDataset,
  BenchmarkFlowOutcome,
  BenchmarkFrame,
  BenchmarkModeSummary,
  BenchmarkQuestionRun,
  BenchmarkSessionDocument,
} from '@/domain/types/benchmarkSession'
import { ContractError } from '../errors/ContractError'
import { optionalString, requireArray, requireNumber, requireObject, requireString } from './primitives'

function requireBoolean(source: Record<string, unknown>, key: string, path: string): boolean {
  const value = source[key]
  if (typeof value !== 'boolean') {
    throw new ContractError(`campo "${path}" deveria ser boolean, recebeu: ${JSON.stringify(value)}`)
  }
  return value
}

function parseMode(value: unknown, path: string): BenchmarkInferenceMode {
  if (value !== 'simple' && value !== 'ralph') {
    throw new ContractError(`campo "${path}" deveria ser "simple" ou "ralph", recebeu: ${JSON.stringify(value)}`)
  }
  return value
}

function parseOutcome(raw: unknown, path: string): BenchmarkFlowOutcome | null {
  if (raw === null) return null
  const obj = requireObject(raw, path)
  return {
    mode: parseMode(obj.mode, `${path}.mode`),
    session_id: optionalString(obj, 'session_id', `${path}.session_id`),
    selected_alternative: optionalString(obj, 'selected_alternative', `${path}.selected_alternative`),
    is_correct: requireBoolean(obj, 'is_correct', `${path}.is_correct`),
    error: optionalString(obj, 'error', `${path}.error`),
    duration_seconds: requireNumber(obj, 'duration_seconds', `${path}.duration_seconds`),
    total_tokens: requireNumber(obj, 'total_tokens', `${path}.total_tokens`),
  }
}

function parseQuestion(raw: unknown, path: string): BenchmarkQuestionRun {
  const obj = requireObject(raw, path)
  const status = obj.status
  if (!isBenchmarkQuestionStatus(status)) {
    throw new ContractError(`campo "${path}.status" tem valor desconhecido: ${JSON.stringify(status)}`)
  }
  return {
    question_id: requireString(obj, 'question_id', `${path}.question_id`),
    expected_alternative: requireString(obj, 'expected_alternative', `${path}.expected_alternative`),
    status,
    current_mode: obj.current_mode == null ? null : parseMode(obj.current_mode, `${path}.current_mode`),
    current_tokens: requireNumber(obj, 'current_tokens', `${path}.current_tokens`),
    total_tokens: requireNumber(obj, 'total_tokens', `${path}.total_tokens`),
    simple: parseOutcome(obj.simple ?? null, `${path}.simple`),
    ralph: parseOutcome(obj.ralph ?? null, `${path}.ralph`),
  }
}

function parseSummary(raw: unknown, path: string): BenchmarkModeSummary {
  const obj = requireObject(raw, path)
  return {
    executed: requireNumber(obj, 'executed', `${path}.executed`),
    correct: requireNumber(obj, 'correct', `${path}.correct`),
    wrong: requireNumber(obj, 'wrong', `${path}.wrong`),
    failures: requireNumber(obj, 'failures', `${path}.failures`),
    accuracy: requireNumber(obj, 'accuracy', `${path}.accuracy`),
    total_tokens: requireNumber(obj, 'total_tokens', `${path}.total_tokens`),
    duration_seconds: requireNumber(obj, 'duration_seconds', `${path}.duration_seconds`),
  }
}

function parseStringArray(source: Record<string, unknown>, key: string, path: string): string[] {
  return requireArray(source, key, path).map((item, index) => {
    if (typeof item !== 'string') {
      throw new ContractError(`campo "${path}[${index}]" deveria ser string, recebeu: ${JSON.stringify(item)}`)
    }
    return item
  })
}

export function parseBenchmarkSession(raw: unknown, path = 'benchmark_session'): BenchmarkSessionDocument {
  const obj = requireObject(raw, path)
  const status = obj.status
  if (!isBenchmarkSessionStatus(status)) {
    throw new ContractError(`campo "${path}.status" tem valor desconhecido: ${JSON.stringify(status)}`)
  }
  const provider = obj.provider
  if (!isModelProvider(provider)) {
    throw new ContractError(`campo "${path}.provider" tem valor desconhecido: ${JSON.stringify(provider)}`)
  }
  const progress = requireObject(obj.progress, `${path}.progress`)
  const summary = requireObject(obj.summary, `${path}.summary`)

  return {
    id: requireString(obj, 'id', `${path}.id`),
    status,
    model_name: requireString(obj, 'model_name', `${path}.model_name`),
    provider,
    max_tokens: requireNumber(obj, 'max_tokens', `${path}.max_tokens`),
    temperature: requireNumber(obj, 'temperature', `${path}.temperature`),
    max_parallel: requireNumber(obj, 'max_parallel', `${path}.max_parallel`),
    question_count: requireNumber(obj, 'question_count', `${path}.question_count`),
    created_at: requireString(obj, 'created_at', `${path}.created_at`),
    updated_at: requireString(obj, 'updated_at', `${path}.updated_at`),
    finished_at: optionalString(obj, 'finished_at', `${path}.finished_at`),
    wall_time_ms: requireNumber(obj, 'wall_time_ms', `${path}.wall_time_ms`),
    error: optionalString(obj, 'error', `${path}.error`),
    progress: {
      total: requireNumber(progress, 'total', `${path}.progress.total`),
      pending: requireNumber(progress, 'pending', `${path}.progress.pending`),
      running: requireNumber(progress, 'running', `${path}.progress.running`),
      finished: requireNumber(progress, 'finished', `${path}.progress.finished`),
      interrupted: requireNumber(progress, 'interrupted', `${path}.progress.interrupted`),
    },
    total_tokens: requireNumber(obj, 'total_tokens', `${path}.total_tokens`),
    session_ids: parseStringArray(obj, 'session_ids', `${path}.session_ids`),
    summary: {
      simple: parseSummary(summary.simple, `${path}.summary.simple`),
      ralph: parseSummary(summary.ralph, `${path}.summary.ralph`),
    },
    questions: requireArray(obj, 'questions', `${path}.questions`).map((item, index) =>
      parseQuestion(item, `${path}.questions[${index}]`),
    ),
  }
}

export function parseBenchmarkSessionList(raw: unknown): BenchmarkSessionDocument[] {
  const obj = requireObject(raw, 'benchmarkSessionList')
  return requireArray(obj, 'benchmark_sessions', 'benchmark_sessions').map((item, index) =>
    parseBenchmarkSession(item, `benchmark_sessions[${index}]`),
  )
}

export function parseBenchmarkDataset(raw: unknown): BenchmarkDataset {
  const obj = requireObject(raw, 'benchmarkDataset')
  return {
    question_ids: parseStringArray(obj, 'question_ids', 'question_ids'),
    max_parallel_limit: requireNumber(obj, 'max_parallel_limit', 'max_parallel_limit'),
  }
}

export function parseBenchmarkFrame(raw: unknown): BenchmarkFrame {
  const obj = requireObject(raw, 'benchmarkFrame')
  const type = obj.type
  if (type === 'error') {
    return { type, content: requireString(obj, 'content', 'content') }
  }
  if (type === 'progress' || type === 'result') {
    return { type, benchmark_session: parseBenchmarkSession(obj.benchmark_session) }
  }
  throw new ContractError(`campo "type" do frame de benchmark tem valor desconhecido: ${JSON.stringify(type)}`)
}
