import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeProvider, useTheme } from './ThemeContext'

function ThemeProbe(): JSX.Element {
  const { theme, setTheme } = useTheme()
  return (
    <div>
      <span data-testid="current-theme">{theme}</span>
      <button type="button" onClick={() => setTheme('dark')}>
        Escuro
      </button>
      <button type="button" onClick={() => setTheme('light')}>
        Claro
      </button>
    </div>
  )
}

beforeEach(() => {
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

describe('ThemeContext', () => {
  it('alternar o tema escreve data-theme no elemento raiz', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Escuro' }))

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark')
  })

  it('a preferência escolhida persiste em localStorage', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Claro' }))

    expect(window.localStorage.getItem('tcc.theme')).toBe('light')
  })

  it('um localStorage que lança não quebra o provider', async () => {
    const storageProto = Object.getPrototypeOf(window.localStorage) as Storage
    const getItemSpy = vi.spyOn(storageProto, 'getItem').mockImplementation(() => {
      throw new Error('acesso bloqueado')
    })
    const setItemSpy = vi.spyOn(storageProto, 'setItem').mockImplementation(() => {
      throw new Error('acesso bloqueado')
    })

    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('system')
    await user.click(screen.getByRole('button', { name: 'Escuro' }))
    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark')

    getItemSpy.mockRestore()
    setItemSpy.mockRestore()
  })
})
