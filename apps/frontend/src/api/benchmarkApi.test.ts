import { afterEach, describe, expect, it, vi } from 'vitest'
import { benchmarkSession } from '@/test/fixtures/benchmarkSession'
import { ContractError } from './errors/ContractError'
import {
  buildBenchmarkRunPayload,
  exportBenchmarkRalphErrors,
  getBenchmarkDataset,
  getBenchmarkSession,
  listBenchmarkSessions,
  ralphErrorsArchiveName,
} from './benchmarkApi'

const CONFIG = {
  modelName: 'vendor/modelo',
  provider: 'open_router' as const,
  maxTokens: 100,
  temperature: 0.34,
}

function mockFetch(body: unknown) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue({ status: 200, text: () => Promise.resolve(JSON.stringify(body)) })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('consultas de benchmark', () => {
  it('busca o dataset', async () => {
    const fetchMock = mockFetch({ question_ids: ['Q1'], max_parallel_limit: 3, max_tokens_limit: 32000 })

    expect(await getBenchmarkDataset()).toEqual({ question_ids: ['Q1'], max_parallel_limit: 3, max_tokens_limit: 32000 })
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/v1/benchmark/questions')
  })

  it('consulta MMLU sem trocar o dataset global', async () => {
    const fetchMock = mockFetch({ question_ids: ['MMLU_Q1'], max_parallel_limit: 3, max_tokens_limit: 32000 })
    await getBenchmarkDataset(undefined, 'mmlu')
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/v1/benchmark/questions?benchmark=mmlu')
  })

  it('lista as baterias', async () => {
    mockFetch({ benchmark_sessions: [benchmarkSession()] })

    expect((await listBenchmarkSessions())[0]?.id).toBe('bench_1')
  })

  it('busca uma bateria com o identificador codificado', async () => {
    const fetchMock = mockFetch(benchmarkSession())

    await getBenchmarkSession('bench 1')

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      'http://localhost:8000/v1/benchmark/sessions/bench%201',
    )
  })
})

describe('buildBenchmarkRunPayload', () => {
  it('envia protocolo, disciplinas e semente da bateria MMLU', () => {
    const payload = buildBenchmarkRunPayload({
      questionCount: 285, maxParallel: 3, config: CONFIG,
      benchmark: 'mmlu', fewShot: 5, subjects: ['college_physics'], sampleSeed: 123,
    })
    expect(payload).toMatchObject({
      benchmark: 'mmlu', few_shot: 5, subjects: ['college_physics'], sample_seed: 123,
    })
    expect(buildBenchmarkRunPayload({ questionCount: 1, maxParallel: 1, config: CONFIG, benchmark: 'mmlu' }))
      .toMatchObject({ few_shot: 0, subjects: [], sample_seed: 42 })
  })

  it.each([-1, 1.5, 4294967296, NaN])('recusa semente MMLU inválida: %s', (sampleSeed) => {
    expect(() => buildBenchmarkRunPayload({
      questionCount: 1, maxParallel: 1, config: CONFIG, benchmark: 'mmlu', sampleSeed,
    })).toThrow('semente inválidos')
  })

  it('monta a abertura com a configuração do modelo e arredonda a temperatura', () => {
    expect(buildBenchmarkRunPayload({ questionCount: 3, maxParallel: 2, config: CONFIG })).toEqual({
      question_count: 3,
      max_parallel: 2,
      llm_model_config: {
        provider: 'open_router',
        provider_config: { model_name: 'vendor/modelo', endpoint: null },
        max_tokens: 100,
        temperature: 0.3,
      },
    })
  })

  it.each([
    [{ questionCount: 0, maxParallel: 1, config: CONFIG }, 'question_count'],
    [{ questionCount: 1, maxParallel: 1.5, config: CONFIG }, 'max_parallel'],
    [{ questionCount: 1, maxParallel: 1, config: { ...CONFIG, maxTokens: 0 } }, 'max_tokens'],
    [{ questionCount: 1, maxParallel: 1, config: { ...CONFIG, temperature: 2 } }, 'temperature'],
  ])('recusa parâmetros inválidos (%#)', (params, field) => {
    expect(() => buildBenchmarkRunPayload(params)).toThrow(ContractError)
    expect(() => buildBenchmarkRunPayload(params)).toThrow(field)
  })
})

describe('exportBenchmarkRalphErrors', () => {
  it('baixa o ZIP da bateria com o identificador codificado', async () => {
    const zip = new Blob(['PK'], { type: 'application/zip' })
    const fetchMock = vi.fn().mockResolvedValue({ status: 200, blob: () => Promise.resolve(zip) })
    vi.stubGlobal('fetch', fetchMock)

    expect(await exportBenchmarkRalphErrors('bench 1')).toBe(zip)
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      'http://localhost:8000/v1/benchmark/sessions/bench%201/ralph-loop-errors/export',
    )
    vi.unstubAllGlobals()
  })
})

