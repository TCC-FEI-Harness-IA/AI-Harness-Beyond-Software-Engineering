# FASE 01 — Fundação: scaffold, configuração, tokens e navegação

> Pré-requisito: ter lido `feature_front/README.md` por completo.
> Trabalhe em `apps/frontend/`. O diretório está vazio — esta fase o cria do zero.

---

## 1. Objetivo

Levantar o esqueleto do frontend com **todas as decisões estruturais do README já materializadas**:
projeto Vite + React + TypeScript estrito, camada de configuração por variáveis de ambiente,
*design tokens* MacFirst, casca de layout e navegação entre as telas — **sem nenhuma chamada ao
backend e sem nenhum componente de conteúdo**.

Ao fim desta fase deve ser possível navegar entre quatro telas vazias, sem refresh, com tema claro
e escuro funcionando, e o app deve **falhar no boot com mensagem clara** se uma variável de
ambiente obrigatória estiver ausente.

---

## 2. Escopo

**Entra nesta fase**

- `package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`
- ESLint + Prettier + Vitest configurados
- `.env.example` completo e `.gitignore`
- `src/config/env.ts` — o único leitor de `import.meta.env`
- `src/styles/` — `reset.css`, `tokens.css`, `animations.css`
- `src/router/` — rotas e `AppRouter`
- `src/components/layout/` — `AppShell`, `TopBar`, `PageContainer`
- `src/state/ThemeContext.tsx` — claro / escuro / sistema
- Quatro telas de placeholder em `src/features/`

**Não entra**

- Qualquer `fetch`, qualquer WebSocket, qualquer tipo de DTO (FASE 02)
- Qualquer componente primitivo além do estritamente usado pelo layout (FASE 03)
- Qualquer conteúdo real de tela (FASES 04–07)

---

## 3. Scaffold

### 3.1 `package.json`

```jsonc
{
  "name": "tcc-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "lint": "eslint . --max-warnings 0",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "@typescript-eslint/parser": "^8.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "eslint": "^8.57.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "jsdom": "^24.0.0",
    "prettier": "^3.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0"
  }
}
```

> `react-markdown` e `remark-gfm` já entram aqui porque são dependências declaradas do projeto,
> mas **só são usados na FASE 03**. Nenhuma outra dependência de runtime pode ser adicionada em
> nenhuma fase sem justificativa explícita — a lista fechada está na seção 4 do README.

### 3.2 `tsconfig.json`

Modo estrito de verdade — a regra 6 do README depende disto:

```jsonc
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "types": ["vite/client", "vitest/globals", "@testing-library/jest-dom"],

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "skipLibCheck": true,
    "noEmit": true,

    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

O alias `@/` precisa ser espelhado em `vite.config.ts` (`resolve.alias`) e na config do Vitest.
**Todo import interno usa `@/`** — nenhum `../../../` no projeto.

### 3.3 `vite.config.ts`

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { port: 5173 },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
```

`src/test/setup.ts` importa `@testing-library/jest-dom/vitest` e registra o `cleanup` automático.

### 3.4 ESLint

Regras que **precisam** estar ligadas, porque implementam regras do README:

| Regra | Implementa |
|---|---|
| `@typescript-eslint/no-explicit-any: error` | Regra 6 — `any` proibido |
| `@typescript-eslint/no-floating-promises: error` | Regra 9 — efeitos tratados |
| `@typescript-eslint/consistent-type-imports: error` | `verbatimModuleSyntax` |
| `react-hooks/rules-of-hooks: error` e `react-hooks/exhaustive-deps: error` | Regra 9 |
| `no-restricted-properties` para `window.location.reload` | Regra 8 — sem refresh |
| `no-restricted-globals` para `fetch` fora de `src/api/**` (via `overrides`) | Regra 3 e reuso 6 |
| `no-restricted-syntax` para `import.meta.env` fora de `src/config/env.ts` | Regra 4 |

