# feature_front — Frontend do Harness (Ralph Wiggum Loop adaptado)

> Documento raiz da feature. **Leia este README antes de executar qualquer FASE.**
> Cada arquivo `FASE_XX_*.md` é autossuficiente quando lido em conjunto com este README:
> juntos, os dois contêm tudo que é necessário para concluir a implementação daquela fase,
> sem precisar consultar o paper, o backend ou o restante do repositório.

---

## Sumário

1. [O que é este projeto](#1-o-que-é-este-projeto)
2. [O fluxo do paper que o front precisa mostrar](#2-o-fluxo-do-paper-que-o-front-precisa-mostrar)
3. [Contrato do backend](#3-contrato-do-backend)
4. [Stack e política de dependências](#4-stack-e-política-de-dependências)
5. [Regras de código obrigatórias](#5-regras-de-código-obrigatórias)
6. [Arquitetura](#6-arquitetura)
7. [Variáveis de ambiente](#7-variáveis-de-ambiente)
8. [Regras de design — MacFirst](#8-regras-de-design--macfirst)
9. [Regras de reuso](#9-regras-de-reuso)
10. [As fases de implementação](#10-as-fases-de-implementação)
11. [Como verificar uma fase](#11-como-verificar-uma-fase)
12. [Como rodar](#12-como-rodar)

---

## 1. O que é este projeto

Este repositório é o artefato prático do TCC **"Um Harness de IA para Resolução de Perguntas em
Linguagem Natural: Adaptando o Ralph Wiggum Loop Além do Desenvolvimento de Software"**
(`docs/paper/TCC.tex`).

O backend (`apps/backend/`) já está implementado e expõe **dois fluxos de inferência comparáveis**
para a mesma pergunta:

| Fluxo | Transporte | Endpoint | Descrição |
|---|---|---|---|
| **Inferência simples** (baseline) | HTTP `POST` | `/v1/message/default` | Uma única chamada ao modelo. Sem planejamento, sem loop, sem validação. Grupo de controle do experimento. |
| **Ralph Loop Adaptado** (harness) | **WebSocket** | `/v1/message/reasoning` | Fluxo completo de *thinking*: Planejamento → Execução em Loop → Criação da Resposta Final. **Cada etapa do pensamento é emitida como um evento** pela conexão, em tempo real. |

Ambos gravam uma **Sessão** persistida, consultável por `GET /v1/sessions` e
`GET /v1/sessions/{id}`, com histórico completo de mensagens, custo de tokens e tempo de inferência.

**O que este frontend precisa entregar:**

1. **Tornar o harness visível.** O diferencial do trabalho não é a resposta final — é o *processo*
   que a produz. O front precisa mostrar, ao vivo, a decomposição em tarefas, o ciclo de tentativa
   e verificação, a reinicialização de contexto (*fresh context*) e a síntese final. É isso que
   sustenta a defesa do TCC.
2. **Tornar o custo visível.** Tokens, tempo de inferência e tamanho da janela de contexto aparecem
   em **cada mensagem**, nos dois fluxos. É o dado que permite comparar baseline e harness.
3. **Tornar o histórico idêntico à execução ao vivo.** Uma sessão salva precisa ser renderizada
   exatamente com os mesmos componentes da execução ao vivo — inclusive com modo gráfico e modo
   chat. A única diferença é a fonte dos dados.

---

## 2. O fluxo do paper que o front precisa mostrar

O fluxo adaptado tem três macro-fases. O front usa esta divisão como espinha dorsal do **Modo
Gráfico** e como rótulo de cada mensagem no **Modo Chat**.

### A. Planejamento

| Etapa | Nome no paper | O que produz | Evento recebido |
|---|---|---|---|
| **A.1** | Definição dos critérios de aceite gerais | Regras que a resposta final deverá respeitar (idioma, formato, restrições do enunciado) | `subtype: "setup"` |
| **A.2** | Quebra em tarefas de objetivo único | Lista ordenada de tarefas (`T1`, `T2`, …), cada uma com critérios de aceite próprios | `subtype: "tasks"` |

### B. Execução em Loop

Roda **uma tarefa por vez**, retirada da fila. Para cada tarefa:

| Etapa | Nome no paper | O que acontece | Evento recebido |
|---|---|---|---|
| — | *Fresh Context* | O contexto é **reinicializado**: janela nova, `context_id` novo, `context_size` volta a zero. Os aprendizados acumulados são injetados como primeira entrada. | `subtype: "reset"` |
| **B.1** | Seleção da tarefa | A tarefa selecionada é apresentada ao modelo | `subtype: "execute"` |
| **B.1** | Resolução | O modelo produz o resultado preliminar | `subtype: "reasoning"` |
| **B.2** | Verificação dos critérios | Valida o preliminar contra os critérios **daquela** tarefa. Reprovado → volta para B.1 **no mesmo contexto** (a tentativa reprovada permanece visível para o modelo se corrigir). | `subtype: "verify_pass"` / `"verify_fail"` |
| **B.3** | Armazenamento do resultado | A resposta aprovada é persistida. Alimenta **exclusivamente** a fase C. Etapa programática, sem chamada ao modelo. | `subtype: "store"` |
| **B.4** | Armazenamento dos aprendizados pontuais | Fatos objetivos descobertos na tarefa (inclusive em tentativas reprovadas) viram *aprendizados*. Alimentam **exclusivamente** o contexto das tarefas seguintes — nunca a resposta final. | `subtype: "learn"` |

> **Invariante que a UI precisa comunicar:** resultados (B.3) e aprendizados (B.4) têm destinos
> **opostos e exclusivos**. Resultado → resposta final. Aprendizado → próxima tarefa. O Modo
> Gráfico deve deixar isso visualmente óbvio (ver FASE 06).

### C. Criação da Resposta Final

| Etapa | Nome no paper | O que acontece | Evento recebido |
|---|---|---|---|
| **C.1** | Compilação e verificação global | Verifica se a **união** dos resultados satisfaz os critérios gerais de A.1 | `subtype: "compile"` (phase `C1`) |
| **C.2** | Planejamento adicional | Só quando C.1 reprova: cria tarefas novas para as lacunas, insere **no topo da fila** e volta para B.1 | `subtype: "replan"` |
| **C.3** | Construção da resposta final | Organiza os resultados no formato e idioma de A.1, sem introduzir fatos novos | `subtype: "compile"` (phase `C3`, `type: "result"`) |

### Resiliência de custo

O backend **nunca aborta por estouro de limite — ele degrada e conclui**. Quando um limite é
atingido (tentativas por tarefa, rodadas de replanejamento, tarefas por sessão, chamadas ao modelo,
orçamento de tokens ou tempo de parede), emite um evento `type: "degraded"` e segue até entregar
uma resposta. O front **precisa renderizar degradações de forma visível mas não alarmante** — é um
comportamento esperado do sistema, não um erro.

---

## 3. Contrato do backend

Base HTTP: `${VITE_API_BASE_URL}${VITE_API_PREFIX}` (ex.: `http://localhost:8000` + `/v1`).
Base WebSocket: `${VITE_WS_BASE_URL}${VITE_API_PREFIX}` (ex.: `ws://localhost:8000` + `/v1`).

**Nenhuma URL literal pode aparecer no código** — ver [seção 7](#7-variáveis-de-ambiente).

### 3.1 `POST /v1/message/default` — inferência simples

Requisição:

```json
{
  "message": { "user_input": "Quais são todos os números primos entre 0 e 20?" },
  "llm_model_config": {
    "provider": "open_router",
    "provider_config": { "model_name": "openai/gpt-4o-mini", "endpoint": null },
    "max_tokens": 1000,
    "temperature": 0.3
  }
}
```

Resposta `200`:

```json
{
  "message": "Quais são todos os números primos entre 0 e 20?",
  "response": "Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19.",
  "session_id": "sess_ab12cd34ef56",
  "tokens_input": 42,
  "tokens_output": 118,
  "inference_time_ms": 812
}
```

Erros: `422` (corpo fora do contrato), `500` (falha no provedor; `detail` traz a mensagem).

### 3.2 `WS /v1/message/reasoning` — Ralph Loop Adaptado

**Protocolo:**

1. O cliente abre a conexão e envia **um único frame de texto** com o payload — **exatamente o
   mesmo formato** do `POST /v1/message/default`.
2. O servidor responde com um frame JSON por etapa de pensamento.
3. O último frame tem `"type": "result"` e traz a resposta final em `content`. Em seguida o
   servidor fecha a conexão com código `1000`.

**Frame de evento** (`ReasoningEventDTO`) — **exatamente estes 9 campos, sem extras:**

| Campo | Tipo | Descrição |
|---|---|---|
| `type` | `string` | `thinking` \| `result` \| `degraded` \| `error` |
| `subtype` | `string` | `setup` \| `tasks` \| `execute` \| `reasoning` \| `verify_pass` \| `verify_fail` \| `store` \| `learn` \| `reset` \| `compile` \| `replan` |
| `phase` | `string` | `A1` \| `A2` \| `B1` \| `B2` \| `B3` \| `B4` \| `C1` \| `C2` \| `C3` |
| `task` | `string` | Id da tarefa (`T1`, `T2`, …), ou `setup` / `synthesis` para etapas globais |
| `session_id` | `string` | Sessão em execução |
| `content` | `string` | **Markdown pronto para renderização** |
| `total_tokens` | `int` | Acumulado da sessão; **nunca decresce** |
| `context_window` | `object` | `{ "context_id": string, "context_size": int }` |
| `inference_time_ms` | `int` | Tempo da chamada; `0` em etapas programáticas (`reset`, `store`, `execute`) |

> `context_size` é o total de tokens **da janela atual** e **volta a zero a cada `reset`**. Essa
> serra dentada é a evidência visual do *Fresh Context* — o mecanismo central do paper contra o
> *context rot*. O Modo Gráfico é obrigado a exibi-la (ver FASE 06).

**Códigos de fechamento:**

| Código | Motivo | O que a UI faz |
|---|---|---|
| `1000` | Fluxo concluído normalmente | Marca a execução como concluída |
| `1003` | Payload inválido — precedido de um frame `{"type":"error","content":"..."}` | Mostra erro de contrato |
| `1009` | Frame de abertura maior que o limite do servidor | Mostra erro de tamanho |
| `1011` | Exceção durante a execução — precedido de frames de erro | Mostra erro de execução, preservando os eventos já recebidos |

**Frames de erro fora do fluxo normal** usam um formato reduzido, **fora** do contrato de 9 campos:

```json
{ "type": "error", "content": "<detalhe do erro>" }
```

O parser do front **precisa tolerar os dois formatos** (ver FASE 02).

### 3.3 `GET /v1/sessions` — listar chats

```json
{ "session_ids": ["sess_ab12cd34ef56", "sess_9f8e7d6c5b4a"] }
```

> ⚠️ **Limitação conhecida do backend, e como o front lida com ela.** O endpoint devolve
> **apenas os identificadores** — não devolve a pergunta do usuário, nem a data, nem o fluxo.
> Como o requisito da tela de histórico é listar o **input do usuário** como resumo, o front
> precisa buscar o documento de cada sessão individualmente (`GET /v1/sessions/{id}`).
> A FASE 07 especifica a estratégia obrigatória: busca com **pool de concorrência limitada**,
> cache em memória, render progressivo com *skeletons* e tolerância a falhas individuais.
> **Não altere o backend** — esta feature é só de frontend.

### 3.4 `GET /v1/sessions/{session_id}` — um chat

```json
{
  "id": "sess_ab12cd34ef56",
  "user_question": "Quais são todos os números primos entre 0 e 20?",
  "flow": "A1",
  "model_name": "openai/gpt-4o-mini",
  "max_tokens": 1200,
  "temperature": 0.3,
  "status": "completed",
  "created_at": "2026-09-11T23:18:06.314083+00:00",
  "updated_at": "2026-09-11T23:18:07.668445+00:00",
  "final_answer": "Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19.",
  "totals": {
    "total_messages": 15, "total_llm_calls": 7,
    "tokens_input": 4210, "tokens_output": 1830, "total_tokens": 6040,
    "inference_time_ms": 5230, "wall_time_ms": 6100
  },
  "messages": [
    {
      "id": "msg_01", "order": 0,
      "timestamp": "2026-09-11T23:18:06.320000+00:00",
      "phase": "A1", "source": "user",
      "content": "Quais são todos os números primos entre 0 e 20?",
      "task_id": null, "context_id": null,
      "tokens_input": 0, "tokens_output": 0, "total_tokens": 0,
      "inference_time_ms": 0, "model_name": null
    }
  ],
  "degradations": []
}
```

- `flow`: `"A1"` = sessão do harness (Ralph Loop); `"DIRECT"` = sessão do baseline. **É o campo que
  decide qual tela de histórico abrir.**
- `status`: `running` \| `completed` \| `degraded` \| `failed`.
- `source` de cada mensagem: `user` \| `llm_agent` \| `system`.
- `degradations[]`: `{ limit, phase, task_id, description, occurred_at }`.

Erros: `404` (não existe), `400` (documento persistido inválido), `500`.

### 3.5 ⚠️ A diferença crítica entre o evento ao vivo e a mensagem persistida

**A mensagem persistida não tem `subtype`.** O evento do WebSocket tem; o documento da sessão não.
Como a tela de histórico precisa ser **idêntica** à da execução ao vivo, o front é obrigado a
**derivar o `subtype`** a partir de `(phase, source, content)`. Esta é a tabela de derivação
canônica, e ela é implementada uma única vez, em `domain/services/` (ver FASE 07):

| `phase` | `source` | `subtype` derivado | Observação |
|---|---|---|---|
| `DIRECT` | `user` | — | Mensagem do usuário no fluxo baseline |
| `DIRECT` | `llm_agent` | — | Resposta do fluxo baseline |
| `A1` | `user` | — | Pergunta original (sempre `order: 0`) |
| `A1` | `llm_agent` | `setup` | Critérios de aceite gerais |
| `A2` | `llm_agent` | `tasks` | Tarefas planejadas |
| `B1` | `system` | `reset` | *Fresh context*. `content` traz o novo `context_id` |
| `B1` | `llm_agent` | `reasoning` | Resultado preliminar da tarefa |
| `B2` | `llm_agent` | `verify_pass` / `verify_fail` | Ver regra abaixo |
| `B3` | `system` | `store` | Resultado armazenado |
| `B4` | `llm_agent` | `learn` | Aprendizados extraídos |
| `C1` | `llm_agent` | `compile` | Verificação global |
| `C2` | `llm_agent` | `replan` | Planejamento adicional |
| `C3` | `llm_agent` | `compile` + `type: "result"` | Resposta final |

**Regra para `verify_pass` vs `verify_fail`** (nesta ordem de precedência):

1. O `content` da mensagem `B2` começa com `**Decisão:** \`approved\`` ou
   `**Decisão:** \`reproved\``. Use esse marcador — ele é gerado por um template fixo do backend.
2. *Fallback posicional*, caso o marcador não seja encontrado: uma mensagem `B2` é `verify_fail`
   se existir **outra** mensagem `B2` com o mesmo `task_id` depois dela; caso contrário é
   `verify_pass`.

**Dois eventos ao vivo não são persistidos** e portanto **não existem** no histórico:

- `subtype: "execute"` (a apresentação da tarefa ao modelo, em B.1);
- o próprio evento `error` do WebSocket.

A reconstrução deve **sintetizar** o passo `execute` a partir do `reset` correspondente + a
descrição da tarefa extraída do conteúdo de `A2`, para que a linha do tempo do histórico tenha
exatamente a mesma cardinalidade da linha do tempo ao vivo. Detalhes na FASE 07.

---

## 4. Stack e política de dependências

| Item | Escolha | Justificativa |
|---|---|---|
| Biblioteca de UI | **React 18 puro** | Requisito do projeto. Sem Next.js, sem Remix, sem qualquer meta-framework. |
| Linguagem | **TypeScript** (`strict: true`) | O backend é fortemente tipado e o contrato tem 9 campos exatos; tipar os DTOs faz um erro de contrato falhar no *build*, não em produção. |
| Build | **Vite** | Padrão de mercado para React puro. Dá `import.meta.env` com o prefixo `VITE_`, que é o mecanismo de variável de ambiente exigido. |
| Estilo | **CSS puro + CSS Modules + custom properties** | Sem Tailwind, sem styled-components, sem CSS-in-JS. O design MacFirst vive em *design tokens* (seção 8). |
| Estado | **Hooks + Context nativos** | Sem Redux, Zustand, Jotai ou MobX. O estado da aplicação é pequeno e local por natureza. |
| Testes | **Vitest + React Testing Library** | Testa comportamento, não implementação. |

### Dependências de runtime permitidas

A regra é: **o mínimo possível, e só o que agrega valor alto e é amplamente recomendado**. A lista
abaixo é **fechada**. Adicionar qualquer outra dependência de runtime exige justificativa explícita
no PR.

| Pacote | Para quê | Por que não escrever à mão |
|---|---|---|
| `react`, `react-dom` | Base | — |
| `react-router-dom` | Rotas (`/`, `/chat/:sessionId`, `/historico`, `/historico/:sessionId`) | Roteamento com histórico, params e navegação programática é território de bug sutil (back/forward, deep link, scroll restoration). Lib madura e minúscula. |
| `react-markdown` | Renderizar o `content` de **toda** mensagem | O backend já entrega Markdown pronto. Escrever um parser de Markdown correto (listas aninhadas, tabelas, código, escaping seguro) é um projeto inteiro — e um parser caseiro é vetor de XSS. `react-markdown` não usa `dangerouslySetInnerHTML`. |
| `remark-gfm` | Tabelas, listas de tarefas e *strikethrough* no Markdown | Os templates do backend usam tabelas e listas GFM. |

**Explicitamente proibidos:** qualquer *UI kit* (MUI, Chakra, Ant, shadcn, Bootstrap), qualquer
biblioteca de animação (Framer Motion, GSAP, react-spring — as animações são CSS), qualquer
biblioteca de ícones pesada (os ícones são SVG inline próprios), `axios` (use `fetch`), `lodash`,
`moment`/`dayjs` (use `Intl.DateTimeFormat` e `Intl.NumberFormat`), qualquer lib de gráfico
(a linha do tempo é SVG/CSS próprios), qualquer lib de estado global.

### Dependências de desenvolvimento permitidas

`vite`, `@vitejs/plugin-react`, `typescript`, `vitest`, `jsdom`, `@testing-library/react`,
`@testing-library/user-event`, `@testing-library/jest-dom`, `eslint` + plugins
(`@typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`), `prettier`.

---

## 5. Regras de código obrigatórias

Valem para **todas as fases**. Uma fase só está concluída se todas forem verdadeiras.

1. **Um componente por arquivo.** O arquivo tem o nome do componente em `PascalCase`
   (`MessageBubble.tsx`). Nenhum módulo exporta dois componentes. Componentes auxiliares usados
   só ali ficam em subpasta própria, não no mesmo arquivo.
2. **Componente = pasta.** Todo componente com estilo próprio mora em uma pasta com seus arquivos:
   `Button/Button.tsx`, `Button/Button.module.css`, `Button/index.ts`. O `index.ts` só reexporta.
3. **Componentes de UI são burros.** Nada em `src/components/` faz `fetch`, abre WebSocket, lê
   `import.meta.env` ou conhece rota. Recebem dados por props e emitem eventos por callback. Todo
   acesso a rede vive em `src/api/`; toda regra vive em `src/domain/`; a orquestração vive em
   `src/hooks/` e `src/features/`.
4. **Nenhum literal de configuração no código.** URL, porta, prefixo de API, nome de modelo,
   limite de caracteres, concorrência, timeout: tudo vem de `src/config/env.ts`, que é o **único**
   módulo do projeto autorizado a tocar em `import.meta.env`. É o espelho do `Settings` do backend.
   Valores de layout (espaçamentos, cores, raios, durações) vêm de *design tokens* CSS, nunca de
   número mágico em componente.
5. **Nenhum valor mágico de domínio no código.** Os `subtype`, `phase`, `type`, `status`, `source`
   e `flow` do contrato viram `const` tipados em `src/domain/enums/`. Nenhum componente compara
   com a string `"verify_fail"` escrita à mão.
6. **Tipagem estrita.** `tsconfig` com `strict: true`, `noUncheckedIndexedAccess: true`,
   `noImplicitOverride: true`. **`any` é proibido** — use `unknown` + validação na fronteira.
   Nenhum `@ts-ignore`; `@ts-expect-error` só com comentário justificando, e só em teste.
7. **Validação na fronteira.** Toda resposta de rede entra como `unknown` e passa por um *parser*
   explícito em `src/api/parsers/` que devolve o tipo do domínio ou lança um erro tipado. O resto
   do app trabalha só com tipos garantidos. Isso vale tanto para o JSON do HTTP quanto para cada
   frame do WebSocket.
8. **Atualização dinâmica, sem refresh.** Nenhum `window.location.reload()`, nenhum `<a href>` para
   rota interna (use `<Link>`/`navigate`), nenhum `<form>` com submit nativo não interceptado.
   Toda mudança de tela e de conteúdo acontece por estado do React.
9. **Efeitos com limpeza.** Todo `useEffect` que abre WebSocket, registra listener, cria timer ou
   dispara `fetch` devolve uma função de limpeza que fecha/cancela (`AbortController` para
   `fetch`, `ws.close()` para WebSocket). Nenhum `setState` depois do *unmount*.
10. **Nada de `key={index}`** em lista que pode reordenar ou crescer no meio. Eventos têm id
    estável — gere um id determinístico na camada de domínio (ver FASE 05).
11. **Acessibilidade obrigatória.** Todo controle interativo é `<button>` / `<a>` / `<input>` real
    (nunca `<div onClick>`), tem rótulo acessível, é alcançável por teclado e mostra *focus ring*
    visível. O interruptor de modo é um `role="radiogroup"` ou um `<button role="switch">` com
    `aria-checked`. Regiões que atualizam sozinhas usam `aria-live="polite"`.
12. **Movimento respeita `prefers-reduced-motion`.** Toda animação é desligada ou reduzida a
    *fade* sob essa media query. Sem exceção — a linha do tempo animada da FASE 06 inclusive.
13. **Estados sempre completos.** Toda tela que carrega dados trata os quatro estados: *carregando*
    (skeleton, não spinner de página inteira), *vazio* (com ação de saída), *erro* (com mensagem
    legível e botão de tentar de novo), *sucesso*. Não existe tela que fique em branco.
14. **Docstrings e comentários em português**, no padrão já praticado no backend: explicam o
    **porquê**, não o **o quê**. Componentes públicos do design system levam um comentário de bloco
    descrevendo props e uso.
15. **Testes de comportamento.** Cada fase declara os testes exigidos. Testam o que o usuário vê e
    faz (`getByRole`, `getByText`, `userEvent`), nunca estado interno nem nome de classe CSS.
    Nenhum teste faz rede real: `fetch` e `WebSocket` são substituídos por duplos.
16. **`eslint` e `tsc` sem nenhum erro nem aviso.** `npm run lint` e `npm run typecheck` fazem
    parte do critério de aceite de toda fase.
17. **Reuso antes de criação.** Antes de escrever um componente novo, procure em
    `src/components/`. Ver [seção 9](#9-regras-de-reuso) — a regra é obrigatória, não conselho.

---

## 6. Arquitetura

### 6.1 Camadas

Espelham as do backend, com as mesmas dependências unidirecionais:

```
features/     Telas — compõem componentes e hooks. Uma pasta por tela.
hooks/        Orquestração — ligam API, domínio e estado de tela. Sem JSX.
components/   UI reutilizável, burra, sem rede e sem regra de negócio.
domain/       Tipos, enums e regras puras (funções, sem React, sem rede). 100% testável isolado.
api/          Acesso à rede — cliente HTTP, cliente WebSocket, parsers de fronteira.
config/       env.ts — único ponto que lê import.meta.env.
styles/       Design tokens, reset e animações globais.
router/       Definição de rotas e navegação.
```

**Direção das dependências:** `features` → `hooks` → `api`/`domain` → `config`.
`components` depende **só** de `domain` (para tipos) e de `styles`. `domain` **não importa nada**
de `api`, `hooks`, `features` ou `react`.

### 6.2 A decisão central: um view-model, duas fontes

Este é o ponto que faz o requisito *"as telas de histórico devem ser IDÊNTICAS às da inferência
dinâmica"* ser verdadeiro **por construção**, e não por disciplina.

Existe **um único** tipo de view-model — `ThinkingRun` — e **dois adaptadores** que o produzem:

```
WebSocket (ao vivo)  ──►  reasoningRunReducer(event)      ──┐
                                                            ├──►  ThinkingRun  ──►  <RalphView />
GET /sessions/{id}   ──►  sessionToThinkingRun(document)  ──┘                         ├── <RalphChatMode />
                                                                                      └── <RalphGraphMode />
```

`<RalphView />` **não sabe** de onde veio o `ThinkingRun`. Recebe também um booleano `isLive`, que
controla apenas detalhes de apresentação (cursor pulsante no passo corrente, *auto-scroll*,
botão de cancelar). Nada além disso pode diferir entre as duas telas.

A mesma regra vale para o fluxo simples: `<SimpleChatView />` recebe um `SimpleRun`, produzido ou
pela resposta do `POST` ou pela reconstrução da sessão `DIRECT`.

### 6.3 O view-model

```ts
// src/domain/types/thinkingRun.ts (referência — a FASE 05 define o arquivo final)

type ThinkingRun = {
  sessionId: string | null
  question: string
  modelName: string | null
  status: RunStatus                 // idle | running | completed | degraded | failed
  steps: ThinkingStep[]             // ordem cronológica — o Modo Chat renderiza isto
  tasks: TaskTimeline[]             // agregação por tarefa — o Modo Gráfico renderiza isto
  phases: PhaseProgress[]           // A1, A2, B, C1, C2, C3 com estado — a trilha macro
  finalAnswer: string | null
  totals: RunTotals                 // tokens, tempo de inferência, chamadas, tempo de parede
  degradations: RunDegradation[]
  error: RunError | null
}

type ThinkingStep = {
  id: string                        // determinístico e estável (ver FASE 05)
  order: number
  type: EventType                   // thinking | result | degraded | error
  subtype: EventSubtype
  phase: ThinkingPhase
  taskId: string                    // 'T1' | 'setup' | 'synthesis'
  content: string                   // markdown
  totalTokens: number               // acumulado da sessão no momento do evento
  contextId: string
  contextSize: number               // zera a cada reset — a serra dentada do fresh context
  inferenceTimeMs: number
  timestamp: string | null          // presente no histórico, ausente ao vivo
}

type TaskTimeline = {
  id: string                        // 'T1'
  title: string | null              // extraído do conteúdo de A2, quando disponível
  status: TaskStatus                // pending | running | approved | degraded | discarded
  origin: 'A2' | 'C2'               // planejamento inicial ou adicional
  attempts: TaskAttemptView[]       // uma por par (reasoning, verify_*)
  steps: ThinkingStep[]             // todos os passos desta tarefa
  contextIds: string[]              // quantas janelas esta tarefa consumiu
  tokens: number
  inferenceTimeMs: number
}
```

### 6.4 Estrutura de diretórios alvo

```
apps/frontend/
├── .env.example
├── .eslintrc.cjs                 (ou eslint.config.js)
├── .prettierrc
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── config/
    │   └── env.ts                        # único leitor de import.meta.env
    ├── router/
    │   ├── routes.ts                     # constantes de rota + builders de path
    │   └── AppRouter.tsx
    ├── domain/
    │   ├── enums/                        # eventType, eventSubtype, thinkingPhase, runStatus…
    │   ├── types/                        # contratos do backend + view-models
    │   └── services/
    │       ├── reasoningRunReducer.ts    # evento ao vivo  → ThinkingRun
    │       ├── sessionToThinkingRun.ts   # sessão salva    → ThinkingRun
    │       ├── sessionToSimpleRun.ts     # sessão DIRECT   → SimpleRun
    │       ├── deriveSubtype.ts          # tabela da seção 3.5
    │       ├── taskParser.ts             # extrai títulos/critérios do markdown de A2/C2
    │       └── formatters.ts             # tokens, ms, datas (Intl)
    ├── api/
    │   ├── httpClient.ts
    │   ├── websocketClient.ts
    │   ├── parsers/                      # unknown → tipo do domínio
    │   ├── messageApi.ts
    │   └── sessionApi.ts
    ├── hooks/
    │   ├── useSimpleInference.ts
    │   ├── useReasoningStream.ts
    │   ├── useSessionList.ts
    │   ├── useSession.ts
    │   ├── useAsync.ts
    │   └── useAutoScroll.ts
    ├── state/
    │   └── RunConfigContext.tsx          # modelo, max_tokens, temperature (global)
    ├── components/
    │   ├── primitives/                   # Button, IconButton, Switch, Segmented, Card, Badge,
    │   │                                 # Spinner, Skeleton, EmptyState, ErrorState, Tooltip
    │   ├── markdown/Markdown/
    │   ├── chat/                         # Composer, MessageBubble, MessageStats, ChatScroller,
    │   │                                 # PhaseTag, FinalAnswerCard
    │   ├── timeline/                     # PhaseTrack, PhaseNode, TaskLane, AttemptDot,
    │   │                                 # ContextMeter, LoopArc
    │   └── layout/                       # AppShell, TopBar, Sidebar, PageContainer
    ├── features/
    │   ├── home/
    │   ├── simple-chat/
    │   ├── ralph/
    │   └── history/
    └── styles/
        ├── reset.css
        ├── tokens.css                    # design tokens MacFirst
        └── animations.css
```

---

## 7. Variáveis de ambiente

**Regra 4 da seção 5, detalhada.** `src/config/env.ts` é o único módulo que lê `import.meta.env`.
Ele **valida na inicialização** e expõe um objeto congelado e tipado — exatamente como a classe
`Settings` faz no backend. Se uma variável obrigatória faltar ou tiver tipo errado, o app falha no
*boot* com uma mensagem que nomeia a variável, em vez de quebrar em runtime numa tela qualquer.

| Variável | Default | Descrição |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Origem HTTP do backend. |
| `VITE_WS_BASE_URL` | `ws://localhost:8000` | Origem WebSocket do backend. |
| `VITE_API_PREFIX` | `/v1` | Prefixo comum de todas as rotas. |
| `VITE_REQUEST_TIMEOUT_MS` | `60000` | Timeout das chamadas HTTP. |
| `VITE_DEFAULT_PROVIDER` | `open_router` | `provider` enviado no `llm_model_config`. |
| `VITE_AVAILABLE_MODELS` | *(CSV)* | Modelos oferecidos no seletor. **Precisa ser um subconjunto do `GENAI_AVAILABLE_MODELS` do backend** — caso contrário o backend recusa a chamada. |
| `VITE_DEFAULT_MODEL` | — | Modelo pré-selecionado. Precisa estar em `VITE_AVAILABLE_MODELS`. |
| `VITE_DEFAULT_MAX_TOKENS` | `1200` | `max_tokens` padrão. |
| `VITE_DEFAULT_TEMPERATURE` | `0.3` | `temperature` padrão. Backend exige `[0, 1]`. |
| `VITE_HISTORY_FETCH_CONCURRENCY` | `6` | Requisições simultâneas ao hidratar a lista de histórico. |
| `VITE_HISTORY_SUMMARY_MAX_CHARS` | `120` | Limite de caracteres do resumo (input do usuário) no card de histórico. |
| `VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS` | `48` | Limite do resumo na barra lateral reduzida. |
| `VITE_WS_OPEN_TIMEOUT_MS` | `15000` | Tempo máximo esperando a conexão WebSocket abrir. |
| `VITE_ENABLE_DEBUG_PANEL` | `false` | Painel de depuração com os frames crus do WebSocket. |

O arquivo `.env.example` precisa listar **todas** elas, com comentários por bloco — mesmo formato
do `.env.example` do backend. `.env` fica no `.gitignore`.

---

## 8. Regras de design — MacFirst

O alvo é a sensação de um aplicativo nativo da Apple rodando na web: **muito espaço em branco,
hierarquia por tipografia e não por caixas, bordas finíssimas, sombras quase imperceptíveis,
superfícies translúcidas e movimento curto com desaceleração natural.** Um usuário de macOS deve
sentir que o app pertence ao sistema.

### 8.1 Princípios

1. **Conteúdo primeiro, cromo depois.** A interface some; o texto do modelo é o protagonista.
   Barras de ferramenta são translúcidas e finas; nada de cabeçalhos coloridos ou grandes.
2. **Hierarquia por tipografia e espaço**, não por borda e preenchimento. Se dá para separar duas
   coisas com espaçamento, não use uma linha. Se dá com uma linha *hairline*, não use uma caixa.
3. **Escala de cinzas é a interface. Cor é informação.** Preto, branco e cinza formam 95% da tela.
   Cor só aparece quando **significa** alguma coisa (seção 8.3) — nunca como decoração.
4. **Uma ação primária por tela.** Fica evidente sem precisar gritar: contraste e posição, não
   tamanho e saturação.
5. **Movimento explica, não enfeita.** Transições curtas mostram de onde veio e para onde foi.
   Nada pisca, nada pula, nada gira sem motivo.
6. **Densidade confortável.** Linha de texto com 65–75 caracteres; `line-height` generoso (1.55 no
   corpo); respiro vertical entre blocos.

### 8.2 Tokens — a única fonte de verdade visual

Todos os valores abaixo vivem em `src/styles/tokens.css` como *custom properties*. **Nenhum
componente escreve um hex, um px de espaçamento, um raio ou uma duração literal** — sempre
`var(--token)`. Isso é verificável: um `grep` por `#` em `*.module.css` deve retornar vazio.

```css
:root {
  /* ─── Escala neutra (a interface) ─────────────────────────────── */
  --color-bg:              #F5F5F7;   /* fundo da janela */
  --color-surface:         #FFFFFF;   /* cartões, bolhas, painéis */
  --color-surface-sunken:  #FAFAFC;   /* áreas recuadas */
  --color-surface-overlay: rgba(255,255,255,0.72); /* barras translúcidas */
  --color-hairline:        rgba(0,0,0,0.08);
  --color-separator:       rgba(0,0,0,0.05);

  --color-text:            #1D1D1F;   /* texto primário — quase preto, nunca #000 */
  --color-text-secondary:  #6E6E73;
  --color-text-tertiary:   #8E8E93;
  --color-text-inverse:    #FFFFFF;

  /* ─── Cor pontual (a informação) ──────────────────────────────── */
  --color-accent:          #0A84FF;   /* etapa corrente, seleção, ação primária */
  --color-success:         #30D158;   /* verify_pass, tarefa aprovada, sessão completed */
  --color-warning:         #FF9F0A;   /* verify_fail, replan, degradação */
  --color-danger:          #FF453A;   /* erro, sessão failed */
  --color-context:         #BF5AF2;   /* fresh context / janela de contexto */

  /* Fundos suaves derivados — uso em badges e halos */
  --color-accent-soft:     rgba(10,132,255,0.10);
  --color-success-soft:    rgba(48,209,88,0.12);
  --color-warning-soft:    rgba(255,159,10,0.12);
  --color-danger-soft:     rgba(255,69,58,0.12);
  --color-context-soft:    rgba(191,90,242,0.12);

  /* ─── Tipografia ──────────────────────────────────────────────── */
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter",
               "Helvetica Neue", Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;

  --text-xs:   0.6875rem;  /* 11px — metadados, estatísticas */
  --text-sm:   0.8125rem;  /* 13px — rótulos, legendas */
  --text-base: 0.9375rem;  /* 15px — corpo (padrão macOS) */
  --text-lg:   1.0625rem;  /* 17px — título de seção */
  --text-xl:   1.375rem;   /* 22px — título de tela */
  --text-2xl:  2rem;       /* 32px — hero da home */

  --leading-tight: 1.25;
  --leading-body:  1.55;
  --tracking-tight: -0.015em;  /* títulos: leve aperto, como SF Display */

  /* ─── Espaçamento — escala de 4pt ─────────────────────────────── */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;  --space-4: 16px;
  --space-5: 20px;  --space-6: 24px;  --space-8: 32px;  --space-10: 40px;
  --space-12: 48px; --space-16: 64px; --space-20: 80px;

  /* ─── Raio ────────────────────────────────────────────────────── */
  --radius-sm: 6px;    /* badge, tag */
  --radius-md: 10px;   /* botão, input */
  --radius-lg: 14px;   /* cartão */
  --radius-xl: 20px;   /* painel, bolha de mensagem */
  --radius-pill: 999px;

  /* ─── Elevação — sombras curtas e difusas, nunca escuras ──────── */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04), 0 0 0 0.5px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.06), 0 0 0 0.5px rgba(0,0,0,0.04);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.10), 0 0 0 0.5px rgba(0,0,0,0.05);

  /* ─── Movimento ───────────────────────────────────────────────── */
  --ease-out:    cubic-bezier(0.32, 0.72, 0, 1);   /* a curva "Apple" */
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast:   140ms;
  --duration-base:   220ms;
  --duration-slow:   360ms;

  /* ─── Layout ──────────────────────────────────────────────────── */
  --measure:        72ch;    /* largura máxima de leitura */
  --content-max:    860px;   /* coluna central do chat */
  --sidebar-width:  272px;
  --topbar-height:  52px;
  --blur-overlay:   saturate(180%) blur(20px);
}
```

### 8.3 Semântica de cor — tabela obrigatória

Cor **nunca** é escolhida por gosto. Esta tabela é a lei; qualquer uso de cor fora dela precisa ser
justificado.

| Cor | Token | Onde aparece, e **só** aí |
|---|---|---|
| Azul | `--color-accent` | Etapa **corrente** na linha do tempo; item selecionado na barra lateral; foco de teclado; ação primária; link. |
| Verde | `--color-success` | `verify_pass`; tarefa aprovada; `store`; sessão `completed`. |
| Laranja | `--color-warning` | `verify_fail` (nova tentativa); `replan` (C.2); evento `degraded`; sessão `degraded`. |
| Vermelho | `--color-danger` | Evento `error`; sessão `failed`; falha de rede. |
| Roxo | `--color-context` | Tudo que fala de **janela de contexto**: `reset`, medidor de `context_size`, badge de `context_id`. É a cor do *fresh context* — o conceito-chave do paper. |
| Cinza | `--color-text-*` | Todo o resto: etapas futuras, metadados, estatísticas, bordas. |

Cor nunca é o **único** portador de informação: todo estado colorido leva também um ícone, um
rótulo ou uma forma distinta (requisito de acessibilidade — daltonismo).

### 8.4 Modo escuro

Obrigatório, via `@media (prefers-color-scheme: dark)` **redefinindo apenas os tokens** — nenhuma
regra de componente duplicada. No escuro: fundo `#000000`, superfícies `#1C1C1E`/`#2C2C2E`,
*hairlines* `rgba(255,255,255,0.10)`, texto `#F5F5F7`, e as cores de acento nas variantes mais
claras do sistema (`#0A84FF`, `#32D74B`, `#FF9F0A`, `#FF453A`, `#BF5AF2`). As sombras ficam mais
sutis e o contorno `0 0 0 0.5px` passa a fazer o trabalho de separação.

### 8.5 Padrões de componente

- **Barras (topo e laterais):** `background: var(--color-surface-overlay)` +
  `backdrop-filter: var(--blur-overlay)` + *hairline* de 0.5px embaixo. Sem sombra.
- **Botões:** altura 32px (`sm`) / 38px (`md`); `--radius-md`; primário = fundo `--color-accent`,
  texto branco; secundário = fundo `--color-surface` + *hairline*; terciário = só texto.
  Transição de `background-color` e `transform: scale(0.98)` no `:active`.
- **Campo de texto / *composer*:** superfície branca, *hairline*, `--radius-xl`, sombra `sm`; ao
  focar, o *hairline* vira `--color-accent` com halo `0 0 0 3px var(--color-accent-soft)`.
  Cresce em altura conforme o conteúdo, até um máximo, e então rola.
- **Bolhas de mensagem:** usuário à direita, fundo `--color-accent`, texto branco,
  `--radius-xl` com o canto inferior direito menor. Modelo à esquerda, fundo `--color-surface`,
  texto normal, *hairline*. Largura máxima `--measure`.
- **Estatísticas por mensagem:** faixa `--text-xs`, `--color-text-tertiary`, separadas por `·`,
  abaixo da bolha. Nunca competem com o conteúdo.
- **Foco:** `outline: 2px solid var(--color-accent); outline-offset: 2px`. Nunca `outline: none`
  sem substituto visível.
- **Scroll:** `scrollbar-width: thin`; barras aparecem no *hover* (comportamento macOS).

### 8.6 Movimento

| Situação | Animação | Duração |
|---|---|---|
| Mensagem nova chega | `opacity 0→1` + `translateY(6px→0)` | `--duration-base`, `--ease-out` |
| Troca de modo (chat ↔ gráfico) | *cross-fade* + `scale(0.98→1)` | `--duration-base` |
| Etapa corrente na linha do tempo | halo pulsando (`box-shadow` 2s, infinito) | — |
| Progresso da trilha | `stroke-dashoffset` animado | `--duration-slow` |
| Entrada de tela (rota) | *fade* + `translateY(8px)` | `--duration-base` |
| Skeleton | *shimmer* de 1.2s | — |

Tudo dentro de `@media (prefers-reduced-motion: reduce)` vira `animation: none` e
`transition-duration: 1ms`, mantendo só o *fade* onde necessário.

### 8.7 Responsividade

Desktop é o alvo primário (é um app de análise), mas nada pode quebrar abaixo de 768px:
a barra lateral do histórico vira uma gaveta sobreposta; a linha do tempo do Modo Gráfico rola
horizontalmente dentro do próprio container (**nunca** fazendo a página rolar na horizontal);
a coluna de chat ocupa a largura toda com margens de 16px.

---

## 9. Regras de reuso

O requisito *"sempre reutilizar código, templates, módulos"* é verificável, e estas são as regras:

1. **Procure antes de criar.** Antes de escrever qualquer componente, verifique
   `src/components/primitives/`. Se existe algo a 80% do que você precisa, **estenda por props**,
   não copie.
2. **Regra dos dois usos.** Na segunda vez que um trecho de JSX ou de CSS for necessário, ele vira
   componente ou token. Não espere a terceira.
3. **Duplicação zero entre ao vivo e histórico.** Se a FASE 07 precisar de um componente que a
   FASE 05/06 já criou, ela **importa** — não recria uma variante "para histórico". Se o
   componente não servir, o conserto é generalizá-lo com uma prop, e a fase antiga é ajustada.
4. **Um só renderizador de Markdown.** `<Markdown />` é o único ponto do app que fala com
   `react-markdown`. Toda mensagem, de todo fluxo, de toda tela, passa por ele.
5. **Um só componente de estatísticas.** `<MessageStats />` renderiza tokens/tempo/modelo tanto no
   fluxo simples quanto no Ralph, ao vivo e no histórico. Ele recebe um objeto normalizado pela
   camada de domínio, não campos soltos de DTO.
6. **Um só cliente HTTP e um só cliente WebSocket.** Nenhum `fetch` direto fora de `src/api/`.
7. **Formatação centralizada.** Tokens (`1.234`), tempo (`1,2 s` / `812 ms`), datas relativas
   (`há 3 min`) — tudo em `domain/services/formatters.ts`, com `Intl`. Nenhum `toFixed` espalhado.
8. **Layout compartilhado.** `<AppShell>`, `<TopBar>`, `<PageContainer>` são usados por todas as
   telas. Nenhuma tela inventa o próprio cabeçalho.

---

## 10. As fases de implementação

Execute na ordem. Cada fase entrega algo verificável e não antecipa trabalho da seguinte.

| Fase | Arquivo | Entrega |
|---|---|---|
| **01** | `FASE_01_FUNDACAO.md` | Scaffold Vite + React + TS, tooling, `env.ts`, design tokens, `AppShell`, roteamento, tema claro/escuro. Telas vazias navegáveis. |
| **02** | `FASE_02_CONTRATOS_E_API.md` | Tipos do contrato, enums do domínio, parsers de fronteira, `httpClient`, `websocketClient`, `messageApi`, `sessionApi`, `formatters`. Sem UI. |
| **03** | `FASE_03_DESIGN_SYSTEM.md` | Biblioteca de componentes reutilizáveis: primitivos, `<Markdown />`, `<MessageBubble />`, `<MessageStats />`, `<Composer />`, estados vazio/erro/skeleton. |
| **04** | `FASE_04_INFERENCIA_SIMPLES.md` | Home (barra de texto + as duas opções) e o chat da inferência simples, com estatísticas por mensagem. Fim a fim contra o backend. |
| **05** | `FASE_05_RALPH_MODO_CHAT.md` | `useReasoningStream`, `reasoningRunReducer`, o view-model `ThinkingRun`, Modo Chat com a resposta final destacada e o interruptor de modo. |
| **06** | `FASE_06_RALPH_MODO_GRAFICO.md` | Linha do tempo animada das fases do paper, com trilha macro A→B→C, faixa por tarefa, ciclo de tentativas, medidor de contexto e arcos de loop. |
| **07** | `FASE_07_HISTORICO.md` | Lista central de chats, barra lateral reduzida no detalhe, reconstrução `sessão → ThinkingRun`/`SimpleRun`, histórico idêntico ao ao vivo nos dois modos. |
| **08** | `FASE_08_QUALIDADE.md` | Acessibilidade, `prefers-reduced-motion`, responsividade, performance, tratamento de erro e degradação, suíte de testes e build de produção. |

---

## 11. Como verificar uma fase

Uma fase está concluída quando **todos** os itens abaixo são verdadeiros:

```bash
cd apps/frontend
npm run lint        # eslint — zero erros e zero avisos
npm run typecheck   # tsc --noEmit — zero erros
npm test            # vitest run — todos verdes
npm run build       # vite build — sem erro e sem aviso de chunk
```

Além disso, percorra a lista de **critérios de aceite** no fim do arquivo da fase, item por item,
e diga explicitamente se cada um foi atendido. Não marque como concluído o que não está.

E rode a verificação manual que a fase descreve, com o backend no ar:

```bash
cd apps/backend && uvicorn src.main:app --reload --port 8000
```

---

## 12. Como rodar

```bash
cd apps/frontend
npm install
cp .env.example .env     # ajuste VITE_AVAILABLE_MODELS e VITE_DEFAULT_MODEL
npm run dev              # http://localhost:5173
```

O backend precisa estar rodando em `http://localhost:8000` e a origem do front precisa constar em
`CORS_ALLOWED_ORIGINS` no `.env` do backend (o default já inclui `http://localhost:5173`).

Os modelos de `VITE_AVAILABLE_MODELS` precisam estar em `GENAI_AVAILABLE_MODELS` no backend, e o
provider (`VITE_DEFAULT_PROVIDER`, normalmente `open_router`) em `GENAI_AVAILABLE_PROVIDERS` —
senão toda chamada volta com erro de modelo indisponível.
