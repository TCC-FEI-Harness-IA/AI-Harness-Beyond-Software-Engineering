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
    const fetchMock = mockFetch({ question_ids: ['Q1'], max_parallel_limit: 3 })

    expect(await getBenchmarkDataset()).toEqual({ question_ids: ['Q1'], max_parallel_limit: 3 })
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/v1/benchmark/questions')
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
