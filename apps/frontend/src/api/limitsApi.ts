// `GET /v1/limits` — limites do backend que o front precisa respeitar ao montar uma requisição.

import type { BackendLimits } from '../domain/types/backendLimits'
import { httpClient } from './httpClient'
import { parseBackendLimits } from './parsers/backendLimits'

const LIMITS_PATH = '/limits'

export function getBackendLimits(signal?: AbortSignal): Promise<BackendLimits> {
  return httpClient.get(LIMITS_PATH, parseBackendLimits, signal)
}
