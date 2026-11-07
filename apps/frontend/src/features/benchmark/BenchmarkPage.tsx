import { PageContainer } from '@/components/layout/PageContainer'
import { Card } from '@/components/primitives/Card'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import { Field } from '@/components/primitives/Field'
import { Select } from '@/components/primitives/Select'
import type { BenchmarkDatasetId, GPQASubset } from '@/domain/types/benchmarkSession'
import { useBenchmarkDataset, useBenchmarkSessions } from '@/hooks/useBenchmarkData'
import { useBenchmarkRun } from '@/state/BenchmarkRunContext'
import { useRunConfig } from '@/state/RunConfigContext'
import { BenchmarkSessionCard } from './BenchmarkSessionCard'
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

/**
 * Controle e acompanhamento do benchmark: inicia uma bateria (inferência simples × Ralph Loop
 * sobre as questões do dataset do backend), monitora a bateria atual pelo WebSocket e lista as
 * baterias persistidas.
 */
export function BenchmarkPage(): JSX.Element {
  const run = useBenchmarkRun()
  const { config } = useRunConfig()
  const [benchmark, setBenchmark] = useState<BenchmarkDatasetId>('vestibular')
  const [gpqaSubset, setGpqaSubset] = useState<GPQASubset>('diamond')
  const dataset = useBenchmarkDataset(benchmark, gpqaSubset)
  const sessions = useBenchmarkSessions(run.finishedCount)

  return (
    <PageContainer width="wide">
      <div className={styles.header}>
        <h1 className={styles.title}>BenchMark</h1>
        <p className={styles.subtitle}>
          Compare inferência simples e Ralph Loop em questões de Vestibulares, MMLU ou GPQA, com
          avaliação automática pelo gabarito.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="nova-bateria">
        <h2 id="nova-bateria" className={styles.sectionTitle}>
          Nova bateria
        </h2>
        <Card padding="lg">
          <Field label="Benchmark" className={styles.selector ?? ''}>
            <Select
              value={benchmark}
              disabled={run.isActive}
              onChange={(event) => setBenchmark(event.target.value as BenchmarkDatasetId)}
            >
              <option value="vestibular">Vestibulares brasileiros</option>
              <option value="mmlu">MMLU</option>
              <option value="gpqa">GPQA</option>
            </Select>
          </Field>
          {benchmark === 'gpqa' ? (
            <Field
              label="Variante GPQA"
              hint="Cada variante é avaliada separadamente; os conjuntos se sobrepõem."
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

      <RunMonitor />

      <section className={styles.section} aria-labelledby="baterias">
        <h2 id="baterias" className={styles.sectionTitle}>
          Baterias
        </h2>
        {sessions.status === 'success' ? (
          sessions.data.length === 0 ? (
            <EmptyState icon={BENCHMARK_ICON} title="Nenhuma bateria executada ainda" />
          ) : (
            <ul className={styles.list}>
              {sessions.data.map((session) => (
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
    </PageContainer>
  )
}
import { useState } from 'react'
