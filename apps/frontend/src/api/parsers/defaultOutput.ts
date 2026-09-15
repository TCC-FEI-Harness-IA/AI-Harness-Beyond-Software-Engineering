// `unknown` → `DefaultOutputDTO` (README, FASE 02, seção 5) — resposta de
// `POST /v1/message/default`.

import type { DefaultOutputDTO } from '../../domain/types/defaultOutput'
import { requireNumber, requireObject, requireString } from './primitives'

export function parseDefaultOutput(raw: unknown): DefaultOutputDTO {
  const obj = requireObject(raw, 'defaultOutput')
  return {
    message: requireString(obj, 'message', 'message'),
    response: requireString(obj, 'response', 'response'),
    session_id: requireString(obj, 'session_id', 'session_id'),
    tokens_input: requireNumber(obj, 'tokens_input', 'tokens_input'),
    tokens_output: requireNumber(obj, 'tokens_output', 'tokens_output'),
    inference_time_ms: requireNumber(obj, 'inference_time_ms', 'inference_time_ms'),
  }
}
