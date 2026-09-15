import { useId, useState } from 'react'
import { Button } from '@/components/primitives/Button'
import { env } from '@/config/env'
import { PROVIDER_LABELS, providerLabel } from '@/domain/enums/modelProvider'
import { formatTemperature } from '@/domain/services/formatters'
import { useRunConfig } from '@/state/RunConfigContext'
import styles from './RunConfigBar.module.css'

const TEMPERATURE_MIN = 0
const TEMPERATURE_MAX = 1
const TEMPERATURE_STEP = 0.1
const MAX_TOKENS_MIN = 1

/**
 * Barra discreta de configuração da home (README, FASE 04, seção 5.4): provedor, modelo, teto
 * de tokens e temperatura, atrás de um popover. Quando só existe uma opção de provedor ou de
 * modelo, o seletor correspondente some e a barra mostra apenas o valor em uso.
 */
export function RunConfigBar(): JSX.Element {
  const { config, setModelName, setMaxTokens, setTemperature, setProvider, reset } = useRunConfig()
  const [open, setOpen] = useState(false)
  const panelId = useId()

  const hasModelChoice = env.availableModels.length > 1
  const hasProviderChoice = env.availableProviders.length > 1
  const modelSummary = hasModelChoice ? config.modelName : (env.availableModels[0] ?? config.modelName)

  return (
    <div className={styles.wrapper}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {providerLabel(config.provider)} · {modelSummary} · {config.maxTokens} tokens · temp.{' '}
        {formatTemperature(config.temperature)}
      </button>

      {open ? (
        <div id={panelId} className={styles.panel} role="group" aria-label="Configuração de execução">
          {hasProviderChoice ? (
            <label className={styles.field}>
              <span>Provedor</span>
              <select value={config.provider} onChange={(event) => setProvider(event.target.value)}>
                {env.availableProviders.map((provider) => (
                  <option key={provider} value={provider}>
                    {PROVIDER_LABELS[provider]}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {hasModelChoice ? (
            <label className={styles.field}>
              <span>Modelo</span>
              <select value={config.modelName} onChange={(event) => setModelName(event.target.value)}>
                {env.availableModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className={styles.field}>
            <span>Máximo de tokens</span>
            <input
              type="number"
              min={MAX_TOKENS_MIN}
              step={1}
              value={config.maxTokens}
              onChange={(event) => setMaxTokens(Number(event.target.value))}
            />
          </label>

          <label className={styles.field}>
            <span>Temperatura ({formatTemperature(config.temperature)})</span>
            <input
              type="range"
              min={TEMPERATURE_MIN}
              max={TEMPERATURE_MAX}
              step={TEMPERATURE_STEP}
              value={config.temperature}
              onChange={(event) => setTemperature(Number(event.target.value))}
            />
          </label>

          <Button variant="ghost" size="sm" onClick={reset}>
            Restaurar padrões
          </Button>
        </div>
      ) : null}
    </div>
  )
}
