import type { BenchmarkDetails } from './benchmarkDetails'
// View-model de um card de histórico (README, FASE 07, seções 4 e 5). `question` já vem
// truncada pelo limite de `env` (aplicado em `useSessionList`, camada de hooks — este tipo de
// domínio não conhece `env`); `fullQuestion` é o texto completo, usado no `title` do card.
import type { SessionStatus } from '../enums/sessionStatus'

export interface SessionSummaryView {
  benchmarkDetails?: BenchmarkDetails | null
  id: string
  question: string
  fullQuestion: string
  flow: 'simple' | 'ralph'
  status: SessionStatus
  createdAt: string
  totalTokens: number
  messageCount: number
}
