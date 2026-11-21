// Reconstrói o view-model `ThinkingRun` evento a evento (README, seção 6.2; FASE 05, seção 4).
// Função pura: não importa React nem nada de `src/api/`. É a peça de que as FASES 06 e 07
// dependem — por isso nunca lança, mesmo diante de uma sequência imperfeita de eventos: toda
// situação inesperada degrada graciosamente, preservando os passos já recebidos.

import { BUDGET_LIMIT } from '../enums/budgetLimit'
import { EVENT_SUBTYPE } from '../enums/eventSubtype'
import { EVENT_TYPE } from '../enums/eventType'
import { FLOW_VERSION, type FlowVersion } from '../enums/flowVersion'
import { RUN_STATUS } from '../enums/runStatus'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '../enums/taskLabels'
import { TASK_STATUS } from '../enums/taskStatus'
import { getPhaseLabel, THINKING_PHASE, type ThinkingPhase } from '../enums/thinkingPhase'
import type { ReasoningErrorFrame, ReasoningEventDTO } from '../types/reasoningEvent'
import type { RunError } from '../types/runError'
import type {
  PhaseNodeId,
  PhaseProgress,
  RunDegradation,
  TaskAttemptView,
  TaskTimeline,
  ThinkingRun,
  ThinkingStep,
} from '../types/thinkingRun'
import { parseTaskTitle, parseTasksFromMarkdown } from './taskParser'

export type RunAction =
  | { kind: 'event'; event: ReasoningEventDTO }
  | { kind: 'errorFrame'; frame: ReasoningErrorFrame }
  | { kind: 'failure'; error: RunError }
  | { kind: 'closed'; code: number }
  /** Frame isolado que não pôde ser lido — não fatal (FASE 08, seção 4): o stream continua. */
  | { kind: 'warning'; message: string }

// A trilha depende da versão do fluxo: na versão 1, A.3 era a extração dos aprendizados do enunciado e não
// havia A.4; na versão 2, A.3 valida a decomposição e A.4 extrai os aprendizados (nova fase de validação).
const PHASE_NODE_ORDER: Record<FlowVersion, PhaseNodeId[]> = {
  [FLOW_VERSION.LEGACY]: ['A1', 'A2', 'A3', 'B', 'C1', 'C2', 'C3'],
  [FLOW_VERSION.VALIDATED_PLANNING]: ['A1', 'A2', 'A3', 'A4', 'B', 'C1', 'C2', 'C3'],
}

const B_NODE_LABEL = 'Execução em loop'

function nodeLabel(id: PhaseNodeId, flowVersion: FlowVersion): string {
  return id === 'B' ? B_NODE_LABEL : getPhaseLabel(id, flowVersion)
}

function emptyPhases(flowVersion: FlowVersion): PhaseProgress[] {
  return PHASE_NODE_ORDER[flowVersion].map((id) => ({
    id,
    label: nodeLabel(id, flowVersion),
    status: 'pending',
    stepCount: 0,
  }))
}

function nodeForPhase(phase: ThinkingPhase): PhaseNodeId | null {
  switch (phase) {
    case THINKING_PHASE.A1:
      return 'A1'
    case THINKING_PHASE.A2:
      return 'A2'
    case THINKING_PHASE.A3:
      return 'A3'
    case THINKING_PHASE.A4:
      return 'A4'
    case THINKING_PHASE.B1:
    case THINKING_PHASE.B2:
    case THINKING_PHASE.B3:
    case THINKING_PHASE.B4:
      return 'B'
    case THINKING_PHASE.C1:
      return 'C1'
    case THINKING_PHASE.C2:
      return 'C2'
    case THINKING_PHASE.C3:
      return 'C3'
    // Defensivo: `ThinkingPhase` já cobre os 11 valores acima na fronteira (parsers), então este
    // ramo nunca é alcançado com dados validados — existe só para a função ser total.
    /* v8 ignore next 2 */
    default:
      return null
  }
}

