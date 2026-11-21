// Espelha ModelProviderEnum do backend (src/domain/enums/model_provider_enum.py) — os
// valores viajam em `llm_model_config.provider` e o backend responde 422 para qualquer
// outro. Ver README, seção 3.1.

export const MODEL_PROVIDER = {
  OPEN_ROUTER: 'open_router',
  AZURE_AI_FOUNDRY: 'azure_ai_foundry',
  OPENAI: 'openai',
} as const

export type ModelProvider = (typeof MODEL_PROVIDER)[keyof typeof MODEL_PROVIDER]

export const PROVIDER_LABELS: Record<ModelProvider, string> = {
  [MODEL_PROVIDER.OPEN_ROUTER]: 'OpenRouter',
  [MODEL_PROVIDER.AZURE_AI_FOUNDRY]: 'Azure AI Foundry',
  [MODEL_PROVIDER.OPENAI]: 'OpenAI',
}

export const isModelProvider = (value: unknown): value is ModelProvider =>
  typeof value === 'string' && (Object.values(MODEL_PROVIDER) as string[]).includes(value)

/** Nome de exibição do provedor; cai no próprio identificador quando ele é desconhecido. */
export function providerLabel(provider: string): string {
  return isModelProvider(provider) ? PROVIDER_LABELS[provider] : provider
}
