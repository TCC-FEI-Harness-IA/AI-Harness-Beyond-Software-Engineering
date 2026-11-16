// Único cliente HTTP do app (README, seção 9, regra de reuso 6). Toda resposta entra como
// `unknown` e só sai tipada depois de passar por um parser de fronteira.

import { env } from '../config/env'
import { emitUnauthorized } from './authEvents'
import { getCsrfToken } from './csrfToken'
import { CanceledError } from './errors/CanceledError'
import { ContractError } from './errors/ContractError'
import { HttpError } from './errors/HttpError'
import { NetworkError } from './errors/NetworkError'
import { TimeoutError } from './errors/TimeoutError'

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE'

interface ClientOptions {
  baseUrl: () => string
  /** `true` na API: um 401 significa que a sessão deixou de valer. */
  notifyUnauthorized: boolean
}

const UNAUTHORIZED = 401

async function readDetail(response: Response): Promise<string | null> {
  try {
    const text = await response.text()
    if (text === '') return null
    const parsed: unknown = JSON.parse(text)
    if (typeof parsed === 'object' && parsed !== null && 'detail' in parsed) {
      const detail = (parsed as { detail: unknown }).detail
      return typeof detail === 'string' ? detail : null
    }
    return null
  } catch {
    return null
  }
}

async function parseBody<T>(response: Response, parse: (raw: unknown) => T): Promise<T> {
  const text = await response.text()
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    throw new ContractError(`corpo da resposta não é JSON válido: ${text.slice(0, 200)}`)
  }
  return parse(raw)
}

async function request<T>(
  options: ClientOptions,
  method: Method,
  path: string,
  body: unknown,
  readBody: (response: Response) => Promise<T>,
  callerSignal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, env.requestTimeoutMs)

  const forwardAbort = () => controller.abort()
  callerSignal?.addEventListener('abort', forwardAbort)

  try {
    // `Blob` (arquivo) segue bruto, com o próprio tipo; o resto vira JSON.
    const isRaw = body instanceof Blob
    const headers: Record<string, string> = {}
    if (body !== undefined) {
      headers['Content-Type'] = isRaw ? body.type || 'application/octet-stream' : 'application/json'
    }
    const csrf = getCsrfToken()
    if (method !== 'GET' && csrf !== null) headers['X-CSRF-Token'] = csrf
    const init: RequestInit = {
      method,
      body: body === undefined ? null : isRaw ? body : JSON.stringify(body),
      signal: controller.signal,
      // Cookies de sessão e da credencial (HttpOnly) seguem sozinhos; o JavaScript nunca os lê.
      credentials: 'same-origin',
      headers,
    }

    const response = await fetch(`${options.baseUrl()}${path}`, init)

    if (response.status === UNAUTHORIZED && options.notifyUnauthorized) emitUnauthorized()
    if (response.status >= 400) {
      const detail = await readDetail(response)
      throw new HttpError(response.status, detail)
    }

    return await readBody(response)
  } catch (error) {
    if (error instanceof HttpError || error instanceof ContractError) throw error

    if (controller.signal.aborted) {
      if (timedOut) throw new TimeoutError(env.requestTimeoutMs)
      // Cancelamento vindo do `signal` do chamador. Repassar o `AbortError` cru violaria o
      // contrato da camada `api/` (só rejeita com `AppError`) e a tela o exibiria como
      // "Violação de contrato" — que é exatamente o que ele não é.
      throw new CanceledError()
    }

    throw new NetworkError(error)
  } finally {
    clearTimeout(timer)
    callerSignal?.removeEventListener('abort', forwardAbort)
  }
}

function createHttpClient(options: ClientOptions) {
  return {
    get: <T>(path: string, parse: (raw: unknown) => T, signal?: AbortSignal): Promise<T> =>
      request(options, 'GET', path, undefined, (response) => parseBody(response, parse), signal),
    /** Baixa um arquivo: devolve o corpo como `Blob`, sem interpretá-lo como JSON. */
    getBlob: (path: string, signal?: AbortSignal): Promise<Blob> =>
      request(options, 'GET', path, undefined, (response) => response.blob(), signal),
    post: <T>(path: string, body: unknown, parse: (raw: unknown) => T, signal?: AbortSignal): Promise<T> =>
      request(options, 'POST', path, body, (response) => parseBody(response, parse), signal),
    put: <T>(path: string, body: unknown, parse: (raw: unknown) => T, signal?: AbortSignal): Promise<T> =>
      request(options, 'PUT', path, body, (response) => parseBody(response, parse), signal),
    /** Envia um arquivo como corpo bruto (`Content-Type` do próprio `Blob`) e interpreta a resposta JSON. */
    upload: <T>(path: string, file: Blob, parse: (raw: unknown) => T, signal?: AbortSignal): Promise<T> =>
      request(options, 'POST', path, file, (response) => parseBody(response, parse), signal),
    /** Remove um recurso; a resposta (204) não tem corpo. */
    delete: (path: string, signal?: AbortSignal): Promise<void> =>
      request(options, 'DELETE', path, undefined, () => Promise.resolve(), signal),
    /** Escrita sem corpo de resposta (204). */
    postEmpty: (path: string, body?: unknown, signal?: AbortSignal): Promise<void> =>
      request(options, 'POST', path, body, () => Promise.resolve(), signal),
  }
}

/** API do backend (`/v1`). */
export const httpClient = createHttpClient({ baseUrl: () => env.apiBaseUrl, notifyUnauthorized: true })

/** Serviço de autenticação (`/auth`): ali, 401 é resposta esperada (sem sessão, login inválido). */
export const authHttpClient = createHttpClient({ baseUrl: () => env.authBaseUrl, notifyUnauthorized: false })
