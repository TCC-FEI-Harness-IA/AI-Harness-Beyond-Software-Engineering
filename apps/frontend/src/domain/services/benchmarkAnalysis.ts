// Análise pareada Simples × Ralph Loop sobre uma ou mais baterias de benchmark. Funções puras, sem
// React: a página de análise só desenha o que sai daqui. Cada observação é uma questão de uma
// bateria em que os dois fluxos terminaram; a mesma questão em baterias diferentes conta duas vezes.

import type {
  BenchmarkDatasetId,
  BenchmarkFlowOutcome,
  BenchmarkSessionDocument,
  GPQASubset,
} from '../types/benchmarkSession'
import {
  benchmarkDatasetLabel,
  benchmarkSubjectLabel,
  GPQA_SUBSET_LABELS,
} from './benchmarkDefinition'
import { formatDateTime } from './formatters'

/** Desfecho do par: o que o Ralph Loop fez com a questão em relação à inferência simples. */
export type PairOutcome = 'both_correct' | 'ralph_recovers' | 'ralph_regresses' | 'both_wrong'

export const PAIR_OUTCOME_LABEL: Record<PairOutcome, string> = {
  both_correct: 'Ambos acertam',
  ralph_recovers: 'Ralph corrige',
  ralph_regresses: 'Ralph piora',
  both_wrong: 'Ambos erram',
}

export interface AnalysisRecord {
  /** `${benchmarkSessionId}:${questionId}` — único entre as baterias selecionadas. */
  key: string
  benchmarkSessionId: string
  executionLabel: string
  dataset: BenchmarkDatasetId
  questionId: string
  subject: string | null
  expected: string
  simple: BenchmarkFlowOutcome
  ralph: BenchmarkFlowOutcome
  outcome: PairOutcome
  /** Quartil (1–4) dos tokens da inferência simples dentro da própria bateria. */
  simpleEffortQuartile: number
  /** Quartil (1–4) dos tokens do Ralph Loop dentro da própria bateria. */
  ralphEffortQuartile: number
}

export interface AnalysisExclusions {
  /** Questões em que ao menos um fluxo não terminou (pendente, em execução ou interrompida). */
  unpaired: number
  /** Questões descartadas por falha técnica, quando o filtro está ligado. */
  failures: number
}

export interface BuildRecordsOptions {
  /** Descarta a questão se algum dos fluxos terminou com falha técnica ou resposta inválida. */
  excludeFailures?: boolean
}

export function executionLabel(session: BenchmarkSessionDocument): string {
  return (
    session.alias ??
    `${benchmarkDatasetLabel(session.benchmark.dataset)} · ${formatDateTime(session.created_at)}`
  )
}

export function pairOutcome(simpleCorrect: boolean, ralphCorrect: boolean): PairOutcome {
  if (simpleCorrect) return ralphCorrect ? 'both_correct' : 'ralph_regresses'
  return ralphCorrect ? 'ralph_recovers' : 'both_wrong'
}

/** Cortes de quartil pela posição mais próxima; valores empatados ficam sempre no mesmo quartil. */
export function quartileOf(value: number, sortedValues: readonly number[]): number {
  const cut = (fraction: number): number =>
    sortedValues[Math.max(0, Math.ceil(fraction * sortedValues.length) - 1)] as number
  if (value <= cut(0.25)) return 1
  if (value <= cut(0.5)) return 2
  if (value <= cut(0.75)) return 3
  return 4
}

const ascending = (left: number, right: number): number => left - right

export function buildAnalysisRecords(
  sessions: readonly BenchmarkSessionDocument[],
  { excludeFailures = false }: BuildRecordsOptions = {},
): { records: AnalysisRecord[]; exclusions: AnalysisExclusions } {
  const exclusions: AnalysisExclusions = { unpaired: 0, failures: 0 }
  const records: AnalysisRecord[] = []

  for (const session of sessions) {
    const pairs: Array<{ questionId: string; subject: string | null; expected: string; simple: BenchmarkFlowOutcome; ralph: BenchmarkFlowOutcome }> = []
    for (const question of session.questions) {
      const { simple, ralph } = question
      if (simple === null || ralph === null) {
        exclusions.unpaired += 1
        continue
      }
      if (excludeFailures && (simple.error !== null || ralph.error !== null)) {
        exclusions.failures += 1
        continue
      }
      pairs.push({
        questionId: question.question_id,
        subject: question.subject,
        expected: question.expected_alternative,
        simple,
        ralph,
      })
    }

    const simpleTokens = pairs.map((pair) => pair.simple.total_tokens).sort(ascending)
    const ralphTokens = pairs.map((pair) => pair.ralph.total_tokens).sort(ascending)
    const label = executionLabel(session)
    for (const pair of pairs) {
      records.push({
        key: `${session.id}:${pair.questionId}`,
        benchmarkSessionId: session.id,
        executionLabel: label,
        dataset: session.benchmark.dataset,
        ...pair,
        outcome: pairOutcome(pair.simple.is_correct, pair.ralph.is_correct),
        simpleEffortQuartile: quartileOf(pair.simple.total_tokens, simpleTokens),
        ralphEffortQuartile: quartileOf(pair.ralph.total_tokens, ralphTokens),
      })
    }
  }

  return { records, exclusions }
}

