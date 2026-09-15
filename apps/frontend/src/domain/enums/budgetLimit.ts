// Espelha o campo `limit` de SessionDegradationDocument (README, seções 2 "Resiliência de
// custo" e 3.4).

export const BUDGET_LIMIT = {
  TASK_ATTEMPTS: 'task_attempts',
  ADDITIONAL_PLANNING_ROUNDS: 'additional_planning_rounds',
  TASKS_PER_SESSION: 'tasks_per_session',
  LLM_CALLS_PER_SESSION: 'llm_calls_per_session',
  SESSION_TOKEN_BUDGET: 'session_token_budget',
  SESSION_TIMEOUT: 'session_timeout',
} as const

export type BudgetLimit = (typeof BUDGET_LIMIT)[keyof typeof BUDGET_LIMIT]

export const isBudgetLimit = (value: unknown): value is BudgetLimit =>
  typeof value === 'string' && (Object.values(BUDGET_LIMIT) as string[]).includes(value)

export const BUDGET_LIMIT_LABEL: Record<BudgetLimit, string> = {
  task_attempts: 'Tentativas por tarefa',
  additional_planning_rounds: 'Rodadas de replanejamento',
  tasks_per_session: 'Tarefas por sessão',
  llm_calls_per_session: 'Chamadas ao modelo',
  session_token_budget: 'Orçamento de tokens',
  session_timeout: 'Tempo de parede',
}
