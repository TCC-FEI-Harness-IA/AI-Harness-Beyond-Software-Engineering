# FASE 05 — Ralph Loop Adaptado: stream, view-model e Modo Chat

> Pré-requisito: FASES 01 a 04 concluídas e `feature_front/README.md` lido por completo —
> em especial as seções 2 (fluxo do paper), 3.2 (contrato do WebSocket) e 6.2/6.3 (view-model).

---

## 1. Objetivo

Esta é a fase mais importante do frontend. Ela entrega:

1. **`useReasoningStream`** — o hook que consome `WS /v1/message/reasoning`.
2. **`reasoningRunReducer`** — a função pura que transforma a sequência de eventos no view-model
   `ThinkingRun`.
3. **Modo Chat** — a visualização do fluxo de pensamento mensagem a mensagem, no mesmo estilo do
   chat comum, **com a mensagem final destacada**.
4. **O interruptor de modo** na parte superior, que alterna entre Modo Chat e Modo Gráfico
   dinamicamente (o Modo Gráfico em si é a FASE 06; aqui ele entra como *placeholder*).

O `ThinkingRun` produzido aqui é o mesmo objeto que a FASE 06 desenha e que a FASE 07 reconstrói a
partir do histórico. **Errar o modelo aqui contamina as duas fases seguintes** — por isso o
reducer é especificado em detalhe e testado exaustivamente.

---

## 2. Escopo

**Entra nesta fase**

- `src/domain/types/thinkingRun.ts` — `ThinkingRun`, `ThinkingStep`, `TaskTimeline`,
  `TaskAttemptView`, `PhaseProgress`, `RunTotals`, `RunDegradation`, `RunError`
- `src/domain/services/reasoningRunReducer.ts`
- `src/domain/services/taskParser.ts`
- `src/hooks/useReasoningStream.ts`
- `src/features/ralph/RalphPage.tsx`, `RalphView.tsx`, `RalphChatMode.tsx`, `ViewModeSwitch.tsx`
- `src/state/ViewModeContext.tsx` (ou estado local elevado — ver seção 8)

**Não entra**

- O desenho da linha do tempo (FASE 06) — aqui `RalphGraphMode` é um *placeholder* que já recebe o
  `ThinkingRun` completo
- Histórico (FASE 07)

---

## 3. O view-model `ThinkingRun`

Use exatamente a forma da seção 6.3 do README. Detalhando os tipos que faltam:

```ts
export interface TaskAttemptView {
  index: number                       // 1-based
  reasoning: ThinkingStep | null      // o passo B.1 daquela tentativa
  verification: ThinkingStep | null   // o passo B.2 correspondente
  approved: boolean | null            // null enquanto a verificação não chegou
}

export interface PhaseProgress {
  /** Nó da trilha macro. 'B' agrega todo o loop de execução. */
  id: 'A1' | 'A2' | 'B' | 'C1' | 'C2' | 'C3'
  label: string
  status: 'pending' | 'active' | 'done' | 'skipped'
  stepCount: number
}

export interface RunTotals {
  totalTokens: number
  inferenceTimeMs: number
  llmCalls: number
  taskCount: number
  attemptCount: number
  contextCount: number       // quantas janelas de contexto foram abertas — métrica do paper
  wallTimeMs: number | null  // só existe no histórico
}

export interface RunDegradation {
  limit: string
  phase: ThinkingPhase
  taskId: string | null
  description: string
  occurredAt: string | null
}
```

### Regra de identidade dos passos (regra 10 do README)

`ThinkingStep.id` precisa ser **estável e determinístico** — ele é a `key` do React e a âncora dos
links entre Modo Chat e Modo Gráfico. Não use `crypto.randomUUID()`:

```
id = `${order}:${phase}:${subtype}:${taskId}`
```

`order` é o índice de chegada do evento (0-based), atribuído pelo reducer. A mesma fórmula é usada
pela FASE 07 sobre as mensagens persistidas, o que garante que um passo tem o **mesmo id** ao vivo
e no histórico.

---

## 4. `reasoningRunReducer` — a especificação

Função **pura**, sem React, sem rede:

