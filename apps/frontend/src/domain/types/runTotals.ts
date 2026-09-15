// Totais agregados de uma execução (README, seção 6.3: "tokens, tempo de inferência, chamadas,
// tempo de parede"). Mesmo formato (em camelCase) do `totals` de `SessionDocument` (README,
// seção 3.4), para que a FASE 07 consiga mapear um documento persistido sem reformular o tipo.
export interface RunTotals {
  totalMessages: number
  totalLlmCalls: number
  tokensInput: number
  tokensOutput: number
  totalTokens: number
  inferenceTimeMs: number
  wallTimeMs: number
}
