import { useMemo, useState } from 'react'
import { Badge } from '@/components/primitives/Badge'
import { Button } from '@/components/primitives/Button'
import { SegmentedControl } from '@/components/primitives/SegmentedControl'
import {
  BENCHMARK_SESSION_STATUS_LABEL,
  BENCHMARK_SESSION_STATUS_TONE,
} from '@/domain/enums/benchmarkStatus'
import { BENCHMARK_DATASETS, benchmarkLabel } from '@/domain/services/benchmarkDefinition'
import { formatDateTime, formatPercent } from '@/domain/services/formatters'
import type { BenchmarkDatasetId, BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { LabeledSwitch } from './LabeledSwitch'
import styles from './BenchmarkAnalysis.module.css'

type DatasetFilter = 'all' | BenchmarkDatasetId

const DATASET_OPTIONS: ReadonlyArray<{ value: DatasetFilter; label: string }> = [
  { value: 'all', label: 'Todos' },
  ...BENCHMARK_DATASETS.map((dataset) => ({ value: dataset.id, label: dataset.label })),
]

export interface ExecutionPickerProps {
  sessions: readonly BenchmarkSessionDocument[]
  selectedIds: ReadonlySet<string>
  onChange: (ids: string[]) => void
}

/** Lista as baterias com caixas de seleção; permite misturar benchmarks na mesma análise. */
export function ExecutionPicker({ sessions, selectedIds, onChange }: ExecutionPickerProps): JSX.Element {
  const [dataset, setDataset] = useState<DatasetFilter>('all')
  const [onlyWithResults, setOnlyWithResults] = useState(true)

  const visible = useMemo(
    () =>
      sessions.filter(
        (session) =>
          (dataset === 'all' || session.benchmark.dataset === dataset) &&
          (!onlyWithResults || (session.summary.simple.executed > 0 && session.summary.ralph.executed > 0)),
      ),
    [sessions, dataset, onlyWithResults],
  )

  const toggle = (id: string): void => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChange([...next])
  }

  const allVisibleSelected = visible.length > 0 && visible.every((session) => selectedIds.has(session.id))

  return (
    <section className={styles.section} aria-labelledby="analysis-picker-title">
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="analysis-picker-title" className={styles.sectionTitle}>
            Execuções
          </h2>
          <p className={styles.sectionHint}>
            Selecione uma ou mais baterias — de qualquer benchmark. Cada questão de cada bateria conta como
            uma observação pareada (o mesmo enunciado respondido pelos dois fluxos).
          </p>
        </div>
        <div className={styles.toolbar}>
          <SegmentedControl
            ariaLabel="Filtrar baterias por benchmark"
            size="sm"
            options={DATASET_OPTIONS}
            value={dataset}
            onChange={setDataset}
          />
          <LabeledSwitch label="Só com resultados" checked={onlyWithResults} onChange={setOnlyWithResults} />
          <Button
            size="sm"
            variant="secondary"
            disabled={visible.length === 0}
            onClick={() =>
              onChange(
                allVisibleSelected
                  ? [...selectedIds].filter((id) => !visible.some((session) => session.id === id))
                  : [...new Set([...selectedIds, ...visible.map((session) => session.id)])],
              )
            }
          >
            {allVisibleSelected ? 'Desmarcar visíveis' : 'Marcar visíveis'}
          </Button>
          <Button size="sm" variant="ghost" disabled={selectedIds.size === 0} onClick={() => onChange([])}>
            Limpar seleção
          </Button>
        </div>
      </div>

      <div className={styles.tableWrapper} style={{ maxHeight: 360 }}>
        <table className={styles.table} aria-label="Baterias disponíveis para análise">
          <thead>
            <tr>
              <th scope="col" className={styles.checkCell} aria-label="Selecionar" />
              <th scope="col" className={styles.left}>
                Execução
              </th>
              <th scope="col" className={styles.left}>
                Benchmark
              </th>
              <th scope="col" className={styles.left}>
                Modelo
              </th>
              <th scope="col">Questões</th>
              <th scope="col" className={styles.left}>
                Status
              </th>
              <th scope="col">Simples</th>
              <th scope="col">Ralph</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={8} className={styles.muted}>
                  Nenhuma bateria neste filtro.
                </td>
              </tr>
            ) : (
              visible.map((session) => {
                const inputId = `analysis-pick-${session.id}`
                return (
                  <tr key={session.id}>
                    <td className={styles.checkCell}>
                      <input
                        id={inputId}
                        type="checkbox"
                        checked={selectedIds.has(session.id)}
                        onChange={() => toggle(session.id)}
                      />
                    </td>
                    <td className={styles.left}>
                      <label htmlFor={inputId} className={styles.groupLabel}>
                        {session.alias ?? formatDateTime(session.created_at)}
                      </label>
                      <span className={styles.groupMeta}>
                        {session.alias ? `${formatDateTime(session.created_at)} · ` : ''}
                        <span className={styles.mono}>{session.id}</span>
                      </span>
                    </td>
                    <td className={styles.left}>{benchmarkLabel(session.benchmark)}</td>
                    <td className={styles.left}>{session.model_name}</td>
                    <td>{session.question_count}</td>
                    <td className={styles.left}>
                      <Badge tone={BENCHMARK_SESSION_STATUS_TONE[session.status]}>
                        {BENCHMARK_SESSION_STATUS_LABEL[session.status]}
                      </Badge>
                    </td>
                    <td>{formatPercent(session.summary.simple.accuracy)}</td>
                    <td>{formatPercent(session.summary.ralph.accuracy)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