As três últimas são o que torna as regras do README **verificáveis pelo lint** em vez de
dependerem de revisão humana. Implemente-as com `overrides` por caminho.

---

## 4. `src/config/env.ts` — a camada de configuração

É o espelho, no front, da classe `Settings` do backend: **lê tudo uma vez, converte, valida e
expõe um objeto congelado e tipado.**

**Requisitos:**

1. É o **único** arquivo do projeto que menciona `import.meta.env`.
2. Lê **todas** as variáveis da seção 7 do README, aplicando os defaults documentados lá.
3. Converte tipos: `readString`, `readNumber`, `readFloat`, `readBoolean`, `readList` (CSV → array
   aparado, sem vazios) — funções privadas do módulo.
4. **Valida na carga** e lança um erro que **nomeia a variável** quando:
   - uma variável sem default está ausente ou vazia;
   - um número não é numérico;
   - `VITE_DEFAULT_TEMPERATURE` está fora de `[0, 1]` (o backend recusa);
   - `VITE_DEFAULT_MAX_TOKENS` não é inteiro positivo;
   - `VITE_AVAILABLE_MODELS` está vazia;
   - `VITE_DEFAULT_MODEL` não pertence a `VITE_AVAILABLE_MODELS`;
   - `VITE_API_BASE_URL` não é URL válida ou `VITE_WS_BASE_URL` não começa com `ws://`/`wss://`.
5. Expõe também os **valores derivados**, para que ninguém concatene URL na mão:
   - `apiBaseUrl` → `${VITE_API_BASE_URL}${VITE_API_PREFIX}`
   - `wsBaseUrl` → `${VITE_WS_BASE_URL}${VITE_API_PREFIX}`
   (normalizando barras duplicadas e barra final).
6. O objeto exportado é `Object.freeze`-ado e tipado com `as const` / uma interface `AppEnv`.

**Forma esperada:**

```ts
export interface AppEnv {
  readonly apiBaseUrl: string
  readonly wsBaseUrl: string
  readonly requestTimeoutMs: number
  readonly defaultProvider: string
  readonly availableModels: readonly string[]
  readonly defaultModel: string
  readonly defaultMaxTokens: number
  readonly defaultTemperature: number
  readonly historyFetchConcurrency: number
  readonly historySummaryMaxChars: number
  readonly historySidebarSummaryMaxChars: number
  readonly wsOpenTimeoutMs: number
  readonly enableDebugPanel: boolean
}

export const env: AppEnv = loadEnv()
```

**Falha no boot, e não na tela.** `src/main.tsx` envolve o `render` em `try/catch`: se
`loadEnv()` lançar, pinta uma tela de erro de configuração (HTML mínimo, sem depender de nada do
app) com o nome da variável problemática. Isso evita o cenário em que o app sobe e só quebra
quando o usuário clica em enviar.

### `.env.example`

Espelha o formato do `.env.example` do backend — blocos comentados, todas as variáveis presentes:

```bash
# ─── Backend ──────────────────────────────────────────────────────────────────
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_API_PREFIX=/v1
VITE_REQUEST_TIMEOUT_MS=60000
VITE_WS_OPEN_TIMEOUT_MS=15000

# ─── Modelo ───────────────────────────────────────────────────────────────────
# Precisa ser subconjunto de GENAI_AVAILABLE_MODELS do backend.
VITE_DEFAULT_PROVIDER=open_router
VITE_AVAILABLE_MODELS=
VITE_DEFAULT_MODEL=
VITE_DEFAULT_MAX_TOKENS=1200
VITE_DEFAULT_TEMPERATURE=0.3

# ─── Histórico ────────────────────────────────────────────────────────────────
VITE_HISTORY_FETCH_CONCURRENCY=6
VITE_HISTORY_SUMMARY_MAX_CHARS=120
VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS=48

# ─── Depuração ────────────────────────────────────────────────────────────────
VITE_ENABLE_DEBUG_PANEL=false
```