// ─── Estatística ──────────────────────────────────────────────────────────────

const Z_95 = 1.959963984540054

/** Intervalo de Wilson a 95% para uma proporção; `[0, 0]` sem observações. */
export function wilsonInterval(successes: number, total: number): [number, number] {
  if (total === 0) return [0, 0]
  const proportion = successes / total
  const zSquared = Z_95 * Z_95
  const denominator = 1 + zSquared / total
  const center = (proportion + zSquared / (2 * total)) / denominator
  const margin =
    (Z_95 * Math.sqrt((proportion * (1 - proportion)) / total + zSquared / (4 * total * total))) /
    denominator
  return [Math.max(0, center - margin), Math.min(1, center + margin)]
}

/**
 * Teste exato de McNemar (bicaudal) sobre os pares discordantes: `b` = Ralph piora, `c` = Ralph
 * corrige. Sob H0 cada discordância cai para um lado com probabilidade 1/2. Sem discordâncias, 1.
 */
export function mcnemarExactPValue(b: number, c: number): number {
  const n = b + c
  if (n === 0) return 1
  const logFactorial: number[] = [0]
  for (let index = 1; index <= n; index += 1) {
    logFactorial.push((logFactorial[index - 1] as number) + Math.log(index))
  }
  const logHalfPowerN = n * Math.log(0.5)
  let tail = 0
  for (let k = 0; k <= Math.min(b, c); k += 1) {
    const logCombination =
      (logFactorial[n] as number) - (logFactorial[k] as number) - (logFactorial[n - k] as number)
    tail += Math.exp(logCombination + logHalfPowerN)
  }
  return Math.min(1, 2 * tail)
}

// ─── Resumo pareado ───────────────────────────────────────────────────────────

export interface PairedSummary {
  n: number
  bothCorrect: number
  recoveries: number
  regressions: number
  bothWrong: number
  simpleCorrect: number
  ralphCorrect: number
  simpleAccuracy: number
  ralphAccuracy: number
  simpleInterval: [number, number]
  ralphInterval: [number, number]
  /** Acurácia do Ralph menos a da simples, como fração (0,05 = +5 p.p.). */
  delta: number
  /** Entre as questões que a simples errou, a fração que o Ralph acertou. `null` sem erros da simples. */
  recoveryRate: number | null
  /** Entre as questões que a simples acertou, a fração que o Ralph errou. `null` sem acertos da simples. */
  regressionRate: number | null
  /** Correções menos pioras. */
  netGain: number
  /** Redução relativa do erro: (erros simples − erros Ralph) / erros simples. */
  errorReduction: number | null
  mcnemarPValue: number
  simpleFailures: number
  ralphFailures: number
  /** Questões em que os fluxos escolheram alternativas diferentes. */
  answerChanged: number
  /** Questões erradas pelos dois fluxos com a mesma alternativa. */
  bothWrongSameAnswer: number
  simpleTokens: number
  ralphTokens: number
  simpleSeconds: number
  ralphSeconds: number
  /** Tokens do Ralph ÷ tokens da simples. */
  tokenMultiplier: number | null
  /** Tokens adicionais do Ralph por acerto líquido ganho; `null` sem ganho líquido. */
  extraTokensPerNetGain: number | null
}

const ratio = (numerator: number, denominator: number): number | null =>
  denominator === 0 ? null : numerator / denominator

