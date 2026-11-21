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
  benchmarkAnalysis: '/analise',
  officialBenchmark: '/benchmark/oficial/:publicationId',
  officialChildSession: '/benchmark/oficial/:publicationId/sessao/:sessionId',
  models: '/modelos',
  login: '/entrar',
  register: '/cadastro',
  credential: '/conta/chave',
  devComponents: '/dev/componentes',
} as const

/** Publicações oficiais têm identificadores `pub_...`; baterias pessoais, `bench_...`. */
export function isOfficialId(id: string): boolean {
  return id.startsWith('pub_')
}

/** Tela de login que, depois de entrar, volta para `next`. */
export function buildLoginPath(next: string): string {
  return `${ROUTES.login}?next=${encodeURIComponent(next)}`
}

export function buildHistoryDetailPath(sessionId: string): string {
  return ROUTES.historyDetail.replace(':sessionId', encodeURIComponent(sessionId))
}

/** Página do BenchMark já na aba do benchmark informado. */
export function buildBenchmarkPath(benchmark: string): string {
  return `${ROUTES.benchmark}?benchmark=${encodeURIComponent(benchmark)}`
}

/** Detalhe de uma bateria pessoal ou, para `pub_...`, de uma publicação oficial. */
export function buildBenchmarkSessionPath(benchmarkSessionId: string): string {
  if (isOfficialId(benchmarkSessionId)) {
    return ROUTES.officialBenchmark.replace(':publicationId', encodeURIComponent(benchmarkSessionId))
  }
  return ROUTES.benchmarkSession.replace(':benchmarkSessionId', encodeURIComponent(benchmarkSessionId))
}

/** Chat de uma sessão (simples ou Ralph) de uma bateria pessoal ou de uma publicação oficial. */
export function buildBenchmarkChildSessionPath(benchmarkSessionId: string, sessionId: string): string {
  if (isOfficialId(benchmarkSessionId)) {
    return ROUTES.officialChildSession
      .replace(':publicationId', encodeURIComponent(benchmarkSessionId))
      .replace(':sessionId', encodeURIComponent(sessionId))
  }
  return ROUTES.benchmarkChildSession
    .replace(':benchmarkSessionId', encodeURIComponent(benchmarkSessionId))
    .replace(':sessionId', encodeURIComponent(sessionId))
}
