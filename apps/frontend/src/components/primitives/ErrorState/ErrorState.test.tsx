import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ErrorState } from './ErrorState'

describe('ErrorState', () => {
  it('mostra error.userMessage', () => {
    render(<ErrorState error={{ userMessage: 'Chat não encontrado.' }} />)
    expect(screen.getByText('Chat não encontrado.')).toBeInTheDocument()
  })

  it('a mensagem técnica fica dentro de um <details>', () => {
    render(<ErrorState error={{ userMessage: 'Falhou.', message: 'HTTP 500: detalhe cru' }} />)

    const details = screen.getByText('Detalhe técnico').closest('details')
    expect(details).not.toBeNull()
    expect(details).toHaveTextContent('HTTP 500: detalhe cru')
  })

  it('"Tentar de novo" chama onRetry', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<ErrorState error={{ userMessage: 'Falhou.' }} onRetry={onRetry} />)

    await user.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('sem onRetry, o botão não aparece', () => {
    render(<ErrorState error={{ userMessage: 'Falhou.' }} />)
    expect(screen.queryByRole('button', { name: 'Tentar de novo' })).not.toBeInTheDocument()
  })
})
