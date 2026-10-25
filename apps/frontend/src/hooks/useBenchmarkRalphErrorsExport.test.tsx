import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as benchmarkApi from '../api/benchmarkApi'
import type * as BenchmarkApiModule from '../api/benchmarkApi'
import { HttpError } from '../api/errors/HttpError'
import * as saveBlobModule from './saveBlob'
import { useBenchmarkRalphErrorsExport } from './useBenchmarkRalphErrorsExport'

vi.mock('../api/benchmarkApi', async () => {
  const actual = await vi.importActual<typeof BenchmarkApiModule>('../api/benchmarkApi')
  return { ...actual, exportBenchmarkRalphErrors: vi.fn() }
})
vi.mock('./saveBlob', () => ({ saveBlob: vi.fn() }))

const exportMock = benchmarkApi.exportBenchmarkRalphErrors as Mock
const saveBlobMock = saveBlobModule.saveBlob as Mock

afterEach(() => {
  exportMock.mockReset()
  saveBlobMock.mockReset()
})

describe('useBenchmarkRalphErrorsExport', () => {
  it('começa ocioso, sem erro e sem download feito', () => {
    const { result } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))

    expect(result.current).toMatchObject({ isExporting: false, error: null, isDone: false })
    expect(exportMock).not.toHaveBeenCalled()
  })

  it('baixa o ZIP da bateria e o entrega com o nome sugerido', async () => {
    const zip = new Blob(['PK'])
    let resolveExport: (blob: Blob) => void = () => {}
    exportMock.mockImplementation(() => new Promise<Blob>((resolve) => (resolveExport = resolve)))
    const { result } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))

    act(() => result.current.start())
    expect(result.current.isExporting).toBe(true)
    expect(exportMock.mock.calls[0]?.[0]).toBe('bench_1')

    await act(async () => resolveExport(zip))

    expect(saveBlobMock).toHaveBeenCalledWith(
      zip,
      'benchmark-session-bench_1-ralph-loop-errors.zip',
    )
    expect(result.current).toMatchObject({ isExporting: false, error: null, isDone: true })
  })

  it('ignora um segundo clique enquanto o download está em andamento', async () => {
    exportMock.mockImplementation(() => new Promise<Blob>(() => {}))
    const { result } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))

    act(() => result.current.start())
    act(() => result.current.start())

    expect(exportMock).toHaveBeenCalledTimes(1)
  })

  it('expõe a falha do servidor e permite tentar de novo', async () => {
    exportMock.mockRejectedValueOnce(new HttpError(409, 'em execução'))
    const { result } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))

    act(() => result.current.start())
    await waitFor(() => expect(result.current.error).toBeInstanceOf(HttpError))
    expect(result.current).toMatchObject({ isExporting: false, isDone: false })
    expect(saveBlobMock).not.toHaveBeenCalled()

    exportMock.mockResolvedValueOnce(new Blob(['PK']))
    act(() => result.current.start())
    await waitFor(() => expect(result.current.isDone).toBe(true))
    expect(result.current.error).toBeNull()
  })

  it('converte um erro inesperado em erro exibível', async () => {
    exportMock.mockRejectedValueOnce(new Error('inesperado'))
    const { result } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))

    act(() => result.current.start())

    await waitFor(() => expect(result.current.error).not.toBeNull())
    expect(result.current.error?.userMessage).toBeTruthy()
  })

  it('falha ao entregar o arquivo vira erro, não download concluído', async () => {
    exportMock.mockResolvedValueOnce(new Blob(['PK']))
    saveBlobMock.mockImplementationOnce(() => {
      throw new Error('bloqueado')
    })
    const { result } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))

    act(() => result.current.start())

    await waitFor(() => expect(result.current.error).not.toBeNull())
    expect(result.current.isDone).toBe(false)
  })

  it('aborta o download ao desmontar e não entrega o arquivo', async () => {
    let signal: AbortSignal | undefined
    let resolveExport: (blob: Blob) => void = () => {}
    exportMock.mockImplementation((_id: string, requestSignal: AbortSignal) => {
      signal = requestSignal
      return new Promise<Blob>((resolve) => (resolveExport = resolve))
    })
    const { result, unmount } = renderHook(() => useBenchmarkRalphErrorsExport('bench_1'))
    act(() => result.current.start())

    unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => resolveExport(new Blob(['PK'])))

    expect(saveBlobMock).not.toHaveBeenCalled()
  })

  it('descarta erro e conclusão ao trocar de bateria', async () => {
    exportMock.mockResolvedValueOnce(new Blob(['PK']))
    const { result, rerender } = renderHook(({ id }) => useBenchmarkRalphErrorsExport(id), {
      initialProps: { id: 'bench_1' },
    })
    act(() => result.current.start())
    await waitFor(() => expect(result.current.isDone).toBe(true))

    rerender({ id: 'bench_2' })

    await waitFor(() => expect(result.current.isDone).toBe(false))
  })
})
