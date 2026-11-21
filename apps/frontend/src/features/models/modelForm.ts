// Valores do formulário de cadastro (texto, como vêm dos inputs) ⇄ `ModelInfo`. Campo numérico vazio
// vira `null` ("desconhecido"); as faixas espelham as do backend (preço ≥ 0, contexto e vazão > 0).

import type { ModelInfo } from '@/domain/types/modelInfo'

export interface ModelFormValues {
  model_name: string
  display_name: string
  input_price_per_million_tokens: string
  output_price_per_million_tokens: string
  context_length: string
  throughput_tokens_per_second: string
}

export const EMPTY_MODEL_FORM: ModelFormValues = {
  model_name: '',
  display_name: '',
  input_price_per_million_tokens: '',
  output_price_per_million_tokens: '',
  context_length: '',
  throughput_tokens_per_second: '',
}

export type ModelFormResult = { ok: true; model: ModelInfo } | { ok: false; message: string }

function toText(value: number | null): string {
  return value === null ? '' : String(value)
}

export function modelToFormValues(model: ModelInfo): ModelFormValues {
  return {
    model_name: model.model_name,
    display_name: model.display_name ?? '',
    input_price_per_million_tokens: toText(model.input_price_per_million_tokens),
    output_price_per_million_tokens: toText(model.output_price_per_million_tokens),
    context_length: toText(model.context_length),
    throughput_tokens_per_second: toText(model.throughput_tokens_per_second),
  }
}

class FieldError extends Error {}

function readNumber(raw: string, label: string, rule: 'nonNegative' | 'positive' | 'positiveInteger'): number | null {
  const text = raw.trim().replace(',', '.')
  if (text === '') return null
  const value = Number(text)
  if (!Number.isFinite(value)) throw new FieldError(`${label} precisa ser um número.`)
  if (rule === 'nonNegative' && value < 0) throw new FieldError(`${label} não pode ser negativo.`)
  if (rule !== 'nonNegative' && value <= 0) throw new FieldError(`${label} precisa ser maior que zero.`)
  if (rule === 'positiveInteger' && !Number.isInteger(value)) {
    throw new FieldError(`${label} precisa ser um número inteiro.`)
  }
  return value
}

export function parseModelForm(values: ModelFormValues): ModelFormResult {
  const modelName = values.model_name.trim()
  if (modelName === '') return { ok: false, message: 'Informe o identificador do modelo.' }

  try {
    return {
      ok: true,
      model: {
        model_name: modelName,
        display_name: values.display_name.trim() || null,
        input_price_per_million_tokens: readNumber(values.input_price_per_million_tokens, 'Preço de entrada', 'nonNegative'),
        output_price_per_million_tokens: readNumber(values.output_price_per_million_tokens, 'Preço de saída', 'nonNegative'),
        context_length: readNumber(values.context_length, 'Contexto', 'positiveInteger'),
        throughput_tokens_per_second: readNumber(values.throughput_tokens_per_second, 'Vazão', 'positive'),
      },
    }
  } catch (error) {
    if (error instanceof FieldError) return { ok: false, message: error.message }
    throw error
  }
}
