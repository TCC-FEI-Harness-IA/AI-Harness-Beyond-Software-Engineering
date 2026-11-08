import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Button } from './Button'

describe('Button', () => {
  it('renderiza o rótulo', () => {
    render(<Button>Enviar</Button>)
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeInTheDocument()
  })

  it('dispara onClick ao clicar', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Enviar</Button>)

    await user.click(screen.getByRole('button', { name: 'Enviar' }))

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('disabled bloqueia o clique', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <Button disabled onClick={onClick}>
        Enviar
      </Button>,
    )

    await user.click(screen.getByRole('button', { name: 'Enviar' }))

    expect(onClick).not.toHaveBeenCalled()
  })

  it('loading bloqueia o clique e põe aria-busy', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <Button loading onClick={onClick}>
        Enviar
      </Button>,
    )

    const button = screen.getByRole('button', { name: 'Enviar' })
    expect(button).toHaveAttribute('aria-busy', 'true')

    await user.click(button)

    expect(onClick).not.toHaveBeenCalled()
  })
})
