// Constantes e builders de rota — nenhum path literal aparece fora deste arquivo.

export const ROUTES = {
  home: '/',
  simpleChat: '/chat/simples',
  ralphChat: '/chat/ralph',
  history: '/historico',
  historyDetail: '/historico/:sessionId',
  benchmark: '/benchmark',
  benchmarkSession: '/benchmark/:benchmarkSessionId',
  benchmarkChildSession: '/benchmark/:benchmarkSessionId/sessao/:sessionId',
  devComponents: '/dev/componentes',
} as const

export function buildHistoryDetailPath(sessionId: string): string {
  return ROUTES.historyDetail.replace(':sessionId', encodeURIComponent(sessionId))
}

export function buildBenchmarkSessionPath(benchmarkSessionId: string): string {
  return ROUTES.benchmarkSession.replace(':benchmarkSessionId', encodeURIComponent(benchmarkSessionId))
}

/** Chat de uma sessão (simples ou Ralph) gerada por uma bateria de benchmark. */
export function buildBenchmarkChildSessionPath(benchmarkSessionId: string, sessionId: string): string {
  return ROUTES.benchmarkChildSession
    .replace(':benchmarkSessionId', encodeURIComponent(benchmarkSessionId))
    .replace(':sessionId', encodeURIComponent(sessionId))
}
