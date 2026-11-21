// README, seção 3.1 — `llm_model_config`.

import type { ModelProvider } from '../enums/modelProvider'
import type { ProviderConfigDTO } from './providerConfig'

export interface ModelConfigDTO {
  provider: ModelProvider
  provider_config: ProviderConfigDTO
  max_tokens: number
  temperature: number
}
