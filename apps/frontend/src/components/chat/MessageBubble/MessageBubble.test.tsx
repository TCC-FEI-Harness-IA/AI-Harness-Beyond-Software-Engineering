import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MessageBubble } from './MessageBubble'

describe('MessageBubble', () => {
  it('role="user" e role="assistant" produzem estruturas distintas', () => {
    render(
      <>
        <MessageBubble role="user" content="Pergunta do usuário" />
        <MessageBubble role="assistant" content="Resposta do modelo" />
      </>,
    )

    expect(screen.getByRole('group', { name: 'Mensagem do usuário' })).toHaveTextContent(
      'Pergunta do usuário',
    )
    expect(screen.getByRole('group', { name: 'Mensagem do modelo' })).toHaveTextContent(
      'Resposta do modelo',
    )
  })

  it('role="system" não usa bolha — vira separador com texto', () => {
    render(<MessageBubble role="system" content="Contexto reinicializado" />)
    expect(screen.getByText('Contexto reinicializado')).toBeInTheDocument()
    expect(screen.queryByRole('group')).not.toBeInTheDocument()
  })

  it('emphasis="final" aplica o destaque', () => {
    render(<MessageBubble role="assistant" content="Resposta final" emphasis="final" />)
    expect(screen.getByRole('group')).toHaveAttribute('aria-roledescription', 'Resposta final')
  })

  it('o conteúdo passa pelo Markdown (negrito vira <strong>)', () => {
    render(<MessageBubble role="assistant" content="Texto em **negrito**" />)
    expect(screen.getByText('negrito').tagName).toBe('STRONG')
  })
})