/**
 * `ThinkingRun` vazio — estado inicial do hook e o que `reset()` devolve (FASE 05, seção 3). Uma
 * execução ao vivo começa na versão atual; o primeiro evento confirma a versão que o backend informou.
 */
export function createEmptyRun(
  question: string,
  modelName: string,
  flowVersion: FlowVersion = FLOW_VERSION.VALIDATED_PLANNING,
): ThinkingRun {
  return {
    sessionId: null,
    flowVersion,
    question,
    modelName,
    status: RUN_STATUS.IDLE,
    steps: [],
    tasks: [],
    phases: emptyPhases(flowVersion),
    finalAnswer: null,
    totals: {
      totalTokens: 0,
      inferenceTimeMs: 0,
      llmCalls: 0,
      taskCount: 0,
      attemptCount: 0,
      contextCount: 0,
      wallTimeMs: null,
    },
    degradations: [],
    error: null,
    warning: null,
  }
}

function buildStepId(order: number, phase: string, subtype: string, taskId: string): string {
  return `${order}:${phase}:${subtype}:${taskId}`
}

function toStep(event: ReasoningEventDTO, order: number): ThinkingStep {
  return {
    id: buildStepId(order, event.phase, event.subtype, event.task),
    order,
    type: event.type,
    subtype: event.subtype,
    phase: event.phase,
    taskId: event.task,
    content: event.content,
    totalTokens: event.total_tokens,
    contextId: event.context_window.context_id,
    contextSize: event.context_window.context_size,
    inferenceTimeMs: event.inference_time_ms,
    timestamp: null,
  }
}

function isNonTask(taskId: string): boolean {
  return taskId === TASK_LABEL_SETUP || taskId === TASK_LABEL_SYNTHESIS
}

function findTaskIndex(tasks: TaskTimeline[], taskId: string): number {
  return tasks.findIndex((task) => task.id === taskId)
}

function emptyAttempt(index: number): TaskAttemptView {
  return { index, reasoning: null, verification: null, approved: null }
}

function hasOpenAttempt(task: TaskTimeline): boolean {
  const last = task.attempts[task.attempts.length - 1]
  return last !== undefined && last.approved === null
}

// Robustez 1 (FASE 05, seção 4.2): evento de uma tarefa desconhecida cria a tarefa na hora,
// em vez de descartar o passo.
function ensureTask(tasks: TaskTimeline[], taskId: string, origin: 'A2' | 'C2'): TaskTimeline[] {
  if (findTaskIndex(tasks, taskId) !== -1) return tasks
  const created: TaskTimeline = {
    id: taskId,
    title: null,
    status: TASK_STATUS.PENDING,
    origin,
    attempts: [],
    steps: [],
    contextIds: [],
    tokens: 0,
    inferenceTimeMs: 0,
  }
  return [...tasks, created]
}

function updateTask(
  tasks: TaskTimeline[],
  taskId: string,
  updater: (task: TaskTimeline) => TaskTimeline,
): TaskTimeline[] {
  return tasks.map((task) => (task.id === taskId ? updater(task) : task))
}

// Custo marginal do próprio passo, derivado do delta do total acumulado da sessão — é o que
// permite atribuir tokens a uma tarefa sem o backend precisar mandar esse campo (não manda).
function appendStepToTask(task: TaskTimeline, step: ThinkingStep, marginalTokens: number): TaskTimeline {
  return {
    ...task,
    steps: [...task.steps, step],
    tokens: task.tokens + marginalTokens,
    inferenceTimeMs: task.inferenceTimeMs + step.inferenceTimeMs,
  }
}

function tasksFromMarkdown(content: string, origin: 'A2' | 'C2'): TaskTimeline[] {
  return parseTasksFromMarkdown(content).map((task) => ({
    id: task.id,
    title: task.title,
    status: TASK_STATUS.PENDING,
    origin,
    attempts: [],
    steps: [],
    contextIds: [],
    tokens: 0,
    inferenceTimeMs: 0,
  }))
}

