# FASE 06 — Ralph Loop Adaptado: Modo Gráfico

> Pré-requisito: FASES 01 a 05 concluídas e `feature_front/README.md` lido por completo —
> em especial a seção 2, que descreve as fases do paper que esta tela desenha.

---

## 1. Objetivo

Requisito, na íntegra: *"vai conter uma animação com cada uma das fases esperadas, em um 'caminho'
com estilo de 'linha do tempo', marcando a fase atual, as anteriores e próximas, dando a ideia de
continuidade. Esse modo deve ser extremamente visual e acoplado à divisão de fases propostas pelo
Ralph Loop adaptado."*

Esta é a tela que se projeta na apresentação do TCC. Ela precisa responder, de relance:

1. **Em que etapa do paper o sistema está agora?**
2. **O que já passou e o que ainda vem?**
3. **Quantas tarefas existem, quantas tentativas cada uma exigiu, quais foram reprovadas?**
4. **O contexto está sendo reinicializado de verdade?** (*Fresh Context* — o mecanismo central
   contra o *context rot*.)

Ela consome o **mesmo `ThinkingRun`** da FASE 05, sem processamento adicional de eventos crus, e
funciona identicamente ao vivo e no histórico.

---

## 2. Escopo

```
src/components/timeline/      PhaseTrack, PhaseNode, TrackConnector, LoopArc,
                              TaskLane, AttemptDot, ContextMeter, ContextSpark, LegendBar
src/features/ralph/graph/     RalphGraphMode, StepDetailPanel, RunSummaryPanel
src/domain/services/          graphLayout.ts  (cálculo puro de posições e estados)
```

**Não entra:** nenhuma biblioteca de gráfico ou de animação (proibidas pela seção 4 do README).
Tudo é SVG inline + CSS. Nenhuma alteração no reducer da FASE 05 — se faltar um dado, ele é
**derivado** aqui, em `graphLayout.ts`, de forma pura.

---

