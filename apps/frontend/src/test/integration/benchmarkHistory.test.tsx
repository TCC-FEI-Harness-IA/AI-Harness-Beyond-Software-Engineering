import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import direct from '@/test/fixtures/session-direct-completed.json'
import ralph from '@/test/fixtures/session-a1-completed-with-a3.json'
import type { BenchmarkDetails } from '@/domain/types/benchmarkDetails'
import { AppRouter } from '@/router/AppRouter'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { ViewModeProvider } from '@/state/ViewModeContext'

const details: BenchmarkDetails = {
  is_banchmark: true, question_name: 'ENEM_Q108', corret_answer: 'A) um', providade_answer: 'A',
  inference_mode: 'simple', run_id: 'run_1', expected_alternative: 'A', selected_alternative: 'A',
  is_correct: true, duration_seconds: 1, error: null,
}
const simple = { ...direct, id: 'sess_bench_simples', user_question: 'Questão do benchmark simples', benchmark_details: details }
const reasoning = {
  ...ralph, id: 'sess_bench_ralph',
  benchmark_details: { ...details, question_name: 'ENEM_Q112', inference_mode: 'ralph' },
}
const normal = { ...direct, id: 'sess_normal', user_question: 'Pergunta normal da API' }

function renderApp(path: string): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider><RunConfigProvider><ViewModeProvider>
        <AppRouter />
      </ViewModeProvider></RunConfigProvider></ThemeProvider>
    </MemoryRouter>,
  )
}

function mockSessions() {
  const documents = [simple, reasoning, normal]
  const fetchMock = vi.fn((url: string) => {
    expect(url).not.toContain('source=')
    const id = decodeURIComponent(url.split('/').at(-1) ?? '')
    const body = url.endsWith('/sessions')
      ? { session_ids: documents.map((document) => document.id) }
      : documents.find((document) => document.id === id)
    return Promise.resolve({ status: 200, text: () => Promise.resolve(JSON.stringify(body)) } as Response)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('Benchmark persistido no histórico normal', () => {
  it('lista somente benchmarks pelos metadados e abre o chat com sua avaliação', async () => {
    const user = userEvent.setup()
    mockSessions()
    renderApp('/')
    await user.click(screen.getByRole('link', { name: 'BenchMark' }))
    expect(await screen.findByRole('heading', { name: 'BenchMark' })).toBeInTheDocument()
    const list = await screen.findByRole('list')
    const card = await within(list).findByRole('link', { name: /Questão do benchmark simples/ })
    expect(screen.queryByText('Pergunta normal da API')).not.toBeInTheDocument()
    expect(card).toHaveAttribute('href', '/benchmark-local/sess_bench_simples')
    expect(within(card).getByText('ENEM_Q108')).toBeInTheDocument()
    await user.click(card)
    expect(await screen.findByLabelText('Histórico de mensagens')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'ENEM_Q108' })).toBeInTheDocument()
    expect(screen.getByText(/Gabarito: A\) um/)).toBeInTheDocument()
    const sidebar = screen.getByRole('navigation', { name: 'Conversas' })
    await waitFor(() => expect(within(sidebar).getAllByRole('link')).toHaveLength(2))
  })

  it('abre o Ralph persistido com os modos Chat e Gráfico existentes', async () => {
    mockSessions()
    renderApp('/benchmark-local/sess_bench_ralph')
    expect(await screen.findByRole('heading', { name: 'ENEM_Q112' })).toBeInTheDocument()
    expect(await screen.findByRole('radio', { name: /Chat/ })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Gráfico/ })).toBeInTheDocument()
  })

  it('o Histórico normal exclui os benchmarks e encerra o carregamento', async () => {
    mockSessions()
    renderApp('/historico')
    const list = await screen.findByRole('list')
    expect(await within(list).findByRole('link', { name: /Pergunta normal da API/ })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText(/carregando/)).not.toBeInTheDocument())
    expect(within(list).getAllByRole('link')).toHaveLength(1)
    expect(screen.queryByText('ENEM_Q108')).not.toBeInTheDocument()
  })

  it('recusa um chat comum aberto pela URL de benchmark', async () => {
    mockSessions()
    renderApp('/benchmark-local/sess_normal')
    expect(await screen.findByText('Esta conversa não existe mais')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Voltar ao histórico' }))
    expect(await screen.findByRole('heading', { name: 'BenchMark' })).toBeInTheDocument()
  })
})
