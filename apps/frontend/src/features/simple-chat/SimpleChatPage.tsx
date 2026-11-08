import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useSimpleInference } from '@/hooks/useSimpleInference'
import { isInferenceNavigationState } from '@/router/navigationState'
import { useRunConfig } from '@/state/RunConfigContext'
import { SimpleChatView } from './SimpleChatView'

/**
 * Conecta o fluxo simples: lê o `state` da navegação (README, FASE 04, seção 5.3), usa
 * `useSimpleInference` e repassa para `SimpleChatView`. É o único ponto desta tela que sabe
 * que existe rede — a view em si é apresentação pura.
 */
export function SimpleChatPage(): JSX.Element {
  const location = useLocation()
  const { config } = useRunConfig()
  const { run, send, retry } = useSimpleInference(config)
  const [composerValue, setComposerValue] = useState('')
  // Ref, não state: o StrictMode do React 18 roda o efeito de montagem duas vezes em
  // desenvolvimento, de forma síncrona — um guard em `useState` (atualização em lote) não
  // impede a segunda chamada de `send` dentro do mesmo par de invocações.
  const autoStartedRef = useRef(false)

  useEffect(() => {
    if (autoStartedRef.current) return
    const state: unknown = location.state
    if (!isInferenceNavigationState(state) || !state.autoStart) return

    autoStartedRef.current = true
    send(state.question)
  }, [location.state, send])

  const handleSend = useCallback(
    (question: string) => {
      send(question)
      setComposerValue('')
    },
    [send],
  )

  return (
    <SimpleChatView
      run={run}
      isLive
      composerValue={composerValue}
      onComposerChange={setComposerValue}
      onSend={handleSend}
      onRetry={retry}
    />
  )
}
