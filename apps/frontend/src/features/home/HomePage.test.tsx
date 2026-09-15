import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { ROUTES } from '@/router/routes'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { HomePage } from './HomePage'

function DestinationProbe({ label }: { label: string }): JSX.Element {
  return <div data-testid="destination">{label}</div>
}

function renderHome(): void {
  render(
    <MemoryRouter initialEntries={[ROUTES.home]}>
      <RunConfigProvider>
        <Routes>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.simpleChat} element={<DestinationProbe label="simples" />} />
          <Route path={ROUTES.ralphChat} element={<DestinationProbe label="ralph" />} />
        </Routes>
      </RunConfigProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('HomePage', () => {
  it('mostra os dois cartões de modo', () => {
    renderHome()

    expect(screen.getByRole('radio', { name: /Inferência Simples/ })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Ralph Loop Adaptado/ })).toBeInTheDocument()
  })

  it('enviar com o cartão Inferência Simples navega para /chat/simples com a pergunta', async () => {
    const user = userEvent.setup()
    renderHome()

    await user.type(screen.getByRole('textbox'), 'Quais são os números primos entre 0 e 20?')
    await user.click(screen.getByRole('radio', { name: /Inferência Simples/ }))

    expect(await screen.findByTestId('destination')).toHaveTextContent('simples')
  })

  it('enviar com o cartão Ralph navega para /chat/ralph', async () => {
    const user = userEvent.setup()
    renderHome()

    await user.type(screen.getByRole('textbox'), 'Quais são os números primos entre 0 e 20?')
    await user.click(screen.getByRole('radio', { name: /Ralph Loop Adaptado/ }))

    expect(await screen.findByTestId('destination')).toHaveTextContent('ralph')
  })

  it('campo vazio não navega e o campo recebe foco', async () => {
    const user = userEvent.setup()
    renderHome()

    await user.click(screen.getByRole('radio', { name: /Ralph Loop Adaptado/ }))

    expect(screen.queryByTestId('destination')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox')).toHaveFocus()
  })

  it('Enter no Composer envia', async () => {
    const user = userEvent.setup()
    renderHome()

    await user.type(
      screen.getByRole('textbox'),
      'Quais são os números primos entre 0 e 20?{Enter}',
    )

    expect(await screen.findByTestId('destination')).toBeInTheDocument()
  })

  it('a seleção de modo é alcançável por teclado', async () => {
    const user = userEvent.setup()
    renderHome()

    await user.type(screen.getByRole('textbox'), 'Pergunta de teste')

    let foundRadio = false
    for (let attempt = 0; attempt < 6 && !foundRadio; attempt += 1) {
      await user.tab()
      foundRadio = document.activeElement?.getAttribute('role') === 'radio'
    }
    expect(foundRadio).toBe(true)

    await user.keyboard('{Enter}')

    expect(await screen.findByTestId('destination')).toBeInTheDocument()
  })
})
