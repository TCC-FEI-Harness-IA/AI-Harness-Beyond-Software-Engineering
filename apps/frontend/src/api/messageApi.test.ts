import { describe, expect, it } from 'vitest'
import { buildInferencePayload, type RunConfig } from './messageApi'
import { ContractError } from './errors/ContractError'

const CONFIG: RunConfig = {
  modelName: 'openai/gpt-4o-mini',
  provider: 'open_router',
  maxTokens: 1000,
  temperature: 0.3,
}

describe('buildInferencePayload', () => {
  it('monta o corpo exato do contrato', () => {
    const payload = buildInferencePayload('Quais são todos os números primos entre 0 e 20?', CONFIG)

    expect(payload).toEqual({
      message: { user_input: 'Quais são todos os números primos entre 0 e 20?' },
      llm_model_config: {
        provider: 'open_router',
        provider_config: { model_name: 'openai/gpt-4o-mini', endpoint: null },
        max_tokens: 1000,
        temperature: 0.3,
      },
    })
  })

  it('lança quando a pergunta é vazia', () => {
    expect(() => buildInferencePayload('', CONFIG)).toThrow(ContractError)
    expect(() => buildInferencePayload('   ', CONFIG)).toThrow(ContractError)
  })

  it('arredonda a temperatura para 1 casa decimal', () => {
    const payload = buildInferencePayload('ping', { ...CONFIG, temperature: 0.75 })
    expect(payload.llm_model_config.temperature).toBeCloseTo(0.8)
  })

  it('lança quando a temperatura fica fora de [0, 1] após arredondar', () => {
    expect(() => buildInferencePayload('ping', { ...CONFIG, temperature: 1.4 })).toThrow(
      ContractError,
    )
  })

  it('lança quando max_tokens não é positivo', () => {
    expect(() => buildInferencePayload('ping', { ...CONFIG, maxTokens: 0 })).toThrow(ContractError)
  })
})
