import type { ReactNode } from 'react'
import { cx } from '@/components/cx'
import styles from './ModeCard.module.css'

export type InferenceMode = 'simple' | 'ralph'

export interface ModeCardProps {
  mode: InferenceMode
  title: string
  description: string
  icon: ReactNode
  selected: boolean
  disabled?: boolean
  onSelect: (mode: InferenceMode) => void
  /** Nota extra em --text-xs, ex.: aviso de custo do modo Ralph (README, FASE 04, seção 5.2). */
  hint?: string
}

/**
 * Cartão de escolha de fluxo — inferência simples vs. Ralph Loop, na home (README, FASE 04,
 * seção 5.2). Não reusa `<Card>` aqui: o controle precisa ser um `<button>` real por
 * acessibilidade (regra 11 do README), e `Card` não pode renderizar como `button` — este
 * componente reimplementa só a superfície (raio, sombra, hairline) com os mesmos tokens que
 * `Card` usa. Espera ser um dos filhos de um container `role="radiogroup"`.
 */
export function ModeCard({
  mode,
  title,
  description,
  icon,
  selected,
  disabled = false,
  onSelect,
  hint,
}: ModeCardProps): JSX.Element {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      aria-label={`${title}. ${description}`}
      disabled={disabled}
      className={cx(styles.card, selected && styles.selected)}
      onClick={() => onSelect(mode)}
    >
      <span className={styles.icon} aria-hidden="true">
        {icon}
      </span>
      <span className={styles.title}>{title}</span>
      <p className={styles.description}>{description}</p>
      {hint ? <span className={styles.hint}>{hint}</span> : null}
    </button>
  )
}
