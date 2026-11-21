import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { SegmentedControl } from './SegmentedControl'

const OPTIONS = [
  { value: 'chat', label: 'Modo chat' },
  { value: 'graph', label: 'Modo gráfico' },
] as const

function ControlledSegmentedControl(): JSX.Element {
  const [value, setValue] = useState<'chat' | 'graph'>('chat')
  return <SegmentedControl ariaLabel="Modo de visualização" options={OPTIONS} value={value} onChange={setValue} />
}

describe('SegmentedControl', () => {
  it('a opção selecionada tem aria-checked="true"', () => {
    render(<ControlledSegmentedControl />)

    expect(screen.getByRole('radio', { name: 'Modo chat' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('radio', { name: 'Modo gráfico' })).toHaveAttribute('aria-checked', 'false')
  })

  it('clicar dispara onChange com o valor tipado', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <SegmentedControl ariaLabel="Modo de visualização" options={OPTIONS} value="chat" onChange={onChange} />,
    )

    await user.click(screen.getByRole('radio', { name: 'Modo gráfico' }))

    expect(onChange).toHaveBeenCalledWith('graph')
  })

  it('setas ← → mudam a seleção', async () => {
    const user = userEvent.setup()
    render(<ControlledSegmentedControl />)

    screen.getByRole('radio', { name: 'Modo chat' }).focus()
    await user.keyboard('{ArrowRight}')

    expect(screen.getByRole('radio', { name: 'Modo gráfico' })).toHaveAttribute('aria-checked', 'true')

    await user.keyboard('{ArrowLeft}')

    expect(screen.getByRole('radio', { name: 'Modo chat' })).toHaveAttribute('aria-checked', 'true')
  })

  it('o radiogroup tem o aria-label', () => {
    render(<ControlledSegmentedControl />)
    expect(screen.getByRole('radiogroup', { name: 'Modo de visualização' })).toBeInTheDocument()
  })
})
