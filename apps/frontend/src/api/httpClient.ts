// Único cliente HTTP do app (README, seção 9, regra de reuso 6). Toda resposta entra como
// `unknown` e só sai tipada depois de passar por um parser de fronteira.

import { env } from '../config/env'
import { ContractError } from './errors/ContractError'
import { HttpError } from './errors/HttpError'
import { NetworkError } from './errors/NetworkError'
import { TimeoutError } from './errors/TimeoutError'

function buildUrl(path: string): string {
  return `${env.apiBaseUrl}${path}`
}

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
  method: 'GET' | 'POST',
  path: string,
  body: unknown,
  parse: (raw: unknown) => T,
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
    const init: RequestInit = {
      method,
      body: body === undefined ? null : JSON.stringify(body),
      signal: controller.signal,
    }
    if (body !== undefined) {
      init.headers = { 'Content-Type': 'application/json' }
    }

    const response = await fetch(buildUrl(path), init)

    if (response.status >= 400) {
      const detail = await readDetail(response)
      throw new HttpError(response.status, detail)
    }

    return await parseBody(response, parse)
  } catch (error) {
    if (error instanceof HttpError || error instanceof ContractError) throw error

    if (controller.signal.aborted) {
      if (timedOut) throw new TimeoutError(env.requestTimeoutMs)
      throw error
    }

    throw new NetworkError(error)
  } finally {
    clearTimeout(timer)
    callerSignal?.removeEventListener('abort', forwardAbort)
  }
}

export const httpClient = {
  get: <T>(path: string, parse: (raw: unknown) => T, signal?: AbortSignal): Promise<T> =>
    request('GET', path, undefined, parse, signal),
  post: <T>(
    path: string,
    body: unknown,
    parse: (raw: unknown) => T,
    signal?: AbortSignal,
  ): Promise<T> => request('POST', path, body, parse, signal),
}
