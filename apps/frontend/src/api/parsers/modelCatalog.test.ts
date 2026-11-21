import { describe, expect, it } from 'vitest'
import { ContractError } from '../errors/ContractError'
import { parseModelCatalog, parseModelInfo } from './modelCatalog'

const COMPLETO = {
  model_name: 'openai/gpt-5-nano',
  display_name: 'OpenAI: GPT-5 Nano',
  input_price_per_million_tokens: 0.05,
  output_price_per_million_tokens: 0.4,
  context_length: 400000,
  throughput_tokens_per_second: 118,
}

describe('parseModelCatalog', () => {
  it('lê o preço, o contexto e a vazão de cada modelo', () => {
    expect(parseModelCatalog({ models: [COMPLETO] })).toEqual([COMPLETO])
  })

  it('aceita campos nulos ou ausentes como "sem dado"', () => {
    const parsed = parseModelCatalog({
      models: [{ model_name: 'vendor/a', display_name: null, context_length: null }],
    })

    expect(parsed).toEqual([
      {
        model_name: 'vendor/a',
        display_name: null,
        input_price_per_million_tokens: null,
        output_price_per_million_tokens: null,
        context_length: null,
        throughput_tokens_per_second: null,
      },
    ])
  })

  it('aceita lista vazia', () => {
    expect(parseModelCatalog({ models: [] })).toEqual([])
  })

  it.each([
    [null, 'modelCatalog'],
    [{}, 'models'],
    [{ models: [null] }, 'models[0]'],
    [{ models: [{}] }, 'models[0].model_name'],
    [{ models: [{ ...COMPLETO, display_name: 3 }] }, 'models[0].display_name'],
    [{ models: [{ ...COMPLETO, context_length: '400000' }] }, 'models[0].context_length'],
    [{ models: [{ ...COMPLETO, throughput_tokens_per_second: Number.NaN }] }, 'throughput_tokens_per_second'],
  ])('recusa %j', (raw, message) => {
    expect(() => parseModelCatalog(raw)).toThrow(ContractError)
    expect(() => parseModelCatalog(raw)).toThrow(message)
  })
})

describe('parseModelInfo', () => {
  it('lê um único modelo e nomeia o caminho informado no erro', () => {
    expect(parseModelInfo(COMPLETO, 'model')).toEqual(COMPLETO)
    expect(() => parseModelInfo({ model_name: 1 }, 'model')).toThrow('model.model_name')
  })
})
