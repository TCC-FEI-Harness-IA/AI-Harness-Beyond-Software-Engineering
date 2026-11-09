import { describe, expect, it } from 'vitest'
import { benchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import { buildAnalysisRecords, groupBy } from './benchmarkAnalysis'
import { buildAnalysisCsv, buildAnalysisMarkdown } from './benchmarkAnalysisReport'

const session = benchmarkSession({
  status: 'completed',
  alias: 'Bateria, "teste"',
  questions: [
    questionRun({
      question_id: 'MATEMATICA_ENEM_2022_AZUL_Q140',
      subject: 'MATEMATICA',
      simple: outcome({ is_correct: false, selected_alternative: 'B', session_id: 's1', total_tokens: 10 }),
      ralph: outcome({ mode: 'ralph', is_correct: true, selected_alternative: 'A', session_id: 'r1', total_tokens: 110 }),
    }),
    questionRun({
      question_id: 'Q2',
      simple: outcome({ selected_alternative: null, is_correct: false, error: 'falha', session_id: 's2' }),
      ralph: outcome({ mode: 'ralph', selected_alternative: null, is_correct: false, session_id: null }),
    }),
  ],
})
const { records } = buildAnalysisRecords([session])

describe('buildAnalysisCsv', () => {
  it('gera uma linha por par, escapando células e preenchendo o processo quando carregado', () => {
    const metrics = new Map([['r1', { taskCount: 3, resolutionCount: 4, verificationFailures: 1, planRejections: 0, replans: 0, llmCalls: 9 }]])
    const lines = buildAnalysisCsv(records, [session], metrics).trimEnd().split('\n')
    expect(lines).toHaveLength(3)
    expect(lines[0]).toMatch(/^benchmark_session_id,execucao,benchmark,question_id/)
    expect(lines[1]).toContain('"Bateria, ""teste"""')
    expect(lines[1]).toContain('Vestibular · ENEM')
    expect(lines[1]).toContain('ralph_recovers,1,3,3,1,0,s1,r1')
    expect(lines[2]).toContain('both_wrong,1,1,,,,s2,')
  })

  it('funciona sem métricas e sem a bateria entre as sessões informadas', () => {
    const csv = buildAnalysisCsv(records, [])
    expect(csv.split('\n')[1]).toContain('Vestibular · ENEM')
  })
})

describe('buildAnalysisMarkdown', () => {
  it('traz execuções, visão geral, quebras, seções extras e questões divergentes', () => {
    const markdown = buildAnalysisMarkdown(records, [session], [
      { title: 'Grupo | extra', groups: groupBy(records, () => ({ key: 'x', label: 'a|b', order: 0 })) },
    ])
    expect(markdown).toContain('# Análise Simples × Ralph Loop')
    expect(markdown).toContain('`bench_1` — Bateria, "teste" · Vestibulares')
    expect(markdown).toContain('- Pares analisados: **2**')
    expect(markdown).toContain('tokens extras por acerto líquido')
    expect(markdown).toContain('## Por matéria')
    expect(markdown).toContain('## Por grupo | extra')
    expect(markdown).toContain('| a/b | 2 |')
    expect(markdown).toContain('| +1 |')
    expect(markdown).toContain('| MATEMATICA_ENEM_2022_AZUL_Q140 | Ralph corrige | A | B | A |')
  })

  it('lida com bateria sem alias, sem ganho e sem pares', () => {
    const plain = benchmarkSession({ status: 'completed' })
    const markdown = buildAnalysisMarkdown([], [plain])
    expect(markdown).toContain('sem alias')
    expect(markdown).not.toContain('tokens extras por acerto líquido')
    expect(markdown).toContain('Recuperação')
    const regress = buildAnalysisRecords([
      benchmarkSession({
        questions: [
          questionRun({ simple: outcome(), ralph: outcome({ mode: 'ralph', is_correct: false, selected_alternative: null }) }),
          questionRun({ question_id: 'Q9', simple: outcome({ is_correct: false, selected_alternative: null }), ralph: outcome({ mode: 'ralph' }) }),
        ],
      }),
    ]).records
    const text = buildAnalysisMarkdown(regress, [plain])
    expect(text).toContain('| Ralph piora | A | A | — |')
    expect(text).toContain('| Q9 | Ralph corrige | A | — | A |')
  })
})
