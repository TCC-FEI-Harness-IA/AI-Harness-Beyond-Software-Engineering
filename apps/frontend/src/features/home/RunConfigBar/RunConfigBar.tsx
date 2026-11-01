import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { RangeInput } from '@/components/primitives/RangeInput'
import { Select } from '@/components/primitives/Select'
import { TextInput } from '@/components/primitives/TextInput'
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
 * Módulo fixo de configuração da home (README, FASE 04, seção 5.4): provedor, modelo, teto
 * de tokens e temperatura, sempre visíveis — não é mais um popover atrás de um botão. Quando
 * só existe uma opção de provedor ou de modelo, o seletor correspondente some e a barra mostra
 * apenas o valor em uso.
 */
export function RunConfigBar(): JSX.Element {
  const { config, setModelName, setMaxTokens, setTemperature, setProvider, reset } = useRunConfig()

  const hasModelChoice = env.availableModels.length > 1
  const hasProviderChoice = env.availableProviders.length > 1
  const modelSummary = hasModelChoice ? config.modelName : (env.availableModels[0] ?? config.modelName)

  return (
    <div className={styles.wrapper} role="group" aria-label="Configuração de execução">
      <div className={styles.header}>
        <span className={styles.title}>Configurações</span>
        <Button variant="ghost" size="sm" onClick={reset}>
          Restaurar padrões
        </Button>
      </div>

      <div className={styles.fields}>
        <Field label="Provedor">
          {hasProviderChoice ? (
            <Select value={config.provider} onChange={(event) => setProvider(event.target.value)}>
              {env.availableProviders.map((provider) => (
                <option key={provider} value={provider}>
                  {PROVIDER_LABELS[provider]}
                </option>
              ))}
            </Select>
          ) : (
            <span className={styles.staticValue}>{providerLabel(config.provider)}</span>
          )}
        </Field>

        <Field label="Modelo">
          {hasModelChoice ? (
            <Select value={config.modelName} onChange={(event) => setModelName(event.target.value)}>
              {env.availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </Select>
          ) : (
            <span className={styles.staticValue}>{modelSummary}</span>
          )}
        </Field>

        <Field label="Máximo de tokens">
          <TextInput
            type="number"
            min={MAX_TOKENS_MIN}
            step={1}
            value={config.maxTokens}
            onChange={(event) => setMaxTokens(Number(event.target.value))}
          />
        </Field>

        <Field label={`Temperatura (${formatTemperature(config.temperature)})`}>
          <RangeInput
            min={TEMPERATURE_MIN}
            max={TEMPERATURE_MAX}
            step={TEMPERATURE_STEP}
            value={config.temperature}
            onChange={(event) => setTemperature(Number(event.target.value))}
          />
        </Field>
      </div>
    </div>
  )
}