```ts
export const createEmptyRun = (question: string, modelName: string): ThinkingRun

export const reasoningRunReducer = (run: ThinkingRun, action: RunAction): ThinkingRun

type RunAction =
  | { kind: 'event'; event: ReasoningEventDTO }
  | { kind: 'errorFrame'; frame: ReasoningErrorFrame }
  | { kind: 'failure'; error: AppError }
  | { kind: 'closed'; code: number }
```

**Regra geral: imutabilidade.** Nunca mute `run` nem seus arrays. Retorne objetos novos. Isso não
é preciosismo — o Modo Gráfico depende de identidade referencial para não reanimar tudo a cada
evento.

### 4.1 Ação `event` — passo a passo

Para **todo** evento, nesta ordem:

1. Cria o `ThinkingStep` com `order = run.steps.length`, convertendo `snake_case` → `camelCase`
   (esta é a única conversão de nomenclatura do app) e achatando `context_window` em
   `contextId`/`contextSize`.
2. Anexa a `steps`.
3. Atualiza `totals`:
   - `totalTokens = event.total_tokens` (**substitui**, não soma — o backend já manda o acumulado
     da sessão, e ele nunca decresce; somar duplicaria tudo);
   - `inferenceTimeMs += event.inference_time_ms`;
   - `llmCalls += 1` **somente se** `inference_time_ms > 0` (etapas programáticas — `reset`,
     `store`, `execute` — não são chamadas ao modelo);
   - `contextCount += 1` quando o `contextId` do evento **difere** do último visto.
4. Define `sessionId` na primeira vez que vir um (`run.sessionId ?? event.session_id`).
5. Aplica a regra específica do `subtype` (tabela abaixo).
6. Recalcula `phases` (seção 4.3).

| `subtype` | Efeito no `ThinkingRun` |
|---|---|
| `setup` (A1) | Nada além do passo. É a exibição dos critérios gerais. |
| `tasks` (A2) | Chama `parseTasksFromMarkdown(content)` e **cria** as `TaskTimeline` com `status: 'pending'` e `origin: 'A2'`, na ordem do conteúdo. |
| `reset` (B1) | Marca a tarefa `event.task` como `running`; acrescenta `event.context_window.context_id` a `task.contextIds`; **abre uma tentativa nova** (`attempts.push({ index: attempts.length + 1, reasoning: null, verification: null, approved: null })`) se e somente se ainda não houver tentativa aberta. |
| `execute` (B1) | Anexa o passo à tarefa. Se `task.title` ainda é `null`, extrai o título do conteúdo (o backend renderiza `### T1 — Título`). |
| `reasoning` (B1) | Preenche `reasoning` da tentativa aberta. Se **não houver** tentativa aberta (caso de retentativa dentro do mesmo contexto, que **não** emite `reset`), abre uma nova tentativa antes. |
| `verify_pass` (B2) | Fecha a tentativa com `approved: true`. |
| `verify_fail` (B2) | Fecha a tentativa com `approved: false` **e abre a tentativa seguinte**, porque o backend volta para B.1 **no mesmo contexto** — e é justamente isso que a UI precisa mostrar. |
| `store` (B3) | Marca a tarefa como `approved`. |
| `learn` (B4) | Apenas anexa o passo à tarefa. (Anotação para a FASE 06: é aqui que nasce a seta "aprendizados → próxima tarefa".) |
| `compile` em `C1` | Nada além do passo. |
| `replan` (C2) | Chama `parseTasksFromMarkdown` e **acrescenta** as tarefas novas com `origin: 'C2'`. **No topo da fila conceitual**, porque é o que o backend faz — mas a ordem de exibição segue a ordem de execução real, que é a ordem em que os eventos chegarem. Não reordene nada; o próprio stream já traz a sequência correta. |
| `compile` em `C3` | Define `finalAnswer = content` e, se `type === 'result'`, coloca `status = 'completed'`. |

**Eventos `type: 'degraded'`:** acrescenta a `degradations` (com `limit` extraído do conteúdo
quando possível, ou string vazia), marca `run.status = 'degraded'` e, se o evento tiver `task`
diferente de `setup`/`synthesis`, marca aquela tarefa como `degraded`. **O fluxo continua** — uma
degradação não encerra a execução.

**Eventos `type: 'error'`:** preenche `run.error` e coloca `status = 'failed'`. Os passos já
recebidos permanecem — nunca descarte o que foi mostrado.

### 4.2 Regras de robustez obrigatórias