describe('ralphErrorsArchiveName', () => {
  it('segue o nome sugerido pelo backend, trocando caracteres inseguros', () => {
    expect(ralphErrorsArchiveName('bench_1')).toBe('benchmark-session-bench_1-ralph-loop-errors.zip')
    expect(ralphErrorsArchiveName('a/b c')).toBe('benchmark-session-a_b_c-ralph-loop-errors.zip')
  })
})

it('consulta GPQA e envia o protocolo sem exemplos', async () => {
  const fetchMock = mockFetch({
    question_ids: ['GPQA_Q1'],
    max_parallel_limit: 3,
    max_tokens_limit: 32000,
  })
  await getBenchmarkDataset(undefined, 'gpqa')
  expect(fetchMock.mock.calls[0]?.[0]).toBe(
    'http://localhost:8000/v1/benchmark/questions?benchmark=gpqa',
  )
  expect(
    buildBenchmarkRunPayload({
      questionCount: 1,
      maxParallel: 1,
      config: CONFIG,
      benchmark: 'gpqa',
    }),
  ).toMatchObject({ benchmark: 'gpqa', few_shot: 0, sample_seed: 42, subjects: [] })
  expect(() =>
    buildBenchmarkRunPayload({
      questionCount: 1,
      maxParallel: 1,
      config: CONFIG,
      benchmark: 'gpqa',
      fewShot: 5,
    }),
  ).toThrow()
})

it.each(['diamond', 'main', 'extended'] as const)('consulta e inicia GPQA %s', async (subset) => {
  const fetchMock = mockFetch({
    question_ids: ['GPQA_Q1'],
    max_parallel_limit: 3,
    max_tokens_limit: 32000,
  })
  await getBenchmarkDataset(undefined, 'gpqa', subset)
  const url = new URL(String(fetchMock.mock.calls[0]?.[0]))
  expect(url.searchParams.get('benchmark')).toBe('gpqa')
  expect(url.searchParams.get('gpqa_subset') ?? 'diamond').toBe(subset)
  expect(
    buildBenchmarkRunPayload({
      questionCount: 1,
      maxParallel: 1,
      config: CONFIG,
      benchmark: 'gpqa',
      gpqaSubset: subset,
    }),
  ).toMatchObject({ benchmark: 'gpqa', gpqa_subset: subset })
})

describe('quantidades por matéria de Vestibulares', () => {
  it('envia as quantidades e o total sem adicionar protocolo de amostragem', () => {
    const counts = { MATEMATICA: 2, FILOSOFIA_SOCIOLOGIA: 1, FISICA: 0 }
    const payload = buildBenchmarkRunPayload({
      questionCount: 3,
      maxParallel: 2,
      config: CONFIG,
      subjectCounts: counts,
    })
    expect(payload).toMatchObject({ question_count: 3, subject_counts: counts })
    expect(payload).not.toHaveProperty('sample_seed')
    expect(payload).not.toHaveProperty('few_shot')
    expect(payload.subject_counts).not.toBe(counts)
  })

  it.each([
    {},
    { FISICA: 0 },
    { FISICA: -1, MATEMATICA: 4 },
    { FISICA: 1.5, MATEMATICA: 1.5 },
    { FISICA: NaN },
    { FISICA: 2 },
  ])('recusa quantidades inválidas ou com total divergente (%#)', (subjectCounts) => {
    expect(() =>
      buildBenchmarkRunPayload({
        questionCount: 3,
        maxParallel: 1,
        config: CONFIG,
        subjectCounts,
      }),
    ).toThrow('subject_counts')
  })

  it.each(['mmlu', 'gpqa'] as const)('aceita cotas por disciplina em %s', (benchmark) => {
    const payload = buildBenchmarkRunPayload({
      benchmark,
      questionCount: 3,
      maxParallel: 1,
      config: CONFIG,
      subjectCounts: { physics: 3 },
    })
    expect(payload).toMatchObject({ benchmark, question_count: 3, subject_counts: { physics: 3 } })
  })

  it('recusa cotas junto de subjects', () => {
    expect(() =>
      buildBenchmarkRunPayload({
        benchmark: 'mmlu',
        questionCount: 3,
        maxParallel: 1,
        config: CONFIG,
        subjects: ['physics'],
        subjectCounts: { physics: 3 },
      }),
    ).toThrow('subject_counts')
  })
})
