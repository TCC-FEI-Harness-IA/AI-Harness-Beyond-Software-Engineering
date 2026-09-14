# FASE 04 — Home e Inferência Simples

> Pré-requisito: FASES 01 a 03 concluídas e `feature_front/README.md` lido por completo.
> Esta é a primeira fase que fala com o backend de verdade.

---

## 1. Objetivo

Entregar as duas primeiras telas do produto:

1. **Página de início** — uma barra de texto e, logo abaixo, as duas opções de fluxo:
   *Inferência Simples* e *Ralph Loop Adaptado*.
2. **Chat da Inferência Simples** — abre um chat comum, faz a chamada a
   `POST /v1/message/default` e mostra a resposta com **consumo de tokens, tempo e estatísticas
   gerais em cada mensagem**.

A tela do Ralph fica como *placeholder* — é a FASE 05 que a constrói. Mas o **caminho** até ela
(escolher o modo na home e navegar carregando a pergunta) é implementado agora, porque é o mesmo
para os dois fluxos.

---

## 2. Escopo

**Entra nesta fase**

- `src/state/RunConfigContext.tsx` — modelo, `max_tokens` e `temperature` globais
- `src/features/home/` — `HomePage` e seus componentes
- `src/features/simple-chat/` — `SimpleChatPage` e a view reutilizável `SimpleChatView`
- `src/hooks/useSimpleInference.ts`
- `src/domain/types/simpleRun.ts` — o view-model do fluxo baseline
- `src/domain/services/buildSimpleRun.ts`

**Não entra**

- WebSocket e qualquer coisa do Ralph (FASES 05–06)
- Histórico (FASE 07)
- Qualquer componente visual novo em `src/components/` — se faltar algum, **generalize** o que
  existe da FASE 03 por prop, e ajuste a FASE 03

---

## 3. Requisito estruturante: sem barra lateral nas telas de inferência

O requisito é explícito: *"não deve existir barra lateral de histórico de chats na tela de
inferência com LLMs"*. Isso vale para esta fase e para as FASES 05 e 06.

Concretamente: `SimpleChatPage` e `RalphPage` usam `<AppShell>` **sem** a prop `sidebar`. O acesso
ao histórico existe apenas como um link na `TopBar`. Nenhuma tela de inferência lista chats.

---

## 4. `RunConfigContext`

Modelo, teto de tokens e temperatura são a configuração de execução, compartilhada pelos dois
fluxos. Ela vive em um Context para não precisar ser passada por props em cascata, e para que a
escolha do usuário sobreviva à navegação entre as telas.

```ts
interface RunConfigState {
  config: RunConfig                              // o tipo da FASE 02
  setModelName: (model: string) => void
  setMaxTokens: (value: number) => void
  setTemperature: (value: number) => void
  reset: () => void
}
```

- Valores iniciais vêm de `env` (`defaultModel`, `defaultProvider`, `defaultMaxTokens`,
  `defaultTemperature`). **Nenhum default escrito no componente.**
- A escolha do modelo persiste em `localStorage` (chave `tcc.runConfig`), dentro de `try/catch`,
  e é **validada contra `env.availableModels` na leitura** — um modelo salvo que saiu da lista
  volta para o default em vez de causar erro `422` no backend.
- `temperature` é limitada a `[0, 1]` no *setter*, e `maxTokens` a inteiro positivo. A validação
  fica aqui, não na UI, para que a UI não possa produzir um payload inválido.

---

## 5. Página de início

### 5.1 Layout

Composição vertical, centralizada, dentro de `PageContainer`:

```
                      (espaço generoso — ~18vh)

              Harness de IA                              ← --text-2xl, --tracking-tight
     Ralph Wiggum Loop adaptado para perguntas           ← --text-base, --color-text-secondary
              em linguagem natural

        ┌─────────────────────────────────────┐
        │  Faça uma pergunta…                 │         ← <Composer>
        │                                 (↑) │
        └─────────────────────────────────────┘

        ┌──────────────────┐  ┌──────────────────┐
        │ ⚡ Inferência     │  │ ◎ Ralph Loop     │        ← os dois cartões de modo
        │   Simples        │  │   Adaptado       │
        │ Uma chamada      │  │ Planeja, resolve │
        │ direta ao modelo │  │ e verifica em    │
        │                  │  │ ciclos           │
        └──────────────────┘  └──────────────────┘

              Modelo: gpt-4o-mini ·  1200 tokens · temp. 0,3      ← barra de configuração discreta
```

