import { screen, waitFor, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getBenchmarkDataset, listBenchmarkSessions } from '@/api/benchmarkApi'
import { getOfficialPublication, getOfficialSession, listOfficialPublications } from '@/api/publicBenchmarkApi'
import { getSession } from '@/api/sessionApi'
import type { OfficialPublication } from '@/domain/types/officialPublication'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import { HistoryDetailPage } from '@/features/history/HistoryDetailPage'
import { ROUTES } from '@/router/routes'
import { BenchmarkRunProvider } from '@/state/BenchmarkRunContext'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { SidebarSlotProvider } from '@/state/SidebarSlotContext'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { completedBenchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import { authApiFor, renderWithAuth } from '@/test/renderWithAuth'
import { BenchmarkPage } from './BenchmarkPage'
import { OfficialBenchmarkPage } from './OfficialBenchmarkPage'

vi.mock('@/api/publicBenchmarkApi', () => ({
  listOfficialPublications: vi.fn(),
  getOfficialPublication: vi.fn(),
  getOfficialSession: vi.fn(),
}))
vi.mock('@/api/benchmarkApi', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  listBenchmarkSessions: vi.fn().mockResolvedValue([]),
  getBenchmarkDataset: vi.fn(() => new Promise(() => {})),
}))
vi.mock('@/api/sessionApi', () => ({ getSession: vi.fn(), listSessionIds: vi.fn() }))

const battery = {
  ...completedBenchmarkSession(),
  id: 'bench_origem',
  alias: 'Execução oficial',
  questions: [
    questionRun({
      question_id: 'Q1',
      status: 'finished',
      simple: outcome({ session_id: 'sess_q1_simple' }),
      ralph: outcome({ mode: 'ralph', session_id: 'sess_q1_ralph' }),
    }),
  ],
}
const publication: OfficialPublication = {
  id: 'pub_1',
  dataset: 'vestibular',
  status: 'active',
  publishedAt: '2026-11-15T12:00:00+00:00',
  supersedes: null,
  supersededBy: null,
  supersededAt: null,
  sourceBenchmarkSessionId: 'bench_origem',
  textRedacted: false,
  battery,
}

afterEach(() => {
  vi.clearAllMocks()
})

function app(): JSX.Element {
  return (
    <RunConfigProvider enabled={false}>
      <ViewModeProvider>
        <BenchmarkRunProvider>
          <SidebarSlotProvider>
            <Routes>
              <Route path={ROUTES.benchmark} element={<BenchmarkPage />} />
              <Route path={ROUTES.officialBenchmark} element={<OfficialBenchmarkPage />} />
              <Route path={ROUTES.officialChildSession} element={<HistoryDetailPage source="official" />} />
            </Routes>
          </SidebarSlotProvider>
        </BenchmarkRunProvider>
      </ViewModeProvider>
    </RunConfigProvider>
  )
}

describe('Resultados oficiais na página BenchMark', () => {
  it('visitante vê o resultado oficial, um convite para entrar e nenhum botão de execução', async () => {
    vi.mocked(listOfficialPublications).mockResolvedValue([publication])
    renderWithAuth(app(), { route: '/benchmark?benchmark=vestibular' })

    const oficial = await screen.findByRole('list', { name: /Resultado oficial de Vestibulares/ })
    expect(within(oficial).getByText('Execução oficial')).toBeInTheDocument()
    expect(within(oficial).getByRole('link')).toHaveAttribute('href', '/benchmark/oficial/pub_1')
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute(
      'href', '/entrar?next=%2Fbenchmark%3Fbenchmark%3Dvestibular',
    )
    expect(screen.queryByRole('button', { name: 'Iniciar bateria' })).not.toBeInTheDocument()
    expect(listBenchmarkSessions).not.toHaveBeenCalled()
    expect(getBenchmarkDataset).not.toHaveBeenCalled()
  })

  it('dataset sem publicação informa a ausência', async () => {
    vi.mocked(listOfficialPublications).mockResolvedValue([publication])
    renderWithAuth(app(), { route: '/benchmark?benchmark=gpqa' })

    expect(await screen.findByText('Ainda não há resultado oficial de GPQA')).toBeInTheDocument()
  })

  it('usuário sem chave válida vê as próprias execuções e o atalho para configurar a chave', async () => {
    vi.mocked(listOfficialPublications).mockResolvedValue([publication])
    renderWithAuth(app(), { route: '/benchmark', api: authApiFor('user') })

    expect(await screen.findByRole('link', { name: 'Configurar chave' })).toHaveAttribute('href', '/conta/chave')
    expect(await screen.findByText(/Nenhuma bateria de Vestibulares executada ainda/)).toBeInTheDocument()
    expect(listBenchmarkSessions).toHaveBeenCalled()
  })

  it('usuário com chave válida pode montar uma nova bateria', async () => {
    vi.mocked(listOfficialPublications).mockResolvedValue([])
    renderWithAuth(app(), { route: '/benchmark', api: authApiFor('user-with-key') })

    await waitFor(() => expect(getBenchmarkDataset).toHaveBeenCalled())
    expect(screen.queryByRole('link', { name: 'Configurar chave' })).not.toBeInTheDocument()
  })
})

describe('Detalhe público de um resultado oficial', () => {
  it('mostra a bateria preservada, somente leitura, com links para as sessões públicas', async () => {
    vi.mocked(getOfficialPublication).mockResolvedValue(publication)
    renderWithAuth(app(), { route: '/benchmark/oficial/pub_1' })

    expect(await screen.findByText('Resultado oficial')).toBeInTheDocument()
    expect(screen.getByText(/Bateria de origem bench_origem/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Exportar/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Executar novamente/ })).not.toBeInTheDocument()
    const links = screen.getAllByRole('link').map((link) => link.getAttribute('href'))
    expect(links).toContain('/benchmark/oficial/pub_1/sessao/sess_q1_ralph')
  })

  it('publicação inexistente', async () => {
    const { HttpError } = await import('@/api/errors/HttpError')
    vi.mocked(getOfficialPublication).mockRejectedValue(new HttpError(404, 'não encontrada'))
    renderWithAuth(app(), { route: '/benchmark/oficial/pub_x' })

    expect(await screen.findByText('Este resultado oficial não existe')).toBeInTheDocument()
  })

  it('a sessão filha é lida pela API pública, sem a API privada', async () => {
    vi.mocked(getOfficialPublication).mockResolvedValue({ ...publication, textRedacted: true })
    vi.mocked(getOfficialSession).mockResolvedValue({
      ...(completedFixture as unknown as SessionDocument),
      id: 'sess_q1_ralph',
      benchmark_details: {
        is_banchmark: true, question_name: 'Q1', corret_answer: null, providade_answer: null, inference_mode: 'ralph',
        run_id: 'bench_origem', expected_alternative: 'A', selected_alternative: 'A', is_correct: true,
        duration_seconds: 1, error: null,
      },
    })
    renderWithAuth(app(), { route: '/benchmark/oficial/pub_1/sessao/sess_q1_ralph' })

    expect(await screen.findByText(/Resultado oficial: sessão pública/)).toBeInTheDocument()
    expect(await screen.findByText(/omitidos a pedido dos autores/)).toBeInTheDocument()
    expect(vi.mocked(getOfficialSession).mock.calls[0]?.slice(0, 2)).toEqual(['pub_1', 'sess_q1_ralph'])
    expect(getSession).not.toHaveBeenCalled()
  })
})
