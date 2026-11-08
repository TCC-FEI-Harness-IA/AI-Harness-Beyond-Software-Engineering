<p align="center">
  <img src="src/assets/ralph_image.png" alt="Ralph, ícone do projeto" height="120" />
</p>

# Frontend — Ralph Wiggum Loop (harness) vs. inferência direta

Interface do TCC **"Um Harness de IA para Resolução de Perguntas em Linguagem Natural: Adaptando
o Ralph Wiggum Loop Além do Desenvolvimento de Software"**.

O backend (`apps/backend/`) expõe dois fluxos de inferência comparáveis para a mesma pergunta —
uma chamada única ao modelo (baseline) e o Ralph Loop Adaptado (harness), com planejamento,
execução em loop e síntese da resposta final. Este app torna **o processo** visível: mostra, ao
vivo, a decomposição em tarefas, o ciclo de tentativa e verificação, a reinicialização de contexto
(*fresh context*) e a síntese final — não só a resposta. Uma sessão salva é renderizada pelos
mesmos componentes da execução ao vivo, nos dois modos de visualização (Chat e Gráfico).

---

## Sumário

- [Como se liga ao backend](#como-se-liga-ao-backend)
- [Como rodar](#como-rodar)
- [Scripts disponíveis](#scripts-disponíveis)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Arquitetura em uma imagem](#arquitetura-em-uma-imagem)
- [A decisão central: um view-model, duas fontes](#a-decisão-central-um-view-model-duas-fontes)
- [Dependências](#dependências)
- [Design tokens](#design-tokens)

---

## Como se liga ao backend

O front fala com o backend por dois transportes:

| Fluxo | Transporte | Endpoint |
|---|---|---|
| Inferência simples (baseline) | HTTP `POST` | `/v1/message/default` |
| Ralph Loop Adaptado (harness) | WebSocket | `/v1/message/reasoning` |
| Histórico | HTTP `GET` | `/v1/sessions`, `/v1/sessions/{id}` |
| Limite de tokens por sessão do backend | HTTP `GET` | `/v1/limits` |
| Catálogo de modelos (lista de escolha e tela "Modelos") | HTTP `GET`, `POST`, `PUT`, `DELETE` | `/v1/models` |
| BenchMark — execução da bateria | WebSocket | `/v1/benchmark/run` |
| BenchMark — baterias e dataset | HTTP `GET` | `/v1/benchmark/sessions`, `/v1/benchmark/sessions/{id}`, `/v1/benchmark/questions` |
| BenchMark — reexecutar uma questão errada | WebSocket | `/v1/benchmark/sessions/{id}/questions/{question_id}/rerun` |
| BenchMark — exportar erros do Ralph Loop | HTTP `GET` | `/v1/benchmark/sessions/{id}/ralph-loop-errors/export` |

A página **BenchMark** (`/benchmark`) inicia uma bateria (quantidade de questões, questões em paralelo e a
configuração de modelo da home), acompanha o progresso pelos frames do WebSocket e lista as baterias; o
detalhe (`/benchmark/:id`) compara os fluxos e leva ao chat de cada sessão (`/benchmark/:id/sessao/:sessionId`).
Em Vestibulares, **Seleção de questões → Por matéria** mostra as sete matérias e seus limites.
Informe quantas questões deseja em cada uma, usando zero para excluí-la. O total é calculado
automaticamente, e o botão de início só é habilitado quando pelo menos uma questão está selecionada.
A bateria usa as primeiras questões de cada matéria na ordem do dataset. A opção **Quantidade total**
continua disponível. O detalhe da bateria mostra a distribuição por matéria persistida nas questões.
A página tem uma aba por benchmark: **Vestibulares** (padrão), **MMLU** e **GPQA**. A aba fica na URL
(`/benchmark?benchmark=mmlu`). Cada uma tem o próprio formulário de nova bateria, o acompanhamento da
bateria atual quando ela é daquele benchmark e o histórico só com as baterias dele. Só uma bateria roda
por vez: as outras abas mostram um aviso com o atalho **Acompanhar**. Na aba GPQA, escolha a variante
(Diamond, Main ou Extended). No MMLU, escolha o
protocolo generativo 0-shot ou 5-shot, uma disciplina ou todas, e a semente da amostra. O formulário inicia
com até 285 questões de teste, e pode executar de 1 questão até o conjunto inteiro. Em MMLU e GPQA, a seleção
**Por disciplina** define a quantidade de cada disciplina, de zero ao máximo dela. O histórico e o detalhe identificam o
dataset e o protocolo; o detalhe MMLU também mostra disciplinas, semente e revisão. A tabela pagina
100 questões por vez. Veja o [guia do MMLU](../backend/src/infra/benchmark/mmlu/README.md) para metodologia,
reprodução e limites de comparação com rankings externos.
O detalhe também traz o botão **Exportar erros do Ralph Loop**, que baixa um ZIP com as questões erradas no
Ralph Loop; fica desabilitado enquanto a bateria executa ou quando nenhuma questão errou nesse fluxo.
A conexão vive em `BenchmarkRunContext`, acima das rotas: navegar pelo app não interrompe a bateria; cancelar,
fechar ou recarregar a aba fecha o WebSocket e o backend a encerra como `interrupted`.

Toda comunicação passa por `src/api/` — um único cliente HTTP (`httpClient.ts`) e um único
cliente WebSocket (`websocketClient.ts`) — e toda resposta entra como `unknown` até passar por um
parser de fronteira em `src/api/parsers/`, que devolve o tipo do domínio ou lança um `ContractError`.

---

## Como rodar

```bash
npm install
cp .env.example .env     # ajuste VITE_DEFAULT_MODEL e VITE_AVAILABLE_PROVIDERS
npm run dev               # http://localhost:5173
```

O backend precisa estar rodando em `http://localhost:8000` (ou no que `VITE_API_BASE_URL`/
`VITE_WS_BASE_URL` apontarem), com a origem deste front (`http://localhost:5173` por padrão)
incluída em `CORS_ALLOWED_ORIGINS` no `.env` do backend.

**Alinhamento obrigatório entre front e backend:** os provedores de `VITE_AVAILABLE_PROVIDERS`
precisam ser um subconjunto de `GENAI_AVAILABLE_PROVIDERS` — do contrário toda chamada volta com erro
de provider indisponível. Os modelos não ficam mais no `.env`: a lista de escolha vem do catálogo do
backend (`GET /v1/models`, guardado no MongoDB) e é mantida na tela "Modelos" (`/modelos`), onde se
cadastra, edita e remove um modelo com preço, contexto e vazão. O provedor escolhido na barra de
configuração da home viaja em `llm_model_config.provider` e decide qual adapter do backend
atende a execução.

```bash
cd apps/backend && uvicorn src.main:app --reload --port 8000
```

---

## Scripts disponíveis

| Script | O que faz |
|---|---|
| `npm run dev` | Sobe o servidor de desenvolvimento (Vite), em `http://localhost:5173` |
| `npm run build` | `tsc --noEmit` seguido de `vite build` — falha se houver erro de tipo |
| `npm run preview` | Serve o build de produção localmente, para verificação final |
| `npm run lint` | `eslint` em todo o projeto, zero avisos tolerados |
| `npm run typecheck` | `tsc --noEmit` isolado |
| `npm test` | `vitest run` — toda a suíte, uma vez |
| `npm run test:watch` | `vitest` em modo observador |
| `npm run test:coverage` | `vitest run --coverage` — aplica os limiares de cobertura por camada |

---

## Variáveis de ambiente

`src/config/env.ts` é o **único** módulo do projeto autorizado a ler `import.meta.env` — ele
valida tudo na inicialização e expõe um objeto congelado e tipado, igual à classe `Settings` do
backend. Se uma variável obrigatória faltar ou tiver tipo errado, o app falha no *boot* com uma
mensagem que nomeia a variável.

| Variável | Default | Descrição |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Origem HTTP do backend. |
| `VITE_WS_BASE_URL` | `ws://localhost:8000` | Origem WebSocket do backend. |
| `VITE_API_PREFIX` | `/v1` | Prefixo comum de todas as rotas. |
| `VITE_REQUEST_TIMEOUT_MS` | `60000` | Timeout das chamadas HTTP. |
| `VITE_AVAILABLE_PROVIDERS` | *(o provedor padrão)* | Provedores oferecidos no seletor (CSV): `open_router`, `azure_ai_foundry`, `openai`. Precisa ser subconjunto de `GENAI_AVAILABLE_PROVIDERS` no backend. |
| `VITE_DEFAULT_PROVIDER` | `open_router` | `provider` pré-selecionado, enviado no `llm_model_config`. Precisa estar em `VITE_AVAILABLE_PROVIDERS`. |
| `VITE_DEFAULT_MODEL` | — | Modelo pré-selecionado. Quando o catálogo chega sem ele, vale o primeiro modelo do catálogo. |
| `VITE_DEFAULT_MAX_TOKENS` | `50000` | `max_tokens` padrão: limite de tokens (entrada + saída) **por sessão** imposto pelo front, somando todas as chamadas ao modelo. Nunca passa do limite por sessão do backend (`LLM_MAX_TOKENS`, lido em `GET /v1/limits`): o valor salvo ou digitado é rebaixado a ele. Para o Ralph, precisa ser maior que `RALPH_FINAL_ANSWER_TOKEN_RESERVE`. |
| `VITE_DEFAULT_TEMPERATURE` | `0.3` | `temperature` padrão. Backend exige `[0, 1]`. |
| `VITE_HISTORY_FETCH_CONCURRENCY` | `6` | Requisições simultâneas ao hidratar a lista de histórico. |
| `VITE_HISTORY_SUMMARY_MAX_CHARS` | `120` | Limite de caracteres do resumo no card de histórico. |
| `VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS` | `48` | Limite do resumo na barra lateral reduzida. |
| `VITE_WS_OPEN_TIMEOUT_MS` | `15000` | Tempo máximo esperando a conexão WebSocket abrir. |
| `VITE_ENABLE_DEBUG_PANEL` | `false` | Habilita a rota `/dev/componentes` (catálogo de componentes) e um painel de depuração. |

`.env.example` lista todas elas com comentários por bloco. `.env` fica no `.gitignore`;
`.env.test` é versionado e carregado automaticamente pelo Vite em modo `test` (Vitest), com
valores fixos e sem segredo — nenhum teste fala com um backend real.

---

## Arquitetura em uma imagem

Camadas espelham as do backend, com as mesmas dependências unidirecionais
(`features → hooks → api/domain → config`; `components` depende só de `domain` e `styles`;
`domain` não importa nada de `api`, `hooks`, `features` ou React):

```
apps/frontend/
├── public/            favicon.png — recorte do rosto de ralph_image.png (aba do navegador)
└── src/
    ├── config/       env.ts — único ponto que lê import.meta.env
    ├── router/        Rotas e navegação
    ├── domain/
    │   ├── enums/     subtype, phase, type, status, source, flow — const tipados
    │   ├── types/     Contratos do backend + view-models
    │   └── services/  reasoningRunReducer, sessionToThinkingRun, sessionToSimpleRun,
    │                  deriveSubtype, taskParser, graphLayout, formatters — lógica pura,
    │                  100% testável isolada, sem React e sem rede
    ├── api/           httpClient, websocketClient, parsers/ (unknown → domínio), messageApi,
    │                  sessionApi
    ├── hooks/         useSimpleInference, useReasoningStream, useSessionList, useSession,
    │                  useAsync, useAutoScroll — orquestração, sem JSX
    ├── state/         RunConfigContext, ThemeContext, ViewModeContext
    ├── components/    UI reutilizável e burra: primitives/, markdown/, chat/, timeline/, layout/
    ├── features/      Telas: home/, simple-chat/, ralph/, history/
    ├── assets/        ralph_image.png — ícone do projeto (TopBar, Home e READMEs)
    └── styles/        reset.css, tokens.css, animations.css
```

---

## A decisão central: um view-model, duas fontes

O requisito *"as telas de histórico devem ser idênticas às da inferência dinâmica"* é verdadeiro
**por construção**, não por disciplina. Existe um único tipo de view-model — `ThinkingRun` (Ralph)
e `SimpleRun` (baseline) — e adaptadores que o produzem a partir de duas fontes diferentes:

```
WebSocket (ao vivo)  ──►  reasoningRunReducer(event)      ──┐
                                                            ├──►  ThinkingRun  ──►  <RalphView />
GET /sessions/{id}   ──►  sessionToThinkingRun(document)  ──┘                         ├── <RalphChatMode />
                                                                                      └── <RalphGraphMode />
```

`<RalphView />` não sabe de onde veio o `ThinkingRun`. Recebe um booleano `isLive`, que controla
só detalhes de apresentação (cursor pulsante no passo corrente, auto-scroll, botão de cancelar) —
nada além disso pode diferir entre a tela ao vivo e a de histórico. A mesma regra vale para o
fluxo simples: `<SimpleChatView />` recebe um `SimpleRun`, vindo da resposta do `POST` ou da
reconstrução de uma sessão `DIRECT`.

**Versão do fluxo.** Todo frame traz `flow_version` (10 campos) e a sessão persistida também; uma sessão
Ralph antiga sem o campo é lida como versão 1 e a inferência direta como `null`
(`domain/enums/flowVersion.ts`). A versão é lida antes das fases, porque `A3` muda de significado:

| Versão | Trilha macro | `A3` | `A4` |
|---|---|---|---|
| 1 (sessões antigas) | A.1 → A.2 → A.3 → B → C.1 → C.2 → C.3 | Aprendizados do enunciado (`learn`) | — |
| 2 (atual) | A.1 → A.2 → A.3 → A.4 → B → C.1 → C.2 → C.3 | Validação da decomposição (`plan_rejected`, `plan_approved`, `tasks`) | Aprendizados do enunciado (`learn`) |

No fluxo versão 2, A.2 emite `plan_candidate`, que **nunca** cria faixa de tarefa nem entra no progresso;
A.3 emite `plan_rejected` ou `plan_approved`; só a confirmação (`tasks`, em A.3, uma única vez) cria as
tarefas. Cada reprovação ativa o arco `plan-revision` (A.3 → A.2) ao lado do nó A.3. Os rótulos
completos vêm de `getPhaseLabel(phase, flowVersion)` e de `getStepLabel` ("Plano candidato", "Plano
reprovado", "Plano aprovado", "Plano confirmado na fila", "Aprendizados do enunciado" em A.4 e, nas
sessões antigas, em A.3). Sessões versão 1 continuam abrindo com a trilha antiga; nelas, A.3 sem passos
aparece como "não foi necessária".

**Subtipo no histórico.** Sessões novas gravam em cada mensagem o `subtype` do evento emitido;
`domain/services/deriveSubtype.ts` usa esse valor diretamente, e registros sem evento (como a auditoria
de uma saída recusada) não viram passo. Sessões antigas não têm o campo, e o `subtype` continua derivado
de `(phase, source, content)`, numa tabela única reusada por toda reconstrução de histórico. Em qualquer
versão, C.3 só grava como etapa do sistema a auditoria de uma saída recusada, que não vira passo nem
resposta; a mensagem aceita é o `thinking/compile`, e o terminal `result/compile` que o backend emite em
seguida é reconstruído quando a sessão tem resposta final (o reducer não conta esse terminal como nova
chamada, nem um `error` em C.3 como resposta). O passo `execute` reconstruído traz o bloco da tarefa
confirmada exatamente como o backend o escreveu (`tasks`/`replan`), com critérios em inglês ou português
e dependências — nunca o de um candidato reprovado. `validatedPlanning.test.ts` compara o histórico com
**frames realmente capturados** do backend na mesma execução (`src/test/fixtures/capture-*.json`, geradas
por `apps/backend/tests/doubles/frontend_parity_capture.py` e conferidas por
`apps/backend/tests/infra/test_frontend_parity_fixtures.py`); `parity.test.ts` cobre sessões antigas com
uma sequência sintética.

**Critério técnico de B.2 (nova fase de validação — 02).** Os relatórios de B.2 passaram a trazer a linha
do critério técnico fixo `<task_id>-TECH` (e, numa revisora, `<task_id>-REV`). O frontend não interpreta
esses IDs: o relatório é mostrado como qualquer outro, a tentativa é aprovada ou reprovada pelo subtipo
(`verify_pass`/`verify_fail`), e o passo `execute` continua mostrando só os critérios planejados. A captura
`capture-v2-tech-retry.json` (reprovação só por TECH seguida de retentativa aprovada) entra na mesma
paridade ao vivo × histórico. Nenhuma mudança de código foi necessária; sessões antigas, sem TECH, seguem
iguais.

---

## Dependências

**Runtime** — lista fechada; adicionar qualquer outra exige justificativa explícita:

| Pacote | Para quê |
|---|---|
| `react`, `react-dom` | Base |
| `react-router-dom` | Rotas (`/`, `/chat/:sessionId`, `/historico`, `/historico/:sessionId`), navegação programática, deep link |
| `react-markdown` | Renderiza o `content` (Markdown) de toda mensagem, sem `dangerouslySetInnerHTML` |
| `remark-gfm` | Tabelas, listas de tarefas e *strikethrough* no Markdown dos templates do backend |

Sem UI kit, sem lib de animação (as animações são CSS), sem lib de ícones (SVG inline próprio),
sem `axios` (usa `fetch`), sem `lodash`, sem `moment`/`dayjs` (usa `Intl`), sem lib de gráfico (a
linha do tempo é SVG/CSS próprios), sem lib de estado global (Hooks + Context nativos).

**Desenvolvimento**: `vite`, `@vitejs/plugin-react`, `typescript`, `vitest` +
`@vitest/coverage-v8`, `jsdom`, `@testing-library/react` + `user-event` + `jest-dom`, `eslint` +
plugins (`@typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`),
`prettier`.

---

## Design tokens

O visual (MacFirst: muito espaço em branco, hierarquia por tipografia, bordas *hairline*, escala
de cinzas como interface e cor só como informação) vive inteiramente em
`src/styles/tokens.css`, como *custom properties* CSS — cor, tipografia, espaçamento (escala de
4pt), raio, elevação e movimento. Nenhum componente escreve um hex, um px de espaçamento, um raio
ou uma duração literal: sempre `var(--token)`. Modo escuro é obrigatório e vive só em
`@media (prefers-color-scheme: dark)` redefinindo os tokens — nenhuma regra de componente
duplicada. Para mudar uma cor, um espaçamento ou uma duração em todo o app, o ponto único é esse
arquivo.
