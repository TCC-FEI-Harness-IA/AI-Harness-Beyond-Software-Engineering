# FASE 07 — Histórico de chats

> Pré-requisito: FASES 01 a 06 concluídas e `feature_front/README.md` lido por completo —
> em especial a seção 3.5, que descreve a diferença entre o evento ao vivo e a mensagem
> persistida, e a seção 6.2, que fixa a arquitetura de "um view-model, duas fontes".

---

## 1. Objetivo

Entregar as duas telas de histórico:

1. **Lista de chats** — todos os chats listados de maneira **centralizada na tela**, com o
   **input do usuário** como resumo, limitado em caracteres.
2. **Detalhe de um chat** — com **menu lateral** listando os chats do histórico de forma reduzida,
   e o conteúdo renderizado **idêntico** ao da inferência ao vivo — **inclusive com Modo Chat e
   Modo Gráfico**.

O trabalho pesado desta fase **não é visual**: é a reconstrução fiel de uma sessão persistida no
view-model `ThinkingRun`/`SimpleRun`. Se essa reconstrução estiver certa, as telas são uma
composição de componentes que já existem.

---

## 2. Escopo

**Entra nesta fase**

- `src/domain/services/deriveSubtype.ts`
- `src/domain/services/sessionToThinkingRun.ts`
- `src/domain/services/sessionToSimpleRun.ts`
- `src/domain/services/sessionSummary.ts`
- `src/hooks/useSessionList.ts`, `src/hooks/useSession.ts`
- `src/features/history/` — `HistoryListPage`, `HistoryDetailPage`, `HistorySidebar`,
  `SessionCard`
- Uso da prop `sidebar` do `AppShell` (deixada pronta na FASE 01)

**Não entra**

- Qualquer componente visual novo de conteúdo. As telas de detalhe usam `RalphView` (FASE 05/06) e
  `SimpleChatView` (FASE 04) **sem modificação**. Se algo não encaixar, a correção é generalizar o
  componente original por prop — não criar uma variante "de histórico"
  (regra de reuso 3 do README)
- Qualquer alteração no backend

---

## 3. A reconstrução da sessão

### 3.1 `deriveSubtype.ts`

Implementa **exatamente** a tabela da seção 3.5 do README:

```ts
export interface DerivedStepKind {
  type: EventType
  subtype: EventSubtype
}

export const deriveStepKind = (
  message: SessionMessageDocument,
  context: { laterMessages: readonly SessionMessageDocument[] },
) => DerivedStepKind | null   // null = a mensagem não vira passo (é a pergunta do usuário)
```

Regras, na ordem:

1. `phase === 'DIRECT'` → `null` (o fluxo baseline não tem passos de pensamento).
2. `source === 'user'` → `null` (é a pergunta; ela vira `run.question`).
3. Aplica a tabela `(phase, source) → subtype`.
4. Para `phase === 'B2'`, decide `verify_pass` vs `verify_fail`:
   - **primário:** `parseDecision(content)` da FASE 05 — o marcador
     `**Decisão:** \`approved|reproved\`` gerado pelo template fixo do backend. **Reuse a função,
     não reimplemente.**
   - **fallback:** se existe outra mensagem `B2` com o mesmo `task_id` em `laterMessages`, é
     `verify_fail`; senão, `verify_pass`.
5. Para `phase === 'C3'` → `{ type: 'result', subtype: 'compile' }`. Para todo o resto,
   `type: 'thinking'`.
6. Combinação `(phase, source)` não prevista → `{ type: 'thinking', subtype: 'reasoning' }` e um
   aviso no console. Nunca lança, nunca descarta a mensagem.

### 3.2 O passo `execute` sintetizado

O evento `execute` **não é persistido** (seção 3.5 do README). Sem ele, a linha do tempo do
histórico teria um ponto a menos por tarefa do que a ao vivo — e o requisito é que as telas sejam
idênticas.

**Regra obrigatória:** para cada mensagem `B1`/`system` (o `reset`), sintetize imediatamente depois
um passo `execute` com:

- `content`: o bloco da tarefa correspondente, extraído do conteúdo da mensagem `A2`
  (ou `C2`) com `parseTasksFromMarkdown` (FASE 05) e casado pelo `task_id`. Se a tarefa não for
  encontrada, use um conteúdo mínimo `### {task_id}`.
- `inferenceTimeMs: 0`, `tokensInput/Output: 0` — é etapa programática, e marcá-la com custo
  falsearia as estatísticas.
