# FASE 03 — Design system: os componentes reutilizáveis

> Pré-requisito: FASES 01 e 02 concluídas e `feature_front/README.md` lido por completo.
> Esta fase constrói o **vocabulário visual inteiro** do app. Depois dela, nenhuma tela escreve
> CSS de componente — só compõe o que existe aqui.

---

## 1. Objetivo

Entregar a biblioteca de componentes de `src/components/`, aplicando literalmente as regras de
design MacFirst da seção 8 do README. Todo componente é **burro** (regra 3): recebe props, emite
callbacks, não faz rede, não lê `env`, não conhece rota.

Este é o investimento que faz o requisito *"sempre reutilizar código"* ser cumprido por
construção: as FASES 04 a 07 montam telas inteiras **sem criar componente visual novo**, salvo os
específicos da linha do tempo (FASE 06).

---

## 2. Escopo

```
src/components/
├── primitives/   Button, IconButton, Switch, SegmentedControl, Card, Badge, Tag,
│                 Spinner, Skeleton, Tooltip, EmptyState, ErrorState, Divider, StatItem
├── markdown/     Markdown
├── chat/         Composer, MessageBubble, MessageStats, PhaseTag, FinalAnswerCard,
│                 ChatScroller, TypingIndicator
└── layout/       (já existe da FASE 01: AppShell, TopBar, PageContainer)
```

Cada componente segue a regra 2 do README: pasta própria com `Componente.tsx`,
`Componente.module.css` e `index.ts`.

**Não entra:** nada de `src/features/`, nada de linha do tempo (FASE 06), nenhuma chamada de rede.

---

## 3. Regras transversais desta fase

1. **Zero cor, espaçamento, raio ou duração literal.** Tudo `var(--token)`. Verificável por grep.
2. **Nenhum estilo inline** (`style={{...}}`), exceto para valores **calculados em runtime** que
   não podem ser token — e, nesse caso, passados como *custom property*:
   `style={{ '--progress': `${pct}%` } as CSSProperties}`.
3. **Variantes por prop, nunca por componente novo.** `<Button variant="primary" size="sm">`,
   não `<PrimaryButtonSmall>`.
4. **Toda prop de variante é uma união de literais**, nunca `string`.
5. **Todo componente interativo encaminha `ref`** (`forwardRef`) e aceita as props nativas do
   elemento que renderiza (`ComponentPropsWithoutRef<'button'>`), para nunca precisar de um
   *wrapper* só para passar `aria-*` ou `onKeyDown`.
6. **Acessibilidade não é opcional** (regra 11): elemento semântico real, rótulo acessível,
   teclado, `:focus-visible` com o *focus ring* do token.
7. **Cada componente tem um comentário de bloco em português** no topo, descrevendo para que serve
   e quais props existem.

---

## 4. Primitivos

### `Button`

```ts
interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  iconLeft?: ReactNode
  iconRight?: ReactNode
  fullWidth?: boolean
}
```

- `primary`: fundo `--color-accent`, texto `--color-text-inverse`.
- `secondary`: fundo `--color-surface`, *hairline*, texto `--color-text`.
- `ghost`: sem fundo nem borda; fundo `--color-accent-soft` no hover.
- `danger`: fundo `--color-danger-soft`, texto `--color-danger`.
- Alturas: 30 / 36 / 44px. Raio `--radius-md`. `:active { transform: scale(0.98) }` com
  `transition: var(--duration-fast) var(--ease-out)`.
- `loading` → mostra `<Spinner size="sm">` no lugar do `iconLeft`, aplica `aria-busy` e
  `disabled`, e **preserva a largura** do botão (sem pulo de layout).
- `disabled` → `opacity: 0.4`, `cursor: not-allowed`, sem hover.

### `IconButton`

Mesmas variantes, quadrado, com `aria-label` **obrigatório** no tipo (não opcional — force isso no
TypeScript: `aria-label: string`).

### `Switch`

O interruptor do estilo macOS, usado pelo seletor de modo (FASE 05) e por qualquer liga/desliga.

- `<button role="switch" aria-checked={checked}>` com trilho `--radius-pill` e polegar branco com
  `--shadow-sm`.
- Ligado: trilho `--color-accent`. Desligado: trilho `--color-hairline`.
- Polegar animado com `transform: translateX()` em `--duration-fast`/`--ease-out`.
- Props: `{ checked, onChange, label, disabled }`. `label` vira `aria-label`.

### `SegmentedControl`

