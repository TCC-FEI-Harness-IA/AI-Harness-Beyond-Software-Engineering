import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { Field } from '@/components/primitives/Field'
import { TextInput } from '@/components/primitives/TextInput'
import { ROUTES } from '@/router/routes'
import { useAuth } from '@/state/AuthContext'
import { ApiKeyField } from './ApiKeyField'
import { authErrorMessage, safeNext } from './authMessages'
import styles from './Auth.module.css'

/** Login por e-mail e senha, com a configuração opcional da chave OpenRouter da sessão. */
export function LoginPage(): JSX.Element {
  const auth = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const next = safeNext(params.get('next'))

  if (auth.status === 'authenticated' && !submitting) {
    return (
      <PageContainer>
        <div className={styles.page}>
          <h1 className={styles.title}>Você já entrou</h1>
          <p className={styles.lead}>Conectado como {auth.user?.email}.</p>
          <div className={styles.actions}>
            <Link to={next} className={styles.link}>Continuar</Link>
            <Button variant="secondary" onClick={() => void auth.logout()}>Sair</Button>
          </div>
        </div>
      </PageContainer>
    )
  }

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault()
    const key = apiKey.trim()
    setApiKey('')
    setError(null)
    setSubmitting(true)
    try {
      await auth.login(email, password)
    } catch (failure) {
      setPassword('')
      setError(authErrorMessage(failure, 'Não foi possível entrar agora.'))
      setSubmitting(false)
      return
    }
    const keyAccepted = key === '' || (await auth.saveApiKey(key))
    setSubmitting(false)
    navigate(keyAccepted ? next : ROUTES.credential, { replace: true })
  }

  return (
    <PageContainer>
      <form className={styles.page} onSubmit={(event) => void submit(event)}>
        <h1 className={styles.title}>Entrar</h1>
        <p className={styles.lead}>
          Entre para executar a inferência simples, o Ralph Loop e os benchmarks com a sua chave OpenRouter.
          Os resultados oficiais continuam abertos sem login.
        </p>
        {error ? <p role="alert" className={styles.error}>{error}</p> : null}
        <div className={styles.form}>
          <Field label="E-mail">
            <TextInput type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Senha">
            <TextInput type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <ApiKeyField label="Chave OpenRouter (opcional agora)" value={apiKey} onChange={setApiKey} />
        </div>
        <div className={styles.actions}>
          <Button type="submit" disabled={submitting}>Entrar</Button>
          <Link to={ROUTES.register} className={styles.link}>Criar conta</Link>
        </div>
      </form>
    </PageContainer>
  )
}