O reducer **não pode assumir** que a sequência é perfeita. Uma conexão pode perder um frame ou o
backend pode evoluir. Portanto:

1. **Evento de uma tarefa desconhecida** (o `task` não está em `run.tasks`): crie a tarefa na hora,
   com `title: null` e `origin: 'A2'`. Nunca descarte o passo.
2. **`verify_pass` sem tentativa aberta:** crie uma tentativa fechada com `reasoning: null`.
3. **`store` sem tarefa:** ignore o efeito, mas mantenha o passo.
4. **`subtype` desconhecido** (a FASE 02 já mapeia para `reasoning`): o passo entra normalmente.
5. Nenhuma dessas situações lança exceção. O reducer **nunca lança** — ele degrada.

### 4.3 Cálculo de `phases`

A trilha macro tem 6 nós: `A1`, `A2`, `B`, `C1`, `C2`, `C3`. Regras:

- Um nó é `done` quando existe pelo menos um passo dele e o fluxo já avançou para um nó posterior.
- Um nó é `active` quando o **último passo recebido** pertence a ele.
- `B` engloba `B1`, `B2`, `B3`, `B4`; `stepCount` é a soma dos quatro.
- `C2` fica `skipped` quando a execução termina (`C3` recebido) sem nenhum passo `C2` — é o caminho
  feliz do paper, e a UI precisa mostrar que essa etapa **existia e não foi necessária**, não
  escondê-la.
- Quando um `replan` chega, `B` volta a `active` e `C1` volta a `done` (não a `pending`) — o loop
  do paper é cíclico e a trilha precisa refletir isso sem "desfazer" o passado.

---

## 5. `taskParser.ts`

Extrai a estrutura das tarefas do Markdown de A.2 e C.2. O backend renderiza cada tarefa assim
(formato fixo de template, não saída livre do modelo):

```markdown
### T1 — Identificar números primos no intervalo de 0 a 10

Nesta tarefa você deve…

**Entrada esperada:** as alternativas fornecidas

**Saída esperada:** lista de primos

**Critérios de aceite:**
- `T1-AC1`: Deve retornar a lista de números primos encontrados
- `T1-AC2`: Deve incluir uma breve explicação da regra
```

```ts
export interface ParsedTask {
  id: string
  title: string | null
  description: string | null
  expectedInput: string | null
  expectedOutput: string | null
  criteria: ParsedCriterion[]
}

export interface ParsedCriterion { id: string; text: string }

export const parseTasksFromMarkdown = (markdown: string): ParsedTask[]
export const parseTaskTitle = (markdown: string): string | null
export const parseDecision = (markdown: string): 'approved' | 'reproved' | null
export const parseCriterionEvaluations = (markdown: string): ParsedEvaluation[]
```

**Requisitos:**

1. **Tolerância acima de tudo.** É texto gerado por LLM através de um template: o formato é
   estável, mas não garantido. Nenhuma função lança — todas devolvem `null` ou array vazio quando
   não reconhecem o formato.
2. Divide as tarefas por cabeçalhos `###` cujo texto comece com um identificador no padrão
   `T<number>`. O separador entre blocos no backend é uma linha em branco dupla.
3. `parseDecision` procura `**Decisão:** \`approved\`` / `\`reproved\``. É o mesmo marcador que a
   FASE 07 usa para derivar `verify_pass`/`verify_fail` no histórico — **implemente aqui, uma vez
   só, e reuse lá**.
4. `parseCriterionEvaluations` lê as linhas `- \`T1-AC1\` — atendido: <justificativa>` /
   `— não atendido: …`, devolvendo `{ id, met, justification }`. A FASE 06 usa isso para mostrar
   quais critérios falharam em cada tentativa.
5. Funções puras, 100% testáveis com as strings reais das sessões salvas em
   `apps/backend/data/sessions/` — use-as como *fixtures*.

---

## 6. `useReasoningStream`

```ts
interface UseReasoningStream {
  run: ThinkingRun
  isStreaming: boolean
  start: (question: string) => void
  cancel: () => void
  reset: () => void
}

export const useReasoningStream = (config: RunConfig): UseReasoningStream
```

**Requisitos:**

1. Usa `useReducer` com `reasoningRunReducer`. **Toda** a lógica de estado está no reducer puro; o
   hook só liga o socket às ações.
