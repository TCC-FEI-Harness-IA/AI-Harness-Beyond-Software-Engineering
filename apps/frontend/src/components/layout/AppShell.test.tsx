import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { ThemeProvider } from '@/state/ThemeContext'

function renderShell(children: ReactNode, sidebar?: ReactNode): void {
  render(
    <MemoryRouter>
      <ThemeProvider>
        <AppShell sidebar={sidebar}>{children}</AppShell>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

describe('AppShell', () => {
  it('renderiza os children', () => {
    renderShell(<p>Conteúdo da tela</p>)

    expect(screen.getByText('Conteúdo da tela')).toBeInTheDocument()
  })

  it('sem a prop sidebar não existe região de barra lateral', () => {
    renderShell(<p>Conteúdo</p>)

    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  })

  it('com a prop sidebar existe região de barra lateral', () => {
    renderShell(<p>Conteúdo</p>, <nav>Menu do histórico</nav>)

    expect(screen.getByRole('complementary')).toBeInTheDocument()
    expect(screen.getByText('Menu do histórico')).toBeInTheDocument()
  })

  it('o link "pular para o conteúdo" é o primeiro elemento focável e aponta para o conteúdo principal', () => {
    renderShell(<p>Conteúdo</p>)

    const skipLink = screen.getByRole('link', { name: 'Pular para o conteúdo' })
    expect(skipLink).toHaveAttribute('href', '#main-content')
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
  })
})
