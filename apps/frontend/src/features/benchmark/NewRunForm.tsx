import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { TextInput } from '@/components/primitives/TextInput'
import { Select } from '@/components/primitives/Select'
import type { BenchmarkDataset, BenchmarkDatasetId } from '@/domain/types/benchmarkSession'
import type { BenchmarkRunParams } from '@/api/benchmarkApi'
import { formatTokens } from '@/domain/services/formatters'
import { RunConfigBar } from '@/features/home/RunConfigBar'
import { useRunConfig } from '@/state/RunConfigContext'
import styles from './NewRunForm.module.css'

const DEFAULT_PARALLEL = 5
const MIN_VALUE = 1

export interface NewRunFormProps {
  dataset: BenchmarkDataset
  benchmark?: BenchmarkDatasetId
  /** Uma bateria já está em execução — só uma por vez. */
  disabled: boolean
  onStart: (
    questionCount: number,
    maxParallel: number,
    options?: Pick<BenchmarkRunParams, 'benchmark' | 'fewShot' | 'subjects' | 'sampleSeed'>,
  ) => void
}

// Os campos guardam o texto digitado (apagar para digitar outro número não pode virar "1" no meio
// do caminho); o valor efetivo é limitado ao intervalo válido no blur e no envio.
function clamp(raw: string, max: number): number {
  const value = Number(raw)
  if (raw.trim() === '' || !Number.isFinite(value)) return MIN_VALUE
  return Math.min(max, Math.max(MIN_VALUE, Math.trunc(value)))
}

/**
 * Parâmetros de uma bateria: quantidade, paralelismo e, nos datasets científicos, disciplina e semente.
 * Modelo, provedor, limite de tokens por sessão e temperatura são os mesmos da tela inicial.
 */
export function NewRunForm({
  dataset,
  benchmark = 'vestibular',
  disabled,
  onStart,
}: NewRunFormProps): JSX.Element {
  const { config } = useRunConfig()
  // O `max_tokens` é o limite de tokens de cada sessão da bateria (uma por fluxo e questão) e não
  // pode passar do limite por sessão do backend. O servidor recusa esse valor; avisar aqui evita
  // abrir a bateria só para vê-la recusada.
  const tokensTooHigh = config.maxTokens > dataset.max_tokens_limit
  const isMmlu = benchmark === 'mmlu'
  const hasSubjects = benchmark !== 'vestibular'
  const [subject, setSubject] = useState('')
  const [fewShot, setFewShot] = useState<0 | 5>(5)
  const [sampleSeed, setSampleSeed] = useState('42')
  const available = subject
    ? (dataset.subjects?.find((item) => item.id === subject)?.question_count ?? 0)
    : dataset.question_ids.length
  const [questionCount, setQuestionCount] = useState(
    String(isMmlu ? Math.min(285, available) : available),
  )
  const [maxParallel, setMaxParallel] = useState(
    String(Math.min(DEFAULT_PARALLEL, dataset.max_parallel_limit)),
  )

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (tokensTooHigh) return
    const count = clamp(questionCount, available)
    const parallel = clamp(maxParallel, dataset.max_parallel_limit)
    if (hasSubjects) {
      const seed = Math.min(4294967295, Math.max(0, Math.trunc(Number(sampleSeed) || 0)))
      onStart(count, parallel, {
        benchmark,
        fewShot: isMmlu ? fewShot : 0,
        subjects: subject ? [subject] : [],
        sampleSeed: seed,
      })
    } else {
      onStart(count, parallel)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Nova bateria de benchmark">
      {hasSubjects ? (
        <>
          <p>
            {isMmlu ? '' : 'Sem exemplos (0-shot). '}A avaliação compara a resposta final dos dois
            fluxos. Resultados dependem do protocolo e da amostra escolhidos.
          </p>
          <div className={styles.fields}>
            {isMmlu ? (
              <Field label="Protocolo MMLU">
                <Select
                  value={fewShot}
                  disabled={disabled}
                  onChange={(event) => setFewShot(Number(event.target.value) as 0 | 5)}
                >
                  <option value={5}>5-shot — cinco exemplos por disciplina</option>
                  <option value={0}>0-shot — sem exemplos</option>
                </Select>
              </Field>
            ) : null}
            <Field label="Disciplina">
              <Select
                value={subject}
                disabled={disabled}
                onChange={(event) => {
                  const nextSubject = event.target.value
                  const limit =
                    dataset.subjects?.find((item) => item.id === nextSubject)?.question_count ??
                    dataset.question_ids.length
                  setSubject(nextSubject)
                  setQuestionCount(String(clamp(questionCount, limit)))
                }}
              >
                <option value="">Todas as disciplinas</option>
                {dataset.subjects?.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.id.replaceAll('_', ' ')} ({item.question_count})
                  </option>
                ))}
              </Select>
            </Field>
            <Field
              label="Semente da amostra"
              hint="Use a mesma semente e configuração para repetir a seleção de questões."
            >
              <TextInput
                type="number"
                min={0}
                max={4294967295}
                step={1}
                value={sampleSeed}
                disabled={disabled}
                onChange={(event) => setSampleSeed(event.target.value)}
              />
            </Field>
          </div>
        </>
      ) : null}
      <div className={styles.fields}>
        <Field
          label="Quantidade de questões"
          hint={
            hasSubjects
              ? `Amostra de ${clamp(questionCount, available)} de ${available} disponíveis, distribuída entre as disciplinas selecionadas.`
              : `As ${clamp(questionCount, available)} primeiras de ${available} disponíveis, na ordem do dataset.`
          }
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
          {formatTokens(dataset.max_tokens_limit)} por sessão. Reduza o valor em “Máximo de tokens
          por sessão” para iniciar a bateria.
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
