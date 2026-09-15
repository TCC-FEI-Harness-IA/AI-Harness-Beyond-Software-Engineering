import { useId, useState } from 'react'
import { Button } from '@/components/primitives/Button'
import { env } from '@/config/env'
import { formatTemperature } from '@/domain/services/formatters'
import { useRunConfig } from '@/state/RunConfigContext'
import styles from './RunConfigBar.module.css'

const TEMPERATURE_MIN = 0
const TEMPERATURE_MAX = 1
const TEMPERATURE_STEP = 0.1
const MAX_TOKENS_MIN = 1

/**
 * Barra discreta de configuração da home (README, FASE 04, seção 5.4): modelo, teto de tokens
 * e temperatura, atrás de um popover. Quando só existe um modelo disponível, o seletor some e
 * a barra mostra o nome do modelo puro.
 */
export function RunConfigBar(): JSX.Element {
  const { config, setModelName, setMaxTokens, setTemperature, reset } = useRunConfig()
  const [open, setOpen] = useState(false)
  const panelId = useId()

  const hasModelChoice = env.availableModels.length > 1
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
        Modelo: {modelSummary} · {config.maxTokens} tokens · temp. {formatTemperature(config.temperature)}
      </button>

      {open ? (
        <div id={panelId} className={styles.panel} role="group" aria-label="Configuração de execução">
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
