import { useState } from 'react'
import type { ReactNode } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { IconButton } from '@/components/primitives/IconButton'
import { Switch } from '@/components/primitives/Switch'
import { SegmentedControl } from '@/components/primitives/SegmentedControl'
import { Card } from '@/components/primitives/Card'
import { Badge } from '@/components/primitives/Badge'
import { Tag } from '@/components/primitives/Tag'
import { Spinner } from '@/components/primitives/Spinner'
import { Skeleton } from '@/components/primitives/Skeleton'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { StatItem } from '@/components/primitives/StatItem'
import { Tooltip } from '@/components/primitives/Tooltip'
import { Divider } from '@/components/primitives/Divider'
import { Markdown } from '@/components/markdown/Markdown'
import { Composer } from '@/components/chat/Composer'
import { MessageStats } from '@/components/chat/MessageStats'
import { PhaseTag } from '@/components/chat/PhaseTag'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { FinalAnswerCard } from '@/components/chat/FinalAnswerCard'
import { ChatScroller } from '@/components/chat/ChatScroller'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import styles from './ComponentsGalleryPage.module.css'

const MARKDOWN_SAMPLE = `## Exemplo de Markdown

Um parágrafo comum com **negrito**, *itálico* e \`código inline\`.

- Item de lista
- Segundo item
  - Subitem

| Coluna A | Coluna B |
|---|---|
| 1 | 2 |
| 3 | 4 |

\`\`\`ts
function soma(a: number, b: number): number {
  return a + b
}
\`\`\`

> Uma citação de exemplo.

[Link de exemplo](https://example.com)
`

const SAMPLE_STATS: MessageStatsView = {
  modelName: 'openai/gpt-4o-mini',
  tokensInput: 420,
  tokensOutput: 118,
  totalTokens: 6040,
  inferenceTimeMs: 812,
  contextId: 'ctx_ab12cd34ef56',
  contextSize: 1834,
  timestamp: '2026-09-11T23:18:06.320000+00:00',
}

function Section({ title, children }: { title: string; children: ReactNode }): JSX.Element {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children}
    </section>
  )
}

/**
 * Catálogo de desenvolvimento do design system — mostra cada componente em todas as suas
 * variantes e estados. Só é registrado quando `VITE_ENABLE_DEBUG_PANEL=true` (README, FASE 03).
 * É onde se verifica o sistema visual nos dois temas e onde as próximas fases conferem reuso.
 */
