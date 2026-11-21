import { useState } from 'react'
import type { FormEvent } from 'react'
import { AppError } from '@/api/errors/AppError'
import { HttpError } from '@/api/errors/HttpError'
import { createModel, deleteModel, updateModel } from '@/api/modelsApi'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { Skeleton } from '@/components/primitives/Skeleton'
import { TextInput } from '@/components/primitives/TextInput'
import type { ModelInfo } from '@/domain/types/modelInfo'
import { useRunConfig } from '@/state/RunConfigContext'
import { ModelTable } from './ModelTable'
import { EMPTY_MODEL_FORM, type ModelFormValues, modelToFormValues, parseModelForm } from './modelForm'
import styles from './ModelsPage.module.css'

type Feedback = { tone: 'success' | 'error'; text: string } | null

// O backend explica em português o motivo de um 400/404/409 (ex.: "Modelo 'x' já está cadastrado.");
// sem esse detalhe, vale a mensagem padrão do erro.
function errorText(error: unknown): string {
  if (error instanceof HttpError && error.detail) return error.detail
  if (error instanceof AppError) return error.userMessage
  return String(error)
}

export interface ModelsPageProps {
  /** Operações do catálogo; os testes as substituem. */
  create?: (model: ModelInfo) => Promise<ModelInfo>
  update?: (model: ModelInfo) => Promise<ModelInfo>
  remove?: (modelName: string) => Promise<void>
}

/**
 * Cadastro do catálogo de modelos (coleção `models` do MongoDB): os modelos daqui são os que
 * aparecem na escolha do modelo, com o preço, o contexto e a vazão informados.
 */
