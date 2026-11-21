// `/v1/credentials/openrouter` — a chave vai uma única vez ao backend, que a valida com a OpenRouter
// e a devolve cifrada num cookie HttpOnly. O front nunca lê o cookie nem recebe a chave de volta.

import type { CredentialStatus } from '../domain/types/auth'
import { httpClient } from './httpClient'
import { parseCredentialStatus } from './parsers/auth'

const CREDENTIAL_PATH = '/credentials/openrouter'

export function getCredentialStatus(signal?: AbortSignal): Promise<CredentialStatus> {
  return httpClient.get(CREDENTIAL_PATH, parseCredentialStatus, signal)
}

export function saveCredential(apiKey: string, signal?: AbortSignal): Promise<CredentialStatus> {
  return httpClient.put(CREDENTIAL_PATH, { api_key: apiKey }, parseCredentialStatus, signal)
}

export function deleteCredential(signal?: AbortSignal): Promise<void> {
  return httpClient.delete(CREDENTIAL_PATH, signal)
}
