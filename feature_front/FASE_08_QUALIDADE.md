# FASE 08 — Qualidade: acessibilidade, resiliência, desempenho e entrega

> Pré-requisito: FASES 01 a 07 concluídas e `feature_front/README.md` lido por completo.
> Esta fase **não adiciona funcionalidade**. Ela fecha o que ficou meio-fechado e torna o
> produto defensável.

---

## 1. Objetivo

Passar o app inteiro por uma auditoria contra as regras do README e corrigir o que estiver fora,
em cinco frentes:

1. Acessibilidade e teclado
2. Movimento e responsividade
3. Resiliência (erro, degradação, offline, dados estranhos)
4. Desempenho sob carga real de eventos
5. Entrega (build, documentação e verificação final)

Cada frente abaixo é uma **auditoria com lista fechada**: percorra item por item e registre o
resultado.

---

## 2. Auditoria de acessibilidade

### 2.1 Percurso obrigatório por teclado

Faça o caminho completo **sem tocar no mouse**, começando com `Tab` a partir da barra de endereço:

1. Home → escrever a pergunta → escolher o modo → enviar
2. Tela do Ralph → alternar Gráfico/Chat → abrir o detalhe de um nó → fechar com `Esc`
3. Ir ao Histórico → navegar pelos cards → abrir um → trocar de conversa pela barra lateral
4. Alternar o tema

**Critérios:** todo elemento interativo é alcançável; a ordem de foco segue a ordem visual; o
*focus ring* é sempre visível; nenhum foco fica preso fora de um diálogo; ao fechar o painel de
detalhe, o foco volta ao elemento que o abriu; `Esc` fecha painel e gaveta.

Adicione um **link "pular para o conteúdo"** como primeiro elemento focável do `AppShell`, visível
só quando focado.

### 2.2 Semântica

| Verificação | Correção esperada |
|---|---|
| Nenhum `<div onClick>` | Trocar por `<button>` |
| Um único `<h1>` por tela, hierarquia sem pular níveis | Ajustar os níveis |
| Listas são `<ul>`/`<li>` (cards de histórico, faixas de tarefa, mensagens) | Trocar `div`s |
| Barra lateral é `<nav aria-label>` com `aria-current` no ativo | Ajustar |
| `SegmentedControl` e `Switch` com `role` e `aria-checked` corretos | Já feito na FASE 03 — confirmar |
| Ícones decorativos com `aria-hidden="true"`; ícones informativos com `<title>` no SVG | Ajustar |
| O SVG do gráfico de contexto tem `role="img"` e `aria-label` descritivo | Já exigido na FASE 06 — confirmar |
| Regiões que atualizam sozinhas (chat ao vivo, trilha) com `aria-live="polite"` | Ajustar |
| Nenhuma informação transmitida **só** por cor | Adicionar ícone ou rótulo |

### 2.3 Contraste

Verifique com o inspetor do navegador, **nos dois temas**:

- Texto primário sobre fundo: ≥ 7:1
- Texto secundário e `--text-xs` de estatísticas: ≥ 4.5:1 — **este é o que costuma falhar**;
  se `--color-text-tertiary` não passar, escureça o token (e não o uso pontual)
- Texto branco sobre `--color-accent`: ≥ 4.5:1
- Bordas e elementos de interface: ≥ 3:1

Correções vão **sempre** nos tokens de `tokens.css`, nunca em um componente específico.

### 2.4 Leitor de tela

Com o VoiceOver (⌘F5 no macOS), percorra a home e uma execução do Ralph. A pergunta, cada passo
anunciado e a resposta final precisam fazer sentido ouvidos em sequência. Corrija rótulos que
soarem como código (`"T1 verify_pass"` → `"Tarefa 1, verificação aprovada"`) — os textos vêm dos
mapas de rótulo da FASE 02, então a correção é lá, e vale para toda a UI.

---

## 3. Movimento e responsividade

### 3.1 `prefers-reduced-motion`

Ligue "Reduzir movimento" no SO e percorra o app inteiro. **Nada** pode animar: nem a trilha da
FASE 06, nem o indicador deslizante do `SegmentedControl`, nem o *shimmer* dos skeletons (que vira
um bloco estático), nem a transição de rota.

Confirme que o bloco global de `animations.css` (FASE 01) cobre tudo e que nenhum componente usa
`animation` via estilo inline, que escaparia da media query.

### 3.2 Larguras

Teste em 360, 414, 768, 1024, 1280 e 1920px. Em **todas**:

- A página **não rola horizontalmente** — verifique com
  `document.documentElement.scrollWidth > document.documentElement.clientWidth` no console
- Gutter lateral mínimo de 16px
- Nenhum texto cortado; nenhum botão sobreposto
- A trilha macro e as faixas de tarefa rolam **dentro de si mesmas**
- A barra lateral do histórico vira gaveta abaixo de 1024px, com foco preso e `Esc` para fechar
- O `Composer` continua utilizável com o teclado virtual aberto (`dvh`, não `vh`)

