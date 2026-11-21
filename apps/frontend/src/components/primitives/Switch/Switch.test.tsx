import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Switch } from './Switch'

describe('Switch', () => {
  it('role="switch" com aria-checked correto', () => {
    const { rerender } = render(<Switch checked={false} onChange={vi.fn()} label="Modo escuro" />)
    expect(screen.getByRole('switch', { name: 'Modo escuro' })).toHaveAttribute('aria-checked', 'false')

    rerender(<Switch checked onChange={vi.fn()} label="Modo escuro" />)
    expect(screen.getByRole('switch', { name: 'Modo escuro' })).toHaveAttribute('aria-checked', 'true')
  })

  it('espaço alterna o estado', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Switch checked={false} onChange={onChange} label="Modo escuro" />)

    screen.getByRole('switch').focus()
    await user.keyboard(' ')

    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('enter alterna o estado', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Switch checked={false} onChange={onChange} label="Modo escuro" />)

    screen.getByRole('switch').focus()
    await user.keyboard('{Enter}')

    expect(onChange).toHaveBeenCalledWith(true)
  })
})
