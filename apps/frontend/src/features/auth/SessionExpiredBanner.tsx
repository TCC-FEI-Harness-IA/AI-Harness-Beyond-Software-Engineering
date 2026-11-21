import { Link, useLocation } from 'react-router-dom'
import { buildLoginPath } from '@/router/routes'
import { useAuth } from '@/state/AuthContext'
import styles from './Auth.module.css'

/** Aviso de que a sessão terminou (expiração ou logout em outra aba); o conteúdo público continua. */
export function SessionExpiredBanner(): JSX.Element | null {
  const auth = useAuth()
  const location = useLocation()
  if (!auth.expired) return null
  return (
    <div role="alert" className={styles.notice}>
      <span>Sua sessão terminou. Os resultados oficiais continuam disponíveis.</span>
      <Link to={buildLoginPath(`${location.pathname}${location.search}`)} className={styles.link}>
        Entrar novamente
      </Link>
      <button type="button" onClick={auth.dismissExpired} aria-label="Fechar aviso">
        ×
      </button>
    </div>
  )
}