### 5.2 Os dois cartões de modo

São o requisito central da home: *"uma barra de texto e logo abaixo 2 opções"*.

```ts
interface ModeCardProps {
  mode: 'simple' | 'ralph'
  title: string
  description: string
  icon: ReactNode
  selected: boolean
  disabled?: boolean
  onSelect: (mode: InferenceMode) => void
}
```

- São **`<button>`** reais, lado a lado, de mesma altura, usando `Card interactive`.
- Comportamento: **um clique seleciona e já envia**. Se o campo estiver vazio, selecionar apenas
  destaca o cartão e foca o campo — não navega. É o modelo mental do ChatGPT: escrever e escolher
  como pensar.
- O cartão selecionado ganha borda `--color-accent` e halo `0 0 0 3px var(--color-accent-soft)`.
  O último modo usado é lembrado (mesmo `localStorage` do `RunConfig`) e volta pré-selecionado.
- O modo também pode ser escolhido por teclado: Tab até o cartão, Enter/Espaço ativa.
- Ícones: raio (`simple`) e ciclo/órbita (`ralph`) — SVG inline, 20px.
- No modo `ralph`, o cartão traz uma linha extra em `--text-xs`/`--color-text-tertiary`:
  "Consome mais tokens", porque é informação honesta e relevante para quem está pagando a conta.

### 5.3 Navegação carregando a pergunta

Ao enviar, a home **não** faz a chamada. Ela navega para a tela do fluxo escolhido, passando a
pergunta pelo `state` da rota:

```ts
navigate(mode === 'simple' ? ROUTES.simpleChat : ROUTES.ralphChat, {
  state: { question, autoStart: true } satisfies InferenceNavigationState,
})
```

Por que pelo `state` da rota e não por query string: a pergunta pode ser longa e ter quebras de
linha, e não queremos URL gigante nem escapar texto. `InferenceNavigationState` é um tipo em
`src/router/navigationState.ts`, e as telas de destino **validam** o que receberam (`useLocation`
devolve `unknown` na prática — trate como tal, regra 6 do README).

Se alguém abrir `/chat/simples` diretamente, sem `state`, a tela mostra um `Composer` vazio e
espera a pergunta ali mesmo. **Nenhuma tela quebra por falta de `state`.**

### 5.4 Barra de configuração

Linha discreta abaixo dos cartões, `--text-xs`, que abre um popover ao clicar:

- `select` nativo (estilizado, mas nativo — acessibilidade) com `env.availableModels`.
- Campo numérico para `max_tokens` e `range` para `temperature` (passo 0,1; `[0, 1]`), com o valor
  exibido via `formatTemperature`.
- Um `Button variant="ghost" size="sm"` "Restaurar padrões" chamando `reset()`.

Quando `env.availableModels` tem um único item, a barra mostra o nome do modelo sem o seletor.

---

## 6. O view-model `SimpleRun`

Mesmo com um fluxo de uma chamada só, o modelo de dados passa pela camada de domínio — é isso que
faz a FASE 07 conseguir renderizar uma sessão `DIRECT` salva com **exatamente** esta tela.

```ts
// src/domain/types/simpleRun.ts
export interface SimpleMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  stats: MessageStatsView | null
}

export interface SimpleRun {
  sessionId: string | null
  status: RunStatus
  messages: SimpleMessage[]
  totals: RunTotals | null
  error: AppError | null
}
```

`src/domain/services/buildSimpleRun.ts` expõe:

```ts
export const simpleRunFromResponse = (question: string, response: DefaultOutputDTO): SimpleRun
```

