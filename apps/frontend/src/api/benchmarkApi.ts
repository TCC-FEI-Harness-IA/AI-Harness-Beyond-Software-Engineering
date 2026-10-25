// `GET /v1/benchmark/questions`, `GET /v1/benchmark/sessions*` e o corpo de abertura de
// `WS /v1/benchmark/run` — único lugar que conhece esses caminhos e o formato da abertura.

import type {
  BenchmarkDataset,
  BenchmarkRunInput,
  BenchmarkSessionDocument,
} from '../domain/types/benchmarkSession'
import { ContractError } from './errors/ContractError'
import { httpClient } from './httpClient'
import type { RunConfig } from './messageApi'
import {
  parseBenchmarkDataset,
  parseBenchmarkSession,
  parseBenchmarkSessionList,
} from './parsers/benchmarkSession'

const QUESTIONS_PATH = '/benchmark/questions'
const SESSIONS_PATH = '/benchmark/sessions'

export interface BenchmarkRunParams {
  questionCount: number
  maxParallel: number
  config: RunConfig
}

export function getBenchmarkDataset(signal?: AbortSignal): Promise<BenchmarkDataset> {
  return httpClient.get(QUESTIONS_PATH, parseBenchmarkDataset, signal)
}

export function listBenchmarkSessions(signal?: AbortSignal): Promise<BenchmarkSessionDocument[]> {
  return httpClient.get(SESSIONS_PATH, parseBenchmarkSessionList, signal)
}

export function getBenchmarkSession(
  benchmarkSessionId: string,
  signal?: AbortSignal,
): Promise<BenchmarkSessionDocument> {
  return httpClient.get(
    `${SESSIONS_PATH}/${encodeURIComponent(benchmarkSessionId)}`,
    (raw) => parseBenchmarkSession(raw),
    signal,
  )
}

const RALPH_ERRORS_EXPORT_SEGMENT = 'ralph-loop-errors/export'
const UNSAFE_FILENAME_CHARS = /[^A-Za-z0-9_.-]/g

/** `GET /v1/benchmark/sessions/{id}/ralph-loop-errors/export` — ZIP com as questões erradas no Ralph Loop. */
export function exportBenchmarkRalphErrors(
  benchmarkSessionId: string,
  signal?: AbortSignal,
): Promise<Blob> {
  return httpClient.getBlob(
    `${SESSIONS_PATH}/${encodeURIComponent(benchmarkSessionId)}/${RALPH_ERRORS_EXPORT_SEGMENT}`,
    signal,
  )
}

/** Mesmo nome que o backend sugere em `Content-Disposition`. */
export function ralphErrorsArchiveName(benchmarkSessionId: string): string {
  return `benchmark-session-${benchmarkSessionId.replace(UNSAFE_FILENAME_CHARS, '_')}-ralph-loop-errors.zip`
}

function requirePositiveInteger(value: number, field: string): void {
  if (!Number.isInteger(value) || value <= 0) {
    throw new ContractError(`${field} precisa ser um inteiro positivo, recebeu: ${value}`)
  }
}

export function buildBenchmarkRunPayload({
  questionCount,
  maxParallel,
  config,
}: BenchmarkRunParams): BenchmarkRunInput {
  requirePositiveInteger(questionCount, 'question_count')
  requirePositiveInteger(maxParallel, 'max_parallel')
  requirePositiveInteger(config.maxTokens, 'max_tokens')
  if (config.temperature < 0 || config.temperature > 1) {
    throw new ContractError(`temperature precisa estar entre 0 e 1, recebeu: ${config.temperature}`)
  }

  return {
    question_count: questionCount,
    max_parallel: maxParallel,
    llm_model_config: {
      provider: config.provider,
      provider_config: { model_name: config.modelName, endpoint: null },
      max_tokens: config.maxTokens,
      temperature: Math.round(config.temperature * 10) / 10,
    },
  }
}
