# FASE 02 — Contratos, domínio e camada de acesso ao backend

> Pré-requisito: FASE 01 concluída e `feature_front/README.md` lido por completo.
> Esta fase **não produz nenhuma tela**. Ela produz a fundação tipada sobre a qual todas as
> outras rodam.

---

## 1. Objetivo

Materializar o contrato do backend (seção 3 do README) em TypeScript, com **validação na
fronteira**, e entregar os dois clientes de rede — HTTP e WebSocket — além dos formatadores
compartilhados.

A regra que governa esta fase: **o backend é território não confiável até a validação passar.**
Toda resposta entra como `unknown`, passa por um *parser* explícito e só então vira um tipo do
domínio. Nenhum `as` de conveniência, nenhum `any`.

---

## 2. Escopo

**Entra nesta fase**

- `src/domain/enums/` — os valores do contrato como constantes tipadas
- `src/domain/types/` — DTOs do backend
- `src/domain/services/formatters.ts`
- `src/api/errors/` — hierarquia de erros tipados
- `src/api/parsers/` — `unknown` → tipo do domínio
- `src/api/httpClient.ts`, `src/api/websocketClient.ts`
- `src/api/messageApi.ts`, `src/api/sessionApi.ts`
- `src/hooks/useAsync.ts`

**Não entra**

- View-models (`ThinkingRun`, `SimpleRun`) — FASE 05
- Reconstrução de sessão — FASE 07
- Qualquer componente ou tela

---

## 3. Enums do domínio

Regra 5 do README: nenhum componente compara com string escrita à mão. Um arquivo por conjunto,
em `src/domain/enums/`, todos no mesmo formato — objeto `as const` + tipo derivado + *type guard*:

```ts
// src/domain/enums/eventSubtype.ts
export const EVENT_SUBTYPE = {
  SETUP: 'setup',
  TASKS: 'tasks',
  EXECUTE: 'execute',
  REASONING: 'reasoning',
  VERIFY_PASS: 'verify_pass',
  VERIFY_FAIL: 'verify_fail',
  STORE: 'store',
  LEARN: 'learn',
  RESET: 'reset',
  COMPILE: 'compile',
  REPLAN: 'replan',
} as const

export type EventSubtype = (typeof EVENT_SUBTYPE)[keyof typeof EVENT_SUBTYPE]

export const isEventSubtype = (value: unknown): value is EventSubtype =>
  typeof value === 'string' && (Object.values(EVENT_SUBTYPE) as string[]).includes(value)
```

Conjuntos obrigatórios, todos espelhando 1:1 os enums do backend:

| Arquivo | Valores |
|---|---|
| `eventType.ts` | `thinking`, `result`, `degraded`, `error` |
| `eventSubtype.ts` | os 11 acima |
| `thinkingPhase.ts` | `A1`, `A2`, `B1`, `B2`, `B3`, `B4`, `C1`, `C2`, `C3`, `DIRECT` |
| `sessionStatus.ts` | `running`, `completed`, `degraded`, `failed` |
| `messageSource.ts` | `user`, `llm_agent`, `system` |
| `budgetLimit.ts` | `task_attempts`, `additional_planning_rounds`, `tasks_per_session`, `llm_calls_per_session`, `session_token_budget`, `session_timeout` |
| `taskStatus.ts` | `pending`, `running`, `approved`, `degraded`, `discarded` |
| `runStatus.ts` | `idle`, `running`, `completed`, `degraded`, `failed` *(view-model; usado a partir da FASE 05)* |

Além dos valores, cada arquivo de enum que precise aparecer na UI exporta o **rótulo em
português** e a **cor semântica**, para que nenhuma tela invente texto ou cor:

```ts
export const PHASE_LABEL: Record<ThinkingPhase, string> = {
  A1: 'Critérios de aceite gerais',
  A2: 'Quebra em tarefas',
  B1: 'Resolução da tarefa',
  B2: 'Verificação dos critérios',
  B3: 'Armazenamento do resultado',
  B4: 'Extração de aprendizados',
  C1: 'Verificação global',
  C2: 'Planejamento adicional',
  C3: 'Resposta final',
  DIRECT: 'Inferência direta',
}

export const PHASE_SHORT_LABEL: Record<ThinkingPhase, string> = {
  A1: 'A.1', A2: 'A.2', B1: 'B.1', B2: 'B.2', B3: 'B.3',
  B4: 'B.4', C1: 'C.1', C2: 'C.2', C3: 'C.3', DIRECT: 'Direta',
}
```

