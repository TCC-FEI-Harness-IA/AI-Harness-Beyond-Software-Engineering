// Limpeza de desmontagem que sobrevive ao StrictMode (README, FASE 04, seção 7).
//
// Em desenvolvimento o StrictMode do React 18 roda montagem → limpeza → montagem de novo, de
// forma síncrona, para provar que o efeito é reexecutável. Uma limpeza que cancela trabalho
// de verdade — abortar um `fetch`, fechar um WebSocket — mata, nessa passagem simulada, o
// trabalho que a primeira montagem iniciou; e como a remontagem devolve o componente ao ar,
// o cancelamento aparece na tela como se o servidor tivesse falhado.
//
// A saída é adiar o cancelamento por um macrotask: se o componente voltar a montar (sempre
// volta, no ciclo simulado, e sempre no mesmo tick), a remontagem desmarca o cancelamento
// antes que ele aconteça. Numa desmontagem real, nada remonta e o cancelamento acontece —
// o WebSocket não fica aberto consumindo tokens de uma tela que ninguém está mais vendo.

import { useEffect, useRef } from 'react'

export function useDeferredTeardown(teardown: () => void): void {
  // Ref, não dependência do efeito: o efeito roda uma vez só, mas precisa enxergar sempre a
  // última versão do callback (que fecha sobre refs vivas do hook chamador).
  const teardownRef = useRef(teardown)
  teardownRef.current = teardown

  const pendingRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (pendingRef.current !== null) {
      clearTimeout(pendingRef.current)
      pendingRef.current = null
    }

    return () => {
      pendingRef.current = setTimeout(() => {
        pendingRef.current = null
        teardownRef.current()
      }, 0)
    }
  }, [])
}
