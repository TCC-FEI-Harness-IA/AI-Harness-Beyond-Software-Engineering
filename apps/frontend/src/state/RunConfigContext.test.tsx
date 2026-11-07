import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { env } from '@/config/env'
import { MODEL_PROVIDER } from '@/domain/enums/modelProvider'
import type { BackendLimits } from '@/domain/types/backendLimits'
import type { ModelInfo } from '@/domain/types/modelInfo'
import { RunConfigProvider, useRunConfig } from './RunConfigContext'

function ConfigProbe(): JSX.Element {
  const {
    config,
    maxTokensLimit,
    models,
    modelsStatus,
    reloadModels,
    setModelName,
    setMaxTokens,
    setTemperature,
    setProvider,
    reset,
  } = useRunConfig()
  return (
    <div>
      <span data-testid="model">{config.modelName}</span>
      <span data-testid="provider">{config.provider}</span>
      <button type="button" onClick={() => setProvider(MODEL_PROVIDER.OPENAI)}>
        Trocar provedor
      </button>
      <button type="button" onClick={() => setProvider('provedor-invalido')}>
        Provedor inválido
      </button>
      <span data-testid="max-tokens">{config.maxTokens}</span>
      <span data-testid="temperature">{config.temperature}</span>
      <button type="button" onClick={() => setModelName('modelo-invalido')}>
        Modelo inválido
      </button>
      <button type="button" onClick={() => setMaxTokens(0)}>
        Zerar tokens
      </button>
      <button type="button" onClick={() => setMaxTokens(1_000_000)}>
        Tokens altos
      </button>
      <span data-testid="models">{models.map((model) => model.model_name).join(',')}</span>
      <span data-testid="models-status">{modelsStatus}</span>
      <button type="button" onClick={reloadModels}>
        Recarregar modelos
      </button>
      <span data-testid="max-tokens-limit">{String(maxTokensLimit)}</span>
      <button type="button" onClick={() => setTemperature(1.4)}>
        Temperatura alta
      </button>
      <button type="button" onClick={reset}>
        Restaurar
      </button>
    </div>
  )
}

function renderProbe(
  loadLimits: (signal: AbortSignal) => Promise<BackendLimits> = () => new Promise(() => {}),
  loadModels: (signal: AbortSignal) => Promise<ModelInfo[]> = () => new Promise(() => {}),
): void {
  render(
    <RunConfigProvider loadLimits={loadLimits} loadModels={loadModels}>
      <ConfigProbe />
    </RunConfigProvider>,
  )
}

function modelo(model_name: string): ModelInfo {
  return {
    model_name,
    display_name: null,
    input_price_per_million_tokens: null,
    output_price_per_million_tokens: null,
    context_length: null,
    throughput_tokens_per_second: null,
  }
}

const BACKEND_LIMIT = { max_tokens_limit: 64000 }

beforeEach(() => {
  window.localStorage.clear()
})

