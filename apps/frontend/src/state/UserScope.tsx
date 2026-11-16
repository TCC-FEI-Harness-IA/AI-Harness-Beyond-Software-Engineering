import { Fragment, type ReactNode } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Skeleton } from '@/components/primitives/Skeleton'
import { useAuth } from './AuthContext'

/**
 * Remonta toda a árvore abaixo quando a conta muda (login, logout, expiração, troca de usuário):
 * estados de tela, conexões abertas e caches de componentes da conta anterior são descartados.
 */
export function UserScope({ children }: { children: ReactNode }): JSX.Element {
  const auth = useAuth()
  if (auth.status === 'loading') {
    return (
      <PageContainer>
        <Skeleton lines={4} />
      </PageContainer>
    )
  }
  return <Fragment key={auth.user?.id ?? 'visitante'}>{children}</Fragment>
}
