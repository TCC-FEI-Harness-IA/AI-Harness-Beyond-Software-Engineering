import { useMemo, useRef } from 'react'
import type { KeyboardEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { SegmentedControl } from '@/components/primitives/SegmentedControl'
import { Skeleton } from '@/components/primitives/Skeleton'
import { formatTokens } from '@/domain/services/formatters'
import { useSessionList } from '@/hooks/useSessionList'
import { ROUTES } from '@/router/routes'
import { SessionCard } from './SessionCard'
import styles from './HistoryListPage.module.css'

type FlowFilter = 'all' | 'simple' | 'ralph'

const FLOW_OPTIONS: ReadonlyArray<{ value: FlowFilter; label: string }> = [
  { value: 'all', label: 'Todos' },
  { value: 'simple', label: 'Simples' },
  { value: 'ralph', label: 'Ralph' },
]

const HISTORY_ICON = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <path d="M4 5h16v11H8l-4 4V5Z" />
  </svg>
)

const SEARCH_ICON = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="m20 20-4.35-4.35" strokeLinecap="round" />
  </svg>
)

// Busca local, sobre as sessões já hidratadas — não existe endpoint de busca (README, FASE 07,
// seção 5). Normaliza para NFD e remove diacríticos, para ignorar acentuação e caixa.
function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

function isFlowFilter(value: string | null): value is FlowFilter {
  return value === 'simple' || value === 'ralph'
}

/**
 * Lista central de chats (README, FASE 07, seção 5) — sem barra lateral. Busca e filtro de
 * fluxo vivem na URL (`?q=` e `?fluxo=`), para que o link seja compartilhável e o botão
 * "voltar" do navegador funcione.
 */
export function HistoryListPage(): JSX.Element {
  const { items, pendingCount, isLoadingIds, error, failedIds, reload } = useSessionList()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const listRef = useRef<HTMLUListElement>(null)

  const query = searchParams.get('q') ?? ''
  const flow: FlowFilter = isFlowFilter(searchParams.get('fluxo')) ? (searchParams.get('fluxo') as FlowFilter) : 'all'

  function setQuery(value: string): void {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value) next.set('q', value)
        else next.delete('q')
        return next
      },
      { replace: true },
    )
  }

  function setFlow(value: FlowFilter): void {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value !== 'all') next.set('fluxo', value)
        else next.delete('fluxo')
        return next
      },
      { replace: true },
    )
  }

  const filtered = useMemo(() => {
    const normalizedQuery = normalize(query.trim())
    return items.filter((item) => {
      if (flow !== 'all' && item.flow !== flow) return false
      if (normalizedQuery && !normalize(item.fullQuestion).includes(normalizedQuery)) return false
      return true
    })
  }, [items, query, flow])

  const totalTokens = items.reduce((sum, item) => sum + item.totalTokens, 0)

  // Navegação por teclado entre cards (README, FASE 07, seção 5): Tab já funciona por ser uma
  // lista de `<a>`; ↑/↓ movem o foco explicitamente entre eles.
  function handleListKeyDown(event: KeyboardEvent<HTMLUListElement>): void {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    const links = Array.from(event.currentTarget.querySelectorAll<HTMLAnchorElement>('a'))
    const currentIndex = links.indexOf(document.activeElement as HTMLAnchorElement)
    if (currentIndex === -1 || links.length === 0) return
    event.preventDefault()
    const step = event.key === 'ArrowDown' ? 1 : -1
    const nextIndex = (currentIndex + step + links.length) % links.length
    links[nextIndex]?.focus()
  }

  if (error) {
    return (
      <PageContainer width="content">
        <ErrorState error={error} onRetry={reload} />
      </PageContainer>
    )
  }

  const hasAnySession = !isLoadingIds && (items.length > 0 || failedIds.length > 0)
  const isEmptyHistory = !isLoadingIds && pendingCount === 0 && items.length === 0 && failedIds.length === 0

  return (
    <PageContainer width="content">
      <div className={styles.header}>
        <h1 className={styles.title}>Histórico</h1>
        {hasAnySession ? (
          <p className={styles.subtitle}>
            {items.length} {items.length === 1 ? 'conversa' : 'conversas'} · {formatTokens(totalTokens)} tokens
          </p>
        ) : null}
      </div>

      {hasAnySession ? (
        <div className={styles.controls}>
          <input
            type="search"
            aria-label="Buscar no histórico"
            placeholder="Buscar…"
            className={styles.search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <SegmentedControl ariaLabel="Filtrar por fluxo" value={flow} onChange={setFlow} options={FLOW_OPTIONS} />
        </div>
      ) : null}

      {isLoadingIds || (items.length === 0 && pendingCount > 0) ? (
        <div className={styles.list}>
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} height="4.5rem" radius="var(--radius-lg)" />
          ))}
        </div>
      ) : isEmptyHistory ? (
        <EmptyState
          icon={HISTORY_ICON}
          title="Nenhuma conversa ainda"
          action={<Button onClick={() => navigate(ROUTES.home)}>Fazer uma pergunta</Button>}
        />
      ) : filtered.length === 0 && failedIds.length === 0 ? (
        <EmptyState
          icon={SEARCH_ICON}
          title={`Nada encontrado para "${query}"`}
          action={
            <Button variant="secondary" onClick={() => setQuery('')}>
              Limpar busca
            </Button>
          }
        />
      ) : (
        <>
          <ul ref={listRef} className={styles.list} onKeyDown={handleListKeyDown}>
            {filtered.map((item) => (
              <SessionCard key={item.id} session={item} />
            ))}
            {failedIds.map((id) => (
              <li key={id} className={styles.failedCard}>
                Sessão {id} — não foi possível carregar
              </li>
            ))}
          </ul>
          {pendingCount > 0 ? (
            <p className={styles.pending} aria-live="polite">
              carregando {items.length} de {items.length + pendingCount}…
            </p>
          ) : null}
        </>
      )}
    </PageContainer>
  )
}