### 3.3 Zoom

Com zoom do navegador em 200%, o app continua utilizável: nada se sobrepõe, nada some.

---

## 4. Resiliência

Cada cenário abaixo precisa ter comportamento definido e verificado:

| Cenário | Como provocar | Comportamento exigido |
|---|---|---|
| Backend fora do ar | Parar o `uvicorn` | Erro em português com "Tentar de novo" em todas as telas; nenhuma tela em branco |
| Backend cai **no meio** do stream | Parar durante uma execução do Ralph | Fechamento anômalo → erro exibido, **todos os passos recebidos permanecem** nos dois modos |
| Modelo não permitido | `VITE_DEFAULT_MODEL` fora do `GENAI_AVAILABLE_MODELS` | `500`/`422` com mensagem clara; a pergunta continua na tela |
| Sem chave de API no backend | Esvaziar `OPENROUTER_API_KEY` | Idem |
| Resposta fora do contrato | Duplo de `fetch` devolvendo `{}` | `ContractError` com a mensagem genérica; nada quebra |
| Frame malformado no meio do stream | `FakeWebSocket` enviando `"{"` | O stream **continua**; um aviso aparece; os frames seguintes são processados |
| Sessão corrompida no histórico | Editar um JSON em `data/sessions/` removendo `totals` | `400` tratado na tela de detalhe; a lista continua funcionando e marca só aquele card |
| Execução degradada | `RALPH_MAX_TASK_ATTEMPTS=1` com uma pergunta difícil | Degradação visível nos dois modos, sem parecer erro; o fluxo chega à resposta final |
| Pergunta gigante | Colar ~2MB de texto | Ou o `Composer` limita antes de enviar, ou o fechamento `1009` é tratado com a mensagem certa |
| Aba em segundo plano durante o stream | Trocar de aba por 2 minutos | Ao voltar, todos os eventos estão lá, na ordem — sem reconexão e sem duplicação |
| Duplo clique em enviar | — | Uma única chamada / um único socket |
| `localStorage` indisponível | Janela privada com cookies bloqueados | Tema, modo e config caem nos defaults; **nada lança** |
| Voltar/avançar do navegador | Botões nativos | Estado coerente em todas as rotas, sem refresh, sem tela quebrada |

---

## 5. Desempenho

O cenário real é uma execução com 30–60 eventos chegando em poucos minutos, cada um com Markdown
de até alguns milhares de caracteres.

### 5.1 Medições obrigatórias

Com o React DevTools Profiler ligado, rode uma execução do Ralph e registre:

1. **Quantos componentes renderizam por evento.** O esperado é: o novo passo, o contêiner da lista
   e os elementos de progresso. **Não** os 30 passos anteriores.
2. **Tempo de commit por evento.** Alvo: < 16ms. Acima disso a interface engasga visivelmente
   durante a execução.
3. **Troca de modo.** Alvo: < 100ms do clique ao conteúdo pintado.

### 5.2 Correções permitidas

Apenas se a medição mostrar problema — **não otimize no escuro**:

- `React.memo` em `ThinkingStepMessage`, `Markdown`, `TaskLane` e `AttemptDot` (as duas primeiras
  já são exigidas nas FASES 03/05 — confirme que estão surtindo efeito)
- `useMemo` nas funções de `graphLayout.ts` chamadas no render, com dependência em
  `run.steps.length` e `run.status`
- `useCallback` nos handlers passados a componentes memoizados — sem isso o `memo` não serve
  para nada
- Agrupar `dispatch` em um *buffer* de um quadro (`requestAnimationFrame`) no
  `useReasoningStream`, **sem tocar no reducer**
- `content-visibility: auto` nos passos fora da viewport, se a lista ficar muito longa

**Proibido:** virtualização com biblioteca externa (dependência nova) e qualquer mudança que
altere a semântica do `ThinkingRun`.

### 5.3 Bundle

`npm run build` e verifique o relatório: o *chunk* principal deve ficar abaixo de ~250KB
comprimido. `react-markdown` + `remark-gfm` são a maior parte disso; se passar muito, aplique
`React.lazy` na tela do Ralph e no histórico (as duas que usam Markdown pesado), com `Suspense`
mostrando o skeleton que já existe.

---

## 6. Suíte de testes

### 6.1 Cobertura mínima por camada

| Camada | Alvo | Justificativa |
|---|---|---|
| `src/domain/services/` | **100%** | É a lógica pura do app: reducer, reconstrução, parsing, layout. Não tem desculpa para não estar coberta, e é onde um erro se propaga para as três telas |
| `src/api/` | ≥ 90% | Fronteira com o não confiável |
| `src/hooks/` | ≥ 85% | Orquestração |
| `src/components/` | ≥ 70% | Comportamento, não pixel |
| `src/features/` | ≥ 70% | Caminhos principais de cada tela |

