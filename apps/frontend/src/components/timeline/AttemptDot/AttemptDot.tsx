import { cx } from '@/components/cx'
import { SUBTYPE_LABEL } from '@/domain/enums/eventSubtype'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import styles from './AttemptDot.module.css'

export interface AttemptDotProps {
  step: ThinkingStep
  /** Passo mais recente ao vivo — recebe o halo pulsante (README, seção 5). */
  isLatest?: boolean
  onSelect: (step: ThinkingStep) => void
}

const SYMBOL: Record<string, string> = {
  reset: '●',
  execute: '▷',
  reasoning: '◆',
  verify_pass: '✓',
  verify_fail: '✗',
  store: '▣',
  learn: '☀',
}

const TONE_CLASS: Record<string, string | undefined> = {
  reset: styles.toneContext,
  execute: styles.toneNeutral,
  reasoning: styles.toneStrong,
  verify_pass: styles.toneSuccess,
  verify_fail: styles.toneWarning,
  store: styles.toneSuccess,
  learn: styles.toneSecondary,
}

/**
 * Um passo dentro da faixa de uma tarefa (README, FASE 06, seção 5) — símbolo e cor fixos por
 * `subtype` (tabela do README). Cada ponto é um `<button>` real: clicar abre o detalhe do passo.
 */
export function AttemptDot({ step, isLatest = false, onSelect }: AttemptDotProps): JSX.Element {
  const label = `${SUBTYPE_LABEL[step.subtype]} — tarefa ${step.taskId}`

  return (
    <button
      type="button"
      className={cx(styles.dot, TONE_CLASS[step.subtype], isLatest && styles.pulse)}
      onClick={() => onSelect(step)}
      aria-label={label}
      title={label}
    >
      <span aria-hidden="true">{SYMBOL[step.subtype] ?? '•'}</span>
    </button>
  )
}
