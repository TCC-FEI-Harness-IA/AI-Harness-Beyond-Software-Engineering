import { Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { HomePage } from '@/features/home/HomePage'
import { SimpleChatPage } from '@/features/simple-chat/SimpleChatPage'
import { RalphPage } from '@/features/ralph/RalphPage'
import { HistoryListPage } from '@/features/history/HistoryListPage'
import { HistoryDetailPage } from '@/features/history/HistoryDetailPage'
import { BenchmarkPage } from '@/features/benchmark/BenchmarkPage'
import { BenchmarkSessionPage } from '@/features/benchmark/BenchmarkSessionPage'
import { BenchmarkAnalysisPage } from '@/features/benchmark-analysis/BenchmarkAnalysisPage'
import { ModelsPage } from '@/features/models/ModelsPage'
import { NotFoundPage } from '@/features/not-found/NotFoundPage'
import { ComponentsGalleryPage } from '@/features/dev/ComponentsGalleryPage'
import { CredentialPage } from '@/features/auth/CredentialPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { SessionExpiredBanner } from '@/features/auth/SessionExpiredBanner'
import { OfficialBenchmarkPage } from '@/features/benchmark/OfficialBenchmarkPage'
import { BenchmarkRunProvider } from '@/state/BenchmarkRunContext'
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
      <SessionExpiredBanner />
      <div key={location.pathname} className={styles.transition}>
        <Routes location={location}>
          <Route path={ROUTES.home} element={<RequireAuth requireCredential><HomePage /></RequireAuth>} />
          <Route path={ROUTES.simpleChat} element={<RequireAuth requireCredential><SimpleChatPage /></RequireAuth>} />
          <Route path={ROUTES.ralphChat} element={<RequireAuth requireCredential><RalphPage /></RequireAuth>} />
          <Route path={ROUTES.history} element={<RequireAuth><HistoryListPage /></RequireAuth>} />
          <Route path={ROUTES.historyDetail} element={<RequireAuth><HistoryDetailPage /></RequireAuth>} />
          <Route path={ROUTES.benchmark} element={<BenchmarkPage />} />
          <Route path={ROUTES.officialBenchmark} element={<OfficialBenchmarkPage />} />
          <Route path={ROUTES.officialChildSession} element={<HistoryDetailPage source="official" />} />
          <Route path={ROUTES.benchmarkSession} element={<RequireAuth><BenchmarkSessionPage /></RequireAuth>} />
          <Route
            path={ROUTES.benchmarkChildSession}
            element={<RequireAuth><HistoryDetailPage source="benchmark" /></RequireAuth>}
          />
          <Route path={ROUTES.benchmarkAnalysis} element={<BenchmarkAnalysisPage />} />
          <Route path={ROUTES.models} element={<RequireAuth><ModelsPage /></RequireAuth>} />
          <Route path={ROUTES.login} element={<LoginPage />} />
          <Route path={ROUTES.register} element={<RegisterPage />} />
          <Route path={ROUTES.credential} element={<CredentialPage />} />
          {enableDevRoute ? (
            <Route path={ROUTES.devComponents} element={<ComponentsGalleryPage />} />
          ) : null}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </div>
    </AppShell>
  )
}

/**
 * Monta a casca de layout e as rotas do app. Espera ser renderizado dentro de um Router. A bateria
 * de benchmark em execução fica acima das rotas, para sobreviver à navegação entre as telas.
 */
export function AppRouter({ enableDevRoute = false }: AppRouterProps): JSX.Element {
  return (
    <BenchmarkRunProvider>
      <SidebarSlotProvider>
        <AppShellWithRoutes enableDevRoute={enableDevRoute} />
      </SidebarSlotProvider>
    </BenchmarkRunProvider>
  )
}
