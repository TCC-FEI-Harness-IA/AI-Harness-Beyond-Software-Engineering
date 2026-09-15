// Único lugar que sabe montar o corpo dos dois fluxos de inferência (README, FASE 02, seção
// 9) — `POST /v1/message/default` e o frame de abertura de `WS /v1/message/reasoning` usam
// exatamente o mesmo corpo.

import type { DefaultInputDTO } from '../domain/types/defaultInput'
import type { DefaultOutputDTO } from '../domain/types/defaultOutput'
import { ContractError } from './errors/ContractError'
import { httpClient } from './httpClient'
import { parseDefaultOutput } from './parsers/defaultOutput'
import { type ReasoningStreamHandle, type ReasoningStreamHandlers, openReasoningStream } from './websocketClient'

const DEFAULT_MESSAGE_PATH = '/message/default'

export interface RunConfig {
  modelName: string
  provider: string
  maxTokens: number
  temperature: number
}

function roundTemperature(temperature: number): number {
  return Math.round(temperature * 10) / 10
}

export function buildInferencePayload(question: string, config: RunConfig): DefaultInputDTO {
  const userInput = question.trim()
  if (userInput === '') {
    throw new ContractError('a pergunta não pode ser vazia')
  }

  if (!Number.isFinite(config.maxTokens) || config.maxTokens <= 0) {
    throw new ContractError(`max_tokens precisa ser um número positivo, recebeu: ${config.maxTokens}`)
  }

  const temperature = roundTemperature(config.temperature)
  if (temperature < 0 || temperature > 1) {
    throw new ContractError(`temperature precisa estar entre 0 e 1, recebeu: ${config.temperature}`)
  }

  return {
    message: { user_input: userInput },
    llm_model_config: {
      provider: config.provider,
      provider_config: { model_name: config.modelName, endpoint: null },
      max_tokens: config.maxTokens,
      temperature,
    },
  }
}

export function sendDefaultMessage(
  payload: DefaultInputDTO,
  signal?: AbortSignal,
): Promise<DefaultOutputDTO> {
  return httpClient.post(DEFAULT_MESSAGE_PATH, payload, parseDefaultOutput, signal)
}

export function openReasoning(
  payload: DefaultInputDTO,
  handlers: ReasoningStreamHandlers,
): ReasoningStreamHandle {
  return openReasoningStream(payload, handlers)
}