Ela monta as duas mensagens (pergunta e resposta) e preenche `MessageStatsView` a partir do DTO:
`modelName` vem do `RunConfig` (o `DefaultOutputDTO` não devolve o modelo — registre isso como
comentário no código, porque é um detalhe fácil de esquecer), `tokensInput`/`tokensOutput`/
`inferenceTimeMs` vêm do DTO, `totalTokens` é a soma, `contextId`/`contextSize` são `null`.

> A função irmã `simpleRunFromSession(document)` — sessão salva → `SimpleRun` — é da FASE 07.
> **Não a escreva agora**, mas deixe `SimpleRun` pronto para recebê-la.

---

## 7. `useSimpleInference`

```ts
interface UseSimpleInference {
  run: SimpleRun
  isBusy: boolean
  send: (question: string) => void
  retry: () => void
  reset: () => void
}

export const useSimpleInference = (config: RunConfig): UseSimpleInference
```

**Requisitos:**

1. `send` adiciona **imediatamente** a mensagem do usuário ao `run` (resposta otimista) e coloca o
   status em `running`. O usuário vê a própria pergunta na hora — esperar o servidor para isso é
   erro de UX.
2. Monta o payload com `buildInferencePayload` (FASE 02) e chama `sendDefaultMessage`.
3. Sucesso → acrescenta a mensagem do assistente com as estatísticas e status `completed`.
4. Erro → status `failed` e `error` preenchido. **A pergunta do usuário permanece na tela** e
   `retry()` reenvia a mesma pergunta sem redigitar.
5. `AbortController` por chamada; aborta no `unmount`; nunca chama `setState` após desmontar.
6. Enquanto `isBusy`, um segundo `send` é ignorado (o backend cobra por chamada).

---

## 8. `SimpleChatView` e `SimpleChatPage`

A separação é deliberada e é o que garante o requisito de o histórico ser idêntico:

- **`SimpleChatView`** (`src/features/simple-chat/SimpleChatView.tsx`) — **apresentação pura**.
  Recebe `{ run, isLive, onSend?, onRetry? }` e renderiza. Não conhece hook, rede nem rota.
- **`SimpleChatPage`** — conecta: lê o `state` da rota, usa `useSimpleInference`, passa para a
  view. É o único que sabe que existe rede.

A FASE 07 renderiza `SimpleChatView` com `isLive={false}` e um `SimpleRun` vindo do histórico —
**sem mudar uma linha da view**.

### Estrutura da view

```
<AppShell>                            ← sem sidebar
  <PageContainer width="content">
    <ChatScroller contentKey={run.messages.length}>
      {run.messages.map(...)}          → <MessageBubble> com <MessageStats>
      {isBusy && <TypingIndicator />}
      {run.error && <ErrorState onRetry={onRetry} />}
    </ChatScroller>
    {isLive && <Composer ... />}       ← fixo embaixo, translúcido com blur
  </PageContainer>
</AppShell>
```

- O `Composer` no rodapé fica `position: sticky; bottom: 0` com fundo
  `--color-surface-overlay` + `backdrop-filter`, para o texto passar por baixo dele ao rolar.
- Cada mensagem do assistente traz `<MessageStats layout="inline">` logo abaixo da bolha, com
  **modelo · tokens · tempo** — o requisito de estatísticas por mensagem.
- Ao concluir, um `MessageStats layout="panel"` opcional pode resumir a execução; mantenha-o
  discreto, abaixo da última mensagem.
- Título da aba (`document.title`) vira os primeiros caracteres da pergunta — detalhe de app
  nativo, feito em um `useEffect` com limpeza.

### Continuação da conversa

O backend **não tem endpoint de conversa multi-turno**: cada `POST /v1/message/default` abre uma
sessão nova. Portanto, enviar uma segunda pergunta na mesma tela cria **outra sessão**.

Como lidar, e isto é requisito: mantenha as mensagens anteriores visíveis na tela (a conversa
continua fazendo sentido para quem lê), mas **cada par pergunta/resposta carrega o seu próprio
`session_id`** nas estatísticas. Exiba o `session_id` abreviado em um `Tag` junto às estatísticas,
com `title` mostrando o id completo. Assim a tela não mente sobre o que o backend faz — e isso
importa: a comparação do experimento é por sessão.

