import { Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { HomePage } from '@/features/home/HomePage'
import { SimpleChatPage } from '@/features/simple-chat/SimpleChatPage'
import { RalphPage } from '@/features/ralph/RalphPage'
import { HistoryListPage } from '@/features/history/HistoryListPage'
import { HistoryDetailPage } from '@/features/history/HistoryDetailPage'
import { NotFoundPage } from '@/features/not-found/NotFoundPage'
import { ComponentsGalleryPage } from '@/features/dev/ComponentsGalleryPage'
import { SidebarSlotProvider, useSidebarSlotValue } from '@/state/SidebarSlotContext'
import { ROUTES } from './routes'
import styles from './AppRouter.module.css'

export interface AppRouterProps {
  /** Registra `/dev/componentes` — decidido em `main.tsx` a partir de `env.enableDebugPanel`,
   * para que este módulo não precise importar `src/config/env` (evita puxar aquele módulo
   * para o chunk estático do router, já que `main.tsx` o importa dinamicamente no boot). */
  enableDevRoute?: boolean
}

// `AppShell` é montado uma única vez, acima das rotas (regra de reuso 8: nenhuma tela inventa o
// próprio cabeçalho). A prop `sidebar` só é preenchida quando a tela atual a registra via
// `useRegisterSidebar` (só `HistoryDetailPage`, FASE 07) — por isso a leitura do slot precisa
// ficar dentro do `SidebarSlotProvider`, num componente separado deste.
function AppShellWithRoutes({ enableDevRoute }: Required<AppRouterProps>): JSX.Element {
  const location = useLocation()
  const sidebar = useSidebarSlotValue()

  return (
    <AppShell sidebar={sidebar ?? undefined}>
      <div key={location.pathname} className={styles.transition}>
        <Routes location={location}>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.simpleChat} element={<SimpleChatPage />} />
          <Route path={ROUTES.ralphChat} element={<RalphPage />} />
          <Route path={ROUTES.history} element={<HistoryListPage />} />
          <Route path={ROUTES.historyDetail} element={<HistoryDetailPage />} />
          {enableDevRoute ? (
            <Route path={ROUTES.devComponents} element={<ComponentsGalleryPage />} />
          ) : null}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </div>
    </AppShell>
  )
}

/** Monta a casca de layout e as rotas do app. Espera ser renderizado dentro de um Router. */
export function AppRouter({ enableDevRoute = false }: AppRouterProps): JSX.Element {
  return (
    <SidebarSlotProvider>
      <AppShellWithRoutes enableDevRoute={enableDevRoute} />
    </SidebarSlotProvider>
  )
}
