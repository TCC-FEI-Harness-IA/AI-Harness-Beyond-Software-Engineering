// README, seção 3.1 — `llm_model_config`.

import type { ProviderConfigDTO } from './providerConfig'

export interface ModelConfigDTO {
  provider: string
  provider_config: ProviderConfigDTO
  max_tokens: number
  temperature: number
}
