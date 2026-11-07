import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HttpError } from '@/api/errors/HttpError'
import { NetworkError } from '@/api/errors/NetworkError'
import type { ModelInfo } from '@/domain/types/modelInfo'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ModelsPage, type ModelsPageProps } from './ModelsPage'

function modelo(model_name: string, overrides: Partial<ModelInfo> = {}): ModelInfo {
  return {
    model_name,
    display_name: null,
    input_price_per_million_tokens: null,
    output_price_per_million_tokens: null,
    context_length: null,
    throughput_tokens_per_second: null,
    ...overrides,
  }
}

/** Catálogo em memória: as operações da página alteram a lista que o provider recarrega. */
function renderPage(initial: ModelInfo[] = [], overrides: ModelsPageProps = {}) {
  const catalogo = new Map(initial.map((model) => [model.model_name, model]))
  const loadModels = vi.fn(() => Promise.resolve([...catalogo.values()]))
  const create = vi.fn((model: ModelInfo) => {
    catalogo.set(model.model_name, model)
    return Promise.resolve(model)
  })
  const update = vi.fn((model: ModelInfo) => {
    catalogo.set(model.model_name, model)
    return Promise.resolve(model)
  })
  const remove = vi.fn((modelName: string) => {
    catalogo.delete(modelName)
    return Promise.resolve()
  })
  render(
    <MemoryRouter>
      <RunConfigProvider loadLimits={() => new Promise(() => {})} loadModels={loadModels}>
        <ModelsPage create={create} update={update} remove={remove} {...overrides} />
      </RunConfigProvider>
    </MemoryRouter>,
  )
  return { create, update, remove, loadModels, user: userEvent.setup() }
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('ModelsPage', () => {
  it('cadastra um modelo e o mostra na lista', async () => {
    const { create, user } = renderPage()
    expect(await screen.findByText('Nenhum modelo cadastrado ainda.')).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Identificador/), 'meta-llama/llama-3.1-8b-instruct')
    await user.type(screen.getByLabelText('Nome exibido'), 'Meta: Llama 3.1 8B Instruct')
    await user.type(screen.getByLabelText(/Preço de entrada/), '0,02')
    await user.type(screen.getByLabelText(/Preço de saída/), '0.04')
    await user.type(screen.getByLabelText(/Contexto máximo/), '131072')
    await user.type(screen.getByLabelText(/Vazão/), '25')
    await user.click(screen.getByRole('button', { name: 'Cadastrar' }))

    expect(create).toHaveBeenCalledWith({
      model_name: 'meta-llama/llama-3.1-8b-instruct',
      display_name: 'Meta: Llama 3.1 8B Instruct',
      input_price_per_million_tokens: 0.02,
      output_price_per_million_tokens: 0.04,
      context_length: 131072,
      throughput_tokens_per_second: 25,
    })
    expect(await screen.findByRole('status')).toHaveTextContent('Modelo meta-llama/llama-3.1-8b-instruct cadastrado.')
    const tabela = await screen.findByRole('table', { name: 'Modelos cadastrados' })
    expect(within(tabela).getByText('Meta: Llama 3.1 8B Instruct')).toBeInTheDocument()
    expect(screen.getByLabelText(/Identificador/)).toHaveValue('')
  })

  it('valida o formulário antes de enviar', async () => {
    const { create, user } = renderPage()

    await user.type(screen.getByLabelText(/Identificador/), 'vendor/x')
    await user.type(screen.getByLabelText(/Contexto máximo/), '0')
    await user.click(screen.getByRole('button', { name: 'Cadastrar' }))

    expect(screen.getByRole('alert')).toHaveTextContent('Contexto precisa ser maior que zero.')
    expect(create).not.toHaveBeenCalled()
  })

  it('mostra o motivo do backend quando o cadastro é recusado', async () => {
    const { user } = renderPage([], {
      create: () => Promise.reject(new HttpError(409, "Modelo 'vendor/x' já está cadastrado.")),
    })

    await user.type(screen.getByLabelText(/Identificador/), 'vendor/x')
    await user.click(screen.getByRole('button', { name: 'Cadastrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Modelo 'vendor/x' já está cadastrado.")
    expect(screen.getByLabelText(/Identificador/)).toHaveValue('vendor/x')
  })

  it('sem detail do backend, usa a mensagem padrão do erro', async () => {
    const { user } = renderPage([], { create: () => Promise.reject(new NetworkError(new Error('offline'))) })

    await user.type(screen.getByLabelText(/Identificador/), 'vendor/x')
    await user.click(screen.getByRole('button', { name: 'Cadastrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível falar com o servidor.')
  })

  it('edita um modelo sem permitir trocar o identificador', async () => {
    const { update, user } = renderPage([modelo('vendor/a', { display_name: 'Vendor: A', context_length: 8192 })])

    await user.click(await screen.findByRole('button', { name: 'Editar vendor/a' }))

    expect(screen.getByRole('heading', { name: 'Editar vendor/a' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Identificador/)).toBeDisabled()
    expect(screen.getByLabelText(/Contexto máximo/)).toHaveValue('8192')

    await user.clear(screen.getByLabelText(/Contexto máximo/))
    await user.type(screen.getByLabelText(/Contexto máximo/), '16384')
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    expect(update).toHaveBeenCalledWith(expect.objectContaining({ model_name: 'vendor/a', context_length: 16384 }))
    expect(await screen.findByRole('status')).toHaveTextContent('Modelo vendor/a atualizado.')
    expect(screen.getByRole('heading', { name: 'Cadastrar modelo' })).toBeInTheDocument()
  })

  it('cancelar a edição limpa o formulário', async () => {
    const { user } = renderPage([modelo('vendor/a')])

    await user.click(await screen.findByRole('button', { name: 'Editar vendor/a' }))
    await user.click(screen.getByRole('button', { name: 'Cancelar edição' }))

    expect(screen.getByLabelText(/Identificador/)).toHaveValue('')
    expect(screen.getByLabelText(/Identificador/)).toBeEnabled()
  })

  it('remove um modelo só depois da confirmação', async () => {
    const { remove, user } = renderPage([modelo('vendor/a'), modelo('vendor/b')])

    await user.click(await screen.findByRole('button', { name: 'Remover vendor/a' }))
    expect(remove).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('button', { name: 'Remover vendor/a' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Remover vendor/a' }))
    await user.click(screen.getByRole('button', { name: 'Confirmar remoção de vendor/a' }))

    expect(remove).toHaveBeenCalledWith('vendor/a')
    expect(await screen.findByRole('status')).toHaveTextContent('Modelo vendor/a removido.')
    await waitFor(() => expect(screen.queryByText('vendor/a')).not.toBeInTheDocument())
    expect(screen.getByText('vendor/b')).toBeInTheDocument()
  })

  it('remover o modelo em edição limpa o formulário', async () => {
    const { user } = renderPage([modelo('vendor/a')])

    await user.click(await screen.findByRole('button', { name: 'Editar vendor/a' }))
    await user.click(screen.getByRole('button', { name: 'Remover vendor/a' }))
    await user.click(screen.getByRole('button', { name: 'Confirmar remoção de vendor/a' }))

    await waitFor(() => expect(screen.getByLabelText(/Identificador/)).toHaveValue(''))
  })

  it('falha ao remover mostra o erro', async () => {
    const { user } = renderPage([modelo('vendor/a')], {
      remove: () => Promise.reject(new HttpError(404, "Modelo 'vendor/a' não cadastrado.")),
    })

    await user.click(await screen.findByRole('button', { name: 'Remover vendor/a' }))
    await user.click(screen.getByRole('button', { name: 'Confirmar remoção de vendor/a' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Modelo 'vendor/a' não cadastrado.")
  })

  it('avisa a falha do catálogo e permite tentar de novo', async () => {
    const loadModels = vi.fn().mockRejectedValueOnce(new Error('fora do ar')).mockResolvedValue([modelo('vendor/a')])
    render(
      <MemoryRouter>
        <RunConfigProvider loadLimits={() => new Promise(() => {})} loadModels={loadModels}>
          <ModelsPage />
        </RunConfigProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o catálogo de modelos.')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByRole('table', { name: 'Modelos cadastrados' })).toBeInTheDocument()
  })
})