O mesmo padrão para `SUBTYPE_LABEL` (ver a tabela da seção 2 do README para os textos) e para
`SUBTYPE_TONE: Record<EventSubtype, Tone>`, onde `Tone` é
`'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'context'` — o mapeamento **tem que
seguir a tabela de semântica de cor da seção 8.3 do README**:

| Subtype | Tone |
|---|---|
| `setup`, `tasks`, `execute`, `reasoning`, `compile` | `neutral` |
| `verify_pass`, `store` | `success` |
| `verify_fail`, `replan` | `warning` |
| `learn` | `neutral` |
| `reset` | `context` |

---

## 4. Tipos do contrato

Em `src/domain/types/`, um arquivo por contrato, com o nome do DTO do backend. **Nomes de campo em
`snake_case` exatamente como chegam do backend** — a conversão para `camelCase` só acontece nos
view-models (FASE 05/07), e é feita uma única vez, na camada de domínio.

```ts
// src/domain/types/reasoningEvent.ts
export interface ContextWindowDTO {
  context_id: string
  context_size: number
}

export interface ReasoningEventDTO {
  type: EventType
  subtype: EventSubtype
  phase: ThinkingPhase
  task: string
  session_id: string
  content: string
  total_tokens: number
  context_window: ContextWindowDTO
  inference_time_ms: number
}

/** Frame reduzido de erro, fora do contrato de 9 campos (README, seção 3.2). */
export interface ReasoningErrorFrame {
  type: 'error'
  content: string
}

export type ReasoningFrame = ReasoningEventDTO | ReasoningErrorFrame
```

Demais tipos obrigatórios: `MessageInputDTO`, `ProviderConfigDTO`, `ModelConfigDTO`,
`DefaultInputDTO`, `DefaultOutputDTO`, `SessionDocument`, `SessionMessageDocument`,
`SessionTotalsDocument`, `SessionDegradationDocument`, `SessionListResponse`.

Constantes de rótulo global (`TASK_LABEL_SETUP = 'setup'`, `TASK_LABEL_SYNTHESIS = 'synthesis'`)
ficam em `src/domain/enums/taskLabels.ts` — o campo `task` do evento usa esses dois valores para
etapas que não pertencem a nenhuma tarefa.

---

## 5. Parsers de fronteira

`src/api/parsers/` — funções puras, sem React, sem rede:

```ts
export const parseReasoningFrame = (raw: unknown): ReasoningFrame => { /* … */ }
export const parseDefaultOutput = (raw: unknown): DefaultOutputDTO => { /* … */ }
export const parseSessionList = (raw: unknown): SessionListResponse => { /* … */ }
export const parseSessionDocument = (raw: unknown): SessionDocument => { /* … */ }
```

**Requisitos:**

1. Verificam **presença e tipo** de cada campo obrigatório. Campo faltando ou de tipo errado →
   lança `ContractError` com uma mensagem que nomeia o campo e o valor recebido.
2. `parseReasoningFrame` **decide primeiro a forma do frame**: se tem os 9 campos, é
   `ReasoningEventDTO`; se tem só `type: 'error'` + `content`, é `ReasoningErrorFrame`; qualquer
   outra coisa é `ContractError`. Isso é obrigatório porque o backend usa os dois formatos na
   mesma conexão.
3. Enums desconhecidos: se `subtype` ou `phase` vier com valor fora do enum, **não derrube o
   stream** — o backend pode ganhar etapas novas. Registre um aviso, mapeie para um valor de
   fallback (`subtype` → `reasoning`, `tone` → `neutral`) e siga. Esta é a única tolerância
   permitida; toda outra violação de contrato é erro.
