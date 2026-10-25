import { afterEach, describe, expect, it, vi } from 'vitest'
import { saveBlob } from './saveBlob'

afterEach(() => {
  vi.restoreAllMocks()
  Reflect.deleteProperty(URL, 'createObjectURL')
  Reflect.deleteProperty(URL, 'revokeObjectURL')
})

describe('saveBlob', () => {
  it('clica num link de download com o nome do arquivo e libera a URL temporária', () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:arquivo')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL, revokeObjectURL }))
    const clicked: HTMLAnchorElement[] = []
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this)
      expect(document.body.contains(this)).toBe(true)
    })
    const blob = new Blob(['PK'])

    saveBlob(blob, 'erros.zip')

    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(clicked).toHaveLength(1)
    expect(clicked[0]?.download).toBe('erros.zip')
    expect(clicked[0]?.href).toBe('blob:arquivo')
    expect(document.body.contains(clicked[0] ?? null)).toBe(false)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:arquivo')
  })

  it('remove o link e libera a URL mesmo quando o clique falha', () => {
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL }))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {
      throw new Error('bloqueado')
    })

    expect(() => saveBlob(new Blob(['PK']), 'erros.zip')).toThrow('bloqueado')
    expect(document.querySelector('a[download]')).toBeNull()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:x')
  })
})
