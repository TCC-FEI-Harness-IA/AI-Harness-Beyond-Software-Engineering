import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { Composer } from './Composer'

// jsdom não calcula layout — scrollHeight é sempre 0. Simula um scrollHeight proporcional ao
// texto para que o teste de "recalcula a altura" seja significativo.
let originalScrollHeight: PropertyDescriptor | undefined

beforeAll(() => {
  originalScrollHeight = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'scrollHeight')
  Object.defineProperty(HTMLTextAreaElement.prototype, 'scrollHeight', {
    configurable: true,
    get(this: HTMLTextAreaElement) {
      return this.value.length * 2 + 20
    },
  })
})

afterAll(() => {
  if (originalScrollHeight) {
    Object.defineProperty(HTMLTextAreaElement.prototype, 'scrollHeight', originalScrollHeight)
  }
})

function ControlledComposer({
  onSubmit,
  busy = false,
}: {
  onSubmit: (value: string) => void
  busy?: boolean
}): JSX.Element {
  const [value, setValue] = useState('')
  return (
    <Composer
      value={value}
      onChange={setValue}
      onSubmit={() => onSubmit(value)}
      busy={busy}
      placeholder="Digite sua pergunta"
    />
  )
}

describe('Composer', () => {
  it('Enter envia', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<ControlledComposer onSubmit={onSubmit} />)

    await user.type(screen.getByRole('textbox'), 'Olá{Enter}')

    expect(onSubmit).toHaveBeenCalledWith('Olá')
  })

  it('Shift+Enter não envia', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<ControlledComposer onSubmit={onSubmit} />)

    await user.type(screen.getByRole('textbox'), 'Olá{Shift>}{Enter}{/Shift}')

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('valor só com espaços não envia', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<ControlledComposer onSubmit={onSubmit} />)

    await user.type(screen.getByRole('textbox'), '   {Enter}')

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('busy bloqueia o envio', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<ControlledComposer onSubmit={onSubmit} busy />)

    await user.type(screen.getByRole('textbox'), 'Olá{Enter}')

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('a altura recalcula ao apagar texto', async () => {
    const user = userEvent.setup()
    render(<ControlledComposer onSubmit={vi.fn()} />)

    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
    await user.type(textarea, 'Uma linha bem longa de texto{Enter}{Shift>}{Enter}{/Shift}outra linha')
    const heightWithText = textarea.style.height

    await user.clear(textarea)
    const heightAfterClear = textarea.style.height

    expect(heightAfterClear).not.toBe(heightWithText)
  })
})