describe('RunConfigContext', () => {
  it('expõe o catálogo de modelos quando ele chega', async () => {
    renderProbe(undefined, () => Promise.resolve([modelo(env.defaultModel), modelo('vendor/b')]))

    expect(screen.getByTestId('models-status')).toHaveTextContent('loading')
    await waitFor(() => expect(screen.getByTestId('models-status')).toHaveTextContent('ready'))
    expect(screen.getByTestId('models')).toHaveTextContent(`${env.defaultModel},vendor/b`)
  })

  it('falha do catálogo vira status de erro e mantém o modelo em uso', async () => {
    renderProbe(undefined, () => Promise.reject(new Error('fora do ar')))

    await waitFor(() => expect(screen.getByTestId('models-status')).toHaveTextContent('error'))
    expect(screen.getByTestId('models')).toBeEmptyDOMElement()
    expect(screen.getByTestId('model')).toHaveTextContent(env.defaultModel)
  })

  it('reloadModels busca o catálogo de novo', async () => {
    const loadModels = vi
      .fn()
      .mockResolvedValueOnce([modelo(env.defaultModel)])
      .mockResolvedValueOnce([modelo(env.defaultModel), modelo('vendor/novo')])
    renderProbe(undefined, loadModels)
    await waitFor(() => expect(screen.getByTestId('models')).toHaveTextContent(env.defaultModel))

    await userEvent.setup().click(screen.getByRole('button', { name: 'Recarregar modelos' }))

    await waitFor(() => expect(screen.getByTestId('models')).toHaveTextContent('vendor/novo'))
    expect(loadModels).toHaveBeenCalledTimes(2)
  })

  it('um modelo salvo que está no catálogo é mantido', async () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({ modelName: 'vendor/salvo', maxTokens: 900, temperature: 0.5 }),
    )

    renderProbe(undefined, () => Promise.resolve([modelo(env.defaultModel), modelo('vendor/salvo')]))

    await waitFor(() => expect(screen.getByTestId('models-status')).toHaveTextContent('ready'))
    expect(screen.getByTestId('model')).toHaveTextContent('vendor/salvo')
  })

  it('sem o default no catálogo, um modelo fora dele cai para o primeiro do catálogo', async () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({ modelName: 'vendor/removido', maxTokens: 900, temperature: 0.5 }),
    )

    renderProbe(undefined, () => Promise.resolve([modelo('vendor/primeiro'), modelo('vendor/segundo')]))

    await waitFor(() => expect(screen.getByTestId('model')).toHaveTextContent('vendor/primeiro'))
    expect(JSON.parse(window.localStorage.getItem('tcc.runConfig') ?? '{}').modelName).toBe('vendor/primeiro')
  })

  it('restaurar os padrões também escolhe um modelo do catálogo', async () => {
    renderProbe(undefined, () => Promise.resolve([modelo('vendor/unico')]))
    await waitFor(() => expect(screen.getByTestId('model')).toHaveTextContent('vendor/unico'))

    await userEvent.setup().click(screen.getByRole('button', { name: 'Restaurar' }))

    expect(screen.getByTestId('model')).toHaveTextContent('vendor/unico')
  })

  it('os defaults vêm de env', () => {
    renderProbe()

    expect(screen.getByTestId('model')).toHaveTextContent(env.defaultModel)
    expect(screen.getByTestId('max-tokens')).toHaveTextContent(String(env.defaultMaxTokens))
    expect(screen.getByTestId('temperature')).toHaveTextContent(String(env.defaultTemperature))
    expect(screen.getByTestId('provider')).toHaveTextContent(env.defaultProvider)
  })

  it('setProvider troca o provedor enviado ao backend', async () => {
    const user = userEvent.setup()
    renderProbe()

    await user.click(screen.getByRole('button', { name: 'Trocar provedor' }))

    expect(screen.getByTestId('provider')).toHaveTextContent(MODEL_PROVIDER.OPENAI)
  })

  it('um provedor fora de availableProviders é ignorado', async () => {
    const user = userEvent.setup()
    renderProbe()

    await user.click(screen.getByRole('button', { name: 'Provedor inválido' }))

    expect(screen.getByTestId('provider')).toHaveTextContent(env.defaultProvider)
  })

  it('um provedor salvo fora de availableProviders cai para o default na leitura', () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({
        modelName: env.defaultModel,
        maxTokens: 900,
        temperature: 0.5,
        provider: 'provedor-que-saiu-da-lista',
      }),
    )

    renderProbe()

    expect(screen.getByTestId('provider')).toHaveTextContent(env.defaultProvider)
  })

  it('o provedor escolhido sobrevive a uma remontagem', () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({
        modelName: env.defaultModel,
        maxTokens: 900,
        temperature: 0.5,
        provider: MODEL_PROVIDER.OPENAI,
      }),
    )

    renderProbe()

    expect(screen.getByTestId('provider')).toHaveTextContent(MODEL_PROVIDER.OPENAI)
  })

  it('um modelo salvo fora do catálogo cai para o default quando o catálogo chega', async () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({ modelName: 'modelo-que-saiu-da-lista', maxTokens: 900, temperature: 0.5 }),
    )

    renderProbe(undefined, () => Promise.resolve([modelo(env.defaultModel)]))

    expect(screen.getByTestId('model')).toHaveTextContent('modelo-que-saiu-da-lista')
    await waitFor(() => expect(screen.getByTestId('model')).toHaveTextContent(env.defaultModel))
    expect(screen.getByTestId('max-tokens')).toHaveTextContent('900')
  })

  it('setTemperature(1.4) é limitado a 1', async () => {
    const user = userEvent.setup()
    renderProbe()

    await user.click(screen.getByRole('button', { name: 'Temperatura alta' }))

    expect(screen.getByTestId('temperature')).toHaveTextContent('1')
  })

  it('setMaxTokens(0) não produz um valor não positivo', async () => {
    const user = userEvent.setup()
    renderProbe()

    await user.click(screen.getByRole('button', { name: 'Zerar tokens' }))

    expect(Number(screen.getByTestId('max-tokens').textContent)).toBeGreaterThan(0)
  })

  it('o limite do backend rebaixa o max_tokens salvo acima dele', async () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({ modelName: env.defaultModel, maxTokens: 900000, temperature: 0.5 }),
    )

    renderProbe(() => Promise.resolve(BACKEND_LIMIT))

    await waitFor(() => expect(screen.getByTestId('max-tokens')).toHaveTextContent('64000'))
    expect(screen.getByTestId('max-tokens-limit')).toHaveTextContent('64000')
    expect(JSON.parse(window.localStorage.getItem('tcc.runConfig') ?? '{}').maxTokens).toBe(64000)
  })

  it('o valor digitado nunca passa do limite por sessão do backend', async () => {
    const user = userEvent.setup()
    renderProbe(() => Promise.resolve(BACKEND_LIMIT))
    await waitFor(() => expect(screen.getByTestId('max-tokens-limit')).toHaveTextContent('64000'))

    await user.click(screen.getByRole('button', { name: 'Tokens altos' }))

    expect(screen.getByTestId('max-tokens')).toHaveTextContent('64000')
  })

  it('restaurar os padrões também respeita o limite do backend', async () => {
    const user = userEvent.setup()
    renderProbe(() => Promise.resolve({ max_tokens_limit: 10 }))
    await waitFor(() => expect(screen.getByTestId('max-tokens-limit')).toHaveTextContent('10'))

    await user.click(screen.getByRole('button', { name: 'Restaurar' }))

    expect(screen.getByTestId('max-tokens')).toHaveTextContent('10')
  })

  it('um max_tokens dentro do limite do backend é preservado', async () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({ modelName: env.defaultModel, maxTokens: 900, temperature: 0.5 }),
    )

    renderProbe(() => Promise.resolve(BACKEND_LIMIT))

    await waitFor(() => expect(screen.getByTestId('max-tokens-limit')).toHaveTextContent('64000'))
    expect(screen.getByTestId('max-tokens')).toHaveTextContent('900')
  })

  it('sem o limite do backend o valor fica sem teto local', async () => {
    const user = userEvent.setup()
    renderProbe(() => Promise.reject(new Error('backend fora do ar')))

    await user.click(screen.getByRole('button', { name: 'Tokens altos' }))

    expect(screen.getByTestId('max-tokens')).toHaveTextContent('1000000')
    expect(screen.getByTestId('max-tokens-limit')).toHaveTextContent('null')
  })

  it('um localStorage que lança não quebra o provider', () => {
    const storageProto = Object.getPrototypeOf(window.localStorage) as Storage
    const getItemSpy = vi.spyOn(storageProto, 'getItem').mockImplementation(() => {
      throw new Error('acesso bloqueado')
    })

    expect(() => renderProbe()).not.toThrow()
    expect(screen.getByTestId('model')).toHaveTextContent(env.defaultModel)

    getItemSpy.mockRestore()
  })
})
