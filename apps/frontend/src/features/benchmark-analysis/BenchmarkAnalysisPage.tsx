import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { Card } from '@/components/primitives/Card'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import {
  type AnalysisDimension,
  buildAnalysisRecords,
  DIMENSION_LABEL,
  groupRecords,
  rankGroupsByDelta,
  sectionTitle,
  summarizePairs,
} from '@/domain/services/benchmarkAnalysis'
import { buildAnalysisCsv, buildAnalysisMarkdown } from '@/domain/services/benchmarkAnalysisReport'
import { groupByProcess, PROCESS_DIMENSION_LABEL, type ProcessDimension } from '@/domain/services/ralphProcessMetrics'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { useBenchmarkSessions } from '@/hooks/useBenchmarkData'
import { useRalphProcessMetrics } from '@/hooks/useRalphProcessMetrics'
import { saveBlob } from '@/hooks/saveBlob'
import { AnalysisOverview } from './AnalysisOverview'
import { BreakdownTable, LOW_N } from './BreakdownTable'
import { DivergentQuestions } from './DivergentQuestions'
import { ExecutionPicker } from './ExecutionPicker'
import { RalphProcessSection } from './RalphProcessSection'
import { LabeledSwitch } from './LabeledSwitch'
import styles from './BenchmarkAnalysis.module.css'

/** Parâmetro de URL com as baterias selecionadas, separadas por vírgula — a análise é compartilhável. */
export const SELECTION_PARAM = 'execucoes'

const CHART_ICON = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" strokeLinecap="round" />
  </svg>
)

const BREAKDOWNS: ReadonlyArray<{ dimension: AnalysisDimension; hint: string; multiOnly?: boolean }> = [
  {
    dimension: 'execution',
    hint: 'Análise executiva de cada bateria selecionada — mesmo modelo e configuração dentro de cada linha.',
  },
  { dimension: 'dataset', hint: 'Consolidado por benchmark.', multiOnly: true },
  {
    dimension: 'subject',
    hint: 'Onde o Ralph mais ajuda e mais atrapalha. Grupos com menos de 5 pares aparecem esmaecidos.',
  },
  {
    dimension: 'area',
    hint: 'Matérias agrupadas nas categorias do MMLU (STEM, humanidades, ciências sociais, outras), comparáveis entre benchmarks.',
  },
  {
    dimension: 'level',
    hint: 'Complexidade intrínseca da questão: vestibular de origem (ENEM → ITA), nível do MMLU pela disciplina e variante do GPQA.',
  },
  {
    dimension: 'simpleEffort',
    hint: 'Dificuldade empírica: quartis, dentro de cada bateria, dos tokens que a inferência simples gastou. Q4 = questões em que o modelo mais "pensou".',
  },
  {
    dimension: 'ralphEffort',
    hint: 'Quartis dos tokens do Ralph Loop dentro de cada bateria: o loop acerta mais quando trabalha mais?',
  },
]

const PROCESS_DIMENSIONS: ProcessDimension[] = ['taskCount', 'verificationFailures', 'planRejections']

function readSelection(params: URLSearchParams): string[] {
  return (params.get(SELECTION_PARAM) ?? '').split(',').filter((id) => id !== '')
}