O controle segmentado da Apple — **este é o componente que a FASE 05 usa para o interruptor
"Modo gráfico / Modo chat"**, então ele precisa ficar bom:

```ts
interface SegmentedControlProps<T extends string> {
  options: ReadonlyArray<{ value: T; label: string; icon?: ReactNode }>
  value: T
  onChange: (value: T) => void
  size?: 'sm' | 'md'
  ariaLabel: string
}
```

- Trilho `--color-surface-sunken` com *hairline*, `--radius-md`, `padding: 2px`.
- O indicador do item selecionado é **um único elemento** que **desliza** entre as posições
  (`transform: translateX()` + `width`), fundo `--color-surface`, `--shadow-sm`. Não é
  "acender o fundo do botão selecionado" — é o retângulo que se move. É esse detalhe que dá a
  sensação nativa.
- Implementação: `role="radiogroup"` com `ariaLabel`; cada opção é um `<button role="radio"
  aria-checked>`. Setas ← → navegam entre as opções.
- Genérico em `T` para que o consumidor receba o valor já tipado (`'graph' | 'chat'`).

### `Card`

`{ children, padding?: 'sm'|'md'|'lg', elevation?: 'flat'|'sm'|'md', interactive?: boolean,
as?: 'div'|'article'|'li' }`. `interactive` adiciona hover (`translateY(-1px)` + `--shadow-md`) e
`:focus-visible`. Fundo `--color-surface`, *hairline*, `--radius-lg`.

### `Badge` e `Tag`

`Badge`: pílula pequena colorida por `tone` (`neutral | accent | success | warning | danger |
context`), com fundo `*-soft` e texto na cor cheia. `--text-xs`, `--radius-pill`.
`Tag`: retangular, monoespaçada (`--font-mono`), para identificadores técnicos (`T1`,
`context_id`, nome do modelo). `--radius-sm`, fundo `--color-surface-sunken`.

> **Regra de acessibilidade (seção 8.3 do README):** `Badge` com `tone` diferente de `neutral`
> **precisa** receber também um ícone ou um texto que carregue o significado. Cor sozinha não
> informa.

### `Spinner`, `Skeleton`

`Spinner`: SVG inline com `stroke-dasharray` girando; tamanhos `sm|md`; `role="status"` +
`aria-label`. Nunca ocupa a tela inteira.
`Skeleton`: bloco com *shimmer* (`--duration` longo, `animations.css`); props
`{ width, height, radius, lines }`. Com `lines > 1` gera várias barras de larguras levemente
diferentes (a última mais curta), que é o que faz o esqueleto parecer texto.

### `EmptyState` e `ErrorState`

`EmptyState`: `{ icon, title, description, action? }` — centralizado, ícone grande em
`--color-text-tertiary`, título `--text-lg`, descrição `--color-text-secondary`.
`ErrorState`: `{ error: AppError, onRetry? }` — mostra `error.userMessage` (nunca a mensagem
técnica crua; essa vai para um `<details>` recolhido, útil na banca), ícone em `--color-danger`,
botão "Tentar de novo" quando `onRetry` existe.

### `StatItem`

A unidade atômica das estatísticas: `{ label, value, tone?, icon?, title? }`. Renderiza
`label` em `--text-xs`/`--color-text-tertiary` e `value` em `--text-xs`/`--color-text-secondary`,
com `title` para o *tooltip* nativo. É a peça que `MessageStats` repete.

### `Tooltip`

Leve, CSS puro (`::after` + `::before` com `content: attr(data-tooltip)`), aparecendo em
`:hover`/`:focus-visible` com atraso de 400ms. Nada de biblioteca de posicionamento — se um caso
precisar de posicionamento inteligente, use o `title` nativo.

---

## 5. `Markdown`

**O único ponto do app que fala com `react-markdown`** (regra de reuso 4). Toda mensagem, de todo
fluxo, de toda tela, passa por aqui.

```ts
interface MarkdownProps {
  content: string
  /** 'bubble' herda a cor do container (bolha azul do usuário); 'block' usa as cores de texto padrão. */
  variant?: 'block' | 'bubble'
}
```

**Requisitos:**

1. `remark-gfm` ligado — os templates do backend usam tabelas, listas e *strikethrough*.
2. **Nunca** habilite `rehype-raw` nem `dangerouslySetInnerHTML`. O conteúdo vem de um LLM: HTML
   cru é vetor de XSS. `react-markdown` sem `rehype-raw` já escapa por padrão — mantenha assim.
