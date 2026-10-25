import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '@/components/primitives/Button'
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
 * em paralelo. Modelo, provedor, teto de tokens e temperatura são os mesmos da tela inicial.
 */
export function NewRunForm({ dataset, disabled, onStart }: NewRunFormProps): JSX.Element {
  const { config } = useRunConfig()
  // O `max_tokens` é o teto de saída de cada chamada: o Ralph o reserva no orçamento da sessão a
  // cada chamada, então um valor perto do orçamento o bloqueia logo na primeira fase, e um valor
  // acima da janela de contexto faz o provedor recusar a inferência simples. O servidor recusa
  // esses valores; avisar aqui evita uma bateria inteira de falhas.
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
        <label className={styles.field}>
          <span>Quantidade de questões</span>
          <input
            type="number"
            min={MIN_VALUE}
            max={available}
            step={1}
            value={questionCount}
            disabled={disabled}
            onChange={(event) => setQuestionCount(event.target.value)}
            onBlur={() => setQuestionCount(String(clamp(questionCount, available)))}
          />
          <small>
            As {clamp(questionCount, available)} primeiras de {available} disponíveis, na ordem do
            dataset.
          </small>
        </label>
        <label className={styles.field}>
          <span>Questões em paralelo</span>
          <input
            type="number"
            min={MIN_VALUE}
            max={dataset.max_parallel_limit}
            step={1}
            value={maxParallel}
            disabled={disabled}
            onChange={(event) => setMaxParallel(event.target.value)}
            onBlur={() => setMaxParallel(String(clamp(maxParallel, dataset.max_parallel_limit)))}
          />
          <small>
            Até {dataset.max_parallel_limit}. Cada questão roda a inferência simples e depois o
            Ralph.
          </small>
        </label>
      </div>

      <RunConfigBar />

      {tokensTooHigh ? (
        <p className={styles.warning} role="alert">
          O máximo de tokens ({formatTokens(config.maxTokens)}) passa do limite de{' '}
          {formatTokens(dataset.max_tokens_limit)} por chamada. Reduza o valor em “Máximo de tokens”
          para iniciar a bateria.
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