4. `parseSessionDocument` valida `messages` como array e valida cada item; uma mensagem inválida
   **invalida o documento** (diferente do caso 3 — aqui não há stream para proteger).
5. Datas ficam como `string` ISO. **Não** converta para `Date` aqui; a formatação é
   responsabilidade de `formatters.ts`.

Utilitários privados compartilhados (`requireString`, `requireNumber`, `requireObject`,
`optionalString`) ficam em `src/api/parsers/primitives.ts` e são reusados por todos os parsers —
é o equivalente à leitura defensiva do `SessionDocumentMapper` do backend.

---

## 6. Erros tipados

`src/api/errors/` — uma classe por arquivo, todas estendendo `AppError`:

| Classe | Quando | O que a UI mostra |
|---|---|---|
| `AppError` | base; carrega `userMessage` em português | — |
| `NetworkError` | `fetch` rejeitou, DNS, offline | "Não foi possível falar com o servidor." |
| `TimeoutError` | estourou `requestTimeoutMs` | "O servidor demorou demais para responder." |
| `HttpError` | status ≥ 400; carrega `status` e o `detail` do FastAPI | Mensagem específica por status (ver abaixo) |
| `ContractError` | resposta fora do contrato | "O servidor respondeu em um formato inesperado." |
| `WebSocketError` | falha ao abrir ou fechamento anômalo; carrega `code` | Mensagem por código de fechamento |

O mapeamento de status e de código de fechamento para texto em português mora em um único lugar —
`src/api/errors/messages.ts` — e cobre exatamente o que o backend documenta:

| Origem | Código | Mensagem |
|---|---|---|
| HTTP | `404` | "Chat não encontrado." |
| HTTP | `400` | "O registro deste chat está corrompido." |
| HTTP | `422` | "Os parâmetros enviados não são aceitos pelo servidor." |
| HTTP | `500` | "O servidor falhou ao processar a requisição." |
| WS | `1003` | "O servidor recusou os parâmetros enviados." |
| WS | `1009` | "A pergunta é grande demais para o servidor." |
| WS | `1011` | "A execução falhou no servidor." |

**Toda** mensagem de erro exibida ao usuário sai daqui. Nenhuma string de erro escrita dentro de
componente (regra de reuso 7, estendida).

---

## 7. `httpClient.ts`

Um único cliente, usado por toda a aplicação (regra de reuso 6).

```ts
export const httpClient = {
  get: <T>(path: string, parse: (raw: unknown) => T, signal?: AbortSignal) => Promise<T>,
  post: <T>(path: string, body: unknown, parse: (raw: unknown) => T, signal?: AbortSignal) => Promise<T>,
}
```

**Requisitos:**

1. Monta a URL com `env.apiBaseUrl` + `path`. Nenhum consumidor passa URL absoluta.
2. `Content-Type: application/json` no `post`.
3. **Timeout com `AbortController`** de `env.requestTimeoutMs`, combinado com o `signal` que o
   chamador passar (o do `useEffect`). Estourou → `TimeoutError`; abortado pelo chamador →
   rejeita com `AbortError` e o chamador ignora.
4. Status ≥ 400 → tenta ler `{ detail }` do corpo e lança `HttpError` com status, detail e a
   mensagem em português da tabela acima.
5. Corpo OK → `JSON.parse` → chama `parse(raw)` → devolve `T`. `JSON.parse` que falha vira
   `ContractError`.
6. Sempre limpa o timer, inclusive no caminho de erro.

---

## 8. `websocketClient.ts`

O ponto mais delicado da fase. É a única abstração de WebSocket do app.

```ts
export interface ReasoningStreamHandlers {
  onEvent: (event: ReasoningEventDTO) => void
  onErrorFrame: (frame: ReasoningErrorFrame) => void
  onClose: (code: number) => void
  onFailure: (error: AppError) => void
}

export interface ReasoningStreamHandle {
  close: () => void
}

export const openReasoningStream: (
  payload: DefaultInputDTO,
  handlers: ReasoningStreamHandlers,
) => ReasoningStreamHandle
```

**Requisitos, um a um:**

