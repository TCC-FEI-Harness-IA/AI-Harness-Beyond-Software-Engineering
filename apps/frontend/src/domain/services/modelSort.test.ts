import { describe, expect, it } from 'vitest'
import type { ModelInfo } from '@/domain/types/modelInfo'
import { DEFAULT_MODEL_SORT, modelLabel, nextModelSort, sortModels } from './modelSort'

function modelo(model_name: string, overrides: Partial<ModelInfo> = {}): ModelInfo {
  return {
    model_name,
    display_name: null,
    input_price_per_million_tokens: null,
    output_price_per_million_tokens: null,
    context_length: null,
    throughput_tokens_per_second: null,
    ...overrides,
  }
}

const nomes = (models: ModelInfo[]): string[] => models.map((model) => model.model_name)

describe('modelLabel', () => {
  it('prefere o nome amigável e cai no identificador', () => {
    expect(modelLabel(modelo('v/a', { display_name: 'Vendor: A' }))).toBe('Vendor: A')
    expect(modelLabel(modelo('v/a'))).toBe('v/a')
  })
})

describe('nextModelSort', () => {
  it('inverte a direção quando a coluna já está ordenada', () => {
    expect(nextModelSort(DEFAULT_MODEL_SORT, 'name')).toEqual({ key: 'name', direction: 'desc' })
    expect(nextModelSort({ key: 'name', direction: 'desc' }, 'name')).toEqual({ key: 'name', direction: 'asc' })
  })

  it('preço começa do menor; contexto e vazão, do maior', () => {
    expect(nextModelSort(DEFAULT_MODEL_SORT, 'input_price_per_million_tokens').direction).toBe('asc')
    expect(nextModelSort(DEFAULT_MODEL_SORT, 'context_length').direction).toBe('desc')
    expect(nextModelSort(DEFAULT_MODEL_SORT, 'throughput_tokens_per_second').direction).toBe('desc')
  })
})

describe('sortModels', () => {
  const catalogo = [
    modelo('v/caro', { display_name: 'B caro', input_price_per_million_tokens: 0.5 }),
    modelo('v/sem-preco', { display_name: 'C sem preço' }),
    modelo('v/barato', { display_name: 'A barato', input_price_per_million_tokens: 0.01 }),
  ]

  it('ordena pelo nome exibido, nas duas direções', () => {
    expect(nomes(sortModels(catalogo, { key: 'name', direction: 'asc' }))).toEqual(['v/barato', 'v/caro', 'v/sem-preco'])
    expect(nomes(sortModels(catalogo, { key: 'name', direction: 'desc' }))).toEqual(['v/sem-preco', 'v/caro', 'v/barato'])
  })

  it('ordena por número e deixa o desconhecido no fim nas duas direções', () => {
    const key = 'input_price_per_million_tokens'
    expect(nomes(sortModels(catalogo, { key, direction: 'asc' }))).toEqual(['v/barato', 'v/caro', 'v/sem-preco'])
    expect(nomes(sortModels(catalogo, { key, direction: 'desc' }))).toEqual(['v/caro', 'v/barato', 'v/sem-preco'])
  })

  it('desempata pelo nome, inclusive entre desconhecidos', () => {
    const empatados = [modelo('v/z'), modelo('v/a'), modelo('v/m', { context_length: 10 }), modelo('v/b', { context_length: 10 })]
    expect(nomes(sortModels(empatados, { key: 'context_length', direction: 'desc' }))).toEqual(['v/b', 'v/m', 'v/a', 'v/z'])
  })

  it('não altera a lista recebida', () => {
    const original = [...catalogo]
    sortModels(catalogo, { key: 'name', direction: 'desc' })
    expect(catalogo).toEqual(original)
  })
})