export function ModelsPage({
  create = createModel,
  update = updateModel,
  remove = deleteModel,
}: ModelsPageProps): JSX.Element {
  const { models, modelsStatus, reloadModels } = useRunConfig()
  const [values, setValues] = useState<ModelFormValues>(EMPTY_MODEL_FORM)
  const [editing, setEditing] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)

  function setField(field: keyof ModelFormValues, value: string): void {
    setValues((prev) => ({ ...prev, [field]: value }))
  }

  function resetForm(): void {
    setValues(EMPTY_MODEL_FORM)
    setEditing(null)
  }

  function startEdit(model: ModelInfo): void {
    setValues(modelToFormValues(model))
    setEditing(model.model_name)
    setPendingDelete(null)
    setFeedback(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const parsed = parseModelForm(values)
    if (!parsed.ok) {
      setFeedback({ tone: 'error', text: parsed.message })
      return
    }

    setSaving(true)
    setFeedback(null)
    try {
      if (editing === null) {
        await create(parsed.model)
        setFeedback({ tone: 'success', text: `Modelo ${parsed.model.model_name} cadastrado.` })
      } else {
        await update(parsed.model)
        setFeedback({ tone: 'success', text: `Modelo ${parsed.model.model_name} atualizado.` })
      }
      resetForm()
      reloadModels()
    } catch (error) {
      setFeedback({ tone: 'error', text: errorText(error) })
    } finally {
      setSaving(false)
    }
  }

  async function confirmDelete(modelName: string): Promise<void> {
    setPendingDelete(null)
    setFeedback(null)
    try {
      await remove(modelName)
      if (editing === modelName) resetForm()
      setFeedback({ tone: 'success', text: `Modelo ${modelName} removido.` })
      reloadModels()
    } catch (error) {
      setFeedback({ tone: 'error', text: errorText(error) })
    }
  }

  function renderActions(model: ModelInfo): JSX.Element {
    const label = model.model_name
    if (pendingDelete === label) {
      return (
        <div className={styles.actions}>
          <Button variant="danger" size="sm" onClick={() => void confirmDelete(label)} aria-label={`Confirmar remoção de ${label}`}>
            Confirmar remoção
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setPendingDelete(null)}>
            Cancelar
          </Button>
        </div>
      )
    }
    return (
      <div className={styles.actions}>
        <Button variant="ghost" size="sm" onClick={() => startEdit(model)} aria-label={`Editar ${label}`}>
          Editar
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setPendingDelete(label)} aria-label={`Remover ${label}`}>
          Remover
        </Button>
      </div>
    )
  }

  return (
    <PageContainer width="wide">
      <header className={styles.header}>
        <h1 className={styles.title}>Modelos</h1>
        <p className={styles.subtitle}>
          Catálogo usado na escolha do modelo. Preços em US$ por 1 milhão de tokens; deixe em branco o que não souber.
        </p>
      </header>

      <form className={styles.form} onSubmit={(event) => void handleSubmit(event)} aria-label="Cadastro de modelo">
        <h2 className={styles.formTitle}>{editing === null ? 'Cadastrar modelo' : `Editar ${editing}`}</h2>
        <div className={styles.fields}>
          <Field label="Identificador" hint="Como o provedor chama o modelo, ex.: meta-llama/llama-3.1-8b-instruct.">
            <TextInput
              value={values.model_name}
              onChange={(event) => setField('model_name', event.target.value)}
              disabled={editing !== null}
              required
              autoComplete="off"
            />
          </Field>
          <Field label="Nome exibido">
            <TextInput value={values.display_name} onChange={(event) => setField('display_name', event.target.value)} />
          </Field>
          <Field label="Preço de entrada (US$ / 1M tokens)">
            <TextInput
              inputMode="decimal"
              value={values.input_price_per_million_tokens}
              onChange={(event) => setField('input_price_per_million_tokens', event.target.value)}
            />
          </Field>
          <Field label="Preço de saída (US$ / 1M tokens)">
            <TextInput
              inputMode="decimal"
              value={values.output_price_per_million_tokens}
              onChange={(event) => setField('output_price_per_million_tokens', event.target.value)}
            />
          </Field>
          <Field label="Contexto máximo (tokens)">
            <TextInput
              inputMode="numeric"
              value={values.context_length}
              onChange={(event) => setField('context_length', event.target.value)}
            />
          </Field>
          <Field label="Vazão (tokens/s)">
            <TextInput
              inputMode="decimal"
              value={values.throughput_tokens_per_second}
              onChange={(event) => setField('throughput_tokens_per_second', event.target.value)}
            />
          </Field>
        </div>
        <div className={styles.formActions}>
          <Button type="submit" loading={saving}>
            {editing === null ? 'Cadastrar' : 'Salvar alterações'}
          </Button>
          {editing !== null ? (
            <Button variant="ghost" onClick={resetForm}>
              Cancelar edição
            </Button>
          ) : null}
        </div>
      </form>

      {feedback ? (
        <p
          className={feedback.tone === 'error' ? styles.feedbackError : styles.feedbackSuccess}
          role={feedback.tone === 'error' ? 'alert' : 'status'}
        >
          {feedback.text}
        </p>
      ) : null}

      <section className={styles.list} aria-label="Modelos cadastrados">
        <h2 className={styles.formTitle}>Cadastrados</h2>
        {modelsStatus === 'loading' ? <Skeleton height="160px" radius="var(--radius-lg)" /> : null}
        {modelsStatus === 'error' ? (
          <div className={styles.notice} role="alert">
            Não foi possível carregar o catálogo de modelos.
            <Button variant="secondary" size="sm" onClick={reloadModels}>
              Tentar de novo
            </Button>
          </div>
        ) : null}
        {modelsStatus === 'ready' && models.length === 0 ? (
          <p className={styles.notice}>Nenhum modelo cadastrado ainda.</p>
        ) : null}
        {modelsStatus === 'ready' && models.length > 0 ? (
          <ModelTable models={models} label="Modelos cadastrados" renderActions={renderActions} />
        ) : null}
      </section>
    </PageContainer>
  )
}