1. Abre `new WebSocket(`${env.wsBaseUrl}/message/reasoning`)`. O caminho `/message/reasoning` é
   constante do módulo, não literal espalhado.
2. No `onopen`, envia **um único frame de texto** com `JSON.stringify(payload)` — e nada mais
   depois disso. O protocolo do backend é de um frame de abertura só.
3. **Timeout de abertura** de `env.wsOpenTimeoutMs`: se `onopen` não disparar até lá, fecha o
   socket e chama `onFailure(new WebSocketError(...))`.
4. Cada `onmessage` passa por `parseReasoningFrame`. Frame completo → `onEvent`; frame reduzido de
   erro → `onErrorFrame`; `ContractError` → `onFailure`, **sem fechar o socket** (um frame
   malformado no meio não deve descartar o que já chegou nem o que ainda vem).
5. `onclose` chama `onClose(event.code)`. **`1000` é sucesso, não erro** — o backend fecha assim
   ao concluir o fluxo. `1003`, `1009` e `1011` viram `onFailure` com a mensagem da tabela da
   seção 6; qualquer outro código anômalo vira mensagem genérica.
6. `onerror` do WebSocket **não carrega detalhe útil** no navegador. Não invente uma mensagem
   específica a partir dele: registre e deixe o `onclose` (que sempre vem em seguida) decidir.
7. `close()` do handle: fecha com código `1000`, **desregistra todos os handlers antes** e marca
   o handle como fechado, para que nenhum callback dispare após o `unmount` (regra 9 do README).
8. Chamar `close()` duas vezes é seguro. Nenhum handler dispara depois do primeiro `close()`.
9. **Sem reconexão automática.** O protocolo é de execução única: reconectar refaria o fluxo do
   zero, gastando tokens do usuário. Quem decide tentar de novo é a pessoa, com um botão.

---

## 9. APIs de alto nível

### `messageApi.ts`

```ts
export const buildInferencePayload = (question: string, config: RunConfig): DefaultInputDTO
export const sendDefaultMessage = (payload: DefaultInputDTO, signal?: AbortSignal) => Promise<DefaultOutputDTO>
export const openReasoning = (payload: DefaultInputDTO, handlers: ReasoningStreamHandlers) => ReasoningStreamHandle
```

`buildInferencePayload` é **o único lugar** que sabe montar o corpo dos dois fluxos — e os dois
usam o mesmo corpo, conforme a seção 3.2 do README. Ele aplica os defaults de `env` e garante:
`user_input` não vazio (senão `ContractError` antes de sair), `temperature` arredondada para 1
casa e dentro de `[0, 1]`, `max_tokens > 0`, `endpoint: null` quando não configurado.

```ts
export interface RunConfig {
  modelName: string
  provider: string
  maxTokens: number
  temperature: number
}
```

### `sessionApi.ts`

```ts
export const listSessionIds = (signal?: AbortSignal) => Promise<string[]>
export const getSession = (sessionId: string, signal?: AbortSignal) => Promise<SessionDocument>
```

`listSessionIds` devolve já o array de dentro de `{ session_ids: [...] }` — nenhum consumidor
precisa conhecer o envelope.

> A busca em lote com concorrência limitada (necessária porque a listagem só devolve ids) **não**
> vive aqui: é um hook, e é a FASE 07 que a especifica.

---

## 10. `formatters.ts`

`src/domain/services/formatters.ts` — funções puras, com `Intl`, em `pt-BR`. **Todo** número, tempo
e data exibidos no app passam por aqui (regra de reuso 7):

| Função | Entrada | Saída |
|---|---|---|
| `formatTokens(n)` | `15284` | `15.284` |
| `formatCompactTokens(n)` | `15284` | `15,3 mil` |
| `formatDuration(ms)` | `812` / `5230` / `64000` | `812 ms` / `5,2 s` / `1 min 4 s` |
| `formatDateTime(iso)` | ISO-8601 | `13/09/2026, 21:26` |
| `formatRelative(iso)` | ISO-8601 | `há 3 minutos` (via `Intl.RelativeTimeFormat`) |
| `truncate(text, max)` | texto + limite | corta na **fronteira de palavra** e acrescenta `…`; nunca corta no meio de uma palavra quando sobra espaço para ao menos uma |
| `formatTemperature(n)` | `0.3` | `0,3` |

