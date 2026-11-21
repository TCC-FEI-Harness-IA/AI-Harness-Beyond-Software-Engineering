import { useEffect, useRef, useState } from 'react'
import { updateBenchmarkAlias } from '@/api/benchmarkApi'
import { AppError } from '@/api/errors/AppError'
import { Button } from '@/components/primitives/Button'
import { TextInput } from '@/components/primitives/TextInput'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import styles from './BenchmarkAliasEditor.module.css'

/** Edição explícita do título; só fecha depois que o servidor confirma a gravação. */
export function BenchmarkAliasEditor({
  session,
  onSaved,
}: {
  session: BenchmarkSessionDocument
  onSaved: () => void
}): JSX.Element {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(session.alias ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])
  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  async function save(): Promise<void> {
    if (controllerRef.current !== null) return
    const controller = new AbortController()
    controllerRef.current = controller
    setSaving(true)
    setError(null)
    try {
      await updateBenchmarkAlias(session.id, value.trim() || null, controller.signal)
      if (controller.signal.aborted) return
      setEditing(false)
      onSaved()
    } catch (failure: unknown) {
      if (!controller.signal.aborted) {
        setError(failure instanceof AppError ? failure.userMessage : 'Tente novamente.')
      }
    } finally {
      controllerRef.current = null
      if (!controller.signal.aborted) setSaving(false)
    }
  }

  if (!editing) {
    return (
      <div>
        <Button variant="secondary" size="sm" onClick={() => {
          setValue(session.alias ?? '')
          setError(null)
          setEditing(true)
        }}>
          {session.alias ? 'Editar alias' : 'Adicionar alias'}
        </Button>
      </div>
    )
  }

  return (
    <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void save() }}>
      <label htmlFor="benchmark-alias">Alias da bateria</label>
      <div className={styles.controls}>
        <TextInput
          ref={inputRef}
          id="benchmark-alias"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          maxLength={120}
          placeholder="Ex.: GPT · comparação de temperatura"
          disabled={saving}
          aria-describedby="benchmark-alias-hint"
          className={styles.input}
        />
        <Button type="submit" size="sm" loading={saving}>Salvar alias</Button>
        <Button variant="ghost" size="sm" disabled={saving} onClick={() => setEditing(false)}>
          Cancelar
        </Button>
      </div>
      <p id="benchmark-alias-hint" className={styles.hint}>
        Até 120 caracteres. Deixe vazio e salve para remover.
      </p>
      {error ? <p role="alert" className={styles.error}>Não foi possível salvar o alias. {error}</p> : null}
    </form>
  )
}
