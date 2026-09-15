import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { env } from '@/config/env'
import { MODEL_PROVIDER, PROVIDER_LABELS } from '@/domain/enums/modelProvider'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { RunConfigBar } from './RunConfigBar'

function renderBar(): void {
  render(
    <RunConfigProvider>
      <RunConfigBar />
    </RunConfigProvider>,
  )
}

async function abrirPainel(): Promise<ReturnType<typeof userEvent.setup>> {
  renderBar()
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { expanded: false }))
  return user
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('RunConfigBar', () => {
  it('o resumo nomeia o provedor em uso', () => {
    renderBar()

    expect(screen.getByRole('button', { expanded: false })).toHaveTextContent(
      PROVIDER_LABELS[env.defaultProvider],
    )
  })

  it('oferece um seletor com todos os provedores disponíveis', async () => {
    await abrirPainel()

    const seletor = screen.getByLabelText('Provedor')
    expect(seletor).toHaveValue(env.defaultProvider)
    for (const provider of env.availableProviders) {
      expect(screen.getByRole('option', { name: PROVIDER_LABELS[provider] })).toBeInTheDocument()
    }
  })

  it('escolher outro provedor atualiza o resumo', async () => {
    const user = await abrirPainel()

    await user.selectOptions(screen.getByLabelText('Provedor'), MODEL_PROVIDER.OPENAI)

    expect(screen.getByRole('button', { expanded: true })).toHaveTextContent(
      PROVIDER_LABELS[MODEL_PROVIDER.OPENAI],
    )
  })

  it('restaurar padrões devolve o provedor default', async () => {
    const user = await abrirPainel()
    await user.selectOptions(screen.getByLabelText('Provedor'), MODEL_PROVIDER.OPENAI)

    await user.click(screen.getByRole('button', { name: 'Restaurar padrões' }))

    expect(screen.getByLabelText('Provedor')).toHaveValue(env.defaultProvider)
  })
})
