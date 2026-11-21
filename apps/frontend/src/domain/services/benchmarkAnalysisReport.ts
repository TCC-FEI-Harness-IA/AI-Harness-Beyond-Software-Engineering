// Saídas da análise para o relatório técnico: um CSV com uma linha por questão pareada (para
// planilhas e testes estatísticos externos) e um resumo em Markdown com as tabelas das quebras.

import type { BenchmarkSessionDocument } from '../types/benchmarkSession'
import {
  type AnalysisGroup,
  type AnalysisRecord,
  type PairedSummary,
  DIMENSION_LABEL,
  type AnalysisDimension,
  formatMultiplier,
  formatPp,
  formatPValue,
  groupRecords,
  knowledgeArea,
  PAIR_OUTCOME_LABEL,
  questionLevel,
  sectionTitle,
  summarizePairs,
  verdict,
} from './benchmarkAnalysis'
import { benchmarkLabel } from './benchmarkDefinition'
import { formatPercent, formatTokens } from './formatters'
import type { RalphProcessMetrics } from './ralphProcessMetrics'

function csvCell(value: string | number | boolean | null): string {
  if (value === null) return ''
  const text = String(value)
  return /[",\n;]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

const CSV_HEADER = [
  'benchmark_session_id', 'execucao', 'benchmark', 'question_id', 'materia', 'area', 'nivel',
  'gabarito', 'simples_alternativa', 'simples_correta', 'simples_falha', 'simples_tokens',
  'simples_segundos', 'ralph_alternativa', 'ralph_correta', 'ralph_falha', 'ralph_tokens',
  'ralph_segundos', 'desfecho', 'quartil_tokens_simples', 'quartil_tokens_ralph',
  'ralph_tarefas', 'ralph_verificacoes_reprovadas', 'ralph_planos_reprovados',
  'simples_session_id', 'ralph_session_id',
]

/** Uma linha por questão pareada; as colunas do processo Ralph ficam vazias se a sessão não foi carregada. */
export function buildAnalysisCsv(
  records: readonly AnalysisRecord[],
  sessions: readonly BenchmarkSessionDocument[],
  metricsBySession: ReadonlyMap<string, RalphProcessMetrics> = new Map(),
): string {
  const splits = new Map(sessions.map((session) => [session.id, session.benchmark.split]))
  const rows = records.map((record) => {
    const metrics =
      record.ralph.session_id === null ? undefined : metricsBySession.get(record.ralph.session_id)
    return [
      record.benchmarkSessionId,
      record.executionLabel,
      record.dataset,
      record.questionId,
      record.subject,
      knowledgeArea(record.dataset, record.subject).label,
      questionLevel(record.dataset, record.questionId, record.subject, splits.get(record.benchmarkSessionId) ?? '').label,
      record.expected,
      record.simple.selected_alternative,
      record.simple.is_correct,
      record.simple.error !== null,
      record.simple.total_tokens,
      record.simple.duration_seconds,
      record.ralph.selected_alternative,
      record.ralph.is_correct,
      record.ralph.error !== null,
      record.ralph.total_tokens,
      record.ralph.duration_seconds,
      record.outcome,
      record.simpleEffortQuartile,
      record.ralphEffortQuartile,
      metrics?.taskCount ?? null,
      metrics?.verificationFailures ?? null,
      metrics?.planRejections ?? null,
      record.simple.session_id,
      record.ralph.session_id,
    ]
      .map(csvCell)
      .join(',')
  })
  return [CSV_HEADER.join(','), ...rows].join('\n') + '\n'
}

const rate = (value: number | null): string => (value === null ? '—' : formatPercent(value))

function groupTable(groups: readonly AnalysisGroup[]): string[] {
  return [
    '| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ...groups.map(({ label, summary: s }) =>
      `| ${label.replaceAll('|', '/')} | ${s.n} | ${formatPercent(s.simpleAccuracy)} | ${formatPercent(s.ralphAccuracy)} | ${formatPp(s.delta)} | ${s.recoveries} | ${s.regressions} | ${s.netGain > 0 ? '+' : ''}${s.netGain} | ${rate(s.recoveryRate)} | ${rate(s.regressionRate)} | ${formatPValue(s.mcnemarPValue)} | ${formatMultiplier(s.tokenMultiplier)} |`,
    ),
  ]
}

function overviewLines(s: PairedSummary): string[] {
  return [
    `- Pares analisados: **${s.n}**`,
    `- Acurácia simples: **${formatPercent(s.simpleAccuracy)}** (IC 95% ${formatPercent(s.simpleInterval[0])}–${formatPercent(s.simpleInterval[1])})`,
    `- Acurácia Ralph Loop: **${formatPercent(s.ralphAccuracy)}** (IC 95% ${formatPercent(s.ralphInterval[0])}–${formatPercent(s.ralphInterval[1])})`,
    `- Diferença: **${formatPp(s.delta)}** — ${verdict(s).label}; McNemar exato p = ${formatPValue(s.mcnemarPValue)}`,
    `- Quando a simples erra, o Ralph acerta: **${s.recoveries} de ${s.recoveries + s.bothWrong}** (${rate(s.recoveryRate)})`,
    `- Quando a simples acerta, o Ralph erra: **${s.regressions} de ${s.bothCorrect + s.regressions}** (${rate(s.regressionRate)})`,
    `- Redução relativa do erro: ${rate(s.errorReduction)}`,
    `- Ambos erram: ${s.bothWrong} (${s.bothWrongSameAnswer} com a mesma alternativa)`,
    `- Falhas técnicas: simples ${s.simpleFailures}, Ralph ${s.ralphFailures}`,
    `- Tokens: simples ${formatTokens(s.simpleTokens)}, Ralph ${formatTokens(s.ralphTokens)} (${formatMultiplier(s.tokenMultiplier)})` +
      (s.extraTokensPerNetGain === null ? '' : `; ${formatTokens(Math.round(s.extraTokensPerNetGain))} tokens extras por acerto líquido`),
  ]
}

const REPORT_DIMENSIONS: AnalysisDimension[] = [
  'execution', 'dataset', 'subject', 'area', 'level', 'simpleEffort', 'ralphEffort',
]

export function buildAnalysisMarkdown(
  records: readonly AnalysisRecord[],
  sessions: readonly BenchmarkSessionDocument[],
  extraSections: ReadonlyArray<{ title: string; groups: readonly AnalysisGroup[] }> = [],
): string {
  const lines = [
    '# Análise Simples × Ralph Loop',
    '',
    '## Execuções',
    '',
    ...sessions.map(
      (session) =>
        `- \`${session.id}\` — ${session.alias ?? 'sem alias'} · ${benchmarkLabel(session.benchmark)} · ${session.model_name} · ${session.question_count} questões`,
    ),
    '',
    '## Visão geral',
    '',
    ...overviewLines(summarizePairs(records)),
  ]
  const sections = [
    ...REPORT_DIMENSIONS.map((dimension) => ({
      title: DIMENSION_LABEL[dimension],
      groups: groupRecords(records, dimension, sessions),
    })),
    ...extraSections,
  ]
  for (const section of sections) {
    lines.push('', `## ${sectionTitle(section.title)}`, '', ...groupTable(section.groups))
  }
  lines.push(
    '',
    '## Questões divergentes',
    '',
    '| Execução | Questão | Desfecho | Gabarito | Simples | Ralph |',
    '|---|---|---|---|---|---|',
    ...records
      .filter((record) => record.outcome === 'ralph_recovers' || record.outcome === 'ralph_regresses')
      .map(
        (record) =>
          `| ${record.executionLabel} | ${record.questionId} | ${PAIR_OUTCOME_LABEL[record.outcome]} | ${record.expected} | ${record.simple.selected_alternative ?? '—'} | ${record.ralph.selected_alternative ?? '—'} |`,
      ),
  )
  return lines.join('\n') + '\n'
}
