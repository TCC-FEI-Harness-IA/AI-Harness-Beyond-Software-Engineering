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
  /** Id da sessão que produziu esta mensagem. Opcional: só o fluxo simples precisa dele —
   * cada envio na mesma tela abre uma sessão nova (README, FASE 04, "Continuação da
   * conversa"), então cada mensagem do assistente carrega a sua própria sessão. */
  sessionId?: string | null
  /** Campos usados só no rodapé de `FinalAnswerCard` do Ralph (README, FASE 05, seção 9):
   * número de chamadas ao modelo, de tarefas, de tentativas e de janelas de contexto. */
  llmCalls?: number | null
  taskCount?: number | null
  attemptCount?: number | null
  contextCount?: number | null
}
