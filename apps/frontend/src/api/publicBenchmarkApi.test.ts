import { afterEach, describe, expect, it, vi } from 'vitest'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import { completedBenchmarkSession } from '@/test/fixtures/benchmarkSession'
import { fakeResponse, fetchCalls, stubBaseEnv } from '@/test/apiTestKit'

export function publicacao(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'pub_1',
    dataset: 'vestibular',
    status: 'active',
    published_at: '2026-11-15T12:00:00+00:00',
    supersedes: null,
    superseded_by: null,
    superseded_at: null,
    source_benchmark_session_id: 'bench_1',
    text_redacted: false,
    benchmark_session: completedBenchmarkSession(),
    ...overrides,
  }
}

async function importPublicApi() {
  vi.resetModules()
  stubBaseEnv()
  const [api, errors] = await Promise.all([import('./publicBenchmarkApi'), import('./errors')])
  return { ...api, ...errors }
}

describe('publicBenchmarkApi', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('lista as publicações oficiais com a bateria preservada', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, { publications: [publicacao()] }))
    vi.stubGlobal('fetch', fetchMock)
    const { listOfficialPublications } = await importPublicApi()

    const [primeira] = await listOfficialPublications()

    expect(primeira).toMatchObject({
      id: 'pub_1', dataset: 'vestibular', status: 'active', textRedacted: false, sourceBenchmarkSessionId: 'bench_1',
    })
    expect(primeira?.battery.id).toBe(completedBenchmarkSession().id)
    expect(fetchCalls(fetchMock)[0]?.url).toBe('http://localhost:8000/v1/public/benchmarks')
  })

  it('consulta o detalhe e as sessões filhas pelo caminho público', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(fakeResponse(200, publicacao({ status: 'superseded', superseded_by: 'pub_2' })))
      .mockResolvedValueOnce(fakeResponse(200, completedFixture))
    vi.stubGlobal('fetch', fetchMock)
    const { getOfficialPublication, getOfficialSession } = await importPublicApi()

    await expect(getOfficialPublication('pub_1')).resolves.toMatchObject({ supersededBy: 'pub_2' })
    await expect(getOfficialSession('pub_1', 'sess 1')).resolves.toMatchObject({ id: completedFixture.id })

    expect(fetchCalls(fetchMock).map((item) => item.url)).toEqual([
      'http://localhost:8000/v1/public/benchmarks/pub_1',
      'http://localhost:8000/v1/public/benchmarks/pub_1/sessions/sess%201',
    ])
  })

  it('status desconhecido viola o contrato', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(fakeResponse(200, publicacao({ status: 'rascunho' }))))
    const { getOfficialPublication, ContractError } = await importPublicApi()

    await expect(getOfficialPublication('pub_1')).rejects.toBeInstanceOf(ContractError)
  })
})
