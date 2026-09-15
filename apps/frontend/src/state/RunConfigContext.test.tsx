import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { env } from '@/config/env'
import { MODEL_PROVIDER } from '@/domain/enums/modelProvider'
import { RunConfigProvider, useRunConfig } from './RunConfigContext'

function ConfigProbe(): JSX.Element {
  const { config, setModelName, setMaxTokens, setTemperature, setProvider, reset } = useRunConfig()
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
      <button type="button" onClick={() => setTemperature(1.4)}>
        Temperatura alta
      </button>
      <button type="button" onClick={reset}>
        Restaurar
      </button>
    </div>
  )
}

function renderProbe(): void {
  render(
    <RunConfigProvider>
      <ConfigProbe />
    </RunConfigProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('RunConfigContext', () => {
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

  it('um modelo salvo fora de availableModels cai para o default na leitura', () => {
    window.localStorage.setItem(
      'tcc.runConfig',
      JSON.stringify({ modelName: 'modelo-que-saiu-da-lista', maxTokens: 900, temperature: 0.5 }),
    )

    renderProbe()

    expect(screen.getByTestId('model')).toHaveTextContent(env.defaultModel)
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