---

## 9. Estados obrigatórios (regra 13)

| Estado | O que a tela mostra |
|---|---|
| Sem pergunta ainda | `EmptyState` discreto: "Faça uma pergunta para começar" + `Composer` focado |
| Enviando | Bolha do usuário já visível + `TypingIndicator` + `Composer` em `busy` |
| Erro | `ErrorState` com `error.userMessage` e botão "Tentar de novo"; a pergunta continua na tela |
| Sucesso | Resposta em Markdown + estatísticas |

---

## 10. Testes exigidos

| Arquivo | O que verifica |
|---|---|
| `RunConfigContext.test.tsx` | Defaults vêm de `env`; modelo fora de `availableModels` salvo no `localStorage` cai para o default; `setTemperature(1.4)` é limitado; `localStorage` que lança não quebra. |
| `HomePage.test.tsx` | Os dois cartões aparecem com os textos certos; enviar com o cartão "Inferência Simples" navega para `/chat/simples` com `state.question`; enviar com "Ralph" navega para `/chat/ralph`; campo vazio **não** navega e o campo recebe foco; Enter no `Composer` envia; a seleção de modo é alcançável por teclado. |
| `useSimpleInference.test.tsx` | A mensagem do usuário aparece **antes** da resposta chegar; sucesso acrescenta a resposta com as estatísticas; erro preserva a pergunta e `retry` refaz a chamada com o mesmo payload; desmontar durante a chamada não gera aviso; `send` durante `isBusy` é ignorado. |
| `buildSimpleRun.test.ts` | `DefaultOutputDTO` → `SimpleRun` com `totalTokens = input + output`, `modelName` vindo do config e `contextId` nulo. |
| `SimpleChatView.test.tsx` | Com `isLive={false}` **não** renderiza o `Composer`; com `isLive` renderiza; cada mensagem do assistente tem estatísticas; o estado de erro mostra "Tentar de novo". |

---

## 11. Verificação manual (com o backend no ar)

1. Suba o backend com `OPENROUTER_API_KEY`, `GENAI_AVAILABLE_MODELS` e
   `GENAI_AVAILABLE_PROVIDERS` preenchidos.
2. Na home, escreva "Quais são todos os números primos entre 0 e 20?" e clique em
   **Inferência Simples**.
3. Confira: a pergunta aparece na hora; o indicador de digitação roda; a resposta chega renderizada
   em Markdown; abaixo dela aparecem modelo, tokens e tempo.
4. Confirme em `apps/backend/data/sessions/` que a sessão foi gravada com `"flow": "DIRECT"`.
5. Desligue o backend e envie de novo: a tela mostra o erro em português, mantém a pergunta e o
   botão "Tentar de novo" funciona depois de religar o servidor.
6. Escolha um `max_tokens` de `0` na barra de configuração: a UI **não permite** enviar — a
   validação acontece antes da rede.

---

## 12. Critérios de aceite

1. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro nem aviso.
2. A home tem exatamente uma barra de texto e, **abaixo dela**, exatamente duas opções de fluxo.
3. Nenhuma tela de inferência renderiza barra lateral de histórico.
4. Toda mensagem do assistente exibe modelo, tokens e tempo, formatados em pt-BR.
5. A navegação home → chat acontece **sem refresh** e preserva a pergunta digitada.
6. Nenhum componente novo foi adicionado a `src/components/` sem que ele seja genuinamente
   reutilizável — e, se algum foi, ele está documentado na página de catálogo da FASE 03.
7. Nenhum literal de configuração (modelo, provider, limites) aparece fora de `env.ts` e do
   `RunConfigContext`.
8. Uma segunda pergunta na mesma tela mostra claramente que gerou uma **sessão nova**.
9. `SimpleChatView` não importa nada de `src/api/` nem de `src/hooks/` (exceto `useAutoScroll`
   indiretamente, via `ChatScroller`).
