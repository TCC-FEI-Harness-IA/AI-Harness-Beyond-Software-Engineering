// `unknown` → publicações oficiais (`/v1/public/benchmarks`).

import type { OfficialPublication, PublicationStatus } from '@/domain/types/officialPublication'
import { isBenchmarkDatasetId } from '@/domain/services/benchmarkDefinition'
import { ContractError } from '../errors/ContractError'
import { parseBenchmarkSession } from './benchmarkSession'
import { optionalString, requireArray, requireObject, requireString } from './primitives'

const STATUSES: readonly PublicationStatus[] = ['active', 'superseded']

export function parseOfficialPublication(raw: unknown, path = 'publicação'): OfficialPublication {
  const source = requireObject(raw, path)
  const dataset = requireString(source, 'dataset', `${path}.dataset`)
  const status = requireString(source, 'status', `${path}.status`)
  if (!isBenchmarkDatasetId(dataset)) throw new ContractError(`campo "${path}.dataset" desconhecido: ${dataset}`)
  if (!(STATUSES as readonly string[]).includes(status)) {
    throw new ContractError(`campo "${path}.status" desconhecido: ${status}`)
  }
  return {
    id: requireString(source, 'id', `${path}.id`),
    dataset,
    status: status as PublicationStatus,
    publishedAt: requireString(source, 'published_at', `${path}.published_at`),
    supersedes: optionalString(source, 'supersedes', `${path}.supersedes`),
    supersededBy: optionalString(source, 'superseded_by', `${path}.superseded_by`),
    supersededAt: optionalString(source, 'superseded_at', `${path}.superseded_at`),
    sourceBenchmarkSessionId: requireString(source, 'source_benchmark_session_id', `${path}.source_benchmark_session_id`),
    textRedacted: source['text_redacted'] === true,
    battery: parseBenchmarkSession(source['benchmark_session']),
  }
}

export function parseOfficialPublicationList(raw: unknown): OfficialPublication[] {
  const source = requireObject(raw, 'resposta')
  return requireArray(source, 'publications', 'publications').map((item, index) =>
    parseOfficialPublication(item, `publications[${index}]`),
  )
}
