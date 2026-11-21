import { describe, expect, it } from 'vitest'
import { completedBenchmarkSession } from '@/test/fixtures/benchmarkSession'
import type { OfficialPublication } from '../types/officialPublication'
import { officialAsDocument } from './officialBattery'

describe('officialAsDocument', () => {
  it('identifica a bateria publicada pelo id da publicação, preservando o conteúdo', () => {
    const battery = completedBenchmarkSession()
    const publication: OfficialPublication = {
      id: 'pub_1', dataset: 'vestibular', status: 'active', publishedAt: '', supersedes: null, supersededBy: null,
      supersededAt: null, sourceBenchmarkSessionId: battery.id, textRedacted: false, battery,
    }

    const documento = officialAsDocument(publication)

    expect(documento.id).toBe('pub_1')
    expect(documento.questions).toBe(battery.questions)
  })
})