- `contextId`/`contextSize` copiados do `reset`.
- `id` seguindo a mesma fórmula da FASE 05, ocupando a posição `order` correta.

Comente no código **por que** esse passo é sintetizado, citando a limitação do contrato. É o tipo
de decisão que, sem explicação, parece um bug.

### 3.3 `sessionToThinkingRun.ts`

```ts
export const sessionToThinkingRun = (document: SessionDocument): ThinkingRun
```

**Estratégia obrigatória: reuse o reducer.** Não escreva uma segunda implementação da agregação de
tarefas, tentativas e totais — isso garantiria divergência entre as duas telas com o tempo.

```
SessionDocument
  → ordena messages por `order`
  → para cada mensagem: deriveStepKind + síntese de `execute`
  → converte cada uma em um ReasoningEventDTO equivalente
  → alimenta reasoningRunReducer, na ordem
  → aplica os dados que só o documento tem (totais reais, degradações, status, timestamps)
```

A conversão mensagem → `ReasoningEventDTO`:

| Campo do evento | Origem no documento |
|---|---|
| `type`, `subtype` | `deriveStepKind` |
| `phase` | `message.phase` |
| `task` | `message.task_id` ?? (`A1`/`A2` → `setup`; `C*` → `synthesis`) |
| `session_id` | `document.id` |
| `content` | `message.content` |
| `total_tokens` | **acumulado progressivo** — some `message.total_tokens` das mensagens até aqui. O documento guarda o valor **por mensagem**, o evento ao vivo guarda o **acumulado da sessão**. Trocar um pelo outro quebra o gráfico de contexto da FASE 06 |
| `context_window.context_id` | `message.context_id` ?? `''` |
| `context_window.context_size` | **não existe no documento** — reconstrua somando `total_tokens` das mensagens com o **mesmo `context_id`**, na ordem. É exatamente o que a `ContextWindow` do backend faz, e é o que reproduz a serra dentada |
| `inference_time_ms` | `message.inference_time_ms` |

Depois de rodar o reducer, sobrescreva com os dados autoritativos do documento:

- `run.question` ← `document.user_question`
- `run.modelName` ← `document.model_name`
- `run.finalAnswer` ← `document.final_answer` (o campo do documento vence o conteúdo de C3)
- `run.status` ← `document.status` mapeado para `RunStatus`
- `run.totals.totalTokens` ← `document.totals.total_tokens`
- `run.totals.inferenceTimeMs` ← `document.totals.inference_time_ms`
- `run.totals.llmCalls` ← `document.totals.total_llm_calls`
- `run.totals.wallTimeMs` ← `document.totals.wall_time_ms` (só existe no histórico)
- `run.degradations` ← `document.degradations` convertidas
- Cada `ThinkingStep.timestamp` ← `message.timestamp`

### 3.4 `sessionToSimpleRun.ts`

Muito mais simples: uma sessão `flow === 'DIRECT'` tem duas mensagens (pergunta e resposta).

- A mensagem `user` vira `SimpleMessage` de `role: 'user'`.
- A mensagem `llm_agent` vira `role: 'assistant'`, com `MessageStatsView` preenchido a partir dela
  (`tokens_input`, `tokens_output`, `inference_time_ms`, `model_name`, `timestamp`).
- Sessões `failed` com uma única mensagem (existem várias em
  `apps/backend/data/sessions/`) produzem um `SimpleRun` com só a pergunta e
  `status: 'failed'` — a tela precisa mostrar "esta execução falhou", não uma tela vazia.

### 3.5 Roteador de reconstrução

```ts
export const sessionToRun = (document: SessionDocument):
  | { kind: 'simple'; run: SimpleRun }
  | { kind: 'ralph'; run: ThinkingRun }
```

A decisão é pelo `document.flow`: `'DIRECT'` → simples; qualquer outro valor → Ralph. É esse tipo
discriminado que a tela de detalhe consome para escolher entre `SimpleChatView` e `RalphView`.

---

## 4. Carregamento da lista — a parte chata, feita direito

`GET /v1/sessions` devolve **apenas ids** (seção 3.3 do README). O resumo exigido é o input do
usuário. Logo, é necessário buscar cada sessão. Implemente assim, e não de outro jeito:

### `useSessionList`

