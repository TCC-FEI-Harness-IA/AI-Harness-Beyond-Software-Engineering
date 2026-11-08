// `unknown` → `ModelInfo[]` (`GET /v1/models`) e `ModelInfo` (resposta do cadastro e da edição).

import type { ModelInfo } from '@/domain/types/modelInfo'
import {
  optionalNumber,
  optionalString,
  requireArray,
  requireObject,
  requireString,
} from './primitives'

export function parseModelInfo(raw: unknown, path: string): ModelInfo {
  const obj = requireObject(raw, path)
  return {
    model_name: requireString(obj, 'model_name', `${path}.model_name`),
    display_name: optionalString(obj, 'display_name', `${path}.display_name`),
    input_price_per_million_tokens: optionalNumber(
      obj,
      'input_price_per_million_tokens',
      `${path}.input_price_per_million_tokens`,
    ),
    output_price_per_million_tokens: optionalNumber(
      obj,
      'output_price_per_million_tokens',
      `${path}.output_price_per_million_tokens`,
    ),
    context_length: optionalNumber(obj, 'context_length', `${path}.context_length`),
    throughput_tokens_per_second: optionalNumber(
      obj,
      'throughput_tokens_per_second',
      `${path}.throughput_tokens_per_second`,
    ),
  }
}

export function parseModelCatalog(raw: unknown): ModelInfo[] {
  const obj = requireObject(raw, 'modelCatalog')
  return requireArray(obj, 'models', 'models').map((item, index) => parseModelInfo(item, `models[${index}]`))
}
