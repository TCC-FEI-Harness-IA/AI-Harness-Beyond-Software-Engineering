// Resposta 200 de `POST /v1/message/default` (README, seção 3.1).

export interface DefaultOutputDTO {
  message: string
  response: string
  session_id: string
  tokens_input: number
  tokens_output: number
  inference_time_ms: number
}