function applyReset(run: ThinkingRun, event: ReasoningEventDTO, step: ThinkingStep, marginalTokens: number): ThinkingRun {
  const taskId = event.task
  let tasks = ensureTask(run.tasks, taskId, 'A2')
  tasks = updateTask(tasks, taskId, (task) => {
    const withStep = appendStepToTask(task, step, marginalTokens)
    const contextIds = withStep.contextIds.includes(step.contextId)
      ? withStep.contextIds
      : [...withStep.contextIds, step.contextId]
    const attempts = hasOpenAttempt(withStep)
      ? withStep.attempts
      : [...withStep.attempts, emptyAttempt(withStep.attempts.length + 1)]
    return { ...withStep, status: TASK_STATUS.RUNNING, contextIds, attempts }
  })
  return { ...run, tasks }
}

function applyExecute(run: ThinkingRun, event: ReasoningEventDTO, step: ThinkingStep, marginalTokens: number): ThinkingRun {
  const taskId = event.task
  let tasks = ensureTask(run.tasks, taskId, 'A2')
  tasks = updateTask(tasks, taskId, (task) => {
    const withStep = appendStepToTask(task, step, marginalTokens)
    const title = withStep.title ?? parseTaskTitle(event.content)
    return { ...withStep, title }
  })
  return { ...run, tasks }
}

function applyReasoning(run: ThinkingRun, event: ReasoningEventDTO, step: ThinkingStep, marginalTokens: number): ThinkingRun {
  const taskId = event.task
  let tasks = ensureTask(run.tasks, taskId, 'A2')
  tasks = updateTask(tasks, taskId, (task) => {
    const withStep = appendStepToTask(task, step, marginalTokens)
    // Retentativa dentro do mesmo contexto não emite `reset` — se não houver tentativa
    // aberta, uma precisa ser aberta aqui (FASE 05, seção 4.1, linha `reasoning`).
    const attempts = hasOpenAttempt(withStep)
      ? withStep.attempts
      : [...withStep.attempts, emptyAttempt(withStep.attempts.length + 1)]
    const lastIndex = attempts.length - 1
    const updatedAttempts = attempts.map((attempt, index) =>
      index === lastIndex ? { ...attempt, reasoning: step } : attempt,
    )
    return { ...withStep, attempts: updatedAttempts }
  })
  return { ...run, tasks }
}

function applyVerify(
  run: ThinkingRun,
  event: ReasoningEventDTO,
  step: ThinkingStep,
  marginalTokens: number,
  approved: boolean,
): ThinkingRun {
  const taskId = event.task
  let tasks = ensureTask(run.tasks, taskId, 'A2')
  tasks = updateTask(tasks, taskId, (task) => {
    const withStep = appendStepToTask(task, step, marginalTokens)
    // Robustez 2: `verify_pass`/`verify_fail` sem tentativa aberta cria uma tentativa
    // fechada com `reasoning: null`, em vez de lançar ou descartar o passo.
    let attempts = hasOpenAttempt(withStep)
      ? withStep.attempts
      : [...withStep.attempts, emptyAttempt(withStep.attempts.length + 1)]
    const lastIndex = attempts.length - 1
    attempts = attempts.map((attempt, index) =>
      index === lastIndex ? { ...attempt, verification: step, approved } : attempt,
    )
    // Reprovado volta para B.1 no mesmo contexto — a UI precisa mostrar a tentativa
    // seguinte já aberta (FASE 05, seção 4.1, linha `verify_fail`).
    if (!approved) {
      attempts = [...attempts, emptyAttempt(attempts.length + 1)]
    }
    return { ...withStep, attempts }
  })
  return { ...run, tasks }
}