Adicione `.env` ao `.gitignore` do projeto (o `.gitignore` da raiz já cobre `.env`, mas garanta).

---

## 5. Design tokens

Crie `src/styles/tokens.css` com **exatamente** o bloco `:root` da seção 8.2 do README, mais o
bloco de tema escuro. A estrutura obrigatória:

```css
:root            { /* tokens claros — seção 8.2 do README */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme='light']) { /* redefine SÓ as cores — seção 8.4 */ }
}

:root[data-theme='dark']  { /* mesmas redefinições, para o toggle manual */ }
:root[data-theme='light'] { /* garante o claro mesmo em SO escuro */ }
```

**Regras:**

- Só **cores** são redefinidas no escuro. Espaçamento, raio, tipografia e duração são únicos.
- Nenhuma cor tem sua única definição dentro de um `@media` — todas nascem no `:root` claro.
- `reset.css`: `box-sizing: border-box` global, `margin: 0`, `body` com
  `background: var(--color-bg)`, `color: var(--color-text)`, `font-family: var(--font-sans)`,
  `font-size: var(--text-base)`, `line-height: var(--leading-body)` e
  `-webkit-font-smoothing: antialiased`. `img`/`svg` com `max-width: 100%` e `display: block`.
  `button`/`input`/`textarea` herdam `font`. Scrollbar fina.
- `animations.css`: `@keyframes` reutilizáveis — `fadeInUp`, `fadeIn`, `pulseHalo`, `shimmer`,
  `drawLine` — e, no fim do arquivo, o bloco global:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Os três arquivos são importados **uma vez**, em `src/main.tsx`, nesta ordem:
`reset.css` → `tokens.css` → `animations.css`.

---

## 6. Tema

`src/state/ThemeContext.tsx` expõe `{ theme, setTheme }` com `theme: 'light' | 'dark' | 'system'`.

- Persiste a escolha em `localStorage` (chave `tcc.theme`), dentro de `try/catch` — em janela
  privada o acesso pode lançar, e o app precisa continuar funcionando com o default `system`.
- Aplica o resultado escrevendo `data-theme` no `<html>` (ou removendo o atributo, no modo
  `system`). **Nunca** re-renderiza a árvore inteira por causa de tema — a troca é só CSS.
- O controle visual fica na `TopBar`, como um botão de três estados com ícone SVG inline.

---

## 7. Roteamento

`src/router/routes.ts` — constantes e *builders*, para que nenhum path literal apareça em
componente:

```ts
export const ROUTES = {
  home: '/',
  simpleChat: '/chat/simples',
  ralphChat: '/chat/ralph',
  history: '/historico',
  historyDetail: '/historico/:sessionId',
} as const

export const buildHistoryDetailPath = (sessionId: string): string =>
  ROUTES.historyDetail.replace(':sessionId', encodeURIComponent(sessionId))
```

`src/router/AppRouter.tsx` monta o `BrowserRouter` com as rotas acima, mais uma rota `*` de
"não encontrado". Requisitos:

- **Sem refresh:** navegação só por `<Link>` e `useNavigate`. Nenhum `<a href>` interno.
- Transição de entrada de rota com `fadeInUp` (`--duration-base`), respeitando reduced-motion.
- O `sessionId` da rota de detalhe é lido com `useParams` e **decodificado** antes do uso.

---

## 8. Casca de layout

### `AppShell`

Estrutura de página usada por **todas** as telas (regra de reuso 8):

```
<AppShell>
  <TopBar />                      // fixa, translúcida, 52px
  <main>                          // rola; recebe o conteúdo
    {children}
  </main>
</AppShell>
```

Props: `{ children, sidebar?: ReactNode }`. Quando `sidebar` é passado (só o histórico faz isso, na
FASE 07), o `<main>` vira um grid de duas colunas — `--sidebar-width` + resto. **Deixe esse slot
pronto agora** e não o use nesta fase.

### `TopBar`

