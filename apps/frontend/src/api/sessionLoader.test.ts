import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { getOfficialSession } from './publicBenchmarkApi'
import { getSession } from './sessionApi'
import { loadSessionDocument } from './sessionLoader'

vi.mock('./publicBenchmarkApi', () => ({ getOfficialSession: vi.fn().mockResolvedValue('publica') }))
vi.mock('./sessionApi', () => ({ getSession: vi.fn().mockResolvedValue('privada') }))

describe('loadSessionDocument', () => {
  it('sessões de publicação oficial vêm da API pública; as demais, da privada', async () => {
    await expect(loadSessionDocument('sess_1', 'pub_9')).resolves.toBe('publica')
    await expect(loadSessionDocument('sess_1', 'bench_9')).resolves.toBe('privada')
    await expect(loadSessionDocument('sess_1', null)).resolves.toBe('privada')

    expect((getOfficialSession as Mock).mock.calls[0]?.slice(0, 2)).toEqual(['pub_9', 'sess_1'])
    expect((getSession as Mock).mock.calls).toHaveLength(2)
  })
})
