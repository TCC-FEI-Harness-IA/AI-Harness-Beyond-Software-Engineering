// Utilitários privados de leitura defensiva, reusados por todos os parsers de fronteira —
// o equivalente ao `SessionDocumentMapper` do backend (README, FASE 02, seção 5).

import { ContractError } from '../errors/ContractError'

export function requireObject(raw: unknown, path: string): Record<string, unknown> {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
    throw new ContractError(`campo "${path}" deveria ser um objeto, recebeu: ${describe(raw)}`)
  }
  return raw as Record<string, unknown>
}

export function requireString(source: Record<string, unknown>, key: string, path: string): string {
  const value = source[key]
  if (typeof value !== 'string') {
    throw new ContractError(`campo "${path}" deveria ser string, recebeu: ${describe(value)}`)
  }
  return value
}

export function requireNumber(source: Record<string, unknown>, key: string, path: string): number {
  const value = source[key]
  if (typeof value !== 'number' || Number.isNaN(value)) {
    throw new ContractError(`campo "${path}" deveria ser number, recebeu: ${describe(value)}`)
  }
  return value
}

export function requireArray(source: Record<string, unknown>, key: string, path: string): unknown[] {
  const value = source[key]
  if (!Array.isArray(value)) {
    throw new ContractError(`campo "${path}" deveria ser array, recebeu: ${describe(value)}`)
  }
  return value
}

export function optionalString(
  source: Record<string, unknown>,
  key: string,
  path: string,
): string | null {
  const value = source[key]
  if (value === null || value === undefined) return null
  if (typeof value !== 'string') {
    throw new ContractError(`campo "${path}" deveria ser string ou null, recebeu: ${describe(value)}`)
  }
  return value
}

function describe(value: unknown): string {
  if (value === undefined) return 'undefined'
  if (value === null) return 'null'
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}
