import { Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { HomePage } from '@/features/home/HomePage'
import { SimpleChatPage } from '@/features/simple-chat/SimpleChatPage'
import { RalphPage } from '@/features/ralph/RalphPage'
import { HistoryListPage } from '@/features/history/HistoryListPage'
import { HistoryDetailPage } from '@/features/history/HistoryDetailPage'
import { NotFoundPage } from '@/features/not-found/NotFoundPage'
import { ROUTES } from './routes'
import styles from './AppRouter.module.css'

/** Monta a casca de layout e as rotas do app. Espera ser renderizado dentro de um Router. */
export function AppRouter(): JSX.Element {
  // Chaveado pelo pathname para reiniciar a animação de entrada a cada troca de rota.
  const location = useLocation()

  return (
    <AppShell>
      <div key={location.pathname} className={styles.transition}>
        <Routes location={location}>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.simpleChat} element={<SimpleChatPage />} />
          <Route path={ROUTES.ralphChat} element={<RalphPage />} />
          <Route path={ROUTES.history} element={<HistoryListPage />} />
          <Route path={ROUTES.historyDetail} element={<HistoryDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </div>
    </AppShell>
  )
}
