import { type FormEvent, useState } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Badge } from '@/components/primitives/Badge'
import { Button } from '@/components/primitives/Button'
import { formatDateTime } from '@/domain/services/formatters'
import { type CredentialUiStatus, useAuth } from '@/state/AuthContext'
import { ApiKeyField } from './ApiKeyField'
import { RequireAuth } from './RequireAuth'
import styles from './Auth.module.css'

const STATUS_TEXT: Record<CredentialUiStatus, string> = {
  unknown: 'Verificando a chave…',
  checking: 'Verificando a chave…',
  missing: 'Nenhuma chave configurada nesta sessão.',
  valid: 'Chave válida nesta sessão.',
  invalid: 'A chave não é aceita. Informe uma nova chave.',
  error: 'Não foi possível verificar a chave agora.',
}

const STATUS_TONE: Record<CredentialUiStatus, 'neutral' | 'success' | 'danger' | 'warning'> = {
  unknown: 'neutral',
  checking: 'neutral',
  missing: 'warning',
  valid: 'success',
  invalid: 'danger',
  error: 'warning',
}

function CredentialManager(): JSX.Element {
  const auth = useAuth()
  const [apiKey, setApiKey] = useState('')
  const { credential } = auth

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault()
    const key = apiKey.trim()
    setApiKey('')
    if (key !== '') await auth.saveApiKey(key)
  }

  return (
    <PageContainer>
      <form className={styles.page} onSubmit={(event) => void submit(event)}>
        <h1 className={styles.title}>Chave OpenRouter</h1>
        <p className={styles.lead}>
          As chamadas ao modelo usam a sua chave. Ela fica cifrada num cookie HttpOnly deste navegador, vale até
          o fim da sessão de login e nunca é gravada no servidor nem exibida de volta.
        </p>
        <div className={styles.status}>
          <Badge tone={STATUS_TONE[credential.status]}>{STATUS_TEXT[credential.status]}</Badge>
          {credential.status === 'valid' && credential.expiresAt ? (
            <span>Válida até {formatDateTime(credential.expiresAt)}</span>
          ) : null}
        </div>
        {credential.message ? <p role="alert" className={styles.error}>{credential.message}</p> : null}
        <ApiKeyField label="Nova chave OpenRouter" value={apiKey} onChange={setApiKey} />
        <div className={styles.actions}>
          <Button type="submit" disabled={credential.status === 'checking'}>Salvar chave</Button>
          {credential.status === 'valid' ? (
            <Button type="button" variant="secondary" onClick={() => void auth.removeApiKey()}>
              Remover chave
            </Button>
          ) : null}
        </div>
      </form>
    </PageContainer>
  )
}

/** Configuração, troca e remoção da chave OpenRouter da sessão atual. */
export function CredentialPage(): JSX.Element {
  return (
    <RequireAuth>
      <CredentialManager />
    </RequireAuth>
  )
}
