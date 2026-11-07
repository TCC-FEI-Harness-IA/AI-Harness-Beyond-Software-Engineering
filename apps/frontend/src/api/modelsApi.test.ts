import { afterEach, describe, expect, it, vi } from 'vitest'
import { createModel, deleteModel, getModelCatalog, updateModel } from './modelsApi'

afterEach(() => vi.unstubAllGlobals())

const MODELO = {
  model_name: 'vendor/a',
  display_name: 'Vendor: A',
  input_price_per_million_tokens: 0.05,
  output_price_per_million_tokens: 0.4,
  context_length: 8192,
  throughput_tokens_per_second: 90,
}

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    status,
    text: () => Promise.resolve(body === undefined ? '' : JSON.stringify(body)),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('modelsApi', () => {
  it('getModelCatalog busca o catálogo', async () => {
    const fetchMock = stubFetch(200, { models: [MODELO] })

    expect(await getModelCatalog()).toEqual([MODELO])
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/v1/models')
  })

  it('createModel envia o modelo inteiro por POST', async () => {
    const fetchMock = stubFetch(201, MODELO)

    expect(await createModel(MODELO)).toEqual(MODELO)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/v1/models')
    expect(init.method).toBe('POST')
    expect(JSON.parse(String(init.body))).toEqual(MODELO)
  })

  it('updateModel envia os campos por PUT no caminho do identificador, mantendo a barra', async () => {
    const fetchMock = stubFetch(200, MODELO)

    await updateModel({ ...MODELO, model_name: 'vendor/modelo:free' })

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/v1/models/vendor/modelo%3Afree')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(String(init.body))).not.toHaveProperty('model_name')
  })

  it('deleteModel usa DELETE e aceita a resposta sem corpo', async () => {
    const fetchMock = stubFetch(204, undefined)

    await expect(deleteModel('vendor/a')).resolves.toBeUndefined()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/v1/models/vendor/a')
    expect(init.method).toBe('DELETE')
  })

  it('cadastro repetido rejeita com o detail do backend', async () => {
    stubFetch(409, { detail: "Modelo 'vendor/a' já está cadastrado." })

    await expect(createModel(MODELO)).rejects.toMatchObject({ status: 409, detail: "Modelo 'vendor/a' já está cadastrado." })
  })
})
