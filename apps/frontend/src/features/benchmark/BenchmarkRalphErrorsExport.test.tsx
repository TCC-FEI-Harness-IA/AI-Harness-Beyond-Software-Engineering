import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as benchmarkApi from '@/api/benchmarkApi'
import type * as BenchmarkApiModule from '@/api/benchmarkApi'
import { HttpError } from '@/api/errors/HttpError'
import * as saveBlobModule from '@/hooks/saveBlob'
import { benchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import { BenchmarkRalphErrorsExport } from './BenchmarkRalphErrorsExport'

vi.mock('@/api/benchmarkApi', async () => {
  const actual = await vi.importActual<typeof BenchmarkApiModule>('@/api/benchmarkApi')
  return { ...actual, exportBenchmarkRalphErrors: vi.fn() }
})
vi.mock('@/hooks/saveBlob', () => ({ saveBlob: vi.fn() }))

const exportMock = benchmarkApi.exportBenchmarkRalphErrors as Mock
const saveBlobMock = saveBlobModule.saveBlob as Mock

const wrongRalph = (id: string) =>
  questionRun({ question_id: id, ralph: outcome({ mode: 'ralph', is_correct: false }) })

afterEach(() => {
  exportMock.mockReset()
  saveBlobMock.mockReset()
})

const BUTTON = { name: 'Exportar erros do Ralph Loop' }

describe('BenchmarkRalphErrorsExport', () => {
  it('fica desabilitado enquanto a bateria executa', () => {
    render(
      <BenchmarkRalphErrorsExport
        session={benchmarkSession({ status: 'running', questions: [wrongRalph('Q1')] })}
      />,
    )

    expect(screen.getByRole('button', BUTTON)).toBeDisabled()
    expect(screen.getByText('Disponível quando a bateria terminar.')).toBeInTheDocument()
  })

  it('informa que não há o que exportar e impede o download quando ninguém errou no Ralph', () => {
    render(
      <BenchmarkRalphErrorsExport
        session={benchmarkSession({
          status: 'completed',
          questions: [questionRun({ ralph: outcome({ mode: 'ralph' }) })],
        })}
      />,
    )

    expect(screen.getByRole('button', BUTTON)).toBeDisabled()
    expect(screen.getByText(/Nenhuma questão errou no Ralph Loop/)).toBeInTheDocument()
  })

  it.each([
    [[wrongRalph('Q1')], '1 questão errada no Ralph Loop será exportada.'],
    [[wrongRalph('Q1'), wrongRalph('Q2')], '2 questões erradas no Ralph Loop serão exportadas.'],
  ])('habilita a exportação e diz quantas questões entram', (questions, text) => {
    render(
      <BenchmarkRalphErrorsExport session={benchmarkSession({ status: 'completed', questions })} />,
    )

    expect(screen.getByRole('button', BUTTON)).toBeEnabled()
    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it('mostra o progresso, entrega o ZIP e confirma ao terminar', async () => {
    const user = userEvent.setup()
    const zip = new Blob(['PK'])
    let resolveExport: (blob: Blob) => void = () => {}
    exportMock.mockImplementation(() => new Promise<Blob>((resolve) => (resolveExport = resolve)))
    render(
      <BenchmarkRalphErrorsExport
        session={benchmarkSession({ status: 'completed', questions: [wrongRalph('Q1')] })}
      />,
    )

    await user.click(screen.getByRole('button', BUTTON))

    expect(await screen.findByText('Gerando o arquivo ZIP…')).toBeInTheDocument()
    expect(screen.getByRole('button', BUTTON)).toBeDisabled()
    expect(exportMock.mock.calls[0]?.[0]).toBe('bench_1')

    resolveExport(zip)

    expect(await screen.findByText(/o download foi iniciado/)).toBeInTheDocument()
    expect(saveBlobMock).toHaveBeenCalledWith(
      zip,
      'benchmark-session-bench_1-ralph-loop-errors.zip',
    )
    expect(screen.queryByText('Gerando o arquivo ZIP…')).not.toBeInTheDocument()
    expect(screen.getByRole('button', BUTTON)).toBeEnabled()
  })

  it('avisa da falha e deixa tentar de novo', async () => {
    const user = userEvent.setup()
    exportMock.mockRejectedValueOnce(new HttpError(500, 'disco fora do ar'))
    render(
      <BenchmarkRalphErrorsExport
        session={benchmarkSession({ status: 'completed', questions: [wrongRalph('Q1')] })}
      />,
    )

    await user.click(screen.getByRole('button', BUTTON))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível exportar os erros. O servidor falhou ao processar a requisição.',
    )
    expect(saveBlobMock).not.toHaveBeenCalled()

    exportMock.mockResolvedValueOnce(new Blob(['PK']))
    await user.click(screen.getByRole('button', BUTTON))

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
    expect(saveBlobMock).toHaveBeenCalledTimes(1)
  })
})
