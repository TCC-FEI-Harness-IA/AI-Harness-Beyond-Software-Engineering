import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppError } from '../api/errors/AppError'
import { useAsync } from './useAsync'

class FakeError extends AppError {
  constructor() {
    super('falha de teste', 'Algo deu errado.')
  }
}

describe('useAsync', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    warnSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    warnSpy.mockRestore()
  })

  it('resolve com sucesso', async () => {
    const run = vi.fn().mockResolvedValue('dado-carregado')
    const { result } = renderHook(() => useAsync(run, []))

    expect(result.current.status).toBe('loading')

    await waitFor(() => {
      expect(result.current.status).toBe('success')
    })
    expect(result.current).toMatchObject({ status: 'success', data: 'dado-carregado' })
  })

  it('reporta erro quando `run` rejeita', async () => {
    const run = vi.fn().mockRejectedValue(new FakeError())
    const { result } = renderHook(() => useAsync(run, []))

    await waitFor(() => {
      expect(result.current.status).toBe('error')
    })
    if (result.current.status !== 'error') throw new Error('esperava status error')
    expect(result.current.error).toBeInstanceOf(AppError)
    expect(result.current.error.userMessage).toBe('Algo deu errado.')
  })

  it('reload() reexecuta a função sem mudar as deps', async () => {
    const run = vi.fn().mockResolvedValueOnce('primeiro').mockResolvedValueOnce('segundo')
    const { result } = renderHook(() => useAsync(run, []))

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(run).toHaveBeenCalledTimes(1)

    act(() => {
      result.current.reload()
    })

    await waitFor(() => {
      expect(result.current).toMatchObject({ status: 'success', data: 'segundo' })
    })
    expect(run).toHaveBeenCalledTimes(2)
  })

  it('desmontar durante a requisição não gera aviso de setState após unmount', async () => {
    let resolvePromise: (value: string) => void = () => {}
    const run = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          resolvePromise = resolve
        }),
    )

    const { unmount } = renderHook(() => useAsync(run, []))
    unmount()
    resolvePromise('valor-tardio')

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(warnSpy).not.toHaveBeenCalled()
  })
})