3. **Estilos tipográficos completos**, todos com tokens, dentro do `.module.css`:
   - `h1..h4`: `--tracking-tight`, escala descendente a partir de `--text-lg`; margem superior
     `--space-6`, inferior `--space-2`. **Não** deixe títulos de Markdown maiores que o título da
     tela — o conteúdo do modelo abre com `##` com frequência.
   - `p`: `--leading-body`, margem `--space-3` entre parágrafos.
   - `ul`/`ol`: `padding-left: var(--space-5)`; itens com `--space-1` de respiro.
   - `code` inline: `--font-mono`, `--text-sm`, fundo `--color-surface-sunken`, `--radius-sm`,
     `padding: 1px 5px`.
   - `pre`: fundo `--color-surface-sunken`, *hairline*, `--radius-md`, `padding: var(--space-4)`,
     **`overflow-x: auto`** — nunca deixe código estourar a largura da bolha.
   - `table`: `border-collapse: collapse`, cabeçalho com fundo `--color-surface-sunken`, células
     com *hairline*; envolvida em um `div` com `overflow-x: auto`.
   - `blockquote`: barra de 3px `--color-hairline` à esquerda, texto `--color-text-secondary`.
   - `a`: `--color-accent`, sublinhado só no hover; `target="_blank"` + `rel="noreferrer"`.
   - `hr`: 1px `--color-separator`, margem `--space-6`.
4. `variant="bubble"`: usa `color: inherit` em tudo e troca os fundos de `code`/`pre` por
   `rgba(255,255,255,0.18)`, para funcionar sobre a bolha azul do usuário.
5. **Memoize** (`React.memo` com comparação por `content` e `variant`). Mensagens antigas não
   podem re-renderizar a cada evento novo do stream — no Ralph chegam dezenas.
6. O primeiro e o último filho não têm margem externa (`:first-child { margin-top: 0 }`), senão
   toda bolha ganha um respiro fantasma.

---

## 6. Componentes de chat

### `Composer`

A barra de texto da home e do chat.

```ts
interface ComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  placeholder?: string
  disabled?: boolean
  busy?: boolean
  /** Ações renderizadas abaixo do campo — a home passa os dois botões de modo. */
  footer?: ReactNode
  autoFocus?: boolean
  maxLength?: number
}
```

- `<textarea>` que **cresce com o conteúdo** até um máximo (~40vh) e então rola. Implemente
  ajustando `height` a partir de `scrollHeight` em um `useLayoutEffect` — e **reseta para `auto`
  antes de medir**, senão a caixa só cresce e nunca encolhe.
- **Enter envia; Shift+Enter quebra linha.** No mobile (`matchMedia('(pointer: coarse)')`), Enter
  quebra linha e o envio é só pelo botão.
- Não envia quando o valor está vazio ou só com espaços, nem quando `busy`.
- Visual: `--radius-xl`, `--shadow-sm`, *hairline*; ao focar, borda `--color-accent` + halo
  `0 0 0 3px var(--color-accent-soft)`; transição em `--duration-fast`.
- Botão de envio circular no canto inferior direito do campo, `IconButton` com seta para cima,
  desabilitado quando não há o que enviar. Vira `Spinner` quando `busy`.
- `maxLength` mostra um contador discreto **apenas** quando passa de 90% do limite.

### `MessageStats`

O componente que cumpre o requisito *"todas as mensagens devem conter o modelo, gasto, tempo e
estatísticas gerais"*. É **um só** para os dois fluxos e para as duas telas (regra de reuso 5).

```ts
interface MessageStatsProps {
  stats: MessageStatsView
  /** 'inline' = faixa discreta sob a mensagem; 'panel' = grade, usada no rodapé de uma execução. */
  layout?: 'inline' | 'panel'
}

/** Vive em src/domain/types/ — normalizado pela camada de domínio, nunca um DTO cru. */
interface MessageStatsView {
  modelName: string | null
  tokensInput: number | null
  tokensOutput: number | null
  totalTokens: number | null          // acumulado da sessão, no Ralph
  inferenceTimeMs: number | null
  contextId: string | null
  contextSize: number | null
  timestamp: string | null
}
```

- Renderiza uma sequência de `StatItem` separados por `·`, omitindo silenciosamente os campos
  `null` (o fluxo simples não tem contexto; passos programáticos não têm tempo).
