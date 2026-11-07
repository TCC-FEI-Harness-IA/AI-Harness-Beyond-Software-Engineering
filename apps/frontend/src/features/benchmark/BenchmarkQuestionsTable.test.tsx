import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import {
  benchmarkSession,
  completedBenchmarkSession,
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
  props: { onRerun?: (questionId: string) => void; rerunDisabled?: boolean } = {},
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
