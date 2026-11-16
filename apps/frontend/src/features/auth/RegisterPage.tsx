import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { TextInput } from '@/components/primitives/TextInput'
import { ROUTES } from '@/router/routes'
import { useAuth } from '@/state/AuthContext'
import { ApiKeyField } from './ApiKeyField'
import { authErrorMessage } from './authMessages'
import styles from './Auth.module.css'

/** Cadastro por e-mail e senha; entra em seguida e, se informada, configura a chave OpenRouter. */
export function RegisterPage(): JSX.Element {
  const auth = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault()
    if (password !== confirmation) {
      setError('As senhas não conferem.')
      return
    }
    const key = apiKey.trim()
    setApiKey('')
    setError(null)
    setSubmitting(true)
    try {
      await auth.register(email, password)
    } catch (failure) {
      setPassword('')
      setConfirmation('')
      setError(authErrorMessage(failure, 'Não foi possível criar a conta agora.'))
      setSubmitting(false)
      return
    }
    const keyAccepted = key === '' || (await auth.saveApiKey(key))
    setSubmitting(false)
    navigate(keyAccepted ? ROUTES.home : ROUTES.credential, { replace: true })
  }

  return (
    <PageContainer>
      <form className={styles.page} onSubmit={(event) => void submit(event)}>
        <h1 className={styles.title}>Criar conta</h1>
        <p className={styles.lead}>
          Seu histórico, baterias e modelos ficam na sua conta. Use uma senha com pelo menos 12 caracteres.
        </p>
        {error ? <p role="alert" className={styles.error}>{error}</p> : null}
        <div className={styles.form}>
          <Field label="E-mail">
            <TextInput type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Senha">
            <TextInput type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Field label="Confirme a senha">
            <TextInput type="password" autoComplete="new-password" required value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
          </Field>
          <ApiKeyField label="Chave OpenRouter (opcional agora)" value={apiKey} onChange={setApiKey} />
        </div>
        <div className={styles.actions}>
          <Button type="submit" disabled={submitting}>Criar conta</Button>
          <Link to={ROUTES.login} className={styles.link}>Já tenho conta</Link>
        </div>
      </form>
    </PageContainer>
  )
}
