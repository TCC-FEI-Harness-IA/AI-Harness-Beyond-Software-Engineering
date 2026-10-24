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

beforeEach(() => {
  window.localStorage.clear()
})

describe('RunConfigBar', () => {
  it('mostra o módulo de configuração sempre visível, sem precisar abrir nada', () => {
    renderBar()

    expect(screen.getByRole('group', { name: 'Configuração de execução' })).toBeInTheDocument()
    expect(screen.getByLabelText('Provedor')).toHaveValue(env.defaultProvider)
  })

  it('oferece um seletor com todos os provedores disponíveis', () => {
    renderBar()

    const seletor = screen.getByLabelText('Provedor')
    expect(seletor).toHaveValue(env.defaultProvider)
    for (const provider of env.availableProviders) {
      expect(screen.getByRole('option', { name: PROVIDER_LABELS[provider] })).toBeInTheDocument()
    }
  })

  it('escolher outro provedor atualiza a seleção', async () => {
    renderBar()
    const user = userEvent.setup()

    await user.selectOptions(screen.getByLabelText('Provedor'), MODEL_PROVIDER.OPENAI)

    expect(screen.getByLabelText('Provedor')).toHaveValue(MODEL_PROVIDER.OPENAI)
  })

  it('restaurar padrões devolve o provedor default', async () => {
    renderBar()
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Provedor'), MODEL_PROVIDER.OPENAI)

    await user.click(screen.getByRole('button', { name: 'Restaurar padrões' }))

    expect(screen.getByLabelText('Provedor')).toHaveValue(env.defaultProvider)
  })
})