function applyStore(run: ThinkingRun, event: ReasoningEventDTO, step: ThinkingStep, marginalTokens: number): ThinkingRun {
  const taskId = event.task
  // Robustez 3: `store` sem tarefa conhecida ignora o efeito, mas o passo já foi anexado
  // a `run.steps` por `applyEvent` antes desta função ser chamada.
  if (findTaskIndex(run.tasks, taskId) === -1) return run
  const tasks = updateTask(run.tasks, taskId, (task) => ({
    ...appendStepToTask(task, step, marginalTokens),
    status: TASK_STATUS.APPROVED,
  }))
  return { ...run, tasks }
}

function applyLearn(run: ThinkingRun, event: ReasoningEventDTO, step: ThinkingStep, marginalTokens: number): ThinkingRun {
  const taskId = event.task
  // `learn` também é emitido por A.3, com o rótulo global `setup`: são os aprendizados do
  // enunciado, que não pertencem a nenhuma tarefa. O passo já está em `run.steps`; não há
  // tarefa a criar nem a atualizar.
  if (isNonTask(taskId)) return run
  let tasks = ensureTask(run.tasks, taskId, 'A2')
  tasks = updateTask(tasks, taskId, (task) => appendStepToTask(task, step, marginalTokens))
  return { ...run, tasks }
}

function applyCompile(run: ThinkingRun, event: ReasoningEventDTO): ThinkingRun {
  // O evento `error` do domínio também usa `compile` e a fase em que a execução parou: uma falha em C.3
  // não é uma resposta final.
  if (event.phase !== THINKING_PHASE.C3 || event.type === EVENT_TYPE.ERROR) return run

  const finalAnswer = event.content
  // Uma degradação anterior não pode ser apagada pela chegada do resultado final — o cartão
  // precisa continuar sinalizando "concluído com degradação" (FASE 05, seção 9).
  const status =
    event.type === EVENT_TYPE.RESULT
      ? run.status === RUN_STATUS.DEGRADED
        ? RUN_STATUS.DEGRADED
        : RUN_STATUS.COMPLETED
      : run.status

  return { ...run, finalAnswer, status }
}

function extractLimit(content: string): string {
  return Object.values(BUDGET_LIMIT).find((limit) => content.includes(limit)) ?? ''
}

function applyDegraded(run: ThinkingRun, event: ReasoningEventDTO): ThinkingRun {
  const degradation: RunDegradation = {
    limit: extractLimit(event.content),
    phase: event.phase,
    taskId: isNonTask(event.task) ? null : event.task,
    description: event.content,
    occurredAt: null,
  }

  let tasks = run.tasks
  if (!isNonTask(event.task)) {
    tasks = ensureTask(tasks, event.task, 'A2')
    tasks = updateTask(tasks, event.task, (task) => ({ ...task, status: TASK_STATUS.DEGRADED }))
  }

  return {
    ...run,
    tasks,
    degradations: [...run.degradations, degradation],
    status: RUN_STATUS.DEGRADED,
  }
}

function recalcAggregates(run: ThinkingRun): ThinkingRun {
  return {
    ...run,
    totals: {
      ...run.totals,
      taskCount: run.tasks.length,
      attemptCount: run.tasks.reduce((sum, task) => sum + task.attempts.length, 0),
    },
  }
}

function computeStepCounts(steps: ThinkingStep[]): Record<PhaseNodeId, number> {
  const counts: Record<PhaseNodeId, number> = { A1: 0, A2: 0, A3: 0, A4: 0, B: 0, C1: 0, C2: 0, C3: 0 }
  for (const step of steps) {
    const node = nodeForPhase(step.phase)
    if (node) counts[node] += 1
  }
  return counts
}

