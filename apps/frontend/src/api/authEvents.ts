// Canal único para "o servidor não reconhece mais a sessão" (HTTP 401 ou WebSocket 4401). O
// `AuthContext` escuta e decide: se havia sessão, ela expirou ou foi revogada; se não havia, ignora.

type Listener = () => void

const listeners = new Set<Listener>()

export function onUnauthorized(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function emitUnauthorized(): void {
  for (const listener of [...listeners]) listener()
}
