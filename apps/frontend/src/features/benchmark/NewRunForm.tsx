import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { TextInput } from '@/components/primitives/TextInput'
import type { BenchmarkDataset } from '@/domain/types/benchmarkSession'
import { formatTokens } from '@/domain/services/formatters'
import { RunConfigBar } from '@/features/home/RunConfigBar'
import { useRunConfig } from '@/state/RunConfigContext'
import styles from './NewRunForm.module.css'

const DEFAULT_PARALLEL = 5
const MIN_VALUE = 1

export interface NewRunFormProps {
  dataset: BenchmarkDataset
  /** Uma bateria já está em execução — só uma por vez. */
  disabled: boolean
  onStart: (questionCount: number, maxParallel: number) => void
}

// Os campos guardam o texto digitado (apagar para digitar outro número não pode virar "1" no meio
// do caminho); o valor efetivo é limitado ao intervalo válido no blur e no envio.
function clamp(raw: string, max: number): number {
  const value = Number(raw)
  if (raw.trim() === '' || !Number.isFinite(value)) return MIN_VALUE
  return Math.min(max, Math.max(MIN_VALUE, Math.trunc(value)))
}

/**
 * Parâmetros de uma nova bateria: quantas questões (as primeiras do dataset, na ordem) e quantas
 * em paralelo. Modelo, provedor, limite de tokens por sessão e temperatura são os mesmos da tela inicial.
 */
export function NewRunForm({ dataset, disabled, onStart }: NewRunFormProps): JSX.Element {
  const { config } = useRunConfig()
  // O `max_tokens` é o limite de tokens de cada sessão da bateria (uma por fluxo e questão) e não
  // pode passar do limite por sessão do backend. O servidor recusa esse valor; avisar aqui evita
  // abrir a bateria só para vê-la recusada.
  const tokensTooHigh = config.maxTokens > dataset.max_tokens_limit
  const available = dataset.question_ids.length
  const [questionCount, setQuestionCount] = useState(String(available))
  const [maxParallel, setMaxParallel] = useState(
    String(Math.min(DEFAULT_PARALLEL, dataset.max_parallel_limit)),
  )

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (tokensTooHigh) return
    onStart(clamp(questionCount, available), clamp(maxParallel, dataset.max_parallel_limit))
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Nova bateria de benchmark">
      <div className={styles.fields}>
        <Field
          label="Quantidade de questões"
          hint={`As ${clamp(questionCount, available)} primeiras de ${available} disponíveis, na ordem do dataset.`}
        >
          <TextInput
            type="number"
            min={MIN_VALUE}
            max={available}
            step={1}
            value={questionCount}
            disabled={disabled}
            onChange={(event) => setQuestionCount(event.target.value)}
            onBlur={() => setQuestionCount(String(clamp(questionCount, available)))}
          />
        </Field>
        <Field
          label="Questões em paralelo"
          hint={`Até ${dataset.max_parallel_limit}. Cada questão roda a inferência simples e depois o Ralph.`}
        >
          <TextInput
            type="number"
            min={MIN_VALUE}
            max={dataset.max_parallel_limit}
            step={1}
            value={maxParallel}
            disabled={disabled}
            onChange={(event) => setMaxParallel(event.target.value)}
            onBlur={() => setMaxParallel(String(clamp(maxParallel, dataset.max_parallel_limit)))}
          />
        </Field>
      </div>

      <RunConfigBar />

      {tokensTooHigh ? (
        <p className={styles.warning} role="alert">
          O máximo de tokens ({formatTokens(config.maxTokens)}) passa do limite de{' '}
          {formatTokens(dataset.max_tokens_limit)} por sessão. Reduza o valor em “Máximo de tokens por
          sessão” para iniciar a bateria.
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button type="submit" disabled={disabled || tokensTooHigh}>
          Iniciar bateria
        </Button>
      </div>
    </form>
  )
}