- Esquerda: nome do app (`--text-sm`, `--color-text-secondary`) — clicável, leva à home.
- Centro: vazio nesta fase (a FASE 05 põe o interruptor de modo aqui).
- Direita: link "Histórico" + botão de tema.
- Visual: `--color-surface-overlay` + `backdrop-filter: var(--blur-overlay)` + *hairline*
  inferior de 0.5px. `position: sticky; top: 0; z-index: 10`.

### `PageContainer`

`max-width: var(--content-max)`, centralizado, `padding-inline: var(--space-4)` e
`padding-block: var(--space-8)`. Prop `width?: 'content' | 'wide' | 'full'` para o Modo Gráfico
(FASE 06) poder ocupar mais espaço sem inventar layout novo.

---

## 9. Telas de placeholder

Crie as quatro, cada uma só com seu título e uma frase, usando `PageContainer`:

| Rota | Arquivo | Placeholder |
|---|---|---|
| `/` | `features/home/HomePage.tsx` | "Home" |
| `/chat/simples` | `features/simple-chat/SimpleChatPage.tsx` | "Inferência Simples" |
| `/chat/ralph` | `features/ralph/RalphPage.tsx` | "Ralph Loop Adaptado" |
| `/historico` | `features/history/HistoryListPage.tsx` | "Histórico" |
| `/historico/:sessionId` | `features/history/HistoryDetailPage.tsx` | mostra o `sessionId` da URL |

Nenhuma delas faz chamada de rede nesta fase.

---

## 10. Testes exigidos

| Arquivo | O que verifica |
|---|---|
| `src/config/env.test.ts` | Com `import.meta.env` simulado: (a) carrega e converte corretamente; (b) lança nomeando a variável quando `VITE_DEFAULT_MODEL` não está em `VITE_AVAILABLE_MODELS`; (c) lança quando a temperatura está fora de `[0,1]`; (d) lança quando `VITE_WS_BASE_URL` não é `ws`/`wss`; (e) `apiBaseUrl` não gera barra dupla quando o base termina com `/`. |
| `src/router/AppRouter.test.tsx` | Renderizando em `MemoryRouter`: cada rota monta a tela certa; a rota desconhecida cai no "não encontrado"; `buildHistoryDetailPath` escapa id com caractere especial. |
| `src/state/ThemeContext.test.tsx` | Alternar o tema escreve `data-theme` no elemento raiz; a preferência persiste; um `localStorage` que lança não quebra o provider. |
| `src/components/layout/AppShell.test.tsx` | Renderiza `children`; sem a prop `sidebar` não existe região de barra lateral; com ela, existe. |

---

## 11. Critérios de aceite

1. `npm install && npm run dev` sobe o app em `http://localhost:5173` sem erro no console.
2. `npm run lint`, `npm run typecheck`, `npm test` e `npm run build` passam sem erro **nem aviso**.
3. Navegar entre as cinco rotas funciona **sem nenhum refresh** (a aba não recarrega; o estado do
   React persiste).
4. Um `grep -rn "import.meta.env" src/` retorna **apenas** `src/config/env.ts`.
5. Um `grep -rnE "#[0-9a-fA-F]{3,8}" src/ --include=*.module.css` retorna **vazio** — todas as
   cores vêm de tokens.
6. Um `grep -rn "\.\./\.\./" src/` retorna vazio — todos os imports internos usam `@/`.
7. Remover `VITE_DEFAULT_MODEL` do `.env` faz o app exibir uma tela de erro de configuração que
   **cita o nome da variável**, em vez de uma tela em branco.
8. Alternar o tema do sistema entre claro e escuro muda o app sem recarregar; o botão de tema
   sobrepõe a preferência do sistema e a escolha sobrevive a um F5.
9. Com "reduzir movimento" ligado no SO, nenhuma transição de rota anima.
10. A `TopBar` está translúcida com desfoque e *hairline*, sem sombra — conforme a seção 8.5 do
    README.
