// Espelha o campo `phase` do ReasoningEventDTO e da mensagem persistida (README, seções 3.2 e
// 3.4). `DIRECT` só aparece em mensagens persistidas do fluxo baseline — nunca em um evento ao
// vivo do WebSocket, que só existe no fluxo do harness. O significado de `A3` depende da versão do
// fluxo (`flowVersion.ts`): use `getPhaseLabel` sempre que o rótulo completo depender dela.

import { FLOW_VERSION, type FlowVersion } from './flowVersion'

export const THINKING_PHASE = {
  A1: 'A1',
  A2: 'A2',
  A3: 'A3',
  A4: 'A4',
  B1: 'B1',
  B2: 'B2',
  B3: 'B3',
  B4: 'B4',
  C1: 'C1',
  C2: 'C2',
  C3: 'C3',
  DIRECT: 'DIRECT',
} as const

export type ThinkingPhase = (typeof THINKING_PHASE)[keyof typeof THINKING_PHASE]

export const isThinkingPhase = (value: unknown): value is ThinkingPhase =>
  typeof value === 'string' && (Object.values(THINKING_PHASE) as string[]).includes(value)

// Rótulos do fluxo atual (versão 2). Nas sessões antigas (versão 1), `A3` registrou a extração dos
// aprendizados do enunciado: `getPhaseLabel` aplica essa exceção.
export const PHASE_LABEL: Record<ThinkingPhase, string> = {
  A1: 'Critérios de aceite gerais',
  A2: 'Quebra em tarefas',
  A3: 'Validação da decomposição',
  A4: 'Aprendizados do enunciado',
  B1: 'Resolução da tarefa',
  B2: 'Verificação dos critérios',
  B3: 'Armazenamento do resultado',
  B4: 'Extração de aprendizados',
  C1: 'Verificação global',
  C2: 'Planejamento adicional',
  C3: 'Resposta final',
  DIRECT: 'Inferência direta',
}

export const PHASE_SHORT_LABEL: Record<ThinkingPhase, string> = {
  A1: 'A.1',
  A2: 'A.2',
  A3: 'A.3',
  A4: 'A.4',
  B1: 'B.1',
  B2: 'B.2',
  B3: 'B.3',
  B4: 'B.4',
  C1: 'C.1',
  C2: 'C.2',
  C3: 'C.3',
  DIRECT: 'Direta',
}

const LEGACY_PHASE_LABEL: Partial<Record<ThinkingPhase, string>> = {
  A3: 'Aprendizados do enunciado',
}

/** Rótulo completo da fase segundo a versão do fluxo da sessão. */
export function getPhaseLabel(phase: ThinkingPhase, flowVersion: FlowVersion): string {
  if (flowVersion === FLOW_VERSION.LEGACY) return LEGACY_PHASE_LABEL[phase] ?? PHASE_LABEL[phase]
  return PHASE_LABEL[phase]
}
