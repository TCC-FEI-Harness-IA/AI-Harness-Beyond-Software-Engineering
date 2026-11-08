// `/v1/models` — catálogo de modelos (preço, contexto e vazão), guardado no MongoDB do backend.

import type { ModelInfo } from '../domain/types/modelInfo'
import { httpClient } from './httpClient'
import { parseModelCatalog, parseModelInfo } from './parsers/modelCatalog'

const MODELS_PATH = '/models'

// O identificador tem barra (`vendor/modelo`) e o backend a aceita no caminho: só os segmentos
// são codificados, para que um caractere especial não quebre a rota.
function modelPath(modelName: string): string {
  return `${MODELS_PATH}/${modelName.split('/').map(encodeURIComponent).join('/')}`
}

export function getModelCatalog(signal?: AbortSignal): Promise<ModelInfo[]> {
  return httpClient.get(MODELS_PATH, parseModelCatalog, signal)
}

/** Cadastra um modelo novo; o backend responde 409 quando o identificador já existe. */
export function createModel(model: ModelInfo, signal?: AbortSignal): Promise<ModelInfo> {
  return httpClient.post(MODELS_PATH, model, (raw) => parseModelInfo(raw, 'model'), signal)
}

/** Substitui as informações de um modelo cadastrado (o identificador não muda). */
export function updateModel(model: ModelInfo, signal?: AbortSignal): Promise<ModelInfo> {
  const { model_name: modelName, ...fields } = model
  return httpClient.put(modelPath(modelName), fields, (raw) => parseModelInfo(raw, 'model'), signal)
}

export function deleteModel(modelName: string, signal?: AbortSignal): Promise<void> {
  return httpClient.delete(modelPath(modelName), signal)
}
