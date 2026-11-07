import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { env } from '@/config/env'
import { MODEL_PROVIDER, PROVIDER_LABELS } from '@/domain/enums/modelProvider'
import type { ModelInfo } from '@/domain/types/modelInfo'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { RunConfigBar } from './RunConfigBar'

function renderBar(
  loadLimits: () => Promise<{ max_tokens_limit: number }> = () => new Promise(() => {}),
  loadModels: () => Promise<ModelInfo[]> = () => new Promise(() => {}),
): void {
  render(
    <MemoryRouter>
      <RunConfigProvider loadLimits={loadLimits} loadModels={loadModels}>
        <RunConfigBar />
      </RunConfigProvider>
    </MemoryRouter>,
  )
}

function infoDe(modelName: string, overrides: Partial<ModelInfo> = {}): ModelInfo {
  return {
    model_name: modelName,
    display_name: 'Vendor: Modelo',
    input_price_per_million_tokens: 0.0434,
    output_price_per_million_tokens: 0.3,
    context_length: 1048576,
    throughput_tokens_per_second: 117.6,
    ...overrides,
  }
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('RunConfigBar', () => {
  it('o máximo de tokens é por sessão e mostra o limite do backend', async () => {
    renderBar(() => Promise.resolve({ max_tokens_limit: 64000 }))

    const campo = screen.getByRole('spinbutton', { name: /Máximo de tokens por sessão/ })
    expect(screen.getByText(/Soma de todas as chamadas ao modelo na sessão/)).toBeInTheDocument()
    expect(await screen.findByText(/Máximo do backend: 64\.000\./)).toBeInTheDocument()
    expect(campo).toHaveAttribute('max', '64000')
  })

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

  it('lista os modelos do catálogo com preço, contexto e vazão', async () => {
    renderBar(undefined, () => Promise.resolve([infoDe(env.defaultModel)]))

    const tabela = await screen.findByRole('table', { name: 'Modelos disponíveis' })
    const linha = within(tabela).getByRole('row', { name: /Vendor: Modelo/ })
    expect(within(linha).getByText(env.defaultModel)).toBeInTheDocument()
    expect(within(linha).getByText(/US\$\s0,0434/)).toBeInTheDocument()
    expect(within(linha).getByText(/US\$\s0,30/)).toBeInTheDocument()
    expect(within(linha).getByText('1 mi tokens')).toBeInTheDocument()
    expect(within(linha).getByText('118 tok/s')).toBeInTheDocument()
  })

  it('marca o modelo em uso e troca a seleção ao clicar em outro', async () => {
    renderBar(undefined, () =>
      Promise.resolve([infoDe(env.defaultModel), infoDe('vendor/outro', { display_name: 'Vendor: Outro' })]),
    )
    const user = userEvent.setup()

    expect(await screen.findByRole('radio', { name: 'Vendor: Modelo' })).toBeChecked()

    await user.click(screen.getByRole('row', { name: /Vendor: Outro/ }))

    expect(screen.getByRole('radio', { name: 'Vendor: Outro' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Vendor: Modelo' })).not.toBeChecked()
    expect(screen.getAllByRole('radio', { checked: true })).toHaveLength(1)
  })

  it('ordena a lista pela coluna clicada', async () => {
    renderBar(undefined, () =>
      Promise.resolve([
        infoDe('vendor/lento', { display_name: 'A lento', throughput_tokens_per_second: 20 }),
        infoDe('vendor/rapido', { display_name: 'B rápido', throughput_tokens_per_second: 300 }),
      ]),
    )
    const user = userEvent.setup()
    const tabela = await screen.findByRole('table', { name: 'Modelos disponíveis' })
    const nomes = (): string[] =>
      within(tabela)
        .getAllByRole('radio')
        .map((radio) => radio.getAttribute('aria-label') ?? '')

    expect(nomes()).toEqual(['A lento', 'B rápido'])

    await user.click(within(tabela).getByRole('button', { name: /Vazão/ }))

    expect(nomes()).toEqual(['B rápido', 'A lento'])
    expect(within(tabela).getByRole('columnheader', { name: /Vazão/ })).toHaveAttribute('aria-sort', 'descending')
  })

  it('mostra "—" para o dado desconhecido, sem esconder os demais', async () => {
    renderBar(undefined, () =>
      Promise.resolve([
        infoDe(env.defaultModel, { input_price_per_million_tokens: null, throughput_tokens_per_second: null }),
      ]),
    )

    const linha = await screen.findByRole('row', { name: /Vendor: Modelo/ })
    expect(within(linha).getAllByText('—')).toHaveLength(2)
    expect(within(linha).getByText('1 mi tokens')).toBeInTheDocument()
  })

  it('mostra um esqueleto enquanto o catálogo não chega', () => {
    renderBar()

    expect(screen.queryByRole('table', { name: 'Modelos disponíveis' })).not.toBeInTheDocument()
    expect(screen.getByText(env.defaultModel)).toBeInTheDocument()
  })

  it('avisa quando não há modelos cadastrados', async () => {
    renderBar(undefined, () => Promise.resolve([]))

    expect(await screen.findByText(/Nenhum modelo cadastrado/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Cadastre o primeiro.' })).toHaveAttribute('href', '/modelos')
  })

  it('avisa a falha do catálogo e permite tentar de novo', async () => {
    let tentativas = 0
    renderBar(undefined, () => {
      tentativas += 1
      return tentativas === 1 ? Promise.reject(new Error('fora do ar')) : Promise.resolve([infoDe(env.defaultModel)])
    })
    const user = userEvent.setup()

    expect(await screen.findByRole('alert')).toHaveTextContent(/Não foi possível carregar o catálogo/)

    await user.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByRole('table', { name: 'Modelos disponíveis' })).toBeInTheDocument()
  })

  it('leva à tela de cadastro de modelos', () => {
    renderBar()

    expect(screen.getByRole('link', { name: 'Gerenciar modelos' })).toHaveAttribute('href', '/modelos')
  })
})
