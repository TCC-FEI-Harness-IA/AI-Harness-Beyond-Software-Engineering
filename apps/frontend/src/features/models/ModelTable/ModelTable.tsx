import { useId, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { cx } from '@/components/cx'
import { formatCompactTokens, formatPricePerMillion, formatThroughput } from '@/domain/services/formatters'
import {
  DEFAULT_MODEL_SORT,
  type ModelSort,
  type ModelSortKey,
  modelLabel,
  nextModelSort,
  sortModels,
} from '@/domain/services/modelSort'
import type { ModelInfo } from '@/domain/types/modelInfo'
import styles from './ModelTable.module.css'

const UNKNOWN = '—'

function orUnknown<T>(value: T | null, format: (value: T) => string): string {
  return value === null ? UNKNOWN : format(value)
}

interface Column {
  key: ModelSortKey
  label: string
  numeric: boolean
  title?: string
  render: (model: ModelInfo) => string
}

const NUMERIC_COLUMNS: readonly Column[] = [
  {
    key: 'input_price_per_million_tokens',
    label: 'Entrada (1M tokens)',
    numeric: true,
    render: (model) => orUnknown(model.input_price_per_million_tokens, formatPricePerMillion),
  },
  {
    key: 'output_price_per_million_tokens',
    label: 'Saída (1M tokens)',
    numeric: true,
    render: (model) => orUnknown(model.output_price_per_million_tokens, formatPricePerMillion),
  },
  {
    key: 'context_length',
    label: 'Contexto',
    numeric: true,
    title: 'Tamanho máximo da janela de contexto (entrada + saída).',
    render: (model) => orUnknown(model.context_length, (tokens) => `${formatCompactTokens(tokens)} tokens`),
  },
  {
    key: 'throughput_tokens_per_second',
    label: 'Vazão',
    numeric: true,
    title: 'Tokens gerados por segundo.',
    render: (model) => orUnknown(model.throughput_tokens_per_second, formatThroughput),
  },
]

const ARIA_SORT = { asc: 'ascending', desc: 'descending' } as const

export interface ModelTableProps {
  models: readonly ModelInfo[]
  /** Nome acessível da tabela. */
  label: string
  /** Com `onSelect`, cada linha ganha um botão de rádio e a tabela vira uma escolha única. */
  selectedModel?: string
  onSelect?: (modelName: string) => void
  /** Conteúdo da última coluna (ex.: editar e remover), quando informado. */
  renderActions?: (model: ModelInfo) => ReactNode
}

/**
 * Lista de modelos do catálogo com preço, contexto e vazão, ordenável por qualquer coluna. Um dado
 * desconhecido aparece como "—" e fica no fim da ordenação.
 */
export function ModelTable({ models, label, selectedModel, onSelect, renderActions }: ModelTableProps): JSX.Element {
  const [sort, setSort] = useState<ModelSort>(DEFAULT_MODEL_SORT)
  const radioName = useId()
  const sorted = useMemo(() => sortModels(models, sort), [models, sort])
  const selectable = onSelect !== undefined

  function sortHeader(key: ModelSortKey, text: string, numeric: boolean, title?: string): JSX.Element {
    const active = sort.key === key
    return (
      <th
        key={key}
        scope="col"
        className={cx(numeric && styles.numeric)}
        aria-sort={active ? ARIA_SORT[sort.direction] : 'none'}
        title={title}
      >
        <button type="button" className={styles.sortButton} onClick={() => setSort((prev) => nextModelSort(prev, key))}>
          {text}
          <span className={cx(styles.sortIcon, active && styles.sortIconActive)} aria-hidden="true">
            {active && sort.direction === 'desc' ? '↓' : '↑'}
          </span>
        </button>
      </th>
    )
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table} aria-label={label}>
        <thead>
          <tr>
            {selectable ? (
              <th scope="col" className={styles.selectCell}>
                <span className={styles.srOnly}>Selecionado</span>
              </th>
            ) : null}
            {sortHeader('name', 'Modelo', false)}
            {NUMERIC_COLUMNS.map((column) => sortHeader(column.key, column.label, column.numeric, column.title))}
            {renderActions ? (
              <th scope="col">
                <span className={styles.srOnly}>Ações</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {sorted.map((model) => {
            const selected = selectable && model.model_name === selectedModel
            return (
              <tr
                key={model.model_name}
                className={cx(selectable && styles.selectableRow, selected && styles.selectedRow)}
                onClick={selectable ? () => onSelect(model.model_name) : undefined}
              >
                {selectable ? (
                  <td className={styles.selectCell}>
                    <input
                      type="radio"
                      name={radioName}
                      value={model.model_name}
                      checked={selected}
                      onChange={() => onSelect(model.model_name)}
                      aria-label={modelLabel(model)}
                    />
                  </td>
                ) : null}
                <th scope="row" className={styles.nameCell}>
                  <span className={styles.displayName}>{modelLabel(model)}</span>
                  {model.display_name ? <span className={styles.modelId}>{model.model_name}</span> : null}
                </th>
                {NUMERIC_COLUMNS.map((column) => (
                  <td key={column.key} className={styles.numeric}>
                    {column.render(model)}
                  </td>
                ))}
                {renderActions ? <td className={styles.actionsCell}>{renderActions(model)}</td> : null}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
