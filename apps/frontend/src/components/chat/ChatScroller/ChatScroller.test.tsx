import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChatScroller } from './ChatScroller'

// jsdom não faz layout real — controla scrollHeight/scrollTop/clientHeight manualmente para
// simular "usuário no fim" vs. "usuário longe do fim" (README: limiar de ~64px).
function mockScrollGeometry(element: HTMLElement, { scrollHeight, scrollTop, clientHeight }: {
  scrollHeight: number
  scrollTop: number
  clientHeight: number
}): void {
  Object.defineProperty(element, 'scrollHeight', { configurable: true, value: scrollHeight })
  Object.defineProperty(element, 'scrollTop', { configurable: true, value: scrollTop, writable: true })
  Object.defineProperty(element, 'clientHeight', { configurable: true, value: clientHeight })
}

describe('ChatScroller', () => {
  it('conteúdo novo com o usuário no fim → rola', () => {
    const { container, rerender } = render(<ChatScroller contentKey={1}>Conteúdo 1</ChatScroller>)
    const scroller = container.firstElementChild as HTMLElement
    mockScrollGeometry(scroller, { scrollHeight: 500, scrollTop: 450, clientHeight: 50 })
    scroller.dispatchEvent(new Event('scroll'))
    scroller.scrollTo = vi.fn()

    rerender(<ChatScroller contentKey={2}>Conteúdo 2</ChatScroller>)

    expect(scroller.scrollTo).toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Ir para o fim' })).not.toBeInTheDocument()
  })

  it('conteúdo novo com o usuário longe do fim → não rola e mostra o botão', () => {
    const { container, rerender } = render(<ChatScroller contentKey={1}>Conteúdo 1</ChatScroller>)
    const scroller = container.firstElementChild as HTMLElement
    mockScrollGeometry(scroller, { scrollHeight: 2000, scrollTop: 0, clientHeight: 50 })
    scroller.scrollTo = vi.fn()
    scroller.dispatchEvent(new Event('scroll'))

    rerender(<ChatScroller contentKey={2}>Conteúdo 2</ChatScroller>)

    expect(scroller.scrollTo).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Ir para o fim' })).toBeInTheDocument()
  })
})
