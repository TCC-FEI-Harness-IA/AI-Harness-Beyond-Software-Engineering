import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { TextInput } from '@/components/primitives/TextInput'
import { Select } from '@/components/primitives/Select'
import type {
  BenchmarkDataset,
  BenchmarkDatasetId,
  GPQASubset,
} from '@/domain/types/benchmarkSession'
import { GPQA_SUBSET_LABELS } from '@/domain/services/benchmarkDefinition'
import type { BenchmarkRunParams } from '@/api/benchmarkApi'
import { formatTokens } from '@/domain/services/formatters'
import { benchmarkSubjectLabel } from '@/domain/services/benchmarkDefinition'
import { RunConfigBar } from '@/features/home/RunConfigBar'
import { useRunConfig } from '@/state/RunConfigContext'
import styles from './NewRunForm.module.css'

const DEFAULT_PARALLEL = 5
const MIN_VALUE = 1

export interface NewRunFormProps {
  dataset: BenchmarkDataset
  benchmark?: BenchmarkDatasetId
  gpqaSubset?: GPQASubset
  /** Uma bateria já está em execução — só uma por vez. */
  disabled: boolean
  onStart: (
    questionCount: number,
    maxParallel: number,
    options?: Pick<
      BenchmarkRunParams,
      'benchmark' | 'fewShot' | 'subjects' | 'sampleSeed' | 'gpqaSubset' | 'subjectCounts'
    >,
  ) => void
}

// Os campos guardam o texto digitado (apagar para digitar outro número não pode virar "1" no meio
// do caminho); o valor efetivo é limitado ao intervalo válido no blur e no envio.
function clamp(raw: string, max: number, min = MIN_VALUE): number {
  const value = Number(raw)
  if (raw.trim() === '' || !Number.isFinite(value)) return min
  return Math.min(max, Math.max(min, Math.trunc(value)))
}

/**
 * Parâmetros de uma bateria: quantidade total ou por matéria nos vestibulares, paralelismo e,
 * nos datasets científicos, disciplina e semente.
 * Modelo, provedor, limite de tokens por sessão e temperatura são os mesmos da tela inicial.
 */
export function NewRunForm({
  dataset,
  benchmark = 'vestibular',
  gpqaSubset = 'diamond',
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
  const [selectionMode, setSelectionMode] = useState('total')
  const [subjectQuantities, setSubjectQuantities] = useState<Record<string, string>>({})
  const perSubject = !hasSubjects && selectionMode === 'subject'
  const subjectCounts = Object.fromEntries(
    (dataset.subjects ?? []).map((item) => [
      item.id,
      clamp(subjectQuantities[item.id] ?? '0', item.question_count, 0),
    ]),
  )
  const subjectTotal = Object.values(subjectCounts).reduce((sum, count) => sum + count, 0)
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
    if (tokensTooHigh || (perSubject && subjectTotal === 0)) return
    const count = perSubject ? subjectTotal : clamp(questionCount, available)
    const parallel = clamp(maxParallel, dataset.max_parallel_limit)
    if (hasSubjects) {
      const seed = Math.min(4294967295, Math.max(0, Math.trunc(Number(sampleSeed) || 0)))
      onStart(count, parallel, {
        benchmark,
        ...(benchmark === 'gpqa' ? { gpqaSubset } : {}),
        fewShot: isMmlu ? fewShot : 0,
        subjects: subject ? [subject] : [],
        sampleSeed: seed,
      })
    } else if (perSubject) {
      onStart(count, parallel, { subjectCounts })
    } else {
      onStart(count, parallel)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Nova bateria de benchmark">
      {hasSubjects ? (
        <>
          <p>
            {isMmlu
              ? ''
              : `GPQA ${GPQA_SUBSET_LABELS[gpqaSubset]}: ${dataset.question_ids.length} questões, sem exemplos (0-shot). `}
            A avaliação compara a resposta final dos dois fluxos. Resultados dependem do protocolo e
            da amostra escolhidos.
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
      {!hasSubjects && (dataset.subjects?.length ?? 0) > 0 ? (
        <Field label="Seleção de questões">
          <Select
            value={selectionMode}
            disabled={disabled}
            onChange={(event) => setSelectionMode(event.target.value)}
          >
            <option value="total">Quantidade total</option>
            <option value="subject">Por matéria</option>
          </Select>
        </Field>
      ) : null}
      {perSubject ? (
        <fieldset className={styles.subjects} disabled={disabled}>
          <legend>Questões por matéria</legend>
          <p>
            Use zero para excluir uma matéria. Serão usadas as primeiras questões de cada matéria.
          </p>
          <div className={styles.fields}>
            {dataset.subjects?.map((item) => (
              <Field
                key={item.id}
                label={benchmarkSubjectLabel(item.id)}
                hint={`Até ${item.question_count} questões disponíveis.`}
              >
                <TextInput
                  type="number"
                  min={0}
                  max={item.question_count}
                  step={1}
                  value={subjectQuantities[item.id] ?? '0'}
                  onChange={(event) =>
                    setSubjectQuantities({ ...subjectQuantities, [item.id]: event.target.value })
                  }
                  onBlur={() =>
                    setSubjectQuantities({
                      ...subjectQuantities,
                      [item.id]: String(subjectCounts[item.id]),
                    })
                  }
                />
              </Field>
            ))}
          </div>
          <p role="status">
            Total da bateria: {subjectTotal} {subjectTotal === 1 ? 'questão' : 'questões'}.
          </p>
        </fieldset>
      ) : null}
      <div className={styles.fields}>
        {!perSubject ? (
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
        ) : null}
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
        <Button
          type="submit"
          disabled={disabled || tokensTooHigh || (perSubject && subjectTotal === 0)}
        >
          Iniciar bateria
        </Button>
      </div>
    </form>
  )
}
