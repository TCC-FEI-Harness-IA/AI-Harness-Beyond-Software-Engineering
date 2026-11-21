import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import {
  benchmarkSession,
  completedBenchmarkSession,
  outcome,
  questionRun,
} from '@/test/fixtures/benchmarkSession'
import { BenchmarkQuestionsTable } from './BenchmarkQuestionsTable'

it('pagina baterias grandes sem renderizar todas as questões a cada atualização', async () => {
  const user = userEvent.setup()
  const session = benchmarkSession({
    questions: Array.from({ length: 101 }, (_, index) =>
      questionRun({ question_id: `MMLU_${index}` }),
    ),
  })
  render(
    <MemoryRouter>
      <BenchmarkQuestionsTable session={session} />
    </MemoryRouter>,
  )
  expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(101)
  expect(screen.queryByText('MMLU_100')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Próxima' }))
  expect(screen.getByText('MMLU_100')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Próxima' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Anterior' }))
  expect(screen.getByText('MMLU_0')).toBeInTheDocument()
})

function renderTable(
  session = completedBenchmarkSession(),
  props: {
    onRerun?: (questionId: string) => void
    onRerunMany?: (questionIds: string[]) => void
    rerunDisabled?: boolean
  } = {},
): void {
  render(
    <MemoryRouter>
      <BenchmarkQuestionsTable session={session} {...props} />
    </MemoryRouter>,
  )
}

it('sem onRerun a tabela não tem coluna nem botão de ação', () => {
  renderTable()

  expect(screen.queryByRole('button', { name: /Executar novamente/ })).not.toBeInTheDocument()
  expect(screen.queryByRole('columnheader', { name: 'Ações' })).not.toBeInTheDocument()
})

it('só a questão com fluxo errado ganha o botão e ele reexecuta aquela questão', async () => {
  const user = userEvent.setup()
  const onRerun = vi.fn()
  renderTable(completedBenchmarkSession(), { onRerun })

  expect(screen.getByRole('columnheader', { name: 'Ações' })).toBeInTheDocument()
  expect(screen.getAllByRole('button', { name: /Executar novamente/ })).toHaveLength(1)
  expect(screen.queryByRole('button', { name: 'Executar novamente Q1' })).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Executar novamente Q2' }))

  expect(onRerun).toHaveBeenCalledWith('Q2')
})

it('o botão fica desabilitado enquanto outra execução está ativa', () => {
  renderTable(completedBenchmarkSession(), { onRerun: vi.fn(), rerunDisabled: true })

  expect(screen.getByRole('button', { name: 'Executar novamente Q2' })).toBeDisabled()
})

it('não oferece reexecução enquanto a própria bateria está em execução', () => {
  renderTable({ ...completedBenchmarkSession(), status: 'running' }, { onRerun: vi.fn() })

  expect(screen.queryByRole('button', { name: /Executar novamente/ })).not.toBeInTheDocument()
})

function failedQuestionsSession(count = 3) {
  return benchmarkSession({
    status: 'completed',
    questions: Array.from({ length: count }, (_, index) => questionRun({
      question_id: `Q${index + 1}`,
      status: 'finished',
      simple: outcome(),
      ralph: outcome({ mode: 'ralph', is_correct: false, error: index === 1 ? 'Falha no provedor' : null }),
    })),
  })
}

it('permite selecionar vários erros e falhas e envia apenas a seleção no mesmo lote', async () => {
  const user = userEvent.setup()
  const onRerunMany = vi.fn()
  renderTable(failedQuestionsSession(), { onRerunMany })

  expect(screen.getByRole('button', { name: 'Executar novamente selecionadas (0)' })).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: 'Selecionar Q1 para reexecução' }))
  await user.click(screen.getByRole('checkbox', { name: 'Selecionar Q2 para reexecução' }))
  expect(screen.getByRole('checkbox', { name: 'Selecionar todas as questões com erro ou falha' })).toBePartiallyChecked()
  await user.click(screen.getByRole('button', { name: 'Executar novamente selecionadas (2)' }))

  expect(onRerunMany).toHaveBeenCalledTimes(1)
  expect(onRerunMany).toHaveBeenCalledWith(['Q1', 'Q2'])
  expect(screen.getByRole('checkbox', { name: 'Selecionar Q1 para reexecução' })).not.toBeChecked()
  expect(screen.getByRole('button', { name: 'Executar novamente selecionadas (0)' })).toBeDisabled()
})

