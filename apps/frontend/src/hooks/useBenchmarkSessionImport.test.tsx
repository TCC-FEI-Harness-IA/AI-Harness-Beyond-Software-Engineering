import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as benchmarkApi from '../api/benchmarkApi'
import type * as BenchmarkApiModule from '../api/benchmarkApi'
import { HttpError } from '../api/errors/HttpError'
import type { BenchmarkSessionDocument } from '../domain/types/benchmarkSession'
import { completedBenchmarkSession } from '../test/fixtures/benchmarkSession'
import { useBenchmarkSessionImport } from './useBenchmarkSessionImport'

vi.mock('../api/benchmarkApi', async () => {
  const actual = await vi.importActual<typeof BenchmarkApiModule>('../api/benchmarkApi')
  return { ...actual, importBenchmarkSession: vi.fn() }
})

const importMock = benchmarkApi.importBenchmarkSession as Mock
const FILE = new File(['PK'], 'bateria.zip', { type: 'application/zip' })

afterEach(() => importMock.mockReset())

describe('useBenchmarkSessionImport', () => {
  it('começa ocioso, sem erro e sem bateria importada', () => {
    const { result } = renderHook(() => useBenchmarkSessionImport())

    expect(result.current).toMatchObject({ isImporting: false, error: null, imported: null })
    expect(importMock).not.toHaveBeenCalled()
  })

  it('envia o arquivo, expõe a bateria importada e avisa quem pediu', async () => {
    const session = completedBenchmarkSession()
    let resolveImport: (value: BenchmarkSessionDocument) => void = () => {}
    importMock.mockImplementation(
      () => new Promise<BenchmarkSessionDocument>((resolve) => (resolveImport = resolve)),
    )
    const onImported = vi.fn()
    const { result } = renderHook(() => useBenchmarkSessionImport(onImported))

    act(() => result.current.start(FILE))
    expect(result.current.isImporting).toBe(true)
    expect(importMock.mock.calls[0]?.[0]).toBe(FILE)

    await act(async () => resolveImport(session))

    expect(result.current).toMatchObject({ isImporting: false, error: null, imported: session })
    expect(onImported).toHaveBeenCalledWith(session)
  })

  it('ignora um segundo arquivo enquanto o envio está em andamento', () => {
    importMock.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useBenchmarkSessionImport())

    act(() => result.current.start(FILE))
    act(() => result.current.start(FILE))

    expect(importMock).toHaveBeenCalledTimes(1)
  })

  it('expõe a recusa do servidor e permite tentar de novo', async () => {
    importMock.mockRejectedValueOnce(new HttpError(409, 'já existe'))
    const { result } = renderHook(() => useBenchmarkSessionImport())

    act(() => result.current.start(FILE))
    await waitFor(() => expect(result.current.error).toBeInstanceOf(HttpError))
    expect(result.current).toMatchObject({ isImporting: false, imported: null })

    importMock.mockResolvedValueOnce(completedBenchmarkSession())
    act(() => result.current.start(FILE))
    await waitFor(() => expect(result.current.imported).not.toBeNull())
    expect(result.current.error).toBeNull()
  })

  it('converte um erro inesperado em erro exibível', async () => {
    importMock.mockRejectedValueOnce(new Error('inesperado'))
    const { result } = renderHook(() => useBenchmarkSessionImport())

    act(() => result.current.start(FILE))

    await waitFor(() => expect(result.current.error?.userMessage).toBeTruthy())
  })

  it('aborta o envio ao desmontar e descarta o resultado', async () => {
    let signal: AbortSignal | undefined
    let rejectImport: (error: unknown) => void = () => {}
    importMock.mockImplementation((_file: File, requestSignal: AbortSignal) => {
      signal = requestSignal
      return new Promise((_resolve, reject) => (rejectImport = reject))
    })
    const onImported = vi.fn()
    const { result, unmount } = renderHook(() => useBenchmarkSessionImport(onImported))
    act(() => result.current.start(FILE))

    unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => rejectImport(new Error('abortado')))

    expect(onImported).not.toHaveBeenCalled()
  })

  it('descarta o sucesso que chega depois de desmontar', async () => {
    let resolveImport: (value: BenchmarkSessionDocument) => void = () => {}
    importMock.mockImplementation(
      () => new Promise<BenchmarkSessionDocument>((resolve) => (resolveImport = resolve)),
    )
    const onImported = vi.fn()
    const { result, unmount } = renderHook(() => useBenchmarkSessionImport(onImported))
    act(() => result.current.start(FILE))

    unmount()
    await act(async () => resolveImport(completedBenchmarkSession()))

    expect(onImported).not.toHaveBeenCalled()
  })
})