## 3. Anatomia da tela

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [ Gráfico | Chat ]                                        ← ViewModeSwitch  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ①  TRILHA MACRO — as fases do paper                                         │
│                                                                              │
│    ╭───────╮   ╭───────╮   ╭─────────────╮   ╭───────╮  ╭────╮   ╭───────╮   │
│    │  A.1  │───│  A.2  │───│      B      │───│  C.1  │──│ C.2│───│  C.3  │   │
│    │Critér.│   │Tarefas│   │ Execução em │   │Verif. │  │Repl│   │Resp.  │   │
│    │gerais │   │       │   │   Loop      │   │global │  │an. │   │final  │   │
│    ╰───────╯   ╰───────╯   ╰─────────────╯   ╰───────╯  ╰────╯   ╰───────╯   │
│       ✓           ✓            ◉ 2/3           ○          ⊘         ○        │
│                                  ▲                        ╰─────────╯        │
│                              (fase atual)              (arco de retorno)     │
│                                                                              │
│  ②  FAIXAS POR TAREFA — o loop de execução aberto                            │
│                                                                              │
│   T1 Identificar primos de 0 a 10                                   ✓ 966 tk │
│      ⟳ ──● reset ──▶ ◆ B.1 ──▶ ✓ B.2 ──▶ ▣ B.3 ──▶ ☀ B.4                     │
│                                                                              │
│   T2 Identificar primos de 11 a 20                                  ✓ 998 tk │
│      ⟳ ──● reset ──▶ ◆ B.1 ──▶ ✗ B.2 ──▶ ◆ B.1 ──▶ ✓ B.2 ──▶ ▣ ──▶ ☀         │
│                             ╰──── tentativa 1 reprovada ────╯                │
│                                                                              │
│   T3 Verificar interseção                            (planejada em C.2)  ◉   │
│      ⟳ ──● reset ──▶ ◆ B.1 ──▶ …                                             │
│                                                                              │
│  ③  JANELA DE CONTEXTO — a serra dentada do Fresh Context                    │
│                                                                              │
│   tokens                                                                     │
│    ▲        ╱|        ╱|         ╱|                                          │
│    │      ╱  |      ╱  |       ╱  |     ← context_size, zera a cada reset    │
│    │    ╱    |    ╱    |     ╱    |                                          │
│    └──────────────────────────────────────▶  passos                          │
│         T1        T2        T3                                               │
│   total acumulado da sessão: ▁▂▃▄▅▆▇█  (sempre crescente)                     │
│                                                                              │
│  ④  RESUMO / DETALHE                                                         │
│   Clique em qualquer nó → painel lateral com o conteúdo Markdown do passo     │
└──────────────────────────────────────────────────────────────────────────────┘
```

A tela usa `<PageContainer width="wide">` (criado na FASE 01), não a coluna estreita do chat.

---

## 4. ① Trilha macro

É o "caminho" pedido no requisito. Seis nós, exatamente a divisão do paper:

| Nó | Rótulo | Subtítulo |
|---|---|---|
| `A1` | A.1 | Critérios de aceite gerais |
| `A2` | A.2 | Quebra em tarefas |
| `B` | B | Execução em Loop |
| `C1` | C.1 | Verificação global |
| `C2` | C.2 | Planejamento adicional |
| `C3` | C.3 | Resposta final |

Os rótulos vêm de `PHASE_LABEL`/`PHASE_SHORT_LABEL` (FASE 02). **Nenhum texto é escrito aqui.**

### Estados visuais de `PhaseNode`

| Estado | Visual |
|---|---|
| `done` (anterior) | Preenchido `--color-text` sobre `--color-surface`, ícone ✓, opacidade 1 |
| `active` (atual) | Contorno e texto `--color-accent`, **halo pulsando** (`box-shadow` animado, 2s, infinito), levemente maior (`scale(1.04)`) |
| `pending` (próxima) | Contorno tracejado `--color-hairline`, texto `--color-text-tertiary` |
| `skipped` | Contorno tracejado, ícone ⊘, opacidade 0.5, `title` "Não foi necessário" |

**A ideia de continuidade** — o ponto explícito do requisito — vem do **conector**, não dos nós:

- `TrackConnector` é um `<path>` SVG entre nós consecutivos.
- O trecho já percorrido é traçado em `--color-text`; o trecho futuro em `--color-hairline`.
- Quando uma fase se torna `active`, o conector que chega nela é **desenhado** com
  `stroke-dasharray` + `stroke-dashoffset` animando de 100% a 0 em `--duration-slow`. O caminho
  literalmente avança na tela.
- Enquanto uma fase está `active`, um ponto luminoso percorre o conector seguinte em loop lento
  (`offset-path` quando suportado; `translateX` em um `<circle>` caso contrário) — o sinal de
  "ainda em movimento".

### O nó `B` é especial

Ele agrega o loop inteiro. Precisa mostrar progresso interno:

- Um contador `2/3` (tarefas concluídas / total conhecido) abaixo do nó.
- Uma barra de progresso fina dentro do próprio nó, preenchendo conforme as tarefas fecham.
- Quando uma nova tarefa nasce em C.2, o total aumenta e a barra **recua proporcionalmente**, com
  transição suave. Isso é honesto e conta a história do replanejamento.

### Arcos de loop — o que torna a trilha fiel ao paper

Duas setas curvas de retorno, desenhadas como `<path>` SVG abaixo da trilha:

1. **B.2 → B.1** (dentro do nó `B`): um pequeno arco circular `⟳` no canto do nó, que **pisca uma
   vez em `--color-warning`** a cada `verify_fail` recebido. É a retentativa do paper.
2. **C.2 → B** : um arco largo ligando `C2` de volta a `B`. Fica em `--color-hairline` (quase
   invisível) enquanto C.2 não acontece, e se **acende em `--color-warning` e é desenhado da
   direita para a esquerda** quando um `replan` chega. É o ciclo de planejamento adicional.

Os dois arcos são o que diferencia esta tela de uma barra de progresso qualquer: eles mostram que
o fluxo **volta**.

---

## 5. ② Faixas por tarefa

Uma `TaskLane` por `TaskTimeline` do `ThinkingRun`, empilhadas verticalmente.

### Cabeçalho da faixa

`T1` (em `Tag` monoespaçada) · título da tarefa · `Badge` de status · tokens e tempo da tarefa.
Quando `origin === 'C2'`, um `Badge tone="warning"` "Planejada em C.2".

Status da faixa segue `TaskStatus`: `pending` (cinza tracejado), `running` (azul com halo),
`approved` (verde), `degraded` (laranja), `discarded` (cinza riscado, opacidade 0.5 — acontece
quando o orçamento estoura e o backend descarta as tarefas restantes).

### A trilha interna

Uma sequência horizontal de `AttemptDot`, um por passo da tarefa, na ordem em que os passos
chegaram, conectados por segmentos:

| Passo | Símbolo | Cor |
|---|---|---|
| `reset` | ● com raio | `--color-context` (roxo) |
| `execute` | ▷ | `--color-text-tertiary` |
| `reasoning` (B.1) | ◆ | `--color-text` |
| `verify_pass` (B.2) | ✓ | `--color-success` |
| `verify_fail` (B.2) | ✗ | `--color-warning` |
| `store` (B.3) | ▣ | `--color-success` |
| `learn` (B.4) | ☀ | `--color-text-secondary` |

Regras obrigatórias:

- **Cada tentativa é visualmente agrupada.** Tentativas além da primeira ficam sob uma chave
  (`╰── tentativa N ──╯`) em `--color-warning`, com o número da tentativa. É assim que o
  ciclo B.1 ⇄ B.2 do paper fica legível.
- O passo mais recente tem halo pulsante quando `isLive`.
- Cada ponto é um **`<button>`** (acessibilidade, regra 11): clicar abre o `StepDetailPanel` com o
  conteúdo Markdown completo daquele passo.
- Faixas novas entram animando (`fadeInUp`, `--duration-base`) — mostrar a tarefa nascer é parte
  da narrativa.
- Passos novos entram com o conector sendo desenhado (`--duration-fast`), e o ponto aparecendo com
  `scale(0.6 → 1)`.
- Sem espaço horizontal: a faixa rola **dentro de si mesma** (`overflow-x: auto`), nunca faz a
  página rolar na horizontal (seção 8.7 do README). Com `isLive`, a faixa ativa rola sozinha para
  manter o último ponto visível.

### Seta de aprendizados

O passo `learn` (B.4) de uma tarefa emite uma seta curva fina, em `--color-text-tertiary`
tracejada, até o `reset` (●) da **tarefa seguinte**, com o rótulo "aprendizados". O passo `store`
(B.3) emite outra seta, sólida, descendo até o bloco de C.1.

Isso desenha a invariante mais importante do paper, declarada na seção 2 do README: **resultado
alimenta a resposta final; aprendizado alimenta a próxima tarefa — e nunca o contrário.**
Uma legenda fixa (`LegendBar`) explica os dois traços.

---

## 6. ③ Janela de contexto

O painel que prova o *Fresh Context*. É um gráfico SVG próprio, pequeno (altura ~120px), largura
total.

- **Série 1 — `context_size`:** uma linha percorrendo os passos na ordem. A cada `reset` ela
  **despenca para zero** e recomeça a subir. O resultado é a serra dentada característica.
  Cor `--color-context`, com área preenchida em `--color-context-soft`.
- **Série 2 — `total_tokens`:** uma linha monotônica crescente, em `--color-text-tertiary`
  tracejada, na mesma escala vertical.
- Marcas verticais finas nas trocas de tarefa, com o id da tarefa abaixo.
- Um rótulo por "dente" com o `context_id` abreviado (7 caracteres), aparecendo no hover.
- Ao passar o mouse, uma linha guia vertical mostra os valores do passo sob o cursor.
- Cálculo de pontos: função pura em `graphLayout.ts`
  (`buildContextSeries(steps) → { contextPoints, totalPoints, resetIndices }`), com `viewBox`
  normalizado — **sem medir DOM**, para o gráfico ser testável sem navegador.
- Abaixo do gráfico, uma frase fixa em `--text-sm`/`--color-text-secondary`:
  *"O contexto é reinicializado a cada tarefa (Fresh Context); o consumo acumulado da sessão
  continua crescendo."* — é o que traduz o gráfico para quem vê pela primeira vez.

Este painel é colapsável, e lembra o estado em `localStorage`.

---

## 7. ④ Detalhe e resumo

### `StepDetailPanel`

Painel lateral direito (largura ~420px) que desliza (`translateX`, `--duration-base`) quando um nó
ou ponto é clicado:

- Cabeçalho: `PhaseTag` + id da tarefa + `MessageStats layout="panel"`.
- Corpo: o `content` do passo em `<Markdown>` — **o mesmo componente do Modo Chat** (regra de
  reuso 4). O Modo Gráfico **não** tem renderização própria de conteúdo.
- Rodapé: "Ver no Modo Chat", que alterna o modo e rola até aquele passo (usando o `step.id` como
  âncora — é por isso que o id é determinístico).
- Fecha com `Esc`, com clique fora e com o botão ✕. Foco fica preso no painel enquanto aberto
  (`role="dialog"` + `aria-modal`), e volta para o nó de origem ao fechar.
- Abaixo de 1024px, vira uma folha que sobe pela base da tela.

### `RunSummaryPanel`

Sempre visível no rodapé da tela, em `Card` com `MessageStats layout="panel"`:

| Métrica | Origem |
|---|---|
| Tokens totais | `run.totals.totalTokens` |
| Tempo de inferência | `run.totals.inferenceTimeMs` |
| Chamadas ao modelo | `run.totals.llmCalls` |
| Tarefas | `run.totals.taskCount` |
| Tentativas | `run.totals.attemptCount` |
| Janelas de contexto | `run.totals.contextCount` |
| Modelo | `run.modelName` |
| Status | `run.status` como `Badge` |

Quando `run.finalAnswer` existe, o `FinalAnswerCard` (FASE 03 — o mesmo do Modo Chat) aparece
**acima** do resumo. A resposta final é destacada nos dois modos; não é privilégio do Modo Chat.

---

## 8. `graphLayout.ts` — toda a matemática, pura

Nada de cálculo de posição dentro de componente. Funções puras, testáveis sem DOM:

```ts
export const buildMacroTrack = (run: ThinkingRun): MacroNodeView[]
export const buildTaskLanes = (run: ThinkingRun): TaskLaneView[]
export const buildContextSeries = (steps: ThinkingStep[]): ContextSeries
export const buildLoopArcs = (run: ThinkingRun): LoopArcView[]
export const findActiveStep = (run: ThinkingRun): ThinkingStep | null
export const describeTaskProgress = (run: ThinkingRun): { done: number; total: number }
```

Cada uma devolve coordenadas em um `viewBox` normalizado (`0..100` no eixo horizontal), e o CSS
cuida do tamanho real. Isso mantém o SVG responsivo sem `ResizeObserver`.

---

## 9. Animação — regras

| Evento | Animação | Duração |
|---|---|---|
| Fase se torna `active` | Conector anterior desenhado (`stroke-dashoffset`) + `scale(1 → 1.04)` no nó | `--duration-slow` |
| Fase concluída | ✓ aparece com `scale(0.6 → 1)` e o nó preenche | `--duration-base` |
| Fase ativa | Halo pulsando (2s, infinito) | — |
| Tarefa nova | `fadeInUp` da faixa | `--duration-base` |
| Passo novo | Conector desenhado + ponto com `scale` | `--duration-fast` |
| `verify_fail` | Arco ⟳ pisca em `--color-warning` (2 ciclos) | `--duration-slow` |
| `replan` | Arco C.2 → B desenhado da direita para a esquerda | `--duration-slow` |
| Série de contexto | Novo segmento desenhado | `--duration-fast` |
| Painel de detalhe | `translateX` + fade | `--duration-base` |

Todas usam `--ease-out`. **Todas** são desligadas sob `prefers-reduced-motion`, e nesse caso os
estados finais aparecem instantaneamente — a tela precisa continuar informativa, só sem movimento.

**Animar só o que mudou.** Use `key` estável (`step.id`, `task.id`) para que o React não remonte
nós já desenhados a cada evento — se a trilha inteira reanimar a cada passo, a tela vira um
piscante. Verifique isso explicitamente durante o desenvolvimento.

---

## 10. Responsividade

| Largura | Comportamento |
|---|---|
| ≥ 1280px | Layout completo, painel de detalhe lateral |
| 1024–1280px | Trilha macro com rótulos abreviados; painel lateral mais estreito |
| 768–1024px | Painel de detalhe vira folha inferior; faixas com rolagem horizontal própria |
| < 768px | Trilha macro rola horizontalmente (com indicador de rolagem); faixas empilhadas e compactas; gráfico de contexto com altura reduzida |

A página **nunca** rola horizontalmente. Cada elemento largo tem seu próprio
`overflow-x: auto`.

---

## 11. Testes exigidos

| Arquivo | O que verifica |
|---|---|
| `graphLayout.test.ts` | Com o `ThinkingRun` da execução real (mesma *fixture* da FASE 05): `buildMacroTrack` marca A1/A2/B/C1 como `done`, C2 como `skipped` e C3 como `active`/`done`; `buildTaskLanes` devolve 2 faixas com 5 passos cada; `buildContextSeries` tem um `resetIndex` por tarefa e o `context_size` **cai para zero** em cada um deles; a série de `total_tokens` é monotônica não decrescente. |
| idem | Execução com `verify_fail`: a faixa tem 2 tentativas e o **mesmo** `context_id` nas duas. |
| idem | Execução com `replan`: `buildLoopArcs` devolve o arco C.2 → B ativo. |
| `PhaseNode.test.tsx` | Cada estado renderiza o ícone e o `aria-label` corretos; `skipped` tem o `title` explicativo. |
| `TaskLane.test.tsx` | Um botão por passo; clicar chama `onStepSelect` com o `step.id`; a tarefa `discarded` recebe o tratamento visual e um rótulo acessível. |
| `RalphGraphMode.test.tsx` | Renderiza os quatro blocos; com `run` vazio mostra o `EmptyState`; com `isLive={false}` nenhum elemento tem a classe de halo pulsante; a resposta final aparece também neste modo. |
| `StepDetailPanel.test.tsx` | Abre com o conteúdo do passo em Markdown; `Esc` fecha; o foco volta ao elemento de origem; "Ver no Modo Chat" chama o callback de troca de modo com o `step.id`. |
| `contextSeries.a11y.test.tsx` | O gráfico SVG tem `role="img"` e um `aria-label` que descreve a série em texto (quantas reinicializações, pico de contexto, total acumulado) — um gráfico sem alternativa textual é inacessível. |

---

## 12. Verificação manual

1. Execute uma pergunta que gere pelo menos 3 tarefas (ex.: *"Compare as vantagens e desvantagens
   de energia solar, eólica e nuclear, e diga qual é a melhor para o Brasil"*).
2. Observe a trilha macro avançando: o conector é desenhado, o nó ativo pulsa, os anteriores
   ficam preenchidos, os próximos permanecem tracejados.
3. Confirme que o nó `B` mostra o contador de tarefas e que ele **aumenta o denominador** se um
   `replan` acontecer.
4. Provoque uma reprovação (uma pergunta com restrição difícil, ex.: *"Responda apenas com uma
   única palavra: qual é o maior país da América do Sul em área?"*) e verifique o arco ⟳ piscando
   e a segunda tentativa agrupada na faixa.
5. No gráfico de contexto, confirme a serra dentada: quedas a zero nos `reset`, linha acumulada
   sempre subindo.
6. Clique em um nó do meio: o painel abre com o Markdown daquele passo. "Ver no Modo Chat" leva ao
   passo correspondente, já rolado.
7. Alterne Gráfico ↔ Chat durante o stream: nada se perde, nada reinicia.
8. Ligue "reduzir movimento" no SO e repita: a tela continua legível e correta, sem animação.

---

## 13. Critérios de aceite

1. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro nem aviso.
2. A trilha macro tem exatamente os seis nós do paper, com os rótulos vindos de `PHASE_LABEL`.
3. Fase atual, anteriores e próximas são visualmente distintas, e o conector comunica continuidade
   (é desenhado, não só colorido).
4. O ciclo B.1 ⇄ B.2 e o retorno C.2 → B aparecem como **arcos de loop**, não como setas retas.
5. A serra dentada do `context_size` está visível e correta.
6. As setas de `store` → C.1 e `learn` → próxima tarefa existem e estão explicadas na legenda.
7. Nenhuma biblioteca de gráfico ou animação foi adicionada.
8. Todo cálculo de posição vive em `graphLayout.ts`, que é puro e testado sem DOM.
9. Todo nó e todo ponto é um elemento interativo real, alcançável por teclado, com rótulo
   acessível.
10. A página não rola horizontalmente em nenhuma largura entre 360px e 1920px.
11. O modo gráfico renderiza um `ThinkingRun` de histórico **sem nenhuma alteração de código** —
    verificável já na FASE 07.
