import { describe, expect, it } from 'vitest'
import { MODEL_PROVIDER, PROVIDER_LABELS, isModelProvider, providerLabel } from './modelProvider'

describe('domain/enums/modelProvider', () => {
  it('declara exatamente os provedores que o backend implementa', () => {
    expect(Object.values(MODEL_PROVIDER)).toEqual(['open_router', 'azure_ai_foundry', 'openai'])
  })

  it('reconhece um provedor válido', () => {
    expect(isModelProvider('azure_ai_foundry')).toBe(true)
  })

  it.each(['local', 'anthropic', '', 42, null, undefined])('recusa %o', (value) => {
    expect(isModelProvider(value)).toBe(false)
  })

  it('tem um rótulo legível para cada provedor', () => {
    for (const provider of Object.values(MODEL_PROVIDER)) {
      expect(PROVIDER_LABELS[provider]).toBeTruthy()
    }
  })

  it('devolve o rótulo do provedor conhecido', () => {
    expect(providerLabel('open_router')).toBe('OpenRouter')
  })

  it('devolve o próprio identificador quando o provedor é desconhecido', () => {
    expect(providerLabel('provedor-novo')).toBe('provedor-novo')
  })
})
