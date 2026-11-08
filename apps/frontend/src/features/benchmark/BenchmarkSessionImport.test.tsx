import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import * as benchmarkApi from '@/api/benchmarkApi'
import type * as BenchmarkApiModule from '@/api/benchmarkApi'
import { HttpError } from '@/api/errors/HttpError'
import { NetworkError } from '@/api/errors/NetworkError'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { completedBenchmarkSession } from '@/test/fixtures/benchmarkSession'
import { BenchmarkSessionImport } from './BenchmarkSessionImport'

vi.mock('@/api/benchmarkApi', async () => {
  const actual = await vi.importActual<typeof BenchmarkApiModule>('@/api/benchmarkApi')
  return { ...actual, importBenchmarkSession: vi.fn() }
})

const importMock = benchmarkApi.importBenchmarkSession as Mock
const FILE = new File(['PK'], 'bateria.zip', { type: 'application/zip' })

afterEach(() => importMock.mockReset())

function fileInput(): HTMLInputElement {
  return screen.getByLabelText('Arquivo ZIP da sessão')
}

describe('BenchmarkSessionImport', () => {
  it('o botão abre o seletor de arquivo ZIP', async () => {
    const user = userEvent.setup()
    render(<BenchmarkSessionImport />)
    const click = vi.spyOn(fileInput(), 'click')

    await user.click(screen.getByRole('button', { name: 'Importar sessão' }))

    expect(click).toHaveBeenCalled()
    expect(fileInput()).toHaveAttribute('accept', '.zip,application/zip')
  })

  it('envia o arquivo escolhido, mostra o progresso e avisa quem pediu', async () => {
    const user = userEvent.setup()
    const session = completedBenchmarkSession()
    let resolveImport: (value: BenchmarkSessionDocument) => void = () => {}
    importMock.mockImplementation(
      () => new Promise<BenchmarkSessionDocument>((resolve) => (resolveImport = resolve)),
    )
    const onImported = vi.fn()
    render(<BenchmarkSessionImport onImported={onImported} />)

    await user.upload(fileInput(), FILE)

    expect(importMock.mock.calls[0]?.[0]).toBe(FILE)
    expect(await screen.findByText('Importando a sessão…')).toBeInTheDocument()
    expect(fileInput().value).toBe('')

    resolveImport(session)

    expect(await screen.findByText('Sessão importada.')).toBeInTheDocument()
    expect(onImported).toHaveBeenCalledWith(session)
  })

  it('cancelar a escolha não envia nada', () => {
    render(<BenchmarkSessionImport />)

    fileInput().dispatchEvent(new Event('change', { bubbles: true }))

    expect(importMock).not.toHaveBeenCalled()
  })

  it('mostra o motivo da recusa dado pelo servidor', async () => {
    const user = userEvent.setup()
    importMock.mockRejectedValueOnce(new HttpError(409, "A bateria de benchmark 'bench_1' já existe."))
    render(<BenchmarkSessionImport />)

    await user.upload(fileInput(), FILE)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Não foi possível importar a sessão. A bateria de benchmark 'bench_1' já existe.",
    )
  })

  it.each([
    [new HttpError(500, null), 'O servidor falhou ao processar a requisição.'],
    [new NetworkError(new TypeError('offline')), ''],
  ])('sem detalhe do servidor, usa a mensagem padrão do erro', async (error, text) => {
    const user = userEvent.setup()
    importMock.mockRejectedValueOnce(error)
    render(<BenchmarkSessionImport />)

    await user.upload(fileInput(), FILE)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(`Não foi possível importar a sessão. ${error.userMessage}`)
    expect(alert.textContent).toContain(text)
  })
})