export function ComponentsGalleryPage(): JSX.Element {
  const [segmentValue, setSegmentValue] = useState<'chat' | 'graph'>('chat')
  const [switchOn, setSwitchOn] = useState(false)
  const [composerValue, setComposerValue] = useState('')

  return (
    <PageContainer width="wide">
      <h1>Catálogo de componentes</h1>

      <Section title="Button">
        <div className={styles.row}>
          <Button variant="primary">Primário</Button>
          <Button variant="secondary">Secundário</Button>
          <Button variant="ghost">Terciário</Button>
          <Button variant="danger">Destrutivo</Button>
        </div>
        <div className={styles.row}>
          <Button size="sm">Pequeno</Button>
          <Button size="md">Médio</Button>
          <Button size="lg">Grande</Button>
          <Button loading>Carregando</Button>
          <Button disabled>Desabilitado</Button>
        </div>
      </Section>

      <Section title="IconButton">
        <div className={styles.row}>
          <IconButton
            aria-label="Adicionar"
            variant="primary"
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3v10M3 8h10" />
              </svg>
            }
          />
          <IconButton
            aria-label="Configurações"
            variant="secondary"
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="8" cy="8" r="3" />
              </svg>
            }
          />
          <IconButton
            aria-label="Carregando"
            loading
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16">
                <circle cx="8" cy="8" r="3" />
              </svg>
            }
          />
        </div>
      </Section>

      <Section title="Switch">
        <div className={styles.row}>
          <Switch checked={switchOn} onChange={setSwitchOn} label="Alternar exemplo" />
          <Switch checked disabled onChange={() => undefined} label="Desabilitado ligado" />
        </div>
      </Section>

      <Section title="SegmentedControl">
        <SegmentedControl
          ariaLabel="Modo de visualização"
          value={segmentValue}
          onChange={setSegmentValue}
          options={[
            { value: 'chat', label: 'Modo chat' },
            { value: 'graph', label: 'Modo gráfico' },
          ]}
        />
      </Section>

      <Section title="Card">
        <div className={styles.row}>
          <Card elevation="flat" padding="md">
            Flat
          </Card>
          <Card elevation="sm" padding="md">
            Sombra sm
          </Card>
          <Card elevation="md" padding="md" interactive>
            Interativo
          </Card>
        </div>
      </Section>

      <Section title="Badge e Tag">
        <div className={styles.row}>
          <Badge tone="neutral">Neutro</Badge>
          <Badge tone="accent">Corrente</Badge>
          <Badge tone="success">Aprovado</Badge>
          <Badge tone="warning">Reprovado</Badge>
          <Badge tone="danger">Erro</Badge>
          <Badge tone="context">Contexto</Badge>
          <Tag title="context_id completo: ctx_ab12cd34ef56">ctx_ab1</Tag>
        </div>
      </Section>

      <Section title="Spinner e Skeleton">
        <div className={styles.row}>
          <Spinner size="sm" />
          <Spinner size="md" />
        </div>
        <div className={styles.stack}>
          <Skeleton width="60%" height="1.2em" />
          <Skeleton lines={3} height="0.9em" />
        </div>
      </Section>

      <Section title="EmptyState e ErrorState">
        <div className={styles.row}>
          <EmptyState
            icon={
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="4" y="4" width="16" height="16" rx="2" />
              </svg>
            }
            title="Nenhum chat ainda"
            description="Inicie uma pergunta para ver o histórico aqui."
            action={<Button size="sm">Nova pergunta</Button>}
          />
          <ErrorState
            error={{ userMessage: 'Não foi possível carregar esta sessão.', message: 'HTTP 500: falha no provedor' }}
            onRetry={() => undefined}
          />
        </div>
      </Section>

      <Section title="StatItem e Tooltip">
        <div className={styles.row}>
          <StatItem label="Modelo" value="gpt-4o-mini" />
          <StatItem label="Contexto" value="1.834 tokens" tone="context" />
          <Tooltip content="Dica de exemplo com 400ms de atraso">
            <Button variant="ghost" size="sm">
              Passe o mouse
            </Button>
          </Tooltip>
        </div>
      </Section>

      <Section title="Divider">
        <Divider />
      </Section>

      <Section title="Markdown">
        <Card padding="lg">
          <Markdown content={MARKDOWN_SAMPLE} />
        </Card>
      </Section>

      <Section title="Composer">
        <Composer
          value={composerValue}
          onChange={setComposerValue}
          onSubmit={() => setComposerValue('')}
          placeholder="Digite sua pergunta…"
        />
      </Section>

      <Section title="MessageStats">
        <MessageStats stats={SAMPLE_STATS} layout="inline" />
        <div className={styles.panelSpacing}>
          <MessageStats stats={SAMPLE_STATS} layout="panel" />
        </div>
      </Section>

      <Section title="PhaseTag">
        <div className={styles.row}>
          <PhaseTag phase="B2" subtype="verify_pass" taskId="T1" />
          <PhaseTag phase="B2" subtype="verify_fail" taskId="T1" />
          <PhaseTag phase="B1" subtype="reset" />
          <PhaseTag phase="C2" subtype="replan" />
        </div>
      </Section>

      <Section title="MessageBubble">
        <div className={styles.stack}>
          <MessageBubble role="user" content="Quais são os números primos entre 0 e 20?" />
          <MessageBubble
            role="assistant"
            content="Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19."
            stats={SAMPLE_STATS}
            header={<PhaseTag phase="B1" subtype="reasoning" taskId="T1" />}
          />
          <MessageBubble
            role="assistant"
            content="Tentativa reprovada — corrigindo com o feedback."
            tone="warning"
            header={<PhaseTag phase="B2" subtype="verify_fail" taskId="T1" />}
          />
          <MessageBubble role="system" content="Contexto reinicializado — janela ctx_9f8e7d6c" />
        </div>
      </Section>

      <Section title="FinalAnswerCard">
        <FinalAnswerCard
          content="Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19."
          stats={SAMPLE_STATS}
        />
      </Section>

      <Section title="ChatScroller">
        <div className={styles.scrollArea}>
          <ChatScroller contentKey="galeria">
            {Array.from({ length: 20 }, (_, index) => (
              <p key={index}>Linha de exemplo {index + 1}</p>
            ))}
          </ChatScroller>
        </div>
      </Section>

      <Section title="TypingIndicator">
        <TypingIndicator />
      </Section>
    </PageContainer>
  )
}
