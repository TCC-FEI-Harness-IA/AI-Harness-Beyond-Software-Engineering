import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@/state/ThemeContext'
import { TopBar } from './TopBar'

function renderTopBar(): void {
  render(
    <MemoryRouter>
      <ThemeProvider>
        <TopBar />
      </ThemeProvider>
    </MemoryRouter>,
  )
}

describe('TopBar', () => {
  it('a marca mostra o ícone do projeto antes do nome, e o link continua se chamando "TCC Harness"', () => {
    renderTopBar()

    const brand = screen.getByRole('link', { name: 'TCC Harness' })
    const icon = brand.querySelector('img')
    expect(icon).not.toBeNull()
    expect(icon?.getAttribute('src')).toContain('ralph_image')
    // Decorativo: o nome acessível do link não pode duplicar o texto ao lado.
    expect(icon).toHaveAttribute('alt', '')
  })
})
