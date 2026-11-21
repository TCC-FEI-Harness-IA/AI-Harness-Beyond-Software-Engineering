import { describe, expect, it, vi } from 'vitest'
import { emitUnauthorized, onUnauthorized } from './authEvents'

describe('authEvents', () => {
  it('avisa os interessados quando o servidor recusa a sessão e permite cancelar a inscrição', () => {
    const ouvinte = vi.fn()
    const cancelar = onUnauthorized(ouvinte)

    emitUnauthorized()
    cancelar()
    emitUnauthorized()

    expect(ouvinte).toHaveBeenCalledTimes(1)
  })
})