2. `start` monta o payload com `buildInferencePayload` (o mesmo do fluxo simples — regra de reuso)
   e chama `openReasoningStream`.
3. Guarda o `ReasoningStreamHandle` em uma `ref`. `cancel()` e o *cleanup* do `useEffect` chamam
   `handle.close()`.
4. **Fechamento `1000` é sucesso.** Se o `status` ainda estiver `running` quando o código `1000`
   chegar (por exemplo, o `result` não veio), passe para `completed` mesmo assim — mas mantenha
   `finalAnswer: null`, para a UI poder dizer que a execução terminou sem resposta final.
5. `start` durante um streaming em andamento é **ignorado** — nunca abra duas conexões.
6. Desmontar durante o stream fecha o socket e não produz nenhum `setState` posterior.
7. **Throttle de render.** Os eventos podem chegar em rajada. Se a fase de testes mostrar
   engasgo, agrupe os `dispatch` com um *buffer* de 1 quadro (`requestAnimationFrame`) — mas
   **só se necessário**, e mantendo o reducer intocado. Não otimize antes de medir.

---

## 7. A tela do Ralph

### Hierarquia

```
RalphPage                 conecta rota + hook + config  (única que conhece rede)
└── RalphView             apresentação pura: { run, isLive, onStart?, onCancel?, onRetry? }
    ├── ViewModeSwitch    o interruptor, no topo
    ├── RalphChatMode     { run, isLive }        ← esta fase
    └── RalphGraphMode    { run, isLive }        ← placeholder; FASE 06
```

`RalphView` é **exatamente** o componente que a FASE 07 vai reutilizar, passando `isLive={false}`
e um `ThinkingRun` reconstruído. Ela não pode conter nenhuma referência a hook de rede, `useParams`
ou `env`.

### O que `isLive` controla — e só isso

| Aspecto | `isLive` | histórico |
|---|---|---|
| `Composer` no rodapé | visível | ausente |
| Auto-scroll | ligado | desligado (abre no topo) |
| Halo pulsante no passo corrente | sim | não |
| Botão "Cancelar execução" | visível enquanto `isStreaming` | ausente |
| `animateIn` no último passo | sim | não |

Nada além disso. Qualquer outra diferença entre ao vivo e histórico é um defeito.

---

## 8. O interruptor de modo

Requisito: *"deve existir um interruptor na parte superior do chat para poder mudar o estilo de
visualização de maneira dinâmica"*.

- Componente `ViewModeSwitch`, implementado com o `SegmentedControl` da FASE 03 (não crie um
  controle novo), com duas opções: **Gráfico** e **Chat**, cada uma com seu ícone.
- Posição: **topo da área de conteúdo**, centralizado, `position: sticky; top: var(--topbar-height)`
  com fundo translúcido e desfoque — acompanha a rolagem, como uma barra de ferramentas do macOS.
- **Troca instantânea, sem perder estado e sem interromper o stream.** Os dois modos leem o mesmo
  `ThinkingRun`; alternar é só trocar qual subárvore está montada. O socket não é tocado.
- A escolha persiste em `localStorage` (chave `tcc.viewMode`) e vale para as duas telas — ao vivo e
  histórico. Estado no `ViewModeContext`, para que a `TopBar` e as telas leiam do mesmo lugar.
- Transição: *cross-fade* + `scale(0.98 → 1)` em `--duration-base`, desligada sob reduced-motion.
- Acessibilidade: `SegmentedControl` já entrega `role="radiogroup"` + setas. Adicione um atalho
  de teclado `⌘/Ctrl + \` para alternar, anunciado por `title` no controle.
- O modo padrão na primeira visita é **Gráfico** — é o diferencial do trabalho e o que deve ser
  visto primeiro.

---

## 9. Modo Chat

Requisito: *"mostra mensagem a mensagem do fluxo de pensamento no mesmo estilo do chat comum,
porém deixando destacada a mensagem final"*.

### Estrutura

```
<ChatScroller contentKey={run.steps.length} isLive={isLive}>
  <MessageBubble role="user" content={run.question} />

  {run.steps.map(step => <ThinkingStepMessage key={step.id} step={step} … />)}

  {run.finalAnswer && <FinalAnswerCard content={run.finalAnswer} stats={runTotalsAsStats(run)} />}
  {isStreaming && <TypingIndicator />}
  {run.error && <ErrorState error={run.error} onRetry={onRetry} />}