`truncate` é o que a FASE 07 usa para o resumo dos cards de histórico, com o limite vindo de
`env.historySummaryMaxChars`. Ele também **normaliza quebras de linha para espaço** — o
`user_question` pode ter várias linhas e o card é de uma linha só.

---

## 11. `useAsync.ts`

Hook genérico de carregamento, para que nenhuma tela reescreva o tripé
`loading / error / data` (regra 13 do README, que exige os quatro estados em toda tela):

```ts
export type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: AppError }
  | { status: 'success'; data: T }

export const useAsync: <T>(
  run: (signal: AbortSignal) => Promise<T>,
  deps: React.DependencyList,
) => AsyncState<T> & { reload: () => void }
```

Requisitos: cria um `AbortController` por execução; aborta no `unmount` e a cada nova execução;
**nunca** chama `setState` após o `unmount`; ignora `AbortError`; `reload()` reexecuta sem mudar
as `deps`.

---

## 12. Testes exigidos

Nenhum teste faz rede real: `globalThis.fetch` e `globalThis.WebSocket` são substituídos por
duplos (um `FakeWebSocket` controlável, em `src/test/doubles/`).

| Arquivo | O que verifica |
|---|---|
| `parsers/reasoningFrame.test.ts` | Frame de 9 campos → `ReasoningEventDTO`; frame `{type:'error',content}` → `ReasoningErrorFrame`; campo faltando → `ContractError` nomeando o campo; `subtype` desconhecido → fallback sem lançar; `context_window` ausente → `ContractError`. |
| `parsers/sessionDocument.test.ts` | Documento real (copie um de `apps/backend/data/sessions/`) → objeto válido; `messages` não-array → erro; mensagem com `phase` inválida → erro; `final_answer: null` e `degradations: []` são aceitos. |
| `httpClient.test.ts` | `200` → parse chamado; `404` → `HttpError` com a mensagem "Chat não encontrado."; corpo não-JSON → `ContractError`; timeout → `TimeoutError`; abort do chamador não vira erro de UI. |
| `websocketClient.test.ts` | Envia exatamente **um** frame no `onopen`; cada mensagem vira `onEvent`; `close(1000)` → `onClose(1000)` e **não** `onFailure`; `close(1011)` → `onFailure`; após `handle.close()` nenhum handler dispara; frame malformado → `onFailure` e o socket **continua aberto**; `onopen` que não vem dentro do timeout → `onFailure`. |
| `messageApi.test.ts` | `buildInferencePayload` monta o corpo exato do contrato; pergunta vazia lança; temperatura `0.75` vira `0.8`; temperatura `1.4` lança. |
| `formatters.test.ts` | Cada linha da tabela da seção 10, incluindo `truncate` cortando em fronteira de palavra e normalizando quebras de linha. |
| `useAsync.test.tsx` | Sucesso, erro, `reload`, e que desmontar durante a requisição não gera aviso de `setState` após unmount. |

---

## 13. Critérios de aceite

1. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro nem aviso.
2. Um `grep -rn "fetch(" src/` retorna resultados **apenas** em `src/api/`.
3. Um `grep -rn "new WebSocket" src/` retorna **apenas** `src/api/websocketClient.ts`.
4. Um `grep -rn ": any\|as any" src/` retorna vazio.
5. Nenhuma string de mensagem de erro voltada ao usuário existe fora de
   `src/api/errors/messages.ts`.
6. `parseSessionDocument` processa, sem erro, **todos** os arquivos de
   `apps/backend/data/sessions/` — incluindo sessões `failed` com uma única mensagem,
   sessões `DIRECT` e a sessão `A1` completa com 15 mensagens. Escreva o teste lendo esses
   arquivos como *fixtures* copiadas para `src/test/fixtures/`.
7. Fechamento `1000` é tratado como sucesso em toda a camada — nenhum caminho o transforma em
   erro exibido.
8. Nenhum arquivo desta fase importa React, exceto `useAsync.ts` e os testes.
