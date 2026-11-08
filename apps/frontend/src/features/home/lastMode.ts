// Lembra o último modo de inferência escolhido na home (README, FASE 04, seção 5.2). Mesma
// tolerância a falha de `localStorage` usada em `ThemeContext` e `RunConfigContext` — nunca
// quebra a home por causa disso.

import type { InferenceMode } from './ModeCard'

const STORAGE_KEY = 'tcc.lastMode'

function isInferenceMode(value: string): value is InferenceMode {
  return value === 'simple' || value === 'ralph'
}

export function readLastMode(): InferenceMode {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored !== null && isInferenceMode(stored)) return stored
  } catch {
    // Acesso bloqueado — segue com o default.
  }
  return 'simple'
}

export function persistLastMode(mode: InferenceMode): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    // Mesma tolerância da leitura.
  }
}
