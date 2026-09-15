// View-model normalizado das estatísticas de uma mensagem (README, FASE 03, seção 6). É o
// formato que `<MessageStats />` consome — nunca um DTO cru do backend. Os campos `null`
// são omitidos silenciosamente pelo componente (fluxo simples não tem contexto; etapas
// programáticas não têm tempo de inferência).

export interface MessageStatsView {
  modelName: string | null
  tokensInput: number | null
  tokensOutput: number | null
  totalTokens: number | null
  inferenceTimeMs: number | null
  contextId: string | null
  contextSize: number | null
  timestamp: string | null
}
