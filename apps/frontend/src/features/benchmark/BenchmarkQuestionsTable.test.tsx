import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, it } from 'vitest'
import { benchmarkSession, questionRun } from '@/test/fixtures/benchmarkSession'
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
