import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as benchmarkApi from '@/api/benchmarkApi'
import type * as BenchmarkApiModule from '@/api/benchmarkApi'
import { HttpError } from '@/api/errors/HttpError'
import * as saveBlobModule from '@/hooks/saveBlob'
import { benchmarkSession, questionRun } from '@/test/fixtures/benchmarkSession'
import { BenchmarkSessionExport } from './BenchmarkSessionExport'

vi.mock('@/api/benchmarkApi', async () => {
  const actual = await vi.importActual<typeof BenchmarkApiModule>('@/api/benchmarkApi')
  return { ...actual, exportBenchmarkSession: vi.fn() }
})
vi.mock('@/hooks/saveBlob', () => ({ saveBlob: vi.fn() }))

const exportMock = benchmarkApi.exportBenchmarkSession as Mock
const saveBlobMock = saveBlobModule.saveBlob as Mock
const BUTTON = { name: 'Exportar sessão completa' }

afterEach(() => {
  exportMock.mockReset()
  saveBlobMock.mockReset()
})

describe('BenchmarkSessionExport', () => {
  it('fica desabilitado enquanto a bateria executa', () => {
    render(<BenchmarkSessionExport session={benchmarkSession({ status: 'running' })} />)

    expect(screen.getByRole('button', BUTTON)).toBeDisabled()
    expect(screen.getByText('Disponível quando a bateria terminar.')).toBeInTheDocument()
  })

  it.each([
    [1, /para 1 questão, enunciado/],
    [2, /para 2 questões, enunciado/],
  ])('habilita a exportação de bateria encerrada com %i questão(ões)', (count, text) => {
    const questions = Array.from({ length: count }, (_, index) => questionRun({ question_id: `Q${index}` }))
    render(
      <BenchmarkSessionExport
        session={benchmarkSession({ status: 'interrupted', questions, question_count: count })}
      />,
    )

    expect(screen.getByRole('button', BUTTON)).toBeEnabled()
    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it('mostra o progresso, entrega o ZIP e confirma ao terminar', async () => {
    const user = userEvent.setup()
    const zip = new Blob(['PK'])
    let resolveExport: (blob: Blob) => void = () => {}
    exportMock.mockImplementation(() => new Promise<Blob>((resolve) => (resolveExport = resolve)))
    render(<BenchmarkSessionExport session={benchmarkSession({ status: 'completed' })} />)

    await user.click(screen.getByRole('button', BUTTON))
    expect(await screen.findByText('Gerando o arquivo ZIP…')).toBeInTheDocument()

    resolveExport(zip)

    expect(await screen.findByText(/o download foi iniciado/)).toBeInTheDocument()
    expect(saveBlobMock).toHaveBeenCalledWith(zip, 'benchmark-session-bench_1.zip')
  })

  it('avisa da falha', async () => {
    const user = userEvent.setup()
    exportMock.mockRejectedValueOnce(new HttpError(500, 'disco fora do ar'))
    render(<BenchmarkSessionExport session={benchmarkSession({ status: 'completed' })} />)

    await user.click(screen.getByRole('button', BUTTON))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível exportar a sessão. O servidor falhou ao processar a requisição.',
    )
  })
})
