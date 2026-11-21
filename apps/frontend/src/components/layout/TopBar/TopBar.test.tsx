import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '@/state/AuthContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { TopBar } from './TopBar'
import { TestAuth } from '@/test/TestAuth'
import { CREDENCIAL_VALIDA, fakeAuthApi, SESSAO_ANA } from '@/test/renderWithAuth'

function renderTopBar(): void {
  render(
    <MemoryRouter>
      <ThemeProvider><TestAuth>
        <TopBar />
      </TestAuth></ThemeProvider>
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

  it('avisa quando o logout falha e oferece uma nova tentativa sem simular a saída', async () => {
    const user = userEvent.setup()
    const logout = vi.fn().mockRejectedValueOnce(new Error('rede')).mockResolvedValue(undefined)
    render(
      <MemoryRouter>
        <ThemeProvider>
          <AuthProvider api={{ ...fakeAuthApi(), logout }} initialState={{ session: SESSAO_ANA, credential: CREDENCIAL_VALIDA }}>
            <TopBar />
          </AuthProvider>
        </ThemeProvider>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Sair' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível confirmar sua saída')
    expect(screen.getByText(SESSAO_ANA.user.email)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Tentar sair novamente' }))

    expect(await screen.findByRole('link', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(logout).toHaveBeenCalledTimes(2)
  })
})
