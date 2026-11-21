import { useRef } from 'react'
import type { KeyboardEvent } from 'react'
import { BENCHMARK_DATASETS } from '@/domain/services/benchmarkDefinition'
import type { BenchmarkDatasetId } from '@/domain/types/benchmarkSession'
import styles from './BenchmarkTabs.module.css'

export function benchmarkTabId(benchmark: BenchmarkDatasetId): string {
  return `benchmark-tab-${benchmark}`
}

export function benchmarkPanelId(benchmark: BenchmarkDatasetId): string {
  return `benchmark-panel-${benchmark}`
}

export interface BenchmarkTabsProps {
  value: BenchmarkDatasetId
  onChange: (benchmark: BenchmarkDatasetId) => void
  /** Benchmark com bateria em execução: a aba ganha um indicador. */
  running: BenchmarkDatasetId | null
}

/**
 * Abas da página do BenchMark, uma por dataset (padrão WAI-ARIA de tabs com ativação automática):
 * ← → Home End movem o foco e já trocam de aba.
 */
export function BenchmarkTabs({ value, onChange, running }: BenchmarkTabsProps): JSX.Element {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])
  const selectedIndex = BENCHMARK_DATASETS.findIndex((dataset) => dataset.id === value)

  function select(index: number): void {
    const dataset = BENCHMARK_DATASETS[index]
    if (!dataset) return
    onChange(dataset.id)
    tabRefs.current[index]?.focus()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    const count = BENCHMARK_DATASETS.length
    const next: Record<string, number> = {
      ArrowRight: (selectedIndex + 1) % count,
      ArrowLeft: (selectedIndex - 1 + count) % count,
      Home: 0,
      End: count - 1,
    }
    const index = next[event.key]
    if (index === undefined) return
    event.preventDefault()
    select(index)
  }

  return (
    <div role="tablist" aria-label="Benchmark" className={styles.tablist} onKeyDown={handleKeyDown}>
      {BENCHMARK_DATASETS.map((dataset, index) => {
        const selected = dataset.id === value
        return (
          <button
            key={dataset.id}
            ref={(element) => {
              tabRefs.current[index] = element
            }}
            type="button"
            role="tab"
            id={benchmarkTabId(dataset.id)}
            aria-selected={selected}
            aria-controls={benchmarkPanelId(dataset.id)}
            tabIndex={selected ? 0 : -1}
            className={styles.tab}
            onClick={() => onChange(dataset.id)}
          >
            {dataset.label}
            {running === dataset.id ? (
              <span className={styles.runningDot} aria-hidden="true" />
            ) : null}
          </button>
        )
      })}
    </div>
  )
}
