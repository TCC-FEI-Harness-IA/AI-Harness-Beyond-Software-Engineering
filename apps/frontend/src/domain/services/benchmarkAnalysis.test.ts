import { describe, expect, it } from 'vitest'
import { benchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import type { BenchmarkQuestionRun, BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import {
  type AnalysisRecord,
  buildAnalysisRecords,
  costByOutcome,
  executionLabel,
  formatMultiplier,
  formatPp,
  formatPValue,
  groupBy,
  groupKeyOf,
  groupRecords,
  knowledgeArea,
  mcnemarExactPValue,
  pairOutcome,
  quartileOf,
  questionLevel,
  rankGroupsByDelta,
  sectionTitle,
  summarizePairs,
  verdict,
  wilsonInterval,
} from './benchmarkAnalysis'

/** Questão encerrada com o desfecho de cada fluxo (`true` = acertou). */
function finished(
  id: string,
  simpleCorrect: boolean,
  ralphCorrect: boolean,
  extra: Partial<BenchmarkQuestionRun> = {},
): BenchmarkQuestionRun {
  return questionRun({
    question_id: id,
    status: 'finished',
    simple: outcome({
      session_id: `${id}_s`,
      selected_alternative: simpleCorrect ? 'A' : 'B',
      is_correct: simpleCorrect,
      total_tokens: 10,
      duration_seconds: 1,
    }),
    ralph: outcome({
      mode: 'ralph',
      session_id: `${id}_r`,
      selected_alternative: ralphCorrect ? 'A' : 'C',
      is_correct: ralphCorrect,
      total_tokens: 100,
      duration_seconds: 10,
    }),
    ...extra,
  })
}

function session(questions: BenchmarkQuestionRun[], overrides: Partial<BenchmarkSessionDocument> = {}): BenchmarkSessionDocument {
  return benchmarkSession({ status: 'completed', questions, ...overrides })
}

function records(...sessions: BenchmarkSessionDocument[]): AnalysisRecord[] {
  return buildAnalysisRecords(sessions).records
}

describe('executionLabel', () => {
  it('usa o alias quando existe e, sem ele, o benchmark com a data', () => {
    expect(executionLabel(session([], { alias: 'Minha bateria' }))).toBe('Minha bateria')
    expect(executionLabel(session([]))).toMatch(/^Vestibulares · /)
  })
})

describe('pairOutcome', () => {
  it('classifica os quatro desfechos do par', () => {
    expect(pairOutcome(true, true)).toBe('both_correct')
    expect(pairOutcome(true, false)).toBe('ralph_regresses')
    expect(pairOutcome(false, true)).toBe('ralph_recovers')
    expect(pairOutcome(false, false)).toBe('both_wrong')
  })
})

describe('quartileOf', () => {
  it('reparte em quatro faixas e mantém empates juntos', () => {
    const sorted = [1, 2, 3, 4, 5, 6, 7, 8]
    expect(sorted.map((value) => quartileOf(value, sorted))).toEqual([1, 1, 2, 2, 3, 3, 4, 4])
    expect(quartileOf(5, [5, 5, 5, 5])).toBe(1)
    expect(quartileOf(9, [9])).toBe(1)
  })
})

describe('buildAnalysisRecords', () => {
  it('pareia só as questões com os dois fluxos concluídos e conta as excluídas', () => {
    const result = buildAnalysisRecords([
      session([
        finished('Q1', true, true),
        questionRun({ question_id: 'Q2' }),
        questionRun({ question_id: 'Q3', simple: outcome() }),
      ]),
    ])
    expect(result.records.map((record) => record.key)).toEqual(['bench_1:Q1'])
    expect(result.exclusions).toEqual({ unpaired: 2, failures: 0 })
    expect(result.records[0]).toMatchObject({ dataset: 'vestibular', outcome: 'both_correct', expected: 'A' })
  })

  it('descarta falhas técnicas de qualquer fluxo quando pedido', () => {
    const questions = [
      finished('Q1', false, true, { simple: outcome({ error: 'timeout', is_correct: false }) }),
      finished('Q2', true, false, { ralph: outcome({ mode: 'ralph', error: 'inválida', is_correct: false }) }),
      finished('Q3', true, true),
    ]
    expect(buildAnalysisRecords([session(questions)]).records).toHaveLength(3)
    const filtered = buildAnalysisRecords([session(questions)], { excludeFailures: true })
    expect(filtered.records.map((record) => record.questionId)).toEqual(['Q3'])
    expect(filtered.exclusions.failures).toBe(2)
  })

  it('calcula os quartis de tokens dentro de cada bateria', () => {
    const questions = [10, 20, 30, 40].map((tokens, index) =>
      finished(`Q${index}`, true, true, {
        simple: outcome({ total_tokens: tokens }),
        ralph: outcome({ mode: 'ralph', total_tokens: 1000 - tokens }),
      }),
    )
    const result = records(session(questions))
    expect(result.map((record) => record.simpleEffortQuartile)).toEqual([1, 2, 3, 4])
    expect(result.map((record) => record.ralphEffortQuartile)).toEqual([4, 3, 2, 1])
  })
})

describe('estatística', () => {
  it('wilsonInterval cobre a proporção e é vazio sem observações', () => {
    expect(wilsonInterval(0, 0)).toEqual([0, 0])
    const [low, high] = wilsonInterval(8, 10)
    expect(low).toBeCloseTo(0.49, 2)
    expect(high).toBeCloseTo(0.943, 2)
    expect(wilsonInterval(10, 10)[1]).toBeCloseTo(1, 10)
    expect(wilsonInterval(0, 10)[0]).toBe(0)
  })

  it('mcnemarExactPValue segue a binomial bicaudal', () => {
    expect(mcnemarExactPValue(0, 0)).toBe(1)
    expect(mcnemarExactPValue(3, 3)).toBe(1)
    expect(mcnemarExactPValue(0, 6)).toBeCloseTo(0.03125, 6)
    expect(mcnemarExactPValue(1, 9)).toBeCloseTo(0.021484375, 6)
    expect(mcnemarExactPValue(400, 600)).toBeLessThan(0.001)
  })
})

describe('summarizePairs', () => {
  it('soma a tabela 2×2, as taxas, os custos e as mudanças de alternativa', () => {
    const summary = summarizePairs(
      records(
        session([
          finished('Q1', true, true),
          finished('Q2', true, false),
          finished('Q3', false, true),
          finished('Q4', false, true),
          finished('Q5', false, false),
          finished('Q6', false, false, {
            simple: outcome({ selected_alternative: 'D', is_correct: false, error: 'falha' }),
            ralph: outcome({ mode: 'ralph', selected_alternative: 'D', is_correct: false, error: 'falha' }),
          }),
        ]),
      ),
    )
    expect(summary).toMatchObject({
      n: 6,
      bothCorrect: 1,
      regressions: 1,
      recoveries: 2,
      bothWrong: 2,
      simpleCorrect: 2,
      ralphCorrect: 3,
      netGain: 1,
      simpleFailures: 1,
      ralphFailures: 1,
      answerChanged: 4,
      bothWrongSameAnswer: 1,
      simpleTokens: 50 + 10,
      ralphTokens: 500 + 10,
    })
    expect(summary.simpleAccuracy).toBeCloseTo(2 / 6)
    expect(summary.ralphAccuracy).toBeCloseTo(3 / 6)
    expect(summary.delta).toBeCloseTo(1 / 6)
    expect(summary.recoveryRate).toBeCloseTo(2 / 4)
    expect(summary.regressionRate).toBeCloseTo(1 / 2)
    expect(summary.errorReduction).toBeCloseTo(1 / 4)
    expect(summary.tokenMultiplier).toBeCloseTo(510 / 60)
    expect(summary.extraTokensPerNetGain).toBe(450)
  })

  it('devolve zeros e nulos sem observações', () => {
    const summary = summarizePairs([])
    expect(summary).toMatchObject({
      n: 0,
      simpleAccuracy: 0,
      ralphAccuracy: 0,
      delta: 0,
      recoveryRate: null,
      regressionRate: null,
      errorReduction: null,
      tokenMultiplier: null,
      extraTokensPerNetGain: null,
      mcnemarPValue: 1,
    })
  })
})

describe('costByOutcome', () => {
  it('calcula a média por desfecho, na ordem fixa, com zero nos desfechos vazios', () => {
    const costs = costByOutcome(records(session([finished('Q1', false, true), finished('Q2', false, true, { ralph: outcome({ mode: 'ralph', total_tokens: 300, duration_seconds: 30 }) })])))
    expect(costs.map((cost) => cost.outcome)).toEqual(['both_correct', 'ralph_recovers', 'ralph_regresses', 'both_wrong'])
    expect(costs[1]).toEqual({ outcome: 'ralph_recovers', count: 2, simpleMeanTokens: 10, ralphMeanTokens: 200, ralphMeanSeconds: 20 })
    expect(costs[0]).toMatchObject({ count: 0, ralphMeanTokens: 0 })
  })
})

describe('knowledgeArea', () => {
  it('mapeia as matérias de cada benchmark para as categorias do MMLU', () => {
    expect(knowledgeArea('vestibular', null).key).toBe('unknown')
    expect(knowledgeArea('gpqa', 'physics').key).toBe('stem')
    expect(knowledgeArea('mmlu', 'high_school_us_history').key).toBe('humanities')
    expect(knowledgeArea('mmlu', 'inexistente').key).toBe('unknown')
    expect(knowledgeArea('vestibular', 'GEOGRAFIA').key).toBe('social')
    expect(knowledgeArea('mmlu', 'nutrition').key).toBe('other')
  })
})

describe('questionLevel', () => {
  it('lê o vestibular de origem do identificador', () => {
    expect(questionLevel('vestibular', 'FISICA_ITA_2024_F1_UNICA_Q05', 'FISICA', 'test')).toEqual({
      key: 'vestibular:ITA',
      label: 'Vestibular · ITA',
      order: 4,
    })
    expect(questionLevel('vestibular', 'Q1', null, 'test').key).toBe('vestibular:other')
  })

  it('usa o prefixo da disciplina do MMLU', () => {
    expect(questionLevel('mmlu', 'MMLU_x', 'college_physics', 'test').label).toBe('MMLU · Graduação')
    expect(questionLevel('mmlu', 'MMLU_x', 'virology', 'test').key).toBe('mmlu:general')
    expect(questionLevel('mmlu', 'MMLU_x', null, 'test').key).toBe('mmlu:general')
  })

  it('usa a variante do GPQA, tolerando uma desconhecida', () => {
    expect(questionLevel('gpqa', 'GPQA_diamond_1', 'physics', 'diamond')).toEqual({
      key: 'gpqa:diamond',
      label: 'GPQA · Diamond',
      order: 23,
    })
    expect(questionLevel('gpqa', 'GPQA_x_1', 'physics', 'x')).toEqual({ key: 'gpqa:x', label: 'GPQA · x', order: 24 })
  })
})

describe('agrupamento', () => {
  const vestibular = session(
    [
      finished('MATEMATICA_ENEM_2022_AZUL_Q140', false, true, { subject: 'MATEMATICA' }),
      finished('FISICA_ITA_2024_F1_UNICA_Q01', true, false, { subject: 'FISICA' }),
      finished('Q_sem_materia', true, true),
    ],
    { id: 'bench_v', alias: 'Vest' },
  )
  const gpqa = session([finished('GPQA_main_1', false, false, { subject: 'physics' })], {
    id: 'bench_g',
    alias: 'GPQA',
    benchmark: { ...vestibular.benchmark, dataset: 'gpqa', split: 'main' },
  })
  const all = records(vestibular, gpqa)

  it('gera a chave de cada dimensão', () => {
    const splits = new Map([['bench_v', 'test']])
    const [math, , noSubject] = all as [AnalysisRecord, AnalysisRecord, AnalysisRecord, AnalysisRecord]
    expect(groupKeyOf(math, 'execution', splits)).toEqual({ key: 'bench_v', label: 'Vest', order: 0 })
    expect(groupKeyOf(math, 'dataset', splits).label).toBe('Vestibulares')
    expect(groupKeyOf(math, 'subject', splits)).toEqual({ key: 'vestibular:MATEMATICA', label: 'Matemática', order: 0 })
    expect(groupKeyOf(noSubject, 'subject', splits).label).toBe('Sem matéria')
    expect(groupKeyOf(math, 'area', splits).key).toBe('stem')
    expect(groupKeyOf(math, 'level', splits).key).toBe('vestibular:ENEM')
    expect(groupKeyOf(all[3] as AnalysisRecord, 'level', splits).key).toBe('gpqa:')
    expect(groupKeyOf(math, 'simpleEffort', splits)).toEqual({ key: 'simple:1', label: 'Q1 · menor', order: 1 })
    expect(groupKeyOf(math, 'ralphEffort', splits).key).toBe('ralph:1')
  })

  it('agrupa na ordem natural e marca o benchmark do grupo quando é um só', () => {
    const levels = groupRecords(all, 'level', [vestibular, gpqa])
    expect(levels.map((group) => group.label)).toEqual([
      'Vestibular · ENEM',
      'Vestibular · ITA',
      'Vestibular · outro',
      'GPQA · Main',
    ])
    expect(levels[0]?.dataset).toBe('vestibular')

    const areas = groupRecords(all, 'area', [vestibular, gpqa])
    expect(areas[0]).toMatchObject({ key: 'stem', dataset: null })
    expect(areas[0]?.summary.n).toBe(3)

    const executions = groupBy(all, (record) => ({ key: record.benchmarkSessionId, label: record.executionLabel, order: 0 }))
    expect(executions.map((group) => group.label)).toEqual(['GPQA', 'Vest'])
  })

  it('ranqueia por Δ, desempata por n e ignora grupos pequenos', () => {
    const subjects = groupRecords(all, 'subject', [vestibular, gpqa])
    expect(rankGroupsByDelta(subjects, 1).map((group) => group.label)).toEqual([
      'Matemática',
      'physics',
      'Sem matéria',
      'Física',
    ])
    expect(rankGroupsByDelta(subjects, 2)).toEqual([])
    const tied = groupRecords(
      records(session([finished('A1', true, true, { subject: 'A' }), finished('A2', true, true, { subject: 'A' }), finished('B1', true, true, { subject: 'B' })])),
      'subject',
      [],
    )
    expect(rankGroupsByDelta(tied, 1).map((group) => group.label)).toEqual(['A', 'B'])
  })
})

describe('leitura e formatação', () => {
  it('verdict combina direção e significância', () => {
    expect(verdict(summarizePairs([])).label).toBe('Empate')
    const better = summarizePairs(records(session(Array.from({ length: 6 }, (_, index) => finished(`Q${index}`, false, true)))))
    expect(verdict(better)).toEqual({ tone: 'success', label: 'Ralph melhor (p < 0,05)' })
    const worse = summarizePairs(records(session([finished('Q1', true, false)])))
    expect(verdict(worse)).toEqual({ tone: 'danger', label: 'Ralph pior (n.s.)' })
  })

  it('monta o título de seção sem apagar nomes próprios', () => {
    expect(sectionTitle('Tokens do Ralph Loop (quartil)')).toBe('Por tokens do Ralph Loop (quartil)')
  })

  it('formata p.p., p-valor e multiplicador', () => {
    expect(formatPp(0.05)).toBe('+5,0 p.p.')
    expect(formatPp(-0.125)).toBe('-12,5 p.p.')
    expect(formatPp(0)).toBe('0,0 p.p.')
    expect(formatPValue(0.0001)).toBe('< 0,001')
    expect(formatPValue(0.0312)).toBe('0,031')
    expect(formatMultiplier(null)).toBe('—')
    expect(formatMultiplier(12.34)).toBe('12,3×')
  })
})
