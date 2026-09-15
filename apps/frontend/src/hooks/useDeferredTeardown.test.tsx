import { renderHook } from '@testing-library/react'
import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { useDeferredTeardown } from './useDeferredTeardown'

function nextMacrotask(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('useDeferredTeardown', () => {
  it('não executa a limpeza enquanto o componente segue montado', async () => {
    const teardown = vi.fn()
    renderHook(() => useDeferredTeardown(teardown))

    await nextMacrotask()

    expect(teardown).not.toHaveBeenCalled()
  })

  it('executa a limpeza no tick seguinte a uma desmontagem real', async () => {
    const teardown = vi.fn()
    const { unmount } = renderHook(() => useDeferredTeardown(teardown))

    unmount()
    expect(teardown).not.toHaveBeenCalled()

    await nextMacrotask()

    expect(teardown).toHaveBeenCalledTimes(1)
  })

  // O motivo de o hook existir: no StrictMode a limpeza roda entre duas montagens do mesmo
  // componente, e cancelar trabalho ali mata o que a primeira montagem acabou de iniciar.
  it('a limpeza simulada do StrictMode é desmarcada pela remontagem', async () => {
    const teardown = vi.fn()
    renderHook(() => useDeferredTeardown(teardown), { wrapper: StrictMode })

    await nextMacrotask()

    expect(teardown).not.toHaveBeenCalled()
  })

  it('usa sempre a última versão do callback', async () => {
    const primeiro = vi.fn()
    const ultimo = vi.fn()
    const { rerender, unmount } = renderHook(
      ({ teardown }: { teardown: () => void }) => useDeferredTeardown(teardown),
      { initialProps: { teardown: primeiro } },
    )

    rerender({ teardown: ultimo })
    unmount()
    await nextMacrotask()

    expect(primeiro).not.toHaveBeenCalled()
    expect(ultimo).toHaveBeenCalledTimes(1)
  })
})
