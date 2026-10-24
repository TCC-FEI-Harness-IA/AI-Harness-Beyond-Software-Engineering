// Espelha o campo `subtype` do ReasoningEventDTO (README, seção 3.2) e a mensagem persistida
// derivada (seção 3.5). Rótulo e tom vivem aqui para que nenhuma tela invente texto ou cor.

import { THINKING_PHASE, type ThinkingPhase } from './thinkingPhase'
import { TONE, type Tone } from './tone'

export const EVENT_SUBTYPE = {
  SETUP: 'setup',
  TASKS: 'tasks',
  EXECUTE: 'execute',
  REASONING: 'reasoning',
  VERIFY_PASS: 'verify_pass',
  VERIFY_FAIL: 'verify_fail',
  STORE: 'store',
  LEARN: 'learn',
  RESET: 'reset',
  COMPILE: 'compile',
  REPLAN: 'replan',
} as const

export type EventSubtype = (typeof EVENT_SUBTYPE)[keyof typeof EVENT_SUBTYPE]

export const isEventSubtype = (value: unknown): value is EventSubtype =>
  typeof value === 'string' && (Object.values(EVENT_SUBTYPE) as string[]).includes(value)

// Rótulo em português exibido na UI — vocabulário do paper (README, seção 2).
export const SUBTYPE_LABEL: Record<EventSubtype, string> = {
  setup: 'Critérios de aceite gerais',
  tasks: 'Quebra em tarefas',
  execute: 'Seleção da tarefa',
  reasoning: 'Resolução',
  verify_pass: 'Verificação aprovada',
  verify_fail: 'Verificação reprovada',
  store: 'Resultado armazenado',
  learn: 'Aprendizados extraídos',
  reset: 'Contexto reinicializado',
  compile: 'Compilação e verificação',
  replan: 'Planejamento adicional',
}

// O mesmo subtype `learn` é emitido por duas etapas: A.3 (aprendizados do enunciado, antes de
// qualquer tarefa) e B.4 (aprendizados de uma tarefa). O rótulo precisa dizer de qual se trata.
const PHASE_SUBTYPE_LABEL: Partial<Record<ThinkingPhase, Partial<Record<EventSubtype, string>>>> = {
  [THINKING_PHASE.A3]: { learn: 'Aprendizados do enunciado' },
}

/** Rótulo de um passo: o do `subtype`, ou o específico da etapa quando o subtype é compartilhado. */
export function getStepLabel(phase: ThinkingPhase, subtype: EventSubtype): string {
  return PHASE_SUBTYPE_LABEL[phase]?.[subtype] ?? SUBTYPE_LABEL[subtype]
}

// Tom semântico — precisa seguir a tabela da seção 8.3 do README (verificável, não decorativo).
export const SUBTYPE_TONE: Record<EventSubtype, Tone> = {
  setup: TONE.NEUTRAL,
  tasks: TONE.NEUTRAL,
  execute: TONE.NEUTRAL,
  reasoning: TONE.NEUTRAL,
  compile: TONE.NEUTRAL,
  verify_pass: TONE.SUCCESS,
  store: TONE.SUCCESS,
  verify_fail: TONE.WARNING,
  replan: TONE.WARNING,
  learn: TONE.NEUTRAL,
  reset: TONE.CONTEXT,
}
