import { describe, expect, it } from 'vitest'
import { EMPTY_MODEL_FORM, modelToFormValues, parseModelForm } from './modelForm'

describe('parseModelForm', () => {
  it('converte texto em ModelInfo, com vazio como desconhecido e vírgula decimal', () => {
    const result = parseModelForm({
      ...EMPTY_MODEL_FORM,
      model_name: ' vendor/modelo ',
      display_name: '  ',
      input_price_per_million_tokens: '0,0434',
      context_length: '131072',
    })

    expect(result).toEqual({
      ok: true,
      model: {
        model_name: 'vendor/modelo',
        display_name: null,
        input_price_per_million_tokens: 0.0434,
        output_price_per_million_tokens: null,
        context_length: 131072,
        throughput_tokens_per_second: null,
      },
    })
  })

  it('exige o identificador', () => {
    expect(parseModelForm(EMPTY_MODEL_FORM)).toEqual({ ok: false, message: 'Informe o identificador do modelo.' })
  })

  it.each([
    [{ input_price_per_million_tokens: 'abc' }, 'Preço de entrada precisa ser um número.'],
    [{ output_price_per_million_tokens: '-1' }, 'Preço de saída não pode ser negativo.'],
    [{ context_length: '0' }, 'Contexto precisa ser maior que zero.'],
    [{ context_length: '10.5' }, 'Contexto precisa ser um número inteiro.'],
    [{ throughput_tokens_per_second: '0' }, 'Vazão precisa ser maior que zero.'],
  ])('recusa %j', (overrides, message) => {
    expect(parseModelForm({ ...EMPTY_MODEL_FORM, model_name: 'v/m', ...overrides })).toEqual({ ok: false, message })
  })

  it('aceita preço zero', () => {
    const result = parseModelForm({ ...EMPTY_MODEL_FORM, model_name: 'v/m', input_price_per_million_tokens: '0' })
    expect(result.ok && result.model.input_price_per_million_tokens).toBe(0)
  })
})

describe('modelToFormValues', () => {
  it('ida e volta preserva o modelo', () => {
    const model = {
      model_name: 'v/m',
      display_name: 'V: M',
      input_price_per_million_tokens: 0.05,
      output_price_per_million_tokens: 0.4,
      context_length: 400000,
      throughput_tokens_per_second: 114,
    }
    expect(parseModelForm(modelToFormValues(model))).toEqual({ ok: true, model })
  })

  it('desconhecido vira campo vazio', () => {
    const values = modelToFormValues({
      model_name: 'v/m',
      display_name: null,
      input_price_per_million_tokens: null,
      output_price_per_million_tokens: null,
      context_length: null,
      throughput_tokens_per_second: null,
    })
    expect(values).toEqual({ ...EMPTY_MODEL_FORM, model_name: 'v/m' })
  })
})
