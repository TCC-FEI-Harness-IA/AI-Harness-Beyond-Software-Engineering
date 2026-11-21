import { useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'

// Distância do fim, em pixels, dentro da qual o usuário é considerado "no fim" — abaixo
// disso o scroll automático continua; acima, ele parou para ler e não deve ser puxado.
const BOTTOM_THRESHOLD_PX = 64

// `Element.scrollTo` não existe no ambiente de teste (jsdom não implementa layout) — cai
// para atribuir `scrollTop` diretamente, que também funciona em qualquer navegador real.
function scrollToEnd(container: HTMLElement): void {
  if (typeof container.scrollTo === 'function') {
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
  } else {
    container.scrollTop = container.scrollHeight
  }
}

export interface UseAutoScrollResult {
  containerRef: RefObject<HTMLDivElement>
  /** true quando há conteúdo novo e o usuário não está no fim — mostra o botão "Ir para o fim". */
  hasNewContentBelow: boolean
  scrollToBottom: () => void
}

/**
 * Lógica de "grudar no fim" de um container rolável (README, FASE 03, `ChatScroller`). Rola
 * automaticamente quando chega conteúdo novo e o usuário já estava perto do fim; caso
 * contrário, sinaliza que há conteúdo novo sem mexer no scroll.
 */
export function useAutoScroll(contentKey: string | number): UseAutoScrollResult {
  const containerRef = useRef<HTMLDivElement>(null)
  const [hasNewContentBelow, setHasNewContentBelow] = useState(false)
  const wasNearBottomRef = useRef(true)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    if (wasNearBottomRef.current) {
      scrollToEnd(container)
      setHasNewContentBelow(false)
    } else {
      setHasNewContentBelow(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentKey])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    function handleScroll(): void {
      if (!container) return
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
      wasNearBottomRef.current = distanceFromBottom <= BOTTOM_THRESHOLD_PX
      if (wasNearBottomRef.current) setHasNewContentBelow(false)
    }

    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  function scrollToBottom(): void {
    const container = containerRef.current
    if (!container) return
    scrollToEnd(container)
    wasNearBottomRef.current = true
    setHasNewContentBelow(false)
  }

  return { containerRef, hasNewContentBelow, scrollToBottom }
}
