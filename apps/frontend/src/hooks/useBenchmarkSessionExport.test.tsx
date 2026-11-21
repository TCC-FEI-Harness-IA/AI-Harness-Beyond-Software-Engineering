import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as benchmarkApi from '../api/benchmarkApi'
import type * as BenchmarkApiModule from '../api/benchmarkApi'
import * as saveBlobModule from './saveBlob'
import { useBenchmarkSessionExport } from './useBenchmarkSessionExport'

vi.mock('../api/benchmarkApi', async () => {
  const actual = await vi.importActual<typeof BenchmarkApiModule>('../api/benchmarkApi')
  return { ...actual, exportBenchmarkSession: vi.fn() }
})
vi.mock('./saveBlob', () => ({ saveBlob: vi.fn() }))

const exportMock = benchmarkApi.exportBenchmarkSession as Mock
const saveBlobMock = saveBlobModule.saveBlob as Mock

afterEach(() => {
  exportMock.mockReset()
  saveBlobMock.mockReset()
})

describe('useBenchmarkSessionExport', () => {
  it('baixa o ZIP da bateria completa e o entrega com o nome sugerido', async () => {
    const zip = new Blob(['PK'])
    exportMock.mockResolvedValueOnce(zip)
    const { result } = renderHook(() => useBenchmarkSessionExport('bench_1'))

    act(() => result.current.start())

    await waitFor(() => expect(result.current.isDone).toBe(true))
    expect(exportMock.mock.calls[0]?.[0]).toBe('bench_1')
    expect(saveBlobMock).toHaveBeenCalledWith(zip, 'benchmark-session-bench_1.zip')
    expect(result.current).toMatchObject({ isExporting: false, error: null })
  })
})
