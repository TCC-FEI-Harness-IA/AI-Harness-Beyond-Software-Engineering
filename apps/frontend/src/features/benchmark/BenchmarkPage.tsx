import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { Card } from '@/components/primitives/Card'
import { Field } from '@/components/primitives/Field'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Select } from '@/components/primitives/Select'
import { Skeleton } from '@/components/primitives/Skeleton'
import {
  BENCHMARK_DATASETS,
  benchmarkDatasetLabel,
  isBenchmarkDatasetId,
} from '@/domain/services/benchmarkDefinition'
import type { BenchmarkDatasetId, GPQASubset } from '@/domain/types/benchmarkSession'
import { useBenchmarkDataset, useBenchmarkSessions } from '@/hooks/useBenchmarkData'
import { useBenchmarkRun } from '@/state/BenchmarkRunContext'
import { useRunConfig } from '@/state/RunConfigContext'
import { BenchmarkSessionCard } from './BenchmarkSessionCard'
import { BenchmarkTabs, benchmarkPanelId, benchmarkTabId } from './BenchmarkTabs'
import { NewRunForm } from './NewRunForm'
import { RunMonitor } from './RunMonitor'
import styles from './BenchmarkPage.module.css'

const BENCHMARK_ICON = (
  <svg
    width="32"
    height="32"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    aria-hidden="true"
  >
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" strokeLinecap="round" />
  </svg>
)

const TAB_PARAM = 'benchmark'

/**
 * Controle e acompanhamento do benchmark, com uma aba por dataset (Vestibulares, MMLU, GPQA).
 * Cada aba inicia baterias do seu dataset, monitora a bateria atual quando ela é desse dataset e
 * lista só as baterias persistidas dele. A aba fica na URL (`?benchmark=`) para sobreviver à
 * navegação até o detalhe de uma bateria e de volta.
 */
export function BenchmarkPage(): JSX.Element {
  const run = useBenchmarkRun()
  const { config } = useRunConfig()
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get(TAB_PARAM)
  // Sem aba na URL, abre na bateria em andamento (se houver) para não escondê-la.
  const benchmark: BenchmarkDatasetId = isBenchmarkDatasetId(requested)
    ? requested
    : (run.benchmark ?? 'vestibular')
  const [gpqaSubset, setGpqaSubset] = useState<GPQASubset>('diamond')
  const dataset = useBenchmarkDataset(benchmark, gpqaSubset)
  const sessions = useBenchmarkSessions(run.finishedCount)
  const ownSessions =
    sessions.status === 'success'
      ? sessions.data.filter((session) => session.benchmark.dataset === benchmark)
      : []
  const description = BENCHMARK_DATASETS.find((item) => item.id === benchmark)?.description
  const label = benchmarkDatasetLabel(benchmark)
  const runningBenchmark = run.isActive ? run.benchmark : null

  function selectBenchmark(next: BenchmarkDatasetId): void {
    setSearchParams({ [TAB_PARAM]: next }, { replace: true })
  }

  return (
    <PageContainer width="wide">
      <div className={styles.header}>
        <h1 className={styles.title}>BenchMark</h1>
        <p className={styles.subtitle}>
          Compare inferência simples e Ralph Loop nas questões de cada benchmark, com avaliação
          automática pelo gabarito.
        </p>
      </div>

      <BenchmarkTabs
        value={benchmark}
        onChange={selectBenchmark}
        running={runningBenchmark}
      />

      <div
        role="tabpanel"
        id={benchmarkPanelId(benchmark)}
        aria-labelledby={benchmarkTabId(benchmark)}
      >
        {description ? <p className={styles.description}>{description}</p> : null}

        <section className={styles.section} aria-labelledby="nova-bateria">
          <h2 id="nova-bateria" className={styles.sectionTitle}>
            Nova bateria
          </h2>
          <Card padding="lg">
            {runningBenchmark !== null && runningBenchmark !== benchmark ? (
              <div className={styles.notice} role="status">
                <span>
                  Uma bateria de {benchmarkDatasetLabel(runningBenchmark)} está em execução. Só
                  uma bateria roda por vez.
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => selectBenchmark(runningBenchmark)}
                >
                  Acompanhar
                </Button>
              </div>
            ) : null}
            {benchmark === 'gpqa' ? (
              <Field
                label="Variante GPQA"
                hint="Cada variante é avaliada separadamente; os conjuntos se sobrepõem."
                className={styles.selector ?? ''}
              >
                <Select
                  value={gpqaSubset}
                  disabled={run.isActive}
                  onChange={(event) => setGpqaSubset(event.target.value as GPQASubset)}
                >
                  <option value="diamond">Diamond — 198 questões</option>
                  <option value="main">Main — 448 questões</option>
                  <option value="extended">Extended — 546 questões</option>
                </Select>
              </Field>
            ) : null}
            {dataset.status === 'success' ? (
              <NewRunForm
                key={`${benchmark}-${gpqaSubset}`}
                benchmark={benchmark}
                gpqaSubset={gpqaSubset}
                dataset={dataset.data}
                disabled={run.isActive}
                onStart={(questionCount, maxParallel, options) =>
                  run.start({ questionCount, maxParallel, ...options, config })
                }
              />
            ) : dataset.status === 'error' ? (
              <ErrorState error={dataset.error} onRetry={dataset.reload} />
            ) : (
              <Skeleton lines={3} />
            )}
          </Card>
        </section>

        {run.benchmark === benchmark ? <RunMonitor /> : null}

        <section className={styles.section} aria-labelledby="baterias">
          <h2 id="baterias" className={styles.sectionTitle}>
            Histórico de baterias
          </h2>
          {sessions.status === 'success' ? (
            ownSessions.length === 0 ? (
              <EmptyState
                icon={BENCHMARK_ICON}
                title={`Nenhuma bateria de ${label} executada ainda`}
              />
            ) : (
              <ul className={styles.list} aria-label={`Baterias de ${label}`}>
                {ownSessions.map((session) => (
                  <BenchmarkSessionCard key={session.id} session={session} />
                ))}
              </ul>
            )
          ) : sessions.status === 'error' ? (
            <ErrorState error={sessions.error} onRetry={sessions.reload} />
          ) : (
            <div className={styles.list}>
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} height="4.5rem" radius="var(--radius-lg)" />
              ))}
            </div>
          )}
        </section>
      </div>
    </PageContainer>
  )
}
