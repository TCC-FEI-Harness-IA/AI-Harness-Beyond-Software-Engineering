import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
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
import { officialAsDocument } from '@/domain/services/officialBattery'
import { useBenchmarkDataset, useBenchmarkSessions } from '@/hooks/useBenchmarkData'
import { useOfficialPublications } from '@/hooks/useOfficialPublications'
import { buildBenchmarkPath, buildBenchmarkSessionPath, buildLoginPath, ROUTES } from '@/router/routes'
import { useAuth } from '@/state/AuthContext'
import { useBenchmarkRun } from '@/state/BenchmarkRunContext'
import { useRunConfig } from '@/state/RunConfigContext'
import { BenchmarkSessionCard } from './BenchmarkSessionCard'
import { BenchmarkSessionImport } from './BenchmarkSessionImport'
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

function OfficialResults({ benchmark }: { benchmark: BenchmarkDatasetId }): JSX.Element {
  const official = useOfficialPublications()
  const label = benchmarkDatasetLabel(benchmark)
  return (
    <section className={styles.section} aria-labelledby="resultado-oficial">
      <h2 id="resultado-oficial" className={styles.sectionTitle}>
        Resultado oficial
      </h2>
      {official.status === 'success' ? (
        official.data.filter((item) => item.dataset === benchmark).length === 0 ? (
          <EmptyState icon={BENCHMARK_ICON} title={`Ainda não há resultado oficial de ${label}`} />
        ) : (
          <ul className={styles.list} aria-label={`Resultado oficial de ${label}`}>
            {official.data
              .filter((item) => item.dataset === benchmark)
              .map((item) => (
                <BenchmarkSessionCard key={item.id} session={officialAsDocument(item)} official />
              ))}
          </ul>
        )
      ) : official.status === 'error' ? (
        <ErrorState error={official.error} onRetry={official.reload} />
      ) : (
        <Skeleton height="4.5rem" radius="var(--radius-lg)" />
      )}
    </section>
  )
}

function PersonalBenchmarks({ benchmark }: { benchmark: BenchmarkDatasetId }): JSX.Element {
  const auth = useAuth()
  const run = useBenchmarkRun()
  const { config } = useRunConfig()
  const navigate = useNavigate()
  const [gpqaSubset, setGpqaSubset] = useState<GPQASubset>('diamond')
  const dataset = useBenchmarkDataset(benchmark, gpqaSubset)
  const sessions = useBenchmarkSessions(run.finishedCount)
  const ownSessions =
    sessions.status === 'success'
      ? sessions.data.filter((session) => session.benchmark.dataset === benchmark)
      : []
  const label = benchmarkDatasetLabel(benchmark)
  const runningBenchmark = run.isActive ? run.benchmark : null

  return (
    <>
      <section className={styles.section} aria-labelledby="nova-bateria">
        <h2 id="nova-bateria" className={styles.sectionTitle}>
          Minhas execuções · nova bateria
        </h2>
        <Card padding="lg">
          {!auth.canRunLlm ? (
            <div className={styles.notice} role="status">
              <span>Configure uma chave OpenRouter válida para executar baterias nesta sessão.</span>
              <Link to={ROUTES.credential}>Configurar chave</Link>
            </div>
          ) : (
            <>
              {runningBenchmark !== null && runningBenchmark !== benchmark ? (
                <div className={styles.notice} role="status">
                  <span>
                    Uma bateria de {benchmarkDatasetLabel(runningBenchmark)} está em execução. Só
                    uma bateria roda por vez.
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate(buildBenchmarkPath(runningBenchmark), { replace: true })}
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
            </>
          )}
        </Card>
      </section>

      {run.benchmark === benchmark ? <RunMonitor /> : null}

      <section className={styles.section} aria-labelledby="baterias">
        <h2 id="baterias" className={styles.sectionTitle}>
          Minhas execuções · histórico
        </h2>
        <BenchmarkSessionImport
          onImported={(imported) => navigate(buildBenchmarkSessionPath(imported.id))}
        />
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
    </>
  )
}

/**
 * BenchMark com uma aba por dataset (Vestibulares, MMLU, GPQA). Todos veem o resultado oficial do
 * dataset; com login, a aba também inicia baterias próprias (com a chave OpenRouter da sessão),
 * acompanha a bateria atual e lista o histórico pessoal. A aba fica na URL (`?benchmark=`).
 */
export function BenchmarkPage(): JSX.Element {
  const auth = useAuth()
  const run = useBenchmarkRun()
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get(TAB_PARAM)
  // Sem aba na URL, abre na bateria em andamento (se houver) para não escondê-la.
  const benchmark: BenchmarkDatasetId = isBenchmarkDatasetId(requested)
    ? requested
    : (run.benchmark ?? 'vestibular')
  const description = BENCHMARK_DATASETS.find((item) => item.id === benchmark)?.description
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

      <BenchmarkTabs value={benchmark} onChange={selectBenchmark} running={runningBenchmark} />

      <div role="tabpanel" id={benchmarkPanelId(benchmark)} aria-labelledby={benchmarkTabId(benchmark)}>
        {description ? <p className={styles.description}>{description}</p> : null}

        <OfficialResults benchmark={benchmark} />

        {auth.status === 'authenticated' ? (
          <PersonalBenchmarks benchmark={benchmark} />
        ) : (
          <section className={styles.section} aria-labelledby="minhas-execucoes">
            <h2 id="minhas-execucoes" className={styles.sectionTitle}>
              Minhas execuções
            </h2>
            <Card padding="lg">
              <div className={styles.notice} role="status">
                <span>Entre para executar baterias com a sua chave OpenRouter e guardar o seu histórico.</span>
                <Link to={buildLoginPath(buildBenchmarkPath(benchmark))}>Entrar</Link>
              </div>
            </Card>
          </section>
        )}
      </div>
    </PageContainer>
  )
}
