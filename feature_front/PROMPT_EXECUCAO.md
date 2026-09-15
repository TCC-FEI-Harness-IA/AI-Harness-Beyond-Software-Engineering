# Prompt padrão de execução de fase

Copie o bloco abaixo, **troque `05` pelo número da fase** (`01` a `08`) e envie ao modelo com CLI
(Claude Code, Codex, Devin, etc.) a partir da raiz do repositório.

---

## O prompt

```
Você vai implementar UMA ÚNICA fase do frontend deste projeto: a FASE 05.

═══════════════════════════════════════════════════════════════════════════
PASSO 1 — LEITURA OBRIGATÓRIA (antes de escrever qualquer linha de código)
═══════════════════════════════════════════════════════════════════════════

Leia, por completo e nesta ordem, estes dois arquivos:

  1. feature_front/README.md          ← LEIA INTEIRO. Não pule seções.
  2. feature_front/FASE_05_*.md       ← a fase que você vai implementar

O README é obrigatório mesmo que você ache que já entendeu a tarefa pelo nome da fase.
Ele contém, e nenhum outro arquivo contém:

  - o contrato completo do backend (endpoints HTTP, contrato do WebSocket, DTOs,
    códigos de fechamento, e a diferença entre o evento ao vivo e a mensagem
    persistida);
  - as fases do Ralph Loop adaptado, que é o que a interface visualiza;
  - as 17 regras de código obrigatórias (seção 5);
  - a arquitetura em camadas e o view-model único (seção 6);
  - as variáveis de ambiente (seção 7);
  - as regras de design MacFirst, com os design tokens (seção 8);
  - as regras de reuso (seção 9).

Os dois arquivos juntos são AUTOSSUFICIENTES. Não leia mais nada:

  ✗ não leia as outras FASE_*.md
  ✗ não leia docs/paper/TCC.tex
  ✗ não leia feature_ralph/
  ✗ não leia o código-fonte do backend em apps/backend/src/

  ✓ ÚNICA EXCEÇÃO: as fases 02, 05, 06 e 07 mandam usar os arquivos JSON de
    apps/backend/data/sessions/ como fixtures de teste. Leia-os quando a fase
    pedir explicitamente, e copie para src/test/fixtures/ os que você usar.

═══════════════════════════════════════════════════════════════════════════
PASSO 2 — IMPLEMENTE SOMENTE A FASE 05
═══════════════════════════════════════════════════════════════════════════

Trabalhe em apps/frontend/.

O ESCOPO É FECHADO. Implemente o que está na seção "Escopo" da FASE 05, e nada além:

  ✗ NÃO antecipe trabalho de fases seguintes, nem "só o comecinho", nem
    "já que estou aqui", nem deixando arquivo vazio preparado.
  ✗ NÃO refatore código de fases anteriores que a FASE 05 não mandou tocar.
  ✗ NÃO adicione funcionalidade que não foi pedida, por melhor que pareça.
  ✗ NÃO adicione nenhuma dependência de runtime além das quatro declaradas na
    seção 4 do README (react, react-dom, react-router-dom, react-markdown +
    remark-gfm).

  ✓ A FASE 05 tem uma seção "Não entra" — ela é tão obrigatória quanto o escopo.
  ✓ Se a fase mandar generalizar um componente de fase anterior por prop, faça —
    isso está no escopo, e os testes das fases anteriores precisam continuar verdes.

Ao implementar:

  - Respeite TODAS as regras da seção 5 (código), da seção 8 (design) e da
    seção 9 (reuso) do README. Sem exceção e sem "depois eu ajusto".
  - Antes de criar qualquer componente, procure em src/components/ se já existe
    um que sirva. Reuso é regra obrigatória, não conselho.
  - Escreva os testes que a fase exige, na seção "Testes exigidos". Testes
    verificam comportamento (papel acessível, texto na tela, interação do
    usuário), nunca estado interno nem classe CSS. Nenhum teste faz rede real.
  - Nada de `any`, nada de literal de configuração fora de src/config/env.ts,
    nada de cor literal fora de src/styles/tokens.css.

═══════════════════════════════════════════════════════════════════════════
PASSO 3 — VERIFIQUE E RELATE
═══════════════════════════════════════════════════════════════════════════

Rode e me mostre a saída completa de:

    cd apps/frontend
    npm run lint
    npm run typecheck
    npm test
    npm run build

Depois, percorra a lista de CRITÉRIOS DE ACEITE da FASE 05, item por item,
numerado, dizendo para cada um se foi atendido e como você verificou.
NÃO marque como concluído o que não está. Se algum item não foi atendido,
diga qual, por quê, e o que falta.

Se a fase descrever uma verificação manual com o backend no ar, diga
exatamente o que você executou e o que observou — ou diga que não executou,
se não executou.

═══════════════════════════════════════════════════════════════════════════
REGRA FINAL
═══════════════════════════════════════════════════════════════════════════

Se encontrar ambiguidade, contradição entre o README e a fase, ou algo que
os documentos não especificam: PARE e me pergunte. Não invente comportamento.
```

---

## Como usar

1. Substitua `05` pelo número da fase nos **três** lugares em que ele aparece no bloco.
2. Rode uma fase por sessão do modelo. Não peça duas fases no mesmo prompt — o escopo fechado é o
   que mantém cada entrega verificável.
3. Ao terminar, revise o relatório de critérios de aceite antes de seguir para a próxima fase.
   Uma fase mal fechada contamina todas as seguintes, porque elas reusam o que ela produziu.

---

## Ordem de execução

As fases têm dependência estrita. Não pule nem reordene:

```
01 Fundação  ──▶ 02 Contratos e API ──▶ 03 Design system ──▶ 04 Inferência simples
                                                                      │
                        ┌─────────────────────────────────────────────┘
                        ▼
              05 Ralph — Modo Chat ──▶ 06 Ralph — Modo Gráfico ──▶ 07 Histórico ──▶ 08 Qualidade
```

| Fase | Arquivo | Depende de |
|---|---|---|
| 01 | `FASE_01_FUNDACAO.md` | — |
| 02 | `FASE_02_CONTRATOS_E_API.md` | 01 (`env.ts`, tooling) |
| 03 | `FASE_03_DESIGN_SYSTEM.md` | 01 (tokens), 02 (enums e rótulos) |
| 04 | `FASE_04_INFERENCIA_SIMPLES.md` | 02 (API), 03 (componentes) |
| 05 | `FASE_05_RALPH_MODO_CHAT.md` | 02 (WebSocket), 03, 04 (`RunConfig`) |
| 06 | `FASE_06_RALPH_MODO_GRAFICO.md` | 05 (view-model `ThinkingRun`) |
| 07 | `FASE_07_HISTORICO.md` | 04, 05 e 06 (reusa as views sem modificar) |
| 08 | `FASE_08_QUALIDADE.md` | todas |

Por que a ordem importa: a **05** define o view-model `ThinkingRun`, do qual a **06** e a **07**
dependem inteiramente; a **07** só funciona porque a **04**, a **05** e a **06** produziram
componentes de apresentação puros (`SimpleChatView`, `RalphView`) que ela reusa sem modificação;
e a **08** audita tudo o que veio antes — rodá-la cedo não adianta.
