import type { BenchmarkDetails } from './benchmarkDetails'
// `GET /v1/sessions/{session_id}` (README, seção 3.4). A mensagem persistida não tem
// `subtype` — a derivação vive em `domain/services/deriveSubtype.ts` (FASE 07).

import type { BudgetLimit } from '../enums/budgetLimit'
import type { EventSubtype } from '../enums/eventSubtype'
import type { FlowVersion } from '../enums/flowVersion'
import type { MessageSource } from '../enums/messageSource'
import type { SessionStatus } from '../enums/sessionStatus'
import type { ThinkingPhase } from '../enums/thinkingPhase'

export interface SessionMessageDocument {
  id: string
  order: number
  timestamp: string
  phase: ThinkingPhase
  source: MessageSource
  content: string
  task_id: string | null
  context_id: string | null
  tokens_input: number
  tokens_output: number
  total_tokens: number
  inference_time_ms: number
  model_name: string | null
  /** Subtipo do evento emitido com a mensagem; `null` em registros sem evento e em sessões antigas. */
  subtype?: EventSubtype | null
}

export interface SessionTotalsDocument {
  total_messages: number
  total_llm_calls: number
  tokens_input: number
  tokens_output: number
  total_tokens: number
  inference_time_ms: number
  wall_time_ms: number
}

export interface SessionDegradationDocument {
  limit: BudgetLimit
  phase: string
  task_id: string | null
  description: string
  occurred_at: string
}

export interface SessionDocument {
  benchmark_details?: BenchmarkDetails
  id: string
  user_question: string
  flow: ThinkingPhase
  /** Versão do fluxo Ralph; sessões Ralph antigas sem o campo são versão 1, a inferência direta é `null`. */
  flow_version: FlowVersion | null
  model_name: string
  max_tokens: number
  temperature: number
  status: SessionStatus
  created_at: string
  updated_at: string
  final_answer: string | null
  totals: SessionTotalsDocument
  messages: SessionMessageDocument[]
  degradations: SessionDegradationDocument[]
}
