// Ordenação da lista de modelos pelos atributos do catálogo. Um dado desconhecido (`null`) vai
// sempre para o fim, nas duas direções — ordenar por preço não pode pôr no topo quem não tem preço.

import type { ModelInfo } from '@/domain/types/modelInfo'

export type ModelSortKey =
  | 'name'
  | 'input_price_per_million_tokens'
  | 'output_price_per_million_tokens'
  | 'context_length'
  | 'throughput_tokens_per_second'

export type SortDirection = 'asc' | 'desc'

export interface ModelSort {
  key: ModelSortKey
  direction: SortDirection
}

export const DEFAULT_MODEL_SORT: ModelSort = { key: 'name', direction: 'asc' }

// No primeiro clique, contexto e vazão começam do maior (o melhor); nome e preços, do menor.
const FIRST_DIRECTION: Readonly<Record<ModelSortKey, SortDirection>> = {
  name: 'asc',
  input_price_per_million_tokens: 'asc',
  output_price_per_million_tokens: 'asc',
  context_length: 'desc',
  throughput_tokens_per_second: 'desc',
}

const nameCollator = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })

/** Nome exibido do modelo: o amigável, quando cadastrado, ou o identificador. */
export function modelLabel(model: ModelInfo): string {
  return model.display_name ?? model.model_name
}

/** Clicar na coluna já ordenada inverte a direção; outra coluna começa na direção natural dela. */
export function nextModelSort(current: ModelSort, key: ModelSortKey): ModelSort {
  if (current.key === key) {
    return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
  }
  return { key, direction: FIRST_DIRECTION[key] }
}

function compareNullable(a: number | null, b: number | null, direction: SortDirection): number {
  if (a === null || b === null) {
    if (a === b) return 0
    return a === null ? 1 : -1
  }
  return direction === 'asc' ? a - b : b - a
}

/** Devolve uma cópia ordenada; empates mantêm a ordem por nome. */
export function sortModels(models: readonly ModelInfo[], sort: ModelSort): ModelInfo[] {
  const byName = (a: ModelInfo, b: ModelInfo): number => nameCollator.compare(modelLabel(a), modelLabel(b))

  return [...models].sort((a, b) => {
    if (sort.key === 'name') {
      return sort.direction === 'asc' ? byName(a, b) : byName(b, a)
    }
    return compareNullable(a[sort.key], b[sort.key], sort.direction) || byName(a, b)
  })
}
