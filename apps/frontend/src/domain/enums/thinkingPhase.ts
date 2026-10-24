// Espelha o campo `phase` do ReasoningEventDTO e da mensagem persistida (README, seções 3.2 e
// 3.4). `DIRECT` só aparece em mensagens persistidas do fluxo baseline — nunca em um evento ao
// vivo do WebSocket, que só existe no fluxo do harness.

export const THINKING_PHASE = {
  A1: 'A1',
  A2: 'A2',
  A3: 'A3',
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

export const PHASE_LABEL: Record<ThinkingPhase, string> = {
  A1: 'Critérios de aceite gerais',
  A2: 'Quebra em tarefas',
  A3: 'Aprendizados do enunciado',
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
  B1: 'B.1',
  B2: 'B.2',
  B3: 'B.3',
  B4: 'B.4',
  C1: 'C.1',
  C2: 'C.2',
  C3: 'C.3',
  DIRECT: 'Direta',
}