```ts
interface SessionSummaryView {
  id: string
  question: string          // já truncado, via truncate() + env.historySummaryMaxChars
  fullQuestion: string
  flow: 'simple' | 'ralph'
  status: SessionStatus
  createdAt: string
  totalTokens: number
  messageCount: number
}

interface UseSessionList {
  items: SessionSummaryView[]       // cresce conforme as sessões chegam
  pendingCount: number
  isLoadingIds: boolean
  error: AppError | null
  failedIds: string[]
  reload: () => void
}
```

**Requisitos:**

1. Busca os ids primeiro. Falha aqui → `ErrorState` na tela inteira, com "Tentar de novo".
2. Hidrata os documentos com um **pool de concorrência** de `env.historyFetchConcurrency`
   requisições simultâneas — nunca um `Promise.all` de N chamadas (com 200 sessões isso derruba o
   navegador e o servidor de desenvolvimento).
3. **Render progressivo:** cada sessão que chega aparece na lista imediatamente; o resto continua
   como `Skeleton`. A tela nunca fica parada esperando o lote inteiro.
4. **Falha individual não derruba a lista:** um id que responde `404`/`400` entra em `failedIds` e
   é exibido como um card em estado de erro, discreto, com o id. Os outros continuam.
5. **Cache em memória** (um `Map` em `useRef` ou um Context pequeno) das sessões já buscadas,
   para que voltar do detalhe para a lista não refaça tudo. O cache também serve à barra lateral
   do detalhe e ao próprio `useSession` — buscar a mesma sessão duas vezes é desperdício visível.
6. **Ordenação:** por `created_at` decrescente (mais recente primeiro). Como a data só chega com o
   documento, ordene **progressivamente**, reordenando conforme as sessões chegam — mas com
   transição suave (`transition: transform`), para os cards não pularem bruscamente.
7. `AbortController` para tudo; desmontar cancela as requisições pendentes.

> Deixe um comentário no código registrando que a causa desse trabalho todo é o endpoint devolver
> só ids, e que um `GET /v1/sessions` com resumo resolveria — é informação útil para a próxima
> evolução do backend. **Não altere o backend nesta feature.**

---

## 5. Tela de lista

Requisito: *"deve ter a página principal, listando todos os chats de maneira centralizada na
tela"* — sem barra lateral.

```
<AppShell>                                   ← sem sidebar
  <PageContainer width="content">
    Histórico                                ← --text-xl
    24 conversas · 312.480 tokens            ← --text-sm, --color-text-secondary

    [ Buscar… ]  [ Todos | Simples | Ralph ]  ← busca + SegmentedControl (FASE 03)

    ┌──────────────────────────────────────────────────┐
    │ ◎ Ralph   Quais são todos os números primos e…   │   ← SessionCard
    │           há 2 horas · 15.284 tokens · 15 msgs   │
    └──────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────┐
    │ ⚡ Simples  Me conte uma piada                     │
    │           ontem · 156 tokens · 2 msgs  ⚠ falhou  │
    └──────────────────────────────────────────────────┘
```

### `SessionCard`

- `Card interactive as="li"` dentro de uma `<ul>` — lista semântica, não `div`s.
- **O resumo é o input do usuário**, truncado com `truncate()` e
  `env.historySummaryMaxChars`, em **uma linha** com `text-overflow: ellipsis`. O texto completo
  fica no `title`.
- Ícone + `Badge` do fluxo (`Ralph` / `Simples`), com as cores da seção 8.3 do README.
- Metadados em `--text-xs`: data relativa (`formatRelative`), tokens (`formatTokens`), contagem de
  mensagens. Status diferente de `completed` vira um `Badge` (`degraded` laranja, `failed`
  vermelho, `running` azul).
- Clicar navega para `/historico/:sessionId` **sem refresh**.
- Navegação por teclado: Tab entre cards, Enter abre; ↑/↓ movem o foco entre cards.

### Busca e filtro

Busca **local**, sobre as sessões já hidratadas (não existe endpoint de busca): filtra por
substring no `user_question`, sem diferenciar acentos nem caixa (`String.prototype.localeCompare`
com `sensitivity: 'base'`, ou normalização `NFD`). O filtro de fluxo usa o `SegmentedControl` já
existente. Ambos são estado de URL (`?q=` e `?fluxo=`), para que o link possa ser compartilhado e o
botão "voltar" do navegador funcione.

### Estados

| Estado | Tela |
|---|---|
| Carregando ids | Seis `Skeleton` de card |
| Hidratando | Cards prontos + skeletons para os pendentes + "carregando 12 de 24…" |
| Vazio | `EmptyState`: "Nenhuma conversa ainda" + botão "Fazer uma pergunta" → home |
| Busca sem resultado | `EmptyState`: "Nada encontrado para '…'" + "Limpar busca" |
| Erro na listagem | `ErrorState` + "Tentar de novo" |

