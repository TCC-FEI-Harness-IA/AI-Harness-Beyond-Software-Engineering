import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { MacroNodeView } from '@/domain/services/graphLayout'
import { PhaseNode } from './PhaseNode'

function buildNode(overrides: Partial<MacroNodeView> = {}): MacroNodeView {
  return {
    id: 'A1',
    shortLabel: 'A.1',
    subtitle: 'Critérios de aceite gerais',
    status: 'pending',
    progress: null,
    ...overrides,
  }
}

describe('PhaseNode', () => {
  it('estado done: botão com aria-label de etapa concluída', () => {
    render(<PhaseNode node={buildNode({ status: 'done' })} />)
    expect(screen.getByRole('button', { name: 'Critérios de aceite gerais — etapa concluída' })).toBeInTheDocument()
  })

  it('estado active: botão com aria-label de etapa atual', () => {
    render(<PhaseNode node={buildNode({ status: 'active' })} />)
    expect(screen.getByRole('button', { name: 'Critérios de aceite gerais — etapa atual' })).toBeInTheDocument()
  })

  it('estado pending: botão com aria-label de próxima etapa', () => {
    render(<PhaseNode node={buildNode({ status: 'pending' })} />)
    expect(screen.getByRole('button', { name: 'Critérios de aceite gerais — próxima etapa' })).toBeInTheDocument()
  })

  it('estado skipped: tem o title explicativo "Não foi necessário"', () => {
    render(<PhaseNode node={buildNode({ status: 'skipped' })} />)
    const button = screen.getByRole('button', { name: 'Critérios de aceite gerais — não foi necessária' })
    expect(button).toHaveAttribute('title', 'Não foi necessário')
  })

  it('nó B mostra o contador de progresso', () => {
    render(<PhaseNode node={buildNode({ id: 'B', shortLabel: 'B', subtitle: 'Execução em Loop', status: 'active', progress: { done: 2, total: 3 } })} />)
    expect(screen.getByText('2/3')).toBeInTheDocument()
  })

  it('clicar chama onSelect', async () => {
    const onSelect = vi.fn()
    render(<PhaseNode node={buildNode()} onSelect={onSelect} />)
    screen.getByRole('button').click()
    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})