- Ordem fixa: **modelo · tokens · tempo · contexto**. Nunca muda entre telas — é o que permite
  comparar visualmente baseline e harness.
- Formatação **sempre** via `formatters.ts`: `formatTokens`, `formatDuration`, `formatDateTime`.
- O `contextSize` aparece com tom `context` (roxo) e o `contextId` abreviado em 7 caracteres,
  dentro de um `Tag`, com `title` mostrando o id inteiro.
- `layout="panel"`: grade de 2–4 colunas com rótulos acima dos valores, usada no resumo de uma
  execução inteira (totais da sessão).

### `PhaseTag`

Etiqueta que identifica a etapa do paper de uma mensagem — usada no Modo Chat do Ralph e no
histórico.

```ts
interface PhaseTagProps {
  phase: ThinkingPhase
  subtype: EventSubtype
  taskId?: string | null
  size?: 'sm' | 'md'
}
```

Renderiza `PHASE_SHORT_LABEL[phase]` + `SUBTYPE_LABEL[subtype]` (+ `taskId` quando houver), com o
`tone` vindo de `SUBTYPE_TONE` (FASE 02) e um ícone SVG por subtipo. **Nenhum texto nem cor é
decidido aqui** — tudo vem dos mapas da FASE 02.

Ícones (SVG inline de 14px, traço 1.5, em `src/components/chat/PhaseTag/icons/`):

| Subtype | Ícone |
|---|---|
| `setup` | lista com marcação |
| `tasks` | blocos empilhados |
| `execute` | play |
| `reasoning` | balão de pensamento |
| `verify_pass` | check |
| `verify_fail` | seta circular (repetir) |
| `store` | disco / caixa |
| `learn` | lâmpada |
| `reset` | raio / faísca (contexto novo) |
| `compile` | camadas convergindo |
| `replan` | ramificação |

### `MessageBubble`

```ts
interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  stats?: MessageStatsView
  header?: ReactNode          // PhaseTag, no fluxo Ralph
  tone?: Tone                 // borda/realce lateral, usado por verify_fail e degraded
  emphasis?: 'none' | 'final' // 'final' = resposta final destacada
  animateIn?: boolean
}
```

- `user`: alinhada à direita, fundo `--color-accent`, texto branco, `--radius-xl` com o canto
  inferior direito em `--radius-sm`. Markdown com `variant="bubble"`.
- `assistant`: à esquerda, fundo `--color-surface`, *hairline*, `--radius-xl` com canto inferior
  esquerdo em `--radius-sm`.
- `system`: largura total, sem bolha — texto `--text-sm` em `--color-text-secondary`, centralizado,
  com *hairlines* dos dois lados (o padrão de "separador com rótulo"). É assim que `reset` e
  `store` aparecem no Modo Chat, sem competir com o conteúdo.
- `tone` diferente de `neutral` adiciona uma barra de 2px na borda interna esquerda na cor
  correspondente. Nada de fundo colorido em bolha de conteúdo.
- `animateIn` aplica `fadeInUp` em `--duration-base`. **Só a mensagem recém-chegada anima** — quem
  controla isso é o consumidor, passando `animateIn` apenas para o último item.
- Largura máxima `--measure`.

### `FinalAnswerCard`

O destaque exigido pelo requisito *"deixando destacada a mensagem final"*.

```ts
interface FinalAnswerCardProps {
  content: string
  stats?: MessageStatsView
  label?: string     // default: 'Resposta final'
}
```

- `Card` de largura total (não bolha), `--radius-xl`, `--shadow-md`, fundo `--color-surface`.
- Cabeçalho com um `Badge tone="accent"` escrito "Resposta final" e um filete de 2px em
  `--color-accent` no topo do cartão.
- Tipografia um passo maior que a das demais mensagens (`--text-lg` no corpo) — é a única coisa na
  tela que recebe esse tratamento. É o que faz o olho ir direto nela ao rolar.
- Rodapé com `MessageStats layout="panel"` mostrando os totais da execução.
- Ao aparecer, anima com `fadeInUp` + um realce de `box-shadow` que decai em `--duration-slow`.

### `ChatScroller`

O container rolável das mensagens, com o comportamento de *stick to bottom* que todo chat precisa:

```ts
interface ChatScrollerProps {
  children: ReactNode
  /** Muda quando chega conteúdo novo; dispara a avaliação de auto-scroll. */
  contentKey: string | number
  isLive?: boolean
}
```

