import { Switch } from '@/components/primitives/Switch'
import styles from './BenchmarkAnalysis.module.css'

/** `Switch` com o rótulo visível ao lado; clicar no texto também alterna. */
export function LabeledSwitch({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}): JSX.Element {
  return (
    <span className={styles.switchField}>
      <Switch label={label} checked={checked} onChange={onChange} />
      {/* O nome acessível já vem do `aria-label` do interruptor. */}
      <span aria-hidden="true" onClick={() => onChange(!checked)}>
        {label}
      </span>
    </span>
  )
}