Configure os limiares no `vitest.config` (`coverage.thresholds`) para que a regressão falhe o
comando, e adicione o script `npm run test:coverage`.

### 6.2 Testes de integração de tela

Três testes de ponta a ponta **com duplos de rede**, cobrindo os fluxos que o TCC demonstra:

1. **Fluxo simples completo:** home → escrever → escolher "Inferência Simples" → resposta com
   estatísticas na tela.
2. **Fluxo Ralph completo:** home → escolher "Ralph" → `FakeWebSocket` emite a sequência real de
   eventos da fixture → o Modo Chat mostra todos os passos e a resposta destacada → alternar para
   o Modo Gráfico mostra as tarefas e a trilha completa.
3. **Histórico:** lista com duas sessões → abrir a Ralph → barra lateral presente → os dois modos
   funcionam → voltar para a lista sem novas requisições.

### 6.3 Higiene

- Nenhum teste acessa rede real (`fetch` e `WebSocket` sempre substituídos)
- Nenhum teste depende de `setTimeout` real — use *fake timers*
- Nenhum teste consulta por classe CSS ou `data-testid` onde existe um papel acessível
- Nenhum aviso do React no console durante a suíte (`act`, `key`, `setState` após unmount) — trate
  aviso como falha

---

## 7. Auditoria das regras do README

Rode e registre a saída de cada verificação. Todas precisam estar limpas:

```bash
cd apps/frontend

# Regra 4 — só env.ts lê variáveis de ambiente
grep -rn "import.meta.env" src/ | grep -v "src/config/env.ts"

# Regra 3 / reuso 6 — rede só em src/api/
grep -rn "fetch(\|new WebSocket" src/ | grep -v "^src/api/"

# Reuso 4 — um só renderizador de Markdown
grep -rn "react-markdown" src/ | grep -v "src/components/markdown/"

# Regra 6 — sem any
grep -rn ": any\|as any\|@ts-ignore" src/

# Regra 8 — sem refresh
grep -rn "location.reload\|location.href =" src/

# Seção 8.2 — sem cor literal
grep -rnE "#[0-9a-fA-F]{3,8}|rgb\(|hsl\(" src/ --include=*.module.css

# Regra 12 — sem animação fora do alcance de reduced-motion
grep -rn "animation:" src/ --include=*.tsx

# Imports relativos profundos
grep -rn "\.\./\.\./" src/
```

Cada resultado não vazio é um defeito a corrigir — ou, se houver exceção legítima, ela é
documentada com um comentário no código explicando o porquê, e listada no relatório final da fase.

---

## 8. Entrega

### 8.1 `apps/frontend/README.md`

Escreva o README do app (não confundir com o desta feature), no mesmo espírito do
`apps/backend/README.md`:

- O que é e como se liga ao backend
- Como rodar (instalar, `.env`, `npm run dev`), incluindo o alinhamento obrigatório entre
  `VITE_AVAILABLE_MODELS` e `GENAI_AVAILABLE_MODELS`
- Scripts disponíveis
- Tabela completa de variáveis de ambiente
- Arquitetura em uma imagem (o bloco da seção 6.1 do README da feature)
- A decisão de "um view-model, duas fontes", que é o que explica a estrutura do código para quem
  chega depois
- Tabela de dependências e por que cada uma existe
- Onde ficam os design tokens e como mexer neles

### 8.2 Build de produção

```bash
npm run build && npm run preview
```

Percorra o app inteiro no *preview*, com o backend no ar. Nenhum erro de console, nenhum recurso
404, tema claro e escuro corretos.

### 8.3 Verificação final

```bash
npm run lint
npm run typecheck
npm test
npm run test:coverage
npm run build
```

Todos verdes, sem avisos.

---

## 9. Critérios de aceite

1. Os cinco comandos da seção 8.3 passam sem erro nem aviso, e os limiares de cobertura da
   seção 6.1 são atingidos.
2. O percurso completo por teclado (seção 2.1) funciona, incluindo o link "pular para o conteúdo".
3. Contraste verificado nos dois temas; correções feitas em tokens, não em componentes.
4. Com "reduzir movimento" ligado, **nada** anima em nenhuma tela.
5. Nenhuma das seis larguras testadas produz rolagem horizontal da página.
6. Todos os cenários da tabela da seção 4 têm comportamento verificado e documentado.
7. Durante uma execução do Ralph com 30+ eventos, o Profiler mostra que passos antigos **não**
   re-renderizam a cada evento.
8. Todas as verificações por `grep` da seção 7 estão limpas, ou as exceções estão documentadas.
9. `apps/frontend/README.md` existe e está completo.
10. Os três testes de integração de tela da seção 6.2 passam.
11. Nenhuma dependência de runtime além das quatro declaradas na seção 4 do README da feature.