---

## 6. Tela de detalhe

Requisito: *"quando clica em um chat histórico, deve existir um menu lateral, listando os chats do
histórico de maneira reduzida"*.

```
<AppShell sidebar={<HistorySidebar … />}>
  ┌──────────┬───────────────────────────────────────────────┐
  │ Histórico│  [ Gráfico | Chat ]        ← ViewModeSwitch   │
  │ ──────── │                              (só no Ralph)    │
  │ ▸ Quais  │                                               │
  │   são os │   <RalphView run={run} isLive={false} />       │
  │   número…│          ou                                   │
  │ ▸ Me con…│   <SimpleChatView run={run} isLive={false} />  │
  │ ▸ Compar…│                                               │
  └──────────┴───────────────────────────────────────────────┘
```

### `HistorySidebar`

- Largura `--sidebar-width`, fundo `--color-surface-sunken`, *hairline* à direita, rolável
  independentemente, `position: sticky` abaixo da `TopBar`.
- Cada item mostra o input do usuário truncado com
  `env.historySidebarSummaryMaxChars` (mais curto que o do card) e um ícone de fluxo. **Uma
  linha só.**
- O item ativo tem fundo `--color-accent-soft` e texto `--color-accent` — é o único uso de cor na
  barra.
- É uma `<nav>` com `aria-label="Conversas"` e `<ul>`; o item ativo tem `aria-current="page"`.
- Reusa o cache de `useSessionList`: ao chegar pelo card, a lista **já está em memória** e a barra
  aparece instantaneamente. Ao entrar direto pela URL, ela carrega com skeletons enquanto o
  conteúdo principal já renderiza.
- Trocar de conversa pela barra **não recarrega a página** e mantém o modo de visualização.
- Abaixo de 1024px, vira gaveta aberta por um botão na `TopBar`, com `Esc` para fechar e foco
  preso enquanto aberta.

### O conteúdo

É aqui que a arquitetura da seção 6.2 do README paga:

```tsx
const state = useSession(sessionId)

if (state.status === 'loading') return <HistoryDetailSkeleton />
if (state.status === 'error')   return <ErrorState error={state.error} onRetry={state.reload} />

const result = sessionToRun(state.data)

return result.kind === 'ralph'
  ? <RalphView run={result.run} isLive={false} />
  : <SimpleChatView run={result.run} isLive={false} />
```

**Nada além disso.** Se essa tela precisar de um `if` a mais para o histórico ficar correto, o
problema está na reconstrução ou na `RalphView` — corrija lá, não aqui.

O interruptor de modo aparece para sessões Ralph e **respeita a mesma preferência** persistida da
FASE 05. Para sessões `DIRECT` ele não aparece — não há dois modos a alternar.

### Estados

| Estado | Tela |
|---|---|
| Carregando | Skeleton no conteúdo; a barra lateral já aparece se estiver em cache |
| `404` | `EmptyState`: "Esta conversa não existe mais" + "Voltar ao histórico" |
| `400` | `ErrorState`: "O registro deste chat está corrompido" + o id, para depuração |
| Sessão `failed` sem resposta | O conteúdo que existe + um aviso "Esta execução falhou antes de terminar" |
| Sessão `running` | O conteúdo salvo até agora + aviso "Esta execução ainda está em andamento"; **não** tente reconectar ao WebSocket — não existe endpoint para retomar |

---

## 7. Testes exigidos

A prioridade é a reconstrução. Use os arquivos reais de `apps/backend/data/sessions/` como
*fixtures* (copie para `src/test/fixtures/sessions/`).