// Recomputa a trilha macro inteira a partir do histórico de passos — mais simples e mais
// robusto que manter estado incremental, e satisfaz por construção a regra de que um replan
// não pode "desfazer" o progresso já mostrado (FASE 05, seção 4.3).
function recalcPhases(run: ThinkingRun): ThinkingRun {
  const counts = computeStepCounts(run.steps)
  const lastStep = run.steps[run.steps.length - 1]
  // `recalcPhases` só é chamada por `applyEvent`, depois de anexar o passo recebido — `run.steps`
  // nunca está vazio neste ponto. O `? :` é defensivo contra `noUncheckedIndexedAccess`.
  /* v8 ignore next */
  const lastNode = lastStep ? nodeForPhase(lastStep.phase) : null
  const hasC3 = counts.C3 > 0
  const hasC2 = counts.C2 > 0
  const hasLoopStarted = counts.B + counts.C1 + counts.C2 + counts.C3 > 0

  const legacy = run.flowVersion === FLOW_VERSION.LEGACY
  const phases: PhaseProgress[] = PHASE_NODE_ORDER[run.flowVersion].map((id) => {
    const stepCount = counts[id]
    let status: PhaseProgress['status']

    if (id === 'C2' && hasC3 && !hasC2) {
      // Caminho feliz do paper: C2 existia no fluxo e não foi necessário — mostrado como
      // "pulado", nunca escondido (FASE 05, seção 4.3).
      status = 'skipped'
    } else if (legacy && id === 'A3' && stepCount === 0 && hasLoopStarted) {
      // Sessão versão 1 anterior à etapa de aprendizados do enunciado: o loop já rodou sem ela. Aparece
      // como "não necessária" em vez de ficar eternamente pendente. Na versão 2, A.3 e A.4 sempre
      // precedem o loop.
      status = 'skipped'
    } else if (stepCount === 0) {
      status = 'pending'
    } else if (id === lastNode) {
      status = 'active'
    } else {
      status = 'done'
    }

    return { id, label: nodeLabel(id, run.flowVersion), status, stepCount }
  })

  return { ...run, phases }
}

// A versão do fluxo vem do frame e precede a interpretação das fases: o mesmo `A3` é validação na versão 2
// e extração na versão 1. Ao mudar de versão, a trilha é refeita com os nós da versão informada.
function withFlowVersion(run: ThinkingRun, flowVersion: FlowVersion): ThinkingRun {
  if (run.flowVersion === flowVersion) return run
  return { ...run, flowVersion, phases: emptyPhases(flowVersion) }
}