it('selecionar todas inclui outras páginas e mantém a seleção ao navegar', async () => {
  const user = userEvent.setup()
  const onRerunMany = vi.fn()
  renderTable(failedQuestionsSession(101), { onRerunMany })

  await user.click(screen.getByRole('checkbox', { name: 'Selecionar todas as questões com erro ou falha' }))
  await user.click(screen.getByRole('button', { name: 'Próxima' }))
  expect(screen.getByRole('checkbox', { name: 'Selecionar Q101 para reexecução' })).toBeChecked()
  await user.click(screen.getByRole('checkbox', { name: 'Selecionar Q101 para reexecução' }))
  await user.click(screen.getByRole('button', { name: 'Anterior' }))
  expect(screen.getByRole('checkbox', { name: 'Selecionar Q1 para reexecução' })).toBeChecked()
  await user.click(screen.getByRole('button', { name: 'Executar novamente selecionadas (100)' }))
  expect(onRerunMany).toHaveBeenCalledWith(Array.from({ length: 100 }, (_, index) => `Q${index + 1}`))
})

it('selecionar todas alterna a seleção e ignora questões com ambos os fluxos corretos', async () => {
  const user = userEvent.setup()
  renderTable(completedBenchmarkSession(), { onRerunMany: vi.fn() })

  expect(screen.queryByRole('checkbox', { name: 'Selecionar Q1 para reexecução' })).not.toBeInTheDocument()
  const selectAll = screen.getByRole('checkbox', { name: 'Selecionar todas as questões com erro ou falha' })
  await user.click(selectAll)
  expect(screen.getByRole('checkbox', { name: 'Selecionar Q2 para reexecução' })).toBeChecked()
  await user.click(selectAll)
  expect(screen.getByRole('checkbox', { name: 'Selecionar Q2 para reexecução' })).not.toBeChecked()
})

it('bloqueia a seleção e a reexecução do lote enquanto outra execução está ativa', () => {
  renderTable(failedQuestionsSession(), { onRerunMany: vi.fn(), rerunDisabled: true })
  for (const checkbox of screen.getAllByRole('checkbox')) expect(checkbox).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Executar novamente selecionadas (0)' })).toBeDisabled()
})

it('não oferece seleção em uma bateria em execução', () => {
  renderTable({ ...failedQuestionsSession(), status: 'running' }, { onRerunMany: vi.fn() })
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Executar novamente selecionadas/ })).not.toBeInTheDocument()
})

it('não transporta a seleção para outra bateria', async () => {
  const user = userEvent.setup()
  const onRerunMany = vi.fn()
  const session = failedQuestionsSession()
  const view = render(
    <MemoryRouter><BenchmarkQuestionsTable session={session} onRerunMany={onRerunMany} /></MemoryRouter>,
  )
  await user.click(screen.getByRole('checkbox', { name: 'Selecionar todas as questões com erro ou falha' }))
  view.rerender(
    <MemoryRouter><BenchmarkQuestionsTable session={{ ...session, id: 'bench_2' }} onRerunMany={onRerunMany} /></MemoryRouter>,
  )
  expect(screen.getByRole('button', { name: 'Executar novamente selecionadas (0)' })).toBeDisabled()
})

it('remove da seleção questões que já foram corrigidas', async () => {
  const user = userEvent.setup()
  const onRerunMany = vi.fn()
  const view = render(
    <MemoryRouter><BenchmarkQuestionsTable session={failedQuestionsSession()} onRerunMany={onRerunMany} /></MemoryRouter>,
  )
  await user.click(screen.getByRole('checkbox', { name: 'Selecionar todas as questões com erro ou falha' }))
  view.rerender(
    <MemoryRouter><BenchmarkQuestionsTable session={completedBenchmarkSession()} onRerunMany={onRerunMany} /></MemoryRouter>,
  )
  await user.click(screen.getByRole('button', { name: 'Executar novamente selecionadas (1)' }))
  expect(onRerunMany).toHaveBeenCalledWith(['Q2'])
})
