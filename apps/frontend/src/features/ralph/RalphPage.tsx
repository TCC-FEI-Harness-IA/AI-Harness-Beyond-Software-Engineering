import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useReasoningStream } from '@/hooks/useReasoningStream'
import { isInferenceNavigationState } from '@/router/navigationState'
import { useRunConfig } from '@/state/RunConfigContext'
import { RalphView } from './RalphView'

/**
 * Conecta o Ralph Loop Adaptado: lê o `state` da navegação (mesmo mecanismo da FASE 04),
 * usa `useReasoningStream` e repassa para `RalphView`. É o único ponto desta tela que sabe
 * que existe rede — a view em si é apresentação pura.
 */
export function RalphPage(): JSX.Element {
  const location = useLocation()
  const { config } = useRunConfig()
  const { run, isStreaming, start, cancel } = useReasoningStream(config)
  const [composerValue, setComposerValue] = useState('')
  const [wasCancelled, setWasCancelled] = useState(false)
  const lastQuestionRef = useRef<string | null>(null)
  // Ref, não state: o StrictMode roda o efeito de montagem duas vezes em desenvolvimento —
  // um guard em state não impede a segunda chamada de `start` dentro do mesmo par (mesma
  // razão documentada em `SimpleChatPage`, FASE 04).
  const autoStartedRef = useRef(false)

  useEffect(() => {
    if (autoStartedRef.current) return
    const state: unknown = location.state
    if (!isInferenceNavigationState(state) || !state.autoStart) return

    autoStartedRef.current = true
    lastQuestionRef.current = state.question
    start(state.question)
  }, [location.state, start])

  const handleStart = useCallback(
    (question: string) => {
      const trimmed = question.trim()
      if (trimmed === '') return
      lastQuestionRef.current = trimmed
      setWasCancelled(false)
      setComposerValue('')
      start(trimmed)
    },
    [start],
  )

  const handleCancel = useCallback(() => {
    cancel()
    setWasCancelled(true)
  }, [cancel])

  const handleRetry = useCallback(() => {
    const question = lastQuestionRef.current
    if (question === null) return
    setWasCancelled(false)
    start(question)
  }, [start])

  return (
    <RalphView
      run={run}
      isLive
      isStreaming={isStreaming}
      wasCancelled={wasCancelled}
      composerValue={composerValue}
      onComposerChange={setComposerValue}
      onStart={handleStart}
      onCancel={handleCancel}
      onRetry={handleRetry}
    />
  )
}
