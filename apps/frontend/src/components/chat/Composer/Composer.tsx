import { useLayoutEffect, useRef } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { IconButton } from '@/components/primitives/IconButton'
import { cx } from '@/components/cx'
import styles from './Composer.module.css'

export interface ComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  placeholder?: string
  disabled?: boolean
  busy?: boolean
  /** Ações renderizadas abaixo do campo — a home passa os dois botões de modo. */
  footer?: ReactNode
  autoFocus?: boolean
  maxLength?: number
}

const COUNTER_WARN_RATIO = 0.9

function isCoarsePointer(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches
}

function canSubmit(value: string, disabled: boolean, busy: boolean): boolean {
  return value.trim().length > 0 && !disabled && !busy
}

/** Barra de texto da home e do chat — cresce com o conteúdo até um máximo, depois rola. */
export function Composer({
  value,
  onChange,
  onSubmit,
  placeholder,
  disabled = false,
  busy = false,
  footer,
  autoFocus = false,
  maxLength,
}: ComposerProps): JSX.Element {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    // Reseta para 'auto' antes de medir — senão a caixa só cresce e nunca encolhe.
    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  }, [value])

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key !== 'Enter' || event.shiftKey || isCoarsePointer()) return
    event.preventDefault()
    if (canSubmit(value, disabled, busy)) onSubmit()
  }

  function handleSubmitClick(): void {
    if (canSubmit(value, disabled, busy)) onSubmit()
  }

  const showCounter = maxLength !== undefined && value.length >= maxLength * COUNTER_WARN_RATIO

  return (
    <div className={styles.wrapper}>
      <div className={styles.field}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          autoFocus={autoFocus}
          maxLength={maxLength}
          rows={1}
          aria-label={placeholder ?? 'Mensagem'}
        />
        <IconButton
          className={styles.submit}
          aria-label="Enviar mensagem"
          icon={
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M8 13V3M3 8l5-5 5 5" />
            </svg>
          }
          loading={busy}
          disabled={!canSubmit(value, disabled, busy)}
          onClick={handleSubmitClick}
        />
      </div>
      {(footer ?? showCounter) ? (
        <div className={styles.footer}>
          <div>{footer}</div>
          {showCounter && maxLength !== undefined ? (
            <span className={cx(styles.counter, value.length >= maxLength && styles.counterWarn)}>
              {value.length}/{maxLength}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
