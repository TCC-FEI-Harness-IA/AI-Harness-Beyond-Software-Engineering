import type { SessionSource } from '@/domain/types/sessionSource'

// Constantes e builders de rota — nenhum path literal aparece fora deste arquivo.

export const ROUTES = {
  home: '/',
  simpleChat: '/chat/simples',
  ralphChat: '/chat/ralph',
  history: '/historico',
  benchmark: '/benchmark-local',
  benchmarkDetail: '/benchmark-local/:sessionId',
  historyDetail: '/historico/:sessionId',
  devComponents: '/dev/componentes',
} as const

export function buildHistoryDetailPath(sessionId: string, source: SessionSource = 'history'): string {
  const path = source === 'benchmark' ? ROUTES.benchmarkDetail : ROUTES.historyDetail
  return path.replace(':sessionId', encodeURIComponent(sessionId))
}
