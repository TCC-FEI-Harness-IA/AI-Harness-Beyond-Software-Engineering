import type { ThinkingPhase } from '@/domain/enums/thinkingPhase'
import { PHASE_SHORT_LABEL } from '@/domain/enums/thinkingPhase'
import type { EventSubtype } from '@/domain/enums/eventSubtype'
import { SUBTYPE_LABEL, SUBTYPE_TONE } from '@/domain/enums/eventSubtype'
import { Badge } from '@/components/primitives/Badge'
import { Tag } from '@/components/primitives/Tag'
import { cx } from '@/components/cx'
import { SUBTYPE_ICON_PATH } from './icons/subtypeIconPaths'
import styles from './PhaseTag.module.css'

export interface PhaseTagProps {
  phase: ThinkingPhase
  subtype: EventSubtype
  taskId?: string | null
  size?: 'sm' | 'md'
}

/**
 * Etiqueta que identifica a etapa do paper de uma mensagem, no Modo Chat do Ralph e no
 * histórico. Texto, cor e ícone vêm inteiramente dos mapas de domínio — nada é decidido aqui.
 */
export function PhaseTag({ phase, subtype, taskId, size = 'md' }: PhaseTagProps): JSX.Element {
  return (
    <span className={cx(styles.tag, styles[size])}>
      <Badge tone={SUBTYPE_TONE[subtype]}>
        <span className={styles.icon} aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d={SUBTYPE_ICON_PATH[subtype]} />
          </svg>
        </span>
        {PHASE_SHORT_LABEL[phase]} · {SUBTYPE_LABEL[subtype]}
      </Badge>
      {taskId ? <Tag>{taskId}</Tag> : null}
    </span>
  )
}