</ChatScroller>
```

### `ThinkingStepMessage`

O único componente visual novo desta fase (em `src/features/ralph/`, não em `components/` — ele é
específico do Ralph). Decide a forma da mensagem a partir do `subtype`:

| Subtypes | Forma |
|---|---|
| `reasoning`, `setup`, `tasks`, `learn`, `compile` (C1), `replan` | `<MessageBubble role="assistant">` com `<PhaseTag>` no `header` e `<MessageStats layout="inline">` no rodapé |
| `verify_pass`, `verify_fail` | Mesma bolha, com `tone="success"`/`tone="warning"` (barra lateral colorida) e o `PhaseTag` correspondente |
| `reset`, `store`, `execute` | `<MessageBubble role="system">` — o separador fino com rótulo, **sem** bolha. São etapas programáticas; não podem ter o mesmo peso visual de um raciocínio |
| `type: 'degraded'` | Bolha com `tone="warning"` e um `Badge` "Degradação" — visível, mas sem alarme |
| `compile` em `C3` | **Não** vira bolha: vira o `FinalAnswerCard` no fim da lista |

Detalhes obrigatórios:

- **Todo** conteúdo passa por `<Markdown>` — requisito de renderização em Markdown.
- **Toda** mensagem traz suas estatísticas: modelo, tokens, tempo e, no Ralph, também o
  `context_size` e o `context_id` abreviado (é o dado que mostra o *fresh context* funcionando).
- Passos `reset` recebem tratamento especial de texto: em vez do markdown cru
  ("Contexto reinicializado para a tarefa `T1`…"), renderize o separador com o rótulo
  **"Contexto reinicializado · T1"** e um `Tag` com o novo `context_id`, em tom `context` (roxo).
  O conteúdo cru continua acessível no `title`.
- Agrupamento visual: passos consecutivos da mesma tarefa ficam mais próximos entre si
  (`--space-3`) do que de passos de outra tarefa (`--space-8`), e uma etiqueta discreta com o id
  da tarefa aparece na troca. É agrupamento por espaçamento, não por caixa — seção 8.1 do README.
- `animateIn` **só** no último passo, e só quando `isLive`.
- Memoize `ThinkingStepMessage` com `React.memo`: numa execução real chegam 15–40 passos, e sem
  isso cada evento re-renderiza todos os anteriores.

### Resposta final destacada

`FinalAnswerCard` (FASE 03) no fim da lista, com os totais da execução no rodapé:
tokens totais, tempo de inferência somado, número de chamadas, número de tarefas, número de
tentativas e número de janelas de contexto. Esse conjunto é o que permite comparar o harness com o
baseline — o requisito de "estatísticas gerais" no caso do Ralph significa **isto**.

Quando a execução termina degradada, o cartão ganha um `Badge tone="warning"` "Concluído com
degradação" e uma lista recolhível com as `degradations` (limite, fase, descrição).

---

## 10. Estados obrigatórios

| Estado | Tela |
|---|---|
| Idle (sem pergunta) | `EmptyState` + `Composer` focado |
| Conectando | Skeleton dos primeiros passos + "Conectando ao servidor…" |
| Streaming | Passos chegando + `TypingIndicator` + botão "Cancelar execução" |
| Concluído | `FinalAnswerCard` + totais |
| Degradado | Idem, com o aviso de degradação |
| Erro | `ErrorState` **preservando todos os passos já recebidos** + "Tentar de novo" |
| Cancelado | Aviso "Execução cancelada" + os passos recebidos + "Executar de novo" |

---

## 11. Testes exigidos

O grosso do esforço vai no reducer — ele é puro e é a peça de que as FASES 06 e 07 dependem.

| Arquivo | O que verifica |
|---|---|
| `reasoningRunReducer.test.ts` | **O núcleo.** Alimente o reducer com a sequência completa de eventos de uma execução real (derive-a de `apps/backend/data/sessions/sess_c848291dc9d34eeea33872d4108e3295.json`, que tem 15 mensagens, 2 tarefas e termina em C3) e verifique: 2 tarefas criadas em A2; cada uma com 1 tentativa aprovada; `finalAnswer` preenchido; `status: 'completed'`; `contextCount` igual ao número de `context_id` distintos; `totalTokens` igual ao último evento (**não** a soma); `llmCalls` contando só eventos com `inference_time_ms > 0`. |
| idem | `verify_fail` abre uma segunda tentativa na mesma tarefa e **não** cria contexto novo (o `context_id` continua igual — é a regra do paper que a UI precisa refletir). |
| idem | `replan` acrescenta tarefas com `origin: 'C2'` e devolve `B` ao estado `active`. |
| idem | Evento `degraded` marca `status: 'degraded'` sem interromper o processamento dos eventos seguintes. |
| idem | Evento `error` marca `failed` e **preserva** todos os passos anteriores. |
| idem | Robustez: evento de tarefa desconhecida cria a tarefa; `verify_pass` sem tentativa aberta não lança; `subtype` fora do enum entra como passo. |
| idem | Imutabilidade: o objeto `run` de entrada **não** é modificado (compare com uma cópia profunda feita antes). |
| idem | Ids de passo são estáveis: processar a mesma sequência duas vezes gera os mesmos ids. |
| `taskParser.test.ts` | Extrai 2 tarefas do markdown real de A2, com títulos e critérios; `parseDecision` reconhece `approved` e `reproved`; markdown fora do formato devolve `[]`/`null` **sem lançar**. |
| `useReasoningStream.test.tsx` | Com `FakeWebSocket`: envia um frame no open; eventos atualizam o `run`; `close(1000)` → `completed`; `close(1011)` → `failed` preservando passos; `cancel()` fecha o socket e nenhum evento posterior é processado; desmontar fecha o socket; `start` durante streaming é ignorado. |
| `ViewModeSwitch.test.tsx` | Alternar troca o modo montado; a escolha persiste; o atalho de teclado funciona; o stream **não** é reiniciado ao alternar (verifique que o `FakeWebSocket` não recebe `close`). |
| `RalphChatMode.test.tsx` | Cada passo vira uma mensagem; `reset`/`store` viram separador e não bolha; a resposta final aparece no `FinalAnswerCard`; toda mensagem tem estatísticas; com `isLive={false}` não há `Composer` nem halo pulsante. |

---

## 12. Verificação manual (com o backend no ar)

1. Na home, pergunte "Quais são todos os números primos entre 0 e 20?" e escolha
   **Ralph Loop Adaptado**.
2. Acompanhe no Modo Chat: critérios gerais → tarefas → para cada tarefa, reinicialização de
   contexto, resolução, verificação, armazenamento e aprendizados → verificação global → resposta
   final destacada.
3. Confira que o `context_size` **volta a valores baixos** a cada `reset` enquanto o
   `total_tokens` só cresce. Essa é a evidência visual do *fresh context* — se não estiver
   visível, o `MessageStats` está errado.
4. Alterne para o Modo Gráfico (placeholder) e volte: **o stream não é interrompido** e nenhum
   passo se perde.
5. Cancele uma execução no meio: a conexão fecha, os passos recebidos ficam na tela e é possível
   executar de novo.
6. Derrube o backend no meio de uma execução: aparece o erro, os passos permanecem.
7. Compare o `session_id` mostrado com o arquivo gerado em `apps/backend/data/sessions/` — o
   documento salvo precisa ter as mesmas fases que a tela mostrou.

---

## 13. Critérios de aceite

1. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro nem aviso.
2. `reasoningRunReducer` é uma função pura: não importa React, não importa `src/api/`, não lança
   em nenhum cenário de teste, e não muta a entrada.
3. O interruptor está na **parte superior**, alterna **sem refresh** e **sem interromper o
   stream**, e a escolha persiste entre telas e sessões do navegador.
4. Toda mensagem do Modo Chat é renderizada em Markdown e exibe modelo, tokens, tempo e contexto.
5. A resposta final é visivelmente destacada das demais mensagens.
6. `RalphView` não importa nada de `src/api/`, `src/hooks/` de rede, `src/config/` nem
   `react-router-dom`.
7. Uma execução com 40 passos não engasga a interface: alternar de modo e rolar continuam fluidos.
8. Degradações aparecem sem interromper o fluxo e sem parecer erro.
9. O `ThinkingRun` produzido tem tudo o que a FASE 06 precisa desenhar — tarefas com tentativas,
   ids de contexto, progresso de fases e totais — sem que a FASE 06 precise reprocessar `steps`
   crus para reconstruir estrutura.
