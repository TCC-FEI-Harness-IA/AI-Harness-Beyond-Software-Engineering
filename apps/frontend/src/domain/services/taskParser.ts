// Extrai a estrutura de tarefas do markdown gerado por template fixo do backend em A.2/C.2, e
// os marcadores de decisão/critério de B.2 (README, FASE 05, seção 5). É texto produzido por um
// LLM através de um template — o formato é estável, mas nunca garantido: nenhuma função aqui
// lança, todas devolvem `null`/array vazio quando não reconhecem o formato.

export interface ParsedCriterion {
  id: string
  text: string
}

export interface ParsedTask {
  id: string
  title: string | null
  description: string | null
  expectedInput: string | null
  expectedOutput: string | null
  criteria: ParsedCriterion[]
}

export interface ParsedEvaluation {
  id: string
  met: boolean
  justification: string
}

// Cabeçalho de tarefa: "### T1 — Título" (o backend também usa hífen simples às vezes).
const TASK_HEADER_RE = /^###\s+(T\d+)\s*(?:—|-)\s*(.+)$/gm
const EXPECTED_INPUT_RE = /\*\*Entrada esperada:\*\*\s*(.+)/
const EXPECTED_OUTPUT_RE = /\*\*Saída esperada:\*\*\s*(.+)/
const CRITERIA_HEADER_RE = /\*\*Crit[ée]rios de aceite:\*\*/
const CRITERION_LINE_RE = /^-\s*`([^`]+)`\s*:\s*(.+)$/gm
const DECISION_RE = /\*\*Decisão:\*\*\s*`(approved|reproved)`/
const EVALUATION_LINE_RE = /^-\s*`([^`]+)`\s*—\s*(atendido|não atendido)\s*:\s*(.+)$/gm

function extractDescription(body: string): string | null {
  const trimmed = body.trim()
  const firstParagraph = trimmed.split(/\n\s*\n/)[0]?.trim()
  if (!firstParagraph || firstParagraph.startsWith('**')) return null
  return firstParagraph
}

function extractField(body: string, pattern: RegExp): string | null {
  const match = pattern.exec(body)
  return match?.[1]?.trim() ?? null
}

function extractCriteria(body: string): ParsedCriterion[] {
  const criteriaIndex = body.search(CRITERIA_HEADER_RE)
  if (criteriaIndex === -1) return []

  const section = body.slice(criteriaIndex)
  const criteria: ParsedCriterion[] = []
  for (const match of section.matchAll(CRITERION_LINE_RE)) {
    const id = match[1]
    const text = match[2]
    if (id && text) criteria.push({ id, text: text.trim() })
  }
  return criteria
}

/** Divide o markdown de A.2/C.2 em tarefas, por cabeçalhos `### T<n> — …`. */
export function parseTasksFromMarkdown(markdown: string): ParsedTask[] {
  const headers = [...markdown.matchAll(TASK_HEADER_RE)]
  if (headers.length === 0) return []

  return headers.map((header, index) => {
    const id = header[1] ?? ''
    const title = header[2]?.trim() ?? null
    const start = (header.index ?? 0) + header[0].length
    const end = headers[index + 1]?.index ?? markdown.length
    const body = markdown.slice(start, end)

    return {
      id,
      title,
      description: extractDescription(body),
      expectedInput: extractField(body, EXPECTED_INPUT_RE),
      expectedOutput: extractField(body, EXPECTED_OUTPUT_RE),
      criteria: extractCriteria(body),
    }
  })
}

/** Título da primeira tarefa encontrada — usado para rotular o passo sintético `execute`. */
export function parseTaskTitle(markdown: string): string | null {
  TASK_HEADER_RE.lastIndex = 0
  const match = TASK_HEADER_RE.exec(markdown)
  return match?.[2]?.trim() ?? null
}

/**
 * Reconhece o marcador fixo `**Decisão:** \`approved\`` / `\`reproved\`` de B.2 — o mesmo
 * marcador usado pela FASE 07 para derivar `verify_pass`/`verify_fail` no histórico
 * (README, seção 3.5): implementado aqui uma única vez, para ser reusado lá.
 */
export function parseDecision(markdown: string): 'approved' | 'reproved' | null {
  const match = DECISION_RE.exec(markdown)
  const decision = match?.[1]
  return decision === 'approved' || decision === 'reproved' ? decision : null
}

/** Lê as linhas `- \`T1-AC1\` — atendido: …` / `— não atendido: …` de uma verificação (B.2/C.1). */
export function parseCriterionEvaluations(markdown: string): ParsedEvaluation[] {
  const evaluations: ParsedEvaluation[] = []
  for (const match of markdown.matchAll(EVALUATION_LINE_RE)) {
    const id = match[1]
    const metText = match[2]
    const justification = match[3]
    if (id && metText && justification) {
      evaluations.push({ id, met: metText === 'atendido', justification: justification.trim() })
    }
  }
  return evaluations
}