| Arquivo | O que verifica |
|---|---|
| `deriveSubtype.test.ts` | Cada linha da tabela da seção 3.5 do README; `B2` com `approved` → `verify_pass`; com `reproved` → `verify_fail`; sem marcador e com outro `B2` depois → `verify_fail`; combinação desconhecida → fallback sem lançar. |
| `sessionToThinkingRun.test.ts` | **O teste central da fase.** Com `sess_c848291dc9d34eeea33872d4108e3295.json` (15 mensagens, 2 tarefas, concluída): produz 2 `TaskTimeline`, cada uma com 1 tentativa aprovada; `finalAnswer` igual ao `final_answer` do documento; `status: 'completed'`; `totals` iguais aos do documento; `contextCount` igual ao número de `context_id` distintos; `context_size` reconstruído **zera** em cada troca de contexto; `total_tokens` dos passos é **monotônico não decrescente**. |
| idem | O passo `execute` é sintetizado: a tarefa `T1` tem os mesmos subtipos, na mesma ordem, que uma execução ao vivo equivalente. |
| idem | Sessão `A1` com `status: 'failed'` e 1–2 mensagens não lança e produz um `run` parcial com `status: 'failed'`. |
| **`parity.test.ts`** | **O teste que prova o requisito.** Pegue a sequência de eventos ao vivo derivada da fixture, rode pelo `reasoningRunReducer`; rode a mesma sessão por `sessionToThinkingRun`; compare os dois `ThinkingRun`, ignorando só os campos que **só existem** em um dos lados (`timestamp`, `wallTimeMs`). Eles precisam ser **estruturalmente iguais**: mesmos ids de passo, mesma ordem, mesmas tarefas, mesmas tentativas, mesmos totais. |
| `sessionToSimpleRun.test.ts` | Sessão `DIRECT` completa → 2 mensagens com estatísticas; sessão `DIRECT` `failed` com 1 mensagem → só a pergunta, `status: 'failed'`. |
| `useSessionList.test.tsx` | Respeita o limite de concorrência (com um duplo de `fetch` que conta chamadas simultâneas); render progressivo; uma sessão que falha não derruba as outras; o cache evita refetch ao remontar; abortar no unmount. |
| `HistoryListPage.test.tsx` | Cards mostram o input truncado; clicar navega para o detalhe; a busca filtra ignorando acentos; o filtro de fluxo funciona; busca e filtro estão na URL; lista vazia mostra o `EmptyState` com ação. |
| `HistoryDetailPage.test.tsx` | Sessão Ralph renderiza `RalphView` com o interruptor; sessão `DIRECT` renderiza `SimpleChatView` **sem** interruptor; a barra lateral marca o item ativo com `aria-current`; trocar de conversa pela barra não desmonta o `AppShell`; `404` mostra a mensagem certa. |

---

## 8. Verificação manual

1. Rode pelo menos 3 perguntas (2 no Ralph, 1 simples) para gerar histórico.
2. Abra `/historico`: os chats aparecem centralizados, com o input do usuário truncado como resumo.
   **Não há barra lateral nesta tela.**
3. Clique em um chat Ralph: **agora** a barra lateral existe, com os chats em forma reduzida, e o
   atual destacado.
4. Compare lado a lado com a execução ao vivo do mesmo tipo de pergunta: **as telas são a mesma
   coisa**, com o conteúdo já todo renderizado. Modo Chat e Modo Gráfico funcionam nos dois.
5. No Modo Gráfico do histórico, confirme que a serra dentada do contexto está desenhada —
   é o dado reconstruído, e é onde um erro apareceria na hora.
6. Troque de conversa pela barra lateral: a troca é instantânea, sem refresh, e o modo escolhido
   permanece.
7. Abra `/historico/sess_inexistente`: mensagem clara e caminho de volta.
8. Com o backend contendo uma sessão `failed` de uma mensagem só: a tela abre e explica o que
   aconteceu, sem quebrar.

---

## 9. Critérios de aceite

1. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro nem aviso.
2. O teste `parity.test.ts` passa — histórico e ao vivo produzem o mesmo `ThinkingRun`.
3. A tela de lista **não** tem barra lateral; a de detalhe **tem**.
4. O resumo de cada chat é o input do usuário, truncado pelo limite de `env`, em uma linha.
5. As telas de detalhe usam `RalphView` e `SimpleChatView` **sem nenhuma modificação** feita nesta
   fase. `git diff` da fase não toca em `src/features/ralph/RalphView.tsx` nem em
   `src/features/simple-chat/SimpleChatView.tsx` — exceto para **generalizar** algo por prop, e,
   nesse caso, o ao vivo continua funcionando (os testes das FASES 04–06 continuam verdes).
6. A hidratação da lista respeita `env.historyFetchConcurrency` e nunca dispara N requisições de
   uma vez.
7. Nenhuma requisição é refeita ao navegar lista → detalhe → lista.
8. Nenhuma sessão corrompida ou falha derruba uma tela inteira.
9. Toda navegação acontece sem refresh.
10. `sessionToThinkingRun` e `sessionToSimpleRun` são funções puras: não importam React, não
    importam `src/api/`, e não lançam para nenhuma das fixtures reais.
