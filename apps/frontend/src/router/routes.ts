// Constantes e builders de rota — nenhum path literal aparece fora deste arquivo.

export const ROUTES = {
  home: '/',
  simpleChat: '/chat/simples',
  ralphChat: '/chat/ralph',
  history: '/historico',
  historyDetail: '/historico/:sessionId',
} as const

export function buildHistoryDetailPath(sessionId: string): string {
  return ROUTES.historyDetail.replace(':sessionId', encodeURIComponent(sessionId))
}