function AnalysisDashboard({ sessions }: { sessions: readonly BenchmarkSessionDocument[] }): JSX.Element {
  const [excludeFailures, setExcludeFailures] = useState(false)
  const { records, exclusions } = useMemo(
    () => buildAnalysisRecords(sessions, { excludeFailures }),
    [sessions, excludeFailures],
  )
  const summary = useMemo(() => summarizePairs(records), [records])
  const groups = useMemo(
    () => new Map(BREAKDOWNS.map(({ dimension }) => [dimension, groupRecords(records, dimension, sessions)])),
    [records, sessions],
  )
  const ralphSessionIds = useMemo(
    () => records.flatMap((record) => (record.ralph.session_id === null ? [] : [record.ralph.session_id])),
    [records],
  )
  const process = useRalphProcessMetrics(ralphSessionIds)
  const multiDataset = new Set(sessions.map((session) => session.benchmark.dataset)).size > 1

  const exportCsv = (): void => {
    saveBlob(
      new Blob([buildAnalysisCsv(records, sessions, process.metrics)], { type: 'text/csv;charset=utf-8' }),
      'analise-benchmark-questoes.csv',
    )
  }
  const exportMarkdown = (): void => {
    const extra = process.enabled
      ? PROCESS_DIMENSIONS.map((dimension) => ({
          title: PROCESS_DIMENSION_LABEL[dimension],
          groups: groupByProcess(records, dimension, process.metrics),
        }))
      : []
    saveBlob(
      new Blob([buildAnalysisMarkdown(records, sessions, extra)], { type: 'text/markdown;charset=utf-8' }),
      'analise-benchmark.md',
    )
  }

  if (records.length === 0) {
    return (
      <EmptyState
        icon={CHART_ICON}
        title="Nenhuma questão pareada"
        description="As baterias selecionadas ainda não têm questões concluídas pelos dois fluxos."
      />
    )
  }

  return (
    <>
      <div className={styles.toolbar}>
        <LabeledSwitch
          label="Desconsiderar questões com falha técnica"
          checked={excludeFailures}
          onChange={setExcludeFailures}
        />
        <Button size="sm" variant="secondary" onClick={exportCsv}>
          Exportar CSV (por questão)
        </Button>
        <Button size="sm" variant="secondary" onClick={exportMarkdown}>
          Exportar relatório (Markdown)
        </Button>
      </div>

      <Card padding="lg">
        <AnalysisOverview
          summary={summary}
          highlights={[
            { dimension: 'matéria', groups: rankGroupsByDelta(groups.get('subject') ?? [], LOW_N) },
            { dimension: 'área', groups: rankGroupsByDelta(groups.get('area') ?? [], LOW_N) },
          ]}
          exclusions={exclusions}
        />
      </Card>

      {BREAKDOWNS.filter((breakdown) => !breakdown.multiOnly || multiDataset).map(({ dimension, hint }) => (
        <BreakdownTable
          key={dimension}
          id={`analysis-${dimension}`}
          title={sectionTitle(DIMENSION_LABEL[dimension])}
          hint={hint}
          groups={groups.get(dimension) ?? []}
          showDataset={multiDataset && dimension === 'subject'}
        />
      ))}

      <RalphProcessSection records={records} process={process} />
      <DivergentQuestions records={records} />

      <p className={styles.notice}>
        Metodologia: só entram questões em que os dois fluxos terminaram; falhas técnicas contam como erro, a
        menos que o filtro acima as descarte. Δ é a acurácia do Ralph menos a da simples, em pontos percentuais.
        O p-valor é o teste exato de McNemar (bicaudal) sobre os pares discordantes — ‘*’ marca p &lt; 0,05. Os
        intervalos de acurácia são de Wilson a 95%. Recuperação = corrigidas ÷ erros da simples; regressão =
        pioradas ÷ acertos da simples. A mesma questão em baterias diferentes conta como observações distintas.
      </p>
    </>
  )
}

/**
 * Análise de resultados do benchmark: seleciona uma ou mais baterias (de qualquer benchmark) e
 * mostra o comparativo pareado Simples × Ralph Loop com as quebras para o relatório técnico.
 */
export function BenchmarkAnalysisPage(): JSX.Element {
  const list = useBenchmarkSessions()
  const [params, setParams] = useSearchParams()
  const selectedIds = useMemo(() => new Set(readSelection(params)), [params])

  const setSelection = (ids: string[]): void => {
    const next = new URLSearchParams(params)
    if (ids.length === 0) next.delete(SELECTION_PARAM)
    else next.set(SELECTION_PARAM, ids.join(','))
    setParams(next, { replace: true })
  }

  const loaded = list.status === 'success' ? list.data : null
  const sessions = useMemo(() => loaded ?? [], [loaded])
  const selected = useMemo(
    () => sessions.filter((session) => selectedIds.has(session.id)),
    [sessions, selectedIds],
  )

  return (
    <PageContainer width="wide">
      <div className={styles.root}>
        <header className={styles.header}>
          <h1 className={styles.title}>Análise de resultados</h1>
          <p className={styles.lead}>
            Compara, questão a questão, a inferência simples com o Ralph Loop nas baterias escolhidas: quanto o
            Ralph corrige, quanto piora, onde ajuda (matéria, área, nível, dificuldade e complexidade do plano) e a
            que custo.
          </p>
        </header>

        {list.status === 'error' ? <ErrorState error={list.error} onRetry={list.reload} /> : null}
        {list.status === 'loading' || list.status === 'idle' ? <Skeleton lines={6} /> : null}
        {list.status === 'success' ? (
          <>
            <div className={styles.toolbar}>
              <Button size="sm" variant="ghost" onClick={list.reload}>
                Atualizar baterias
              </Button>
            </div>
            <ExecutionPicker sessions={sessions} selectedIds={selectedIds} onChange={setSelection} />
            {selected.length === 0 ? (
              <EmptyState
                icon={CHART_ICON}
                title="Selecione ao menos uma execução"
                description="Marque baterias na lista acima para montar o dashboard."
              />
            ) : (
              <AnalysisDashboard sessions={selected} />
            )}
          </>
        ) : null}
      </div>
    </PageContainer>
  )
}