function applyEvent(current: ThinkingRun, event: ReasoningEventDTO): ThinkingRun {
  const run = withFlowVersion(current, event.flow_version)
  const order = run.steps.length
  const step = toStep(event, order)
  const previousStep = run.steps[run.steps.length - 1]
  const marginalTokens = Math.max(0, event.total_tokens - run.totals.totalTokens)
  const contextChanged = previousStep === undefined || previousStep.contextId !== step.contextId
  // O evento terminal `result` repete o conteúdo e o tempo da chamada de C.3, já contada no `thinking/compile`:
  // não é uma nova chamada nem um novo consumo.
  const isTerminalEcho = event.type === EVENT_TYPE.RESULT
  const inferenceTimeMs = isTerminalEcho ? 0 : event.inference_time_ms
  const llmCallDelta = inferenceTimeMs > 0 ? 1 : 0

  let next: ThinkingRun = {
    ...run,
    // Um frame válido depois de um aviso confirma que o stream se recuperou.
    warning: null,
    sessionId: run.sessionId ?? event.session_id,
    steps: [...run.steps, step],
    totals: {
      ...run.totals,
      // O backend manda o acumulado da sessão inteira — substitui, nunca soma (e nunca
      // decresce; o `Math.max` é só uma salvaguarda contra um frame fora de ordem).
      totalTokens: Math.max(run.totals.totalTokens, event.total_tokens),
      inferenceTimeMs: run.totals.inferenceTimeMs + inferenceTimeMs,
      llmCalls: run.totals.llmCalls + llmCallDelta,
      contextCount: run.totals.contextCount + (contextChanged ? 1 : 0),
    },
  }

  switch (event.subtype) {
    case EVENT_SUBTYPE.TASKS:
      // Única entrada do plano inicial nas tarefas: na versão 2, a confirmação depois da aprovação de A.3.
      next = { ...next, tasks: [...next.tasks, ...tasksFromMarkdown(event.content, 'A2')] }
      break
    case EVENT_SUBTYPE.REPLAN:
      // A ordem de exibição segue a ordem real dos eventos — não reordena a fila.
      next = { ...next, tasks: [...next.tasks, ...tasksFromMarkdown(event.content, 'C2')] }
      break
    case EVENT_SUBTYPE.RESET:
      next = applyReset(next, event, step, marginalTokens)
      break
    case EVENT_SUBTYPE.EXECUTE:
      next = applyExecute(next, event, step, marginalTokens)
      break
    case EVENT_SUBTYPE.REASONING:
      next = applyReasoning(next, event, step, marginalTokens)
      break
    case EVENT_SUBTYPE.VERIFY_PASS:
      next = applyVerify(next, event, step, marginalTokens, true)
      break
    case EVENT_SUBTYPE.VERIFY_FAIL:
      next = applyVerify(next, event, step, marginalTokens, false)
      break
    case EVENT_SUBTYPE.STORE:
      next = applyStore(next, event, step, marginalTokens)
      break
    case EVENT_SUBTYPE.LEARN:
      next = applyLearn(next, event, step, marginalTokens)
      break
    case EVENT_SUBTYPE.COMPILE:
      next = applyCompile(next, event)
      break
    case EVENT_SUBTYPE.SETUP:
    default:
      // `setup`, os passos do planejamento validado (`plan_candidate`, `plan_approved`, `plan_rejected`
      // — um candidato nunca vira tarefa nem conta no progresso) e qualquer subtype não mapeado (a
      // FASE 02 já normaliza para `reasoning` na fronteira): nada além do passo, já anexado acima.
      break
  }

  if (event.type === EVENT_TYPE.DEGRADED) {
    next = applyDegraded(next, event)
  } else if (event.type === EVENT_TYPE.ERROR) {
    next = {
      ...next,
      status: RUN_STATUS.FAILED,
      error: { message: event.content, userMessage: event.content },
    }
  }

  next = recalcAggregates(next)
  next = recalcPhases(next)

  return next
}

function applyErrorFrame(run: ThinkingRun, frame: ReasoningErrorFrame): ThinkingRun {
  return { ...run, status: RUN_STATUS.FAILED, error: { message: frame.content, userMessage: frame.content } }
}

function applyFailure(run: ThinkingRun, error: RunError): ThinkingRun {
  return { ...run, status: RUN_STATUS.FAILED, error }
}

function applyWarning(run: ThinkingRun, message: string): ThinkingRun {
  return { ...run, warning: message }
}

function applyClosed(run: ThinkingRun, code: number): ThinkingRun {
  // Fechamento 1000 é sucesso (README, FASE 05, seção 6). Um fechamento com outro código já
  // vem acompanhado de um frame de erro que define `status`/`error` — nada a fazer aqui.
  if (code === 1000 && run.status === RUN_STATUS.RUNNING) {
    return { ...run, status: RUN_STATUS.COMPLETED }
  }
  return run
}

/** Transforma a sequência de eventos do WebSocket no view-model `ThinkingRun`. Nunca lança. */
export function reasoningRunReducer(run: ThinkingRun, action: RunAction): ThinkingRun {
  try {
    switch (action.kind) {
      case 'event':
        return applyEvent(run, action.event)
      case 'errorFrame':
        return applyErrorFrame(run, action.frame)
      case 'failure':
        return applyFailure(run, action.error)
      case 'warning':
        return applyWarning(run, action.message)
      case 'closed':
        return applyClosed(run, action.code)
      default:
        return run
    }
  } catch (error) {
    console.error('[reasoningRunReducer] falha inesperada ao processar ação; run preservado', error)
    return run
  }
}
