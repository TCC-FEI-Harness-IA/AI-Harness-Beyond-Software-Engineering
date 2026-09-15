// Corpo de `POST /v1/message/default` e do frame de abertura de `WS /v1/message/reasoning` —
// exatamente o mesmo formato nos dois fluxos (README, seções 3.1 e 3.2).

import type { MessageInputDTO } from './messageInput'
import type { ModelConfigDTO } from './modelConfig'

export interface DefaultInputDTO {
  message: MessageInputDTO
  llm_model_config: ModelConfigDTO
}
