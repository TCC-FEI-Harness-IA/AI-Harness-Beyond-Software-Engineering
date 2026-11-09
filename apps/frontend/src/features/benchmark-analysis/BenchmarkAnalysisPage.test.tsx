import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { listBenchmarkSessions } from '@/api/benchmarkApi'
import { NetworkError } from '@/api/errors/NetworkError'
import { getSession } from '@/api/sessionApi'
import type { BenchmarkQuestionRun, BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { saveBlob } from '@/hooks/saveBlob'
import { clearRalphProcessMetricsCache } from '@/hooks/useRalphProcessMetrics'
import { ROUTES } from '@/router/routes'
import { benchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import { BenchmarkAnalysisPage } from './BenchmarkAnalysisPage'

vi.mock('@/api/benchmarkApi', () => ({ listBenchmarkSessions: vi.fn() }))
vi.mock('@/api/sessionApi', () => ({ getSession: vi.fn() }))
vi.mock('@/hooks/saveBlob', () => ({ saveBlob: vi.fn() }))

const listMock = listBenchmarkSessions as unknown as Mock
const getSessionMock = getSession as unknown as Mock
const saveBlobMock = saveBlob as unknown as Mock

function pair(id: string, subject: string, simpleCorrect: boolean, ralphCorrect: boolean): BenchmarkQuestionRun {
  return questionRun({
    question_id: id,
    subject,
    status: 'finished',
    simple: outcome({ session_id: `${id}_s`, is_correct: simpleCorrect, selected_alternative: simpleCorrect ? 'A' : 'B' }),
    ralph: outcome({
      mode: 'ralph',
      session_id: `${id}_r`,
      is_correct: ralphCorrect,
      selected_alternative: ralphCorrect ? 'A' : 'C',
      total_tokens: 200,
      error: ralphCorrect ? null : 'resposta inválida',
    }),
  })
}

function withResults(overrides: Partial<BenchmarkSessionDocument>): BenchmarkSessionDocument {
  const base = benchmarkSession({ status: 'completed', ...overrides })
  const executed = { ...base.summary.simple, executed: base.questions.length, accuracy: 0.5 }
  return { ...base, summary: { simple: executed, ralph: executed } }
}

const vestibular = withResults({
  id: 'bench_v',
  alias: 'Vestibular A',
  questions: [
    pair('MATEMATICA_ENEM_2022_AZUL_Q140', 'MATEMATICA', false, true),
    pair('MATEMATICA_ENEM_2022_AZUL_Q141', 'MATEMATICA', false, true),
    pair('FISICA_ITA_2024_F1_UNICA_Q01', 'FISICA', true, false),
    pair('HISTORIA_ENEM_2022_AZUL_Q10', 'HISTORIA', true, true),
    pair('QUIMICA_ENEM_2022_AZUL_Q120', 'QUIMICA', true, false),
    pair('QUIMICA_ENEM_2022_AZUL_Q121', 'QUIMICA', true, false),
    questionRun({ question_id: 'PENDENTE' }),
  ],
})
const mmlu = withResults({
  id: 'bench_m',
  alias: 'MMLU B',
  benchmark: { ...vestibular.benchmark, dataset: 'mmlu', split: 'test', few_shot: 0 },
  questions: [pair('MMLU_college_physics_test_1', 'college_physics', false, false)],
})
const empty = benchmarkSession({ id: 'bench_e', alias: 'Vazia', status: 'running' })

function LocationProbe(): JSX.Element {
  const location = useLocation()
  return <output data-testid="location">{location.search}</output>
}

function renderPage(search = ''): void {
  render(
    <MemoryRouter initialEntries={[`${ROUTES.benchmarkAnalysis}${search}`]}>
      <Routes>
        <Route
          path={ROUTES.benchmarkAnalysis}
          element={
            <>
              <BenchmarkAnalysisPage />
              <LocationProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => {
  clearRalphProcessMetricsCache()
  vi.clearAllMocks()
})

describe('BenchmarkAnalysisPage', () => {
  it('pede uma seleção e guarda as baterias escolhidas na URL', async () => {
    listMock.mockResolvedValue([vestibular, mmlu, empty])
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByText('Selecione ao menos uma execução')).toBeInTheDocument()
    // "Só com resultados" esconde a bateria sem questões executadas.
    expect(screen.queryByLabelText('Vazia')).not.toBeInTheDocument()
    await user.click(screen.getByRole('switch', { name: 'Só com resultados' }))
    expect(screen.getByLabelText('Vazia')).toBeInTheDocument()

    await user.click(screen.getByLabelText('Vestibular A'))
    expect(screen.getByTestId('location').textContent).toBe('?execucoes=bench_v')
    expect(screen.getByRole('heading', { name: 'Resumo executivo' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Marcar visíveis' }))
    expect(screen.getByTestId('location').textContent).toContain('bench_m')
    await user.click(screen.getByRole('button', { name: 'Desmarcar visíveis' }))
    expect(screen.getByText('Selecione ao menos uma execução')).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: 'MMLU' }))
    expect(screen.queryByLabelText('Vestibular A')).not.toBeInTheDocument()
    await user.click(screen.getByLabelText('MMLU B'))
    await user.click(screen.getByRole('button', { name: 'Limpar seleção' }))
    expect(screen.getByTestId('location').textContent).toBe('')
  })

  it('monta o dashboard consolidado com as quebras, a lista qualitativa e as exportações', async () => {
    listMock.mockResolvedValue([vestibular, mmlu])
    const user = userEvent.setup()
    renderPage('?execucoes=bench_v,bench_m')

    const summary = await screen.findByRole('list', { name: 'Resumo executivo' })
    expect(summary.textContent).toContain('Em 7 questões pareadas')
    // Nenhuma matéria tem 5 pares (destaque seria ruído); a área STEM tem, e o Ralph perde nela.
    expect(summary.textContent).not.toContain('por matéria')
    expect(summary.textContent).toContain('Maior perda do Ralph por área: Exatas e biológicas (STEM)')
    expect(summary.textContent).toContain('1 questões sem os dois fluxos concluídos')

    const matrix = screen.getByRole('table', { name: 'Tabela de contingência Simples × Ralph' })
    expect(within(matrix).getByText('Ralph corrige · 28,6%')).toBeInTheDocument()

    expect(screen.getByRole('table', { name: 'Por benchmark' })).toBeInTheDocument()
    const subjects = screen.getByRole('table', { name: 'Por matéria' })
    expect(within(subjects).getByText('Matemática')).toBeInTheDocument()
    expect(within(subjects).getAllByText('Vestibulares').length).toBeGreaterThan(0)
    const levels = screen.getByRole('table', { name: 'Por nível / origem da questão' })
    expect(within(levels).getByText('Vestibular · ITA')).toBeInTheDocument()
    expect(within(levels).getByText('MMLU · Graduação')).toBeInTheDocument()

    const subjectSort = screen.getByRole('radiogroup', { name: 'Ordenar Por matéria' })
    await user.click(within(subjectSort).getByRole('radio', { name: 'Maior Δ' }))
    expect(within(subjects).getAllByRole('row')[1]?.textContent).toContain('Matemática')
    await user.click(within(subjectSort).getByRole('radio', { name: 'Maior n' }))
    expect(within(subjects).getAllByRole('row')[1]?.textContent).toContain('Matemática')

    const divergent = screen.getByRole('table', { name: 'Questões divergentes' })
    expect(within(divergent).getByText('MATEMATICA_ENEM_2022_AZUL_Q140')).toBeInTheDocument()
    await user.click(screen.getByRole('radio', { name: 'Ralph piora (3)' }))
    expect(within(divergent).getAllByText('C · falha')).toHaveLength(3)

    await user.click(screen.getByRole('switch', { name: 'Desconsiderar questões com falha técnica' }))
    expect(screen.getByRole('list', { name: 'Resumo executivo' }).textContent).toContain('Em 3 questões pareadas')

    await user.click(screen.getByRole('button', { name: 'Exportar CSV (por questão)' }))
    await user.click(screen.getByRole('button', { name: 'Exportar relatório (Markdown)' }))
    expect(saveBlobMock.mock.calls.map((call) => call[1])).toEqual([
      'analise-benchmark-questoes.csv',
      'analise-benchmark.md',
    ])
  })

  it('carrega as métricas do processo Ralph sob demanda', async () => {
    listMock.mockResolvedValue([vestibular])
    getSessionMock.mockImplementation((id: string) =>
      Promise.resolve({
        id,
        user_question: 'Q',
        flow: 'A1',
        flow_version: 2,
        model_name: 'm',
        max_tokens: 1,
        temperature: 0,
        status: 'completed',
        created_at: '',
        updated_at: '',
        final_answer: null,
        totals: { total_messages: 0, total_llm_calls: 1, tokens_input: 0, tokens_output: 0, total_tokens: 0, inference_time_ms: 0, wall_time_ms: 0 },
        messages: [],
        degradations: [],
      }),
    )
    const user = userEvent.setup()
    renderPage('?execucoes=bench_v')

    await user.click(await screen.findByRole('button', { name: 'Carregar métricas do processo (6 sessões)' }))
    expect(await screen.findByText('6/6 sessões')).toBeInTheDocument()
    const tasks = screen.getByRole('table', { name: 'Tarefas no plano do Ralph' })
    expect(within(tasks).getByText('0 tarefas')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Exportar relatório (Markdown)' }))
    expect(saveBlobMock).toHaveBeenCalledTimes(1)
  })

  it('mostra o estado vazio sem pares e o erro da listagem', async () => {
    listMock.mockResolvedValueOnce([empty])
    renderPage('?execucoes=bench_e')
    expect(await screen.findByText('Nenhuma questão pareada')).toBeInTheDocument()
  })

  it('mostra o erro da listagem com opção de tentar de novo', async () => {
    listMock.mockRejectedValueOnce(new NetworkError('offline')).mockResolvedValueOnce([vestibular])
    const user = userEvent.setup()
    renderPage()
    await user.click(await screen.findByRole('button', { name: /tentar/i }))
    expect(await screen.findByLabelText('Vestibular A')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Atualizar baterias' }))
    await waitFor(() => expect(listMock).toHaveBeenCalledTimes(3))
  })
})
