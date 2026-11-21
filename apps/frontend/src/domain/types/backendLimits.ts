/** Resposta de `GET /v1/limits`: limites do backend que toda requisição precisa respeitar. */
export interface BackendLimits {
  /** Limite de tokens por sessão do backend (`LLM_MAX_TOKENS`); o `max_tokens` pedido nunca passa dele. */
  max_tokens_limit: number
}