- Rola para o fim quando chega conteúdo novo **apenas se** o usuário já estava a menos de ~64px do
  fim. Se ele subiu para ler, **não puxe a tela** — mostre um botão flutuante "Ir para o fim" com
  contador de novas mensagens.
- `scroll-behavior: smooth`, desligado sob `prefers-reduced-motion`.
- A lógica de medição vive em `src/hooks/useAutoScroll.ts` (criado nesta fase), não no componente.
- `aria-live="polite"` na região, para que leitores de tela anunciem o conteúdo que chega.

### `TypingIndicator`

Três pontos pulsando em `--color-text-tertiary`, com `aria-label="Gerando resposta"`. Usado
enquanto se espera a primeira resposta do fluxo simples e entre eventos do Ralph.

---

## 7. Página de catálogo (obrigatória)

Crie a rota de desenvolvimento `/dev/componentes` (`features/dev/ComponentsGalleryPage.tsx`),
registrada **apenas** quando `env.enableDebugPanel` é verdadeiro, mostrando cada componente em
todas as suas variantes e estados, com um Markdown de exemplo que exercita títulos, listas,
tabela, código inline, bloco de código, citação e link.

Por que ela é obrigatória: é onde se verifica o design system nos dois temas de uma vez só, e é
onde as fases seguintes conferem se já existe um componente antes de criar outro (regra de
reuso 1). Também é a tela que se abre na apresentação do TCC para mostrar o sistema visual.

---

## 8. Testes exigidos

| Arquivo | O que verifica |
|---|---|
| `Button.test.tsx` | Renderiza o rótulo; `onClick` dispara; `disabled` e `loading` bloqueiam o clique; `loading` põe `aria-busy`. |
| `SegmentedControl.test.tsx` | Opção selecionada tem `aria-checked="true"`; clicar dispara `onChange` com o valor **tipado**; setas ← → mudam a seleção; `role="radiogroup"` tem o `aria-label`. |
| `Switch.test.tsx` | `role="switch"` com `aria-checked` correto; espaço/Enter alternam. |
| `Markdown.test.tsx` | Tabela GFM vira `<table>`; bloco de código vira `<pre><code>`; **HTML cru no conteúdo é exibido como texto, não interpretado** (teste de XSS — obrigatório); link recebe `rel="noreferrer"`. |
| `Composer.test.tsx` | Enter envia; Shift+Enter não envia; valor só com espaços não envia; `busy` bloqueia; a altura recalcula ao apagar texto (não fica travada no máximo). |
| `MessageStats.test.tsx` | Campos `null` não são renderizados; a ordem é modelo → tokens → tempo → contexto; os números saem formatados em pt-BR. |
| `MessageBubble.test.tsx` | `role="user"` e `role="assistant"` produzem estruturas distintas; `emphasis="final"` aplica o destaque; o conteúdo passa pelo `Markdown`. |
| `ChatScroller.test.tsx` | Conteúdo novo com o usuário no fim → rola; com o usuário longe do fim → **não** rola e mostra o botão "Ir para o fim". |
| `ErrorState.test.tsx` | Mostra `error.userMessage`; a mensagem técnica fica dentro de um `<details>`; "Tentar de novo" chama `onRetry`. |

---

## 9. Critérios de aceite

1. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro nem aviso.
2. `grep -rnE "#[0-9a-fA-F]{3,8}|[0-9]+px" src/components --include=*.module.css` só retorna
   ocorrências de `px` em valores que **não** existem como token (larguras de traço de 1px/0.5px e
   dimensões de ícone). Nenhum hex.
3. `grep -rn "style={{" src/components` só retorna casos que passam *custom properties*
   calculadas — nenhum estilo estático inline.
4. `grep -rn "react-markdown" src/` retorna **apenas** `src/components/markdown/Markdown/`.
5. O teste de XSS do `Markdown` passa: `<img src=x onerror=alert(1)>` no conteúdo aparece como
   texto literal na tela.
6. Com `VITE_ENABLE_DEBUG_PANEL=true`, `/dev/componentes` mostra todos os componentes, e a tela
   está correta nos temas claro **e** escuro, verificada manualmente nos dois.
7. Navegando só pelo teclado na página de catálogo, **todo** controle é alcançável e mostra
   *focus ring* visível.
8. Com "reduzir movimento" ligado, nenhum componente anima.
9. Nenhum componente de `src/components/` importa de `src/api/`, `src/features/`, `src/hooks/`
   (exceto `useAutoScroll`) ou `src/config/`.
