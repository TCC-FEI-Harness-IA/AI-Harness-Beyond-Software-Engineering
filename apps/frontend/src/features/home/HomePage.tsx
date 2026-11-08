import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ralphImage from '@/assets/ralph_image.png'
import { Composer } from '@/components/chat/Composer'
import { PageContainer } from '@/components/layout/PageContainer'
import type { InferenceNavigationState } from '@/router/navigationState'
import { ROUTES } from '@/router/routes'
import { ModeCard, type InferenceMode } from './ModeCard'
import { RunConfigBar } from './RunConfigBar'
import { persistLastMode, readLastMode } from './lastMode'
import styles from './HomePage.module.css'

const LIGHTNING_ICON = (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
  </svg>
)

const ORBIT_ICON = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
    <circle cx="12" cy="12" r="3" />
    <ellipse cx="12" cy="12" rx="10" ry="4.2" transform="rotate(30 12 12)" />
  </svg>
)

/**
 * Página de início (README, FASE 04, seção 5): uma barra de texto e, logo abaixo, as duas
 * opções de fluxo. Um clique num cartão já seleciona e envia; com o campo vazio, apenas
 * seleciona e devolve o foco ao campo.
 */
export function HomePage(): JSX.Element {
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<InferenceMode>(readLastMode)
  const composerRef = useRef<HTMLDivElement>(null)

  function focusComposer(): void {
    composerRef.current?.querySelector('textarea')?.focus()
  }

  function handleSelectMode(nextMode: InferenceMode): void {
    setMode(nextMode)
    persistLastMode(nextMode)

    const trimmed = question.trim()
    if (trimmed === '') {
      focusComposer()
      return
    }

    navigate(nextMode === 'simple' ? ROUTES.simpleChat : ROUTES.ralphChat, {
      state: { question: trimmed, autoStart: true } satisfies InferenceNavigationState,
    })
  }

  return (
    <PageContainer width="content">
      <div className={styles.hero}>
        <img className={styles.logo} src={ralphImage} alt="" />
        <h1 className={styles.title}>Harness de IA</h1>
        <p className={styles.subtitle}>
          Ralph Wiggum Loop adaptado para perguntas em linguagem natural
        </p>
      </div>

      <div ref={composerRef} className={styles.composer}>
        <Composer
          value={question}
          onChange={setQuestion}
          onSubmit={() => handleSelectMode(mode)}
          placeholder="Faça uma pergunta…"
          autoFocus
        />
      </div>

      <div role="radiogroup" aria-label="Fluxo de inferência" className={styles.modes}>
        <ModeCard
          mode="simple"
          title="Inferência Simples"
          description="Uma chamada direta ao modelo"
          icon={LIGHTNING_ICON}
          selected={mode === 'simple'}
          onSelect={handleSelectMode}
        />
        <ModeCard
          mode="ralph"
          title="Ralph Loop Adaptado"
          description="Planeja, resolve e verifica em ciclos"
          icon={ORBIT_ICON}
          selected={mode === 'ralph'}
          onSelect={handleSelectMode}
          hint="Consome mais tokens"
        />
      </div>

      <div className={styles.configBar}>
        <RunConfigBar />
      </div>
    </PageContainer>
  )
}
