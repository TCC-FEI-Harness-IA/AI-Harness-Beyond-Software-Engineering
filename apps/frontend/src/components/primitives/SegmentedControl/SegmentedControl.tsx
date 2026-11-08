import { useLayoutEffect, useRef, useState } from 'react'
import type { CSSProperties, KeyboardEvent, ReactNode } from 'react'
import { cx } from '@/components/cx'
import styles from './SegmentedControl.module.css'

export interface SegmentedControlOption<T extends string> {
  value: T
  label: string
  icon?: ReactNode
}

export interface SegmentedControlProps<T extends string> {
  options: ReadonlyArray<SegmentedControlOption<T>>
  value: T
  onChange: (value: T) => void
  size?: 'sm' | 'md'
  ariaLabel: string
}

/**
 * Controle segmentado no estilo macOS. O indicador do item selecionado é um único elemento
 * que desliza entre as posições (não é "acender o fundo do botão") — é esse detalhe que dá a
 * sensação nativa exigida pelo README.
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  size = 'md',
  ariaLabel,
}: SegmentedControlProps<T>): JSX.Element {
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([])
  const [indicatorStyle, setIndicatorStyle] = useState<CSSProperties>({})

  const selectedIndex = options.findIndex((option) => option.value === value)

  useLayoutEffect(() => {
    const selectedButton = buttonRefs.current[selectedIndex]
    if (!selectedButton) return
    setIndicatorStyle({
      transform: `translateX(${selectedButton.offsetLeft}px)`,
      width: `${selectedButton.offsetWidth}px`,
    })
  }, [selectedIndex, options.length])

  function focusAndSelect(index: number): void {
    const option = options[index]
    if (!option) return
    onChange(option.value)
    buttonRefs.current[index]?.focus()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      focusAndSelect((selectedIndex + 1) % options.length)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      focusAndSelect((selectedIndex - 1 + options.length) % options.length)
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cx(styles.track, styles[size])}
      onKeyDown={handleKeyDown}
    >
      <span className={styles.indicator} style={indicatorStyle} aria-hidden="true" />
      {options.map((option, index) => (
        <button
          key={option.value}
          ref={(el) => {
            buttonRefs.current[index] = el
          }}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          tabIndex={option.value === value ? 0 : -1}
          className={styles.option}
          onClick={() => onChange(option.value)}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  )
}
