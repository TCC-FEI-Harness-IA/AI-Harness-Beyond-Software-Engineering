import { useMemo, useState } from 'react'
import { SegmentedControl } from '@/components/primitives/SegmentedControl'
import {
  type AnalysisGroup,
  formatMultiplier,
  formatPp,
  formatPValue,
  isSignificant,
} from '@/domain/services/benchmarkAnalysis'
import { benchmarkDatasetLabel } from '@/domain/services/benchmarkDefinition'
import { formatPercent } from '@/domain/services/formatters'
import styles from './BenchmarkAnalysis.module.css'

type SortKey = 'natural' | 'delta' | 'n'

const SORT_OPTIONS: ReadonlyArray<{ value: SortKey; label: string }> = [
  { value: 'natural', label: 'Padrão' },
  { value: 'delta', label: 'Maior Δ' },
  { value: 'n', label: 'Maior n' },
]

/** Grupos com menos pares que isto aparecem esmaecidos: a diferença ainda é ruído. */
export const LOW_N = 5

const rate = (value: number | null): string => (value === null ? '—' : formatPercent(value))

function signClass(value: number): string | undefined {
  if (value > 0) return styles.positive
  if (value < 0) return styles.negative
  return undefined
}

function Dumbbell({ simple, ralph, label }: { simple: number; ralph: number; label: string }): JSX.Element {
  const low = Math.min(simple, ralph) * 100
  const high = Math.max(simple, ralph) * 100
  return (
    <div
      className={styles.dumbbell}
      role="img"
      aria-label={`${label}: simples ${formatPercent(simple)}, Ralph ${formatPercent(ralph)}`}
    >
      <span className={styles.dumbbellTrack} />
      <span className={styles.dumbbellLink} style={{ left: `${low}%`, width: `${high - low}%` }} />
      <span
        className={`${styles.dot} ${styles.dotSimple}`}
        style={{ left: `${simple * 100}%` }}
        title={`Simples: ${formatPercent(simple)}`}
      />
      <span
        className={`${styles.dot} ${styles.dotRalph}`}
        style={{ left: `${ralph * 100}%` }}
        title={`Ralph: ${formatPercent(ralph)}`}
      />
    </div>
  )
}

export function FlowLegend(): JSX.Element {
  return (
    <ul className={styles.legend} aria-label="Legenda dos fluxos">
      <li>
        <span className={styles.swatch} style={{ background: 'var(--series-simple)' }} />
        Inferência simples
      </li>
      <li>
        <span className={styles.swatch} style={{ background: 'var(--series-ralph)' }} />
        Ralph Loop
      </li>
    </ul>
  )
}

export interface BreakdownTableProps {
  id: string
  title: string
  hint?: string
  groups: readonly AnalysisGroup[]
  /** Mostra o benchmark de cada grupo — útil quando a seleção mistura benchmarks. */
  showDataset?: boolean
}

/**
 * Uma quebra da análise pareada: acurácia dos dois fluxos no mesmo eixo, o que o Ralph corrige e
 * o que piora, a significância (McNemar exato) e o custo relativo em tokens.
 */
export function BreakdownTable({ id, title, hint, groups, showDataset = false }: BreakdownTableProps): JSX.Element {
  const [sort, setSort] = useState<SortKey>('natural')
  const sorted = useMemo(() => {
    if (sort === 'natural') return groups
    const key = sort === 'delta' ? (group: AnalysisGroup) => group.summary.delta : (group: AnalysisGroup) => group.summary.n
    return [...groups].sort((left, right) => key(right) - key(left))
  }, [groups, sort])

  return (
    <section className={styles.section} aria-labelledby={id}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 id={id} className={styles.sectionTitle}>
            {title}
          </h2>
          {hint ? <p className={styles.sectionHint}>{hint}</p> : null}
        </div>
        <div className={styles.toolbar}>
          <FlowLegend />
          <SegmentedControl ariaLabel={`Ordenar ${title}`} size="sm" options={SORT_OPTIONS} value={sort} onChange={setSort} />
        </div>
      </div>
      <div className={styles.tableWrapper}>
        <table className={styles.table} aria-label={title}>
          <thead>
            <tr>
              <th scope="col">Grupo</th>
              <th scope="col" title="Questões pareadas (os dois fluxos terminaram)">n</th>
              <th scope="col">Simples</th>
              <th scope="col">Ralph</th>
              <th scope="col" className={styles.left}>
                <span className={styles.dumbbellHead}>
                  <span>0%</span>
                  <span>Acurácia</span>
                  <span>100%</span>
                </span>
              </th>
              <th scope="col" title="Acurácia do Ralph menos a da simples">Δ</th>
              <th scope="col" title="Simples errou e o Ralph acertou">Corrige</th>
              <th scope="col" title="Simples acertou e o Ralph errou">Piora</th>
              <th scope="col" title="Corrige − piora">Líquido</th>
              <th scope="col" title="Dos erros da simples, quantos o Ralph acertou">Recuperação</th>
              <th scope="col" title="Dos acertos da simples, quantos o Ralph errou">Regressão</th>
              <th scope="col" title="Teste exato de McNemar (bicaudal) sobre os pares discordantes">p</th>
              <th scope="col" title="Tokens do Ralph ÷ tokens da simples">Tokens ×</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((group) => {
              const s = group.summary
              return (
                <tr key={group.key} className={s.n < LOW_N ? styles.lowN : undefined}>
                  <th scope="row" className={styles.left}>
                    <span className={styles.groupLabel} title={group.label}>
                      {group.label}
                    </span>
                    {showDataset && group.dataset !== null ? (
                      <span className={styles.groupMeta}>{benchmarkDatasetLabel(group.dataset)}</span>
                    ) : null}
                  </th>
                  <td>{s.n}</td>
                  <td>{formatPercent(s.simpleAccuracy)}</td>
                  <td>{formatPercent(s.ralphAccuracy)}</td>
                  <td className={styles.left}>
                    <Dumbbell simple={s.simpleAccuracy} ralph={s.ralphAccuracy} label={group.label} />
                  </td>
                  <td className={signClass(s.delta)}>{formatPp(s.delta)}</td>
                  <td>{s.recoveries}</td>
                  <td>{s.regressions}</td>
                  <td className={signClass(s.netGain)}>
                    {s.netGain > 0 ? '+' : ''}
                    {s.netGain}
                  </td>
                  <td>{rate(s.recoveryRate)}</td>
                  <td>{rate(s.regressionRate)}</td>
                  <td title={isSignificant(s) ? 'Significativo a 5%' : 'Não significativo a 5%'}>
                    {formatPValue(s.mcnemarPValue)}
                    {isSignificant(s) ? ' *' : ''}
                  </td>
                  <td>{formatMultiplier(s.tokenMultiplier)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
