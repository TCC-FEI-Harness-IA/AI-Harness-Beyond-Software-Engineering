import { describe, expect, it } from 'vitest'
import fixture from '@/test/fixtures/session-direct-completed.json'
import { parseSessionDocument } from '@/api/parsers/sessionDocument'
import { getCachedSession, setCachedSession } from './sessionCache'

describe('isolamento das fontes do histórico', () => {
  it('sessões com o mesmo ID nas duas fontes não compartilham o cache', () => {
    const history = parseSessionDocument({ ...fixture, id: 'mesmo_id', user_question: 'Histórico normal' })
    const benchmark = parseSessionDocument({ ...fixture, id: 'mesmo_id', user_question: 'Benchmark local', benchmark_details: { is_banchmark: true, is_correct: true } })
    setCachedSession(history)
    setCachedSession(benchmark, 'benchmark')
    expect(getCachedSession('mesmo_id')?.user_question).toBe('Histórico normal')
    expect(getCachedSession('mesmo_id', 'benchmark')?.user_question).toBe('Benchmark local')
  })

  it('não guarda uma avaliação pendente como se fosse um resultado definitivo', () => {
    const pending = parseSessionDocument({
      ...fixture, id: 'sess_pendente', benchmark_details: { is_banchmark: true, is_correct: null },
    })
    setCachedSession(pending, 'benchmark')
    expect(getCachedSession('sess_pendente', 'benchmark')).toBeUndefined()
  })
})