export function summarizePairs(records: readonly AnalysisRecord[]): PairedSummary {
  const counts: Record<PairOutcome, number> = {
    both_correct: 0,
    ralph_recovers: 0,
    ralph_regresses: 0,
    both_wrong: 0,
  }
  let simpleFailures = 0
  let ralphFailures = 0
  let answerChanged = 0
  let bothWrongSameAnswer = 0
  let simpleTokens = 0
  let ralphTokens = 0
  let simpleSeconds = 0
  let ralphSeconds = 0

  for (const record of records) {
    counts[record.outcome] += 1
    if (record.simple.error !== null) simpleFailures += 1
    if (record.ralph.error !== null) ralphFailures += 1
    const sameAnswer = record.simple.selected_alternative === record.ralph.selected_alternative
    if (!sameAnswer) answerChanged += 1
    if (record.outcome === 'both_wrong' && sameAnswer) bothWrongSameAnswer += 1
    simpleTokens += record.simple.total_tokens
    ralphTokens += record.ralph.total_tokens
    simpleSeconds += record.simple.duration_seconds
    ralphSeconds += record.ralph.duration_seconds
  }

  const n = records.length
  const simpleCorrect = counts.both_correct + counts.ralph_regresses
  const ralphCorrect = counts.both_correct + counts.ralph_recovers
  const simpleErrors = n - simpleCorrect
  const netGain = counts.ralph_recovers - counts.ralph_regresses

  return {
    n,
    bothCorrect: counts.both_correct,
    recoveries: counts.ralph_recovers,
    regressions: counts.ralph_regresses,
    bothWrong: counts.both_wrong,
    simpleCorrect,
    ralphCorrect,
    simpleAccuracy: ratio(simpleCorrect, n) ?? 0,
    ralphAccuracy: ratio(ralphCorrect, n) ?? 0,
    simpleInterval: wilsonInterval(simpleCorrect, n),
    ralphInterval: wilsonInterval(ralphCorrect, n),
    delta: ratio(netGain, n) ?? 0,
    recoveryRate: ratio(counts.ralph_recovers, simpleErrors),
    regressionRate: ratio(counts.ralph_regresses, simpleCorrect),
    netGain,
    errorReduction: ratio(simpleErrors - (n - ralphCorrect), simpleErrors),
    mcnemarPValue: mcnemarExactPValue(counts.ralph_regresses, counts.ralph_recovers),
    simpleFailures,
    ralphFailures,
    answerChanged,
    bothWrongSameAnswer,
    simpleTokens,
    ralphTokens,
    simpleSeconds,
    ralphSeconds,
    tokenMultiplier: ratio(ralphTokens, simpleTokens),
    extraTokensPerNetGain: netGain > 0 ? (ralphTokens - simpleTokens) / netGain : null,
  }
}

// ─── Dimensões de quebra ──────────────────────────────────────────────────────

export type AnalysisDimension =
  | 'execution'
  | 'dataset'
  | 'subject'
  | 'area'
  | 'level'
  | 'simpleEffort'
  | 'ralphEffort'

export interface GroupKey {
  key: string
  label: string
  /** Ordem natural do grupo (nível, quartil); grupos sem ordem natural usam 0 e o rótulo desempata. */
  order: number
}

const NO_SUBJECT = 'Sem matéria'

// Categorias oficiais do MMLU (Hendrycks et al., `categories.py`): disciplina → área.
const MMLU_AREA: Record<string, string> = {
  abstract_algebra: 'stem', anatomy: 'other', astronomy: 'stem', business_ethics: 'other',
  clinical_knowledge: 'other', college_biology: 'stem', college_chemistry: 'stem',
  college_computer_science: 'stem', college_mathematics: 'stem', college_medicine: 'other',
  college_physics: 'stem', computer_security: 'stem', conceptual_physics: 'stem',
  econometrics: 'social', electrical_engineering: 'stem', elementary_mathematics: 'stem',
  formal_logic: 'humanities', global_facts: 'other', high_school_biology: 'stem',
  high_school_chemistry: 'stem', high_school_computer_science: 'stem',
  high_school_european_history: 'humanities', high_school_geography: 'social',
  high_school_government_and_politics: 'social', high_school_macroeconomics: 'social',
  high_school_mathematics: 'stem', high_school_microeconomics: 'social',
  high_school_physics: 'stem', high_school_psychology: 'social', high_school_statistics: 'stem',
  high_school_us_history: 'humanities', high_school_world_history: 'humanities',
  human_aging: 'other', human_sexuality: 'social', international_law: 'humanities',
  jurisprudence: 'humanities', logical_fallacies: 'humanities', machine_learning: 'stem',
  management: 'other', marketing: 'other', medical_genetics: 'other', miscellaneous: 'other',
  moral_disputes: 'humanities', moral_scenarios: 'humanities', nutrition: 'other',
  philosophy: 'humanities', prehistory: 'humanities', professional_accounting: 'other',
  professional_law: 'humanities', professional_medicine: 'other',
  professional_psychology: 'social', public_relations: 'social', security_studies: 'social',
  sociology: 'social', us_foreign_policy: 'social', virology: 'other',
  world_religions: 'humanities',
}

