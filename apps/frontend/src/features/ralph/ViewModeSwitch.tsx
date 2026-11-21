import { useEffect } from 'react'
import { SegmentedControl } from '@/components/primitives/SegmentedControl'
import { useViewMode } from '@/state/ViewModeContext'
import styles from './ViewModeSwitch.module.css'

const GRAPH_ICON = (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="4" cy="12" r="1.5" />
    <circle cx="8" cy="6" r="1.5" />
    <circle cx="13" cy="9" r="1.5" />
    <path d="M5.3 11 6.8 7.3M9.2 6.8l2.6 1.5" />
  </svg>
)

const CHAT_ICON = (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M2 3.5h12v7H6l-3 3v-3H2v-7Z" />
  </svg>
)

const OPTIONS = [
  { value: 'graph', label: 'Gráfico', icon: GRAPH_ICON },
  { value: 'chat', label: 'Chat', icon: CHAT_ICON },
] as const

/**
 * Interruptor entre Modo Gráfico e Modo Chat (README, FASE 05, seção 8). Os dois modos leem o
 * mesmo `ThinkingRun` — alternar só troca qual subárvore está montada; o socket nunca é
 * tocado. A escolha persiste em `ViewModeContext` e vale ao vivo e no histórico.
 */
export function ViewModeSwitch(): JSX.Element {
  const { viewMode, setViewMode, toggleViewMode } = useViewMode()

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      if ((event.metaKey || event.ctrlKey) && event.key === '\\') {
        event.preventDefault()
        toggleViewMode()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleViewMode])

  return (
    <div className={styles.wrapper} title="Alternar modo de visualização (⌘/Ctrl + \)">
      <SegmentedControl
        options={OPTIONS}
        value={viewMode}
        onChange={setViewMode}
        size="sm"
        ariaLabel="Modo de visualização"
      />
    </div>
  )
}
