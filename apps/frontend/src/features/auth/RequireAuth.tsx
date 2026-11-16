import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { Skeleton } from '@/components/primitives/Skeleton'
import { buildLoginPath, ROUTES } from '@/router/routes'
import { useAuth } from '@/state/AuthContext'
import styles from './Auth.module.css'

export interface RequireAuthProps {
  children: ReactNode
  /** A página executa chamadas ao modelo: exige também uma chave OpenRouter válida. */
  requireCredential?: boolean
}

/**
 * Guarda das páginas privadas. É só a camada de interface: quem garante o acesso é o servidor,
 * que recusa qualquer chamada sem sessão (e sem credencial, nas execuções).
 */
export function RequireAuth({ children, requireCredential = false }: RequireAuthProps): JSX.Element {
  const auth = useAuth()
  const location = useLocation()
  const here = `${location.pathname}${location.search}`

  if (auth.status === 'loading') {
    return (
      <PageContainer>
        <Skeleton lines={4} />
      </PageContainer>
    )
  }

  if (auth.status === 'anonymous') {
    return (
      <PageContainer>
        <div className={styles.prompt}>
          <h1 className={styles.title}>Entre para continuar</h1>
          <p className={styles.lead}>
            Esta página usa dados da sua conta ou executa chamadas ao modelo com a sua chave OpenRouter. Os
            resultados oficiais e a análise continuam disponíveis sem login.
          </p>
          <div className={styles.actions}>
            <Link to={buildLoginPath(here)} className={styles.link}>Entrar</Link>
            <Link to={ROUTES.register} className={styles.link}>Criar conta</Link>
            <Link to={ROUTES.benchmark} className={styles.link}>Ver resultados oficiais</Link>
          </div>
        </div>
      </PageContainer>
    )
  }

  if (requireCredential && !auth.canRunLlm && auth.credential.status !== 'checking') {
    return (
      <PageContainer>
        <div className={styles.prompt}>
          <h1 className={styles.title}>Configure a sua chave OpenRouter</h1>
          <p className={styles.lead}>
            Para executar chamadas ao modelo nesta sessão, informe uma chave OpenRouter válida.
          </p>
          {auth.credential.message ? <p role="alert" className={styles.error}>{auth.credential.message}</p> : null}
          <Link to={ROUTES.credential} className={styles.link}>Configurar chave</Link>
        </div>
      </PageContainer>
    )
  }

  return <>{children}</>
}
