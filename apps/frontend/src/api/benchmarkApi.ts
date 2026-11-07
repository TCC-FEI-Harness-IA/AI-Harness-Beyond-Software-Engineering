// `GET /v1/benchmark/questions`, `GET /v1/benchmark/sessions*` e o corpo de abertura de
// `WS /v1/benchmark/run` — único lugar que conhece esses caminhos e o formato da abertura.

import type {
  BenchmarkDataset,
  BenchmarkDatasetId,
  BenchmarkRunInput,
  BenchmarkSessionDocument,
  GPQASubset,
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

/** Define ou remove o alias de uma bateria encerrada. */
export function updateBenchmarkAlias(
  benchmarkSessionId: string,
  alias: string | null,
  signal?: AbortSignal,
): Promise<BenchmarkSessionDocument> {
  return httpClient.put(
    `${SESSIONS_PATH}/${encodeURIComponent(benchmarkSessionId)}/alias`,
    { alias },
    (raw) => parseBenchmarkSession(raw),
    signal,
  )
}

export interface BenchmarkRunParams {
  questionCount: number
  maxParallel: number
  config: RunConfig
  benchmark?: BenchmarkDatasetId
  fewShot?: 0 | 5
  subjects?: string[]
  sampleSeed?: number
  gpqaSubset?: GPQASubset
  subjectCounts?: Record<string, number>
}

export function getBenchmarkDataset(
  signal?: AbortSignal,
  benchmark: BenchmarkDatasetId = 'vestibular',
  gpqaSubset: GPQASubset = 'diamond',
): Promise<BenchmarkDataset> {
  let path =
    benchmark !== 'vestibular' ? `${QUESTIONS_PATH}?benchmark=${benchmark}` : QUESTIONS_PATH
  if (benchmark === 'gpqa' && gpqaSubset !== 'diamond') path += `&gpqa_subset=${gpqaSubset}`
  return httpClient.get(path, parseBenchmarkDataset, signal)
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
  benchmark = 'vestibular',
  fewShot = 0,
  subjects = [],
  sampleSeed = 42,
  gpqaSubset = 'diamond',
  subjectCounts,
}: BenchmarkRunParams): BenchmarkRunInput {
  requirePositiveInteger(questionCount, 'question_count')
  requirePositiveInteger(maxParallel, 'max_parallel')
  requirePositiveInteger(config.maxTokens, 'max_tokens')
  if (subjectCounts !== undefined) {
    if (subjects.length > 0) {
      throw new ContractError('subject_counts não pode ser usado junto de subjects.')
    }
    const counts = Object.values(subjectCounts)
    if (
      counts.some((count) => !Number.isInteger(count) || count < 0) ||
      counts.reduce((sum, count) => sum + count, 0) !== questionCount
    ) {
      throw new ContractError(
        'subject_counts deve conter inteiros não negativos cuja soma seja question_count.',
      )
    }
  }
  if (config.temperature < 0 || config.temperature > 1) {
    throw new ContractError(`temperature precisa estar entre 0 e 1, recebeu: ${config.temperature}`)
  }
  if (
    benchmark !== 'vestibular' &&
    (![0, 5].includes(fewShot) ||
      (benchmark === 'gpqa' &&
        (fewShot !== 0 || !['diamond', 'main', 'extended'].includes(gpqaSubset))) ||
      !Number.isInteger(sampleSeed) ||
      sampleSeed < 0 ||
      sampleSeed > 4294967295)
  ) {
    throw new ContractError('Protocolo do benchmark ou semente inválidos.')
  }

  return {
    ...(benchmark === 'gpqa' ? { gpqa_subset: gpqaSubset } : {}),
    ...(subjectCounts === undefined ? {} : { subject_counts: { ...subjectCounts } }),
    ...(benchmark !== 'vestibular'
      ? {
          benchmark,
          few_shot: fewShot,
          subjects,
          sample_seed: sampleSeed,
        }
      : {}),
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