// Vestibulares no mesmo vocabulário do MMLU, para que as áreas se somem entre benchmarks.
const VESTIBULAR_AREA: Record<string, string> = {
  MATEMATICA: 'stem', FISICA: 'stem', QUIMICA: 'stem', BIOLOGIA: 'stem',
  HISTORIA: 'humanities', FILOSOFIA_SOCIOLOGIA: 'humanities', GEOGRAFIA: 'social',
}

const AREAS: Record<string, GroupKey> = {
  stem: { key: 'stem', label: 'Exatas e biológicas (STEM)', order: 1 },
  humanities: { key: 'humanities', label: 'Humanidades', order: 2 },
  social: { key: 'social', label: 'Ciências sociais', order: 3 },
  other: { key: 'other', label: 'Outras (saúde, negócios, geral)', order: 4 },
  unknown: { key: 'unknown', label: 'Sem área', order: 5 },
}

export function knowledgeArea(dataset: BenchmarkDatasetId, subject: string | null): GroupKey {
  if (subject === null) return AREAS.unknown as GroupKey
  if (dataset === 'gpqa') return AREAS.stem as GroupKey
  const table = dataset === 'mmlu' ? MMLU_AREA : VESTIBULAR_AREA
  return AREAS[table[subject] ?? 'unknown'] as GroupKey
}

const VESTIBULAR_EXAM_ORDER: Record<string, number> = { ENEM: 1, UNICAMP: 2, FUVEST: 3, ITA: 4 }
const VESTIBULAR_EXAM = /_(ENEM|UNICAMP|FUVEST|ITA)_\d{4}_/

const MMLU_LEVELS: ReadonlyArray<{ prefix: string; label: string; order: number }> = [
  { prefix: 'elementary_', label: 'Ensino fundamental', order: 11 },
  { prefix: 'high_school_', label: 'Ensino médio', order: 12 },
  { prefix: 'college_', label: 'Graduação', order: 13 },
  { prefix: 'professional_', label: 'Profissional', order: 14 },
]

const GPQA_SUBSET_ORDER: Record<GPQASubset, number> = { extended: 21, main: 22, diamond: 23 }

/**
 * Nível/origem da questão — o indicador de complexidade intrínseca disponível em cada dataset:
 * o vestibular de origem (ENEM → ITA), o nível do MMLU pelo prefixo da disciplina e a variante do GPQA.
 */
export function questionLevel(
  dataset: BenchmarkDatasetId,
  questionId: string,
  subject: string | null,
  split: string,
): GroupKey {
  if (dataset === 'vestibular') {
    const exam = VESTIBULAR_EXAM.exec(questionId)?.[1]
    return exam === undefined
      ? { key: 'vestibular:other', label: 'Vestibular · outro', order: 9 }
      : { key: `vestibular:${exam}`, label: `Vestibular · ${exam}`, order: VESTIBULAR_EXAM_ORDER[exam] as number }
  }
  if (dataset === 'mmlu') {
    const level = MMLU_LEVELS.find((candidate) => subject?.startsWith(candidate.prefix))
    return level === undefined
      ? { key: 'mmlu:general', label: 'MMLU · geral/especializado', order: 15 }
      : { key: `mmlu:${level.prefix}`, label: `MMLU · ${level.label}`, order: level.order }
  }
  const subset = split as GPQASubset
  return {
    key: `gpqa:${subset}`,
    label: `GPQA · ${GPQA_SUBSET_LABELS[subset] ?? split}`,
    order: GPQA_SUBSET_ORDER[subset] ?? 24,
  }
}

const QUARTILE_LABEL = ['Q1 · menor', 'Q2', 'Q3', 'Q4 · maior']

function quartileGroup(prefix: string, quartile: number): GroupKey {
  return { key: `${prefix}:${quartile}`, label: QUARTILE_LABEL[quartile - 1] as string, order: quartile }
}

export const DIMENSION_LABEL: Record<AnalysisDimension, string> = {
  execution: 'Execução',
  dataset: 'Benchmark',
  subject: 'Matéria',
  area: 'Área do conhecimento',
  level: 'Nível / origem da questão',
  simpleEffort: 'Tokens da inferência simples (quartil)',
  ralphEffort: 'Tokens do Ralph Loop (quartil)',
}

/** Título de seção "Por …" a partir do rótulo da dimensão, preservando nomes próprios. */
export function sectionTitle(label: string): string {
  return `Por ${label.charAt(0).toLowerCase()}${label.slice(1)}`
}

