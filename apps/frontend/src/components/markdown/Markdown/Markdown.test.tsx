import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Markdown } from './Markdown'

describe('Markdown', () => {
  it('tabela GFM vira <table>', () => {
    const content = '| A | B |\n|---|---|\n| 1 | 2 |\n'
    render(<Markdown content={content} />)

    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
  })

  it('bloco de código vira <pre><code>', () => {
    const content = '```ts\nconst x = 1\n```'
    const { container } = render(<Markdown content={content} />)

    const pre = container.querySelector('pre')
    expect(pre).not.toBeNull()
    expect(pre?.querySelector('code')).not.toBeNull()
  })

  it('HTML cru no conteúdo é exibido como texto, não interpretado (XSS)', () => {
    const content = 'Antes <img src=x onerror="window.__xss = true"> depois'
    const { container } = render(<Markdown content={content} />)

    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('<img src=x onerror="window.__xss = true">')
  })

  it('link recebe rel="noreferrer"', () => {
    render(<Markdown content="[exemplo](https://example.com)" />)

    expect(screen.getByRole('link', { name: 'exemplo' })).toHaveAttribute('rel', 'noreferrer')
  })
})