export function groupKeyOf(
  record: AnalysisRecord,
  dimension: AnalysisDimension,
  splits: ReadonlyMap<string, string>,
): GroupKey {
  switch (dimension) {
    case 'execution':
      return { key: record.benchmarkSessionId, label: record.executionLabel, order: 0 }
    case 'dataset':
      return { key: record.dataset, label: benchmarkDatasetLabel(record.dataset), order: 0 }
    case 'subject':
      return record.subject === null
        ? { key: `${record.dataset}:`, label: NO_SUBJECT, order: 0 }
        : {
            key: `${record.dataset}:${record.subject}`,
            label: benchmarkSubjectLabel(record.subject),
            order: 0,
          }
    case 'area':
      return knowledgeArea(record.dataset, record.subject)
    case 'level':
      return questionLevel(
        record.dataset,
        record.questionId,
        record.subject,
        splits.get(record.benchmarkSessionId) ?? '',
      )
    case 'simpleEffort':
      return quartileGroup('simple', record.simpleEffortQuartile)
    case 'ralphEffort':
      return quartileGroup('ralph', record.ralphEffortQuartile)
  }
}

export interface AnalysisGroup extends GroupKey {
  /** Benchmark do grupo quando todos os registros são do mesmo; senão `null`. */
  dataset: BenchmarkDatasetId | null
  records: AnalysisRecord[]
  summary: PairedSummary
}

/** Agrupa por uma chave qualquer, na ordem natural do grupo e, no empate, pelo rótulo. */
export function groupBy(
  records: readonly AnalysisRecord[],
  keyOf: (record: AnalysisRecord) => GroupKey,
): AnalysisGroup[] {
  const groups = new Map<string, GroupKey & { records: AnalysisRecord[] }>()
  for (const record of records) {
    const group = keyOf(record)
    const existing = groups.get(group.key)
    if (existing === undefined) groups.set(group.key, { ...group, records: [record] })
    else existing.records.push(record)
  }
  return [...groups.values()]
    .map((group) => {
      const datasets = new Set(group.records.map((record) => record.dataset))
      return {
        ...group,
        dataset: datasets.size === 1 ? (group.records[0] as AnalysisRecord).dataset : null,
        summary: summarizePairs(group.records),
      }
    })
    .sort((left, right) => left.order - right.order || left.label.localeCompare(right.label, 'pt-BR'))
}

export function groupRecords(
  records: readonly AnalysisRecord[],
  dimension: AnalysisDimension,
  sessions: readonly BenchmarkSessionDocument[],
): AnalysisGroup[] {
  const splits = new Map(sessions.map((session) => [session.id, session.benchmark.split]))
  return groupBy(records, (record) => groupKeyOf(record, dimension, splits))
}

// ─── Leitura executiva ────────────────────────────────────────────────────────

const SIGNIFICANCE = 0.05

export function isSignificant(summary: PairedSummary): boolean {
  return summary.mcnemarPValue < SIGNIFICANCE
}

/** Veredito curto: o Ralph ajuda, atrapalha ou empata, com a significância do McNemar. */
export function verdict(summary: PairedSummary): { tone: 'success' | 'danger' | 'neutral'; label: string } {
  if (summary.netGain === 0) return { tone: 'neutral', label: 'Empate' }
  const direction = summary.netGain > 0 ? 'Ralph melhor' : 'Ralph pior'
  return {
    tone: summary.netGain > 0 ? 'success' : 'danger',
    label: isSignificant(summary) ? `${direction} (p < 0,05)` : `${direction} (n.s.)`,
  }
}

/** Grupos com ao menos `minSize` pares, do maior para o menor Δ — base de "onde o Ralph ajuda". */
export function rankGroupsByDelta(groups: readonly AnalysisGroup[], minSize: number): AnalysisGroup[] {
  return groups
    .filter((group) => group.summary.n >= minSize)
    .sort((left, right) => right.summary.delta - left.summary.delta || right.summary.n - left.summary.n)
}

const deltaFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
  signDisplay: 'exceptZero',
})
const pValueFormatter = new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 2 })
const multiplierFormatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

/** Diferença de acurácia em pontos percentuais: `+5,0 p.p.`. */
export function formatPp(delta: number): string {
  return `${deltaFormatter.format(delta * 100)} p.p.`
}

export function formatPValue(pValue: number): string {
  return pValue < 0.001 ? '< 0,001' : pValueFormatter.format(pValue)
}

export function formatMultiplier(multiplier: number | null): string {
  return multiplier === null ? '—' : `${multiplierFormatter.format(multiplier)}×`
}
