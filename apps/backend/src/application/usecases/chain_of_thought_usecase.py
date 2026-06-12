from collections.abc import AsyncGenerator
import asyncio
import json

# ── Token metadata per message ────────────────────────────────────────────
# (context_id, context_size, total_tokens)
#
# Scheme (alinhado com o paper):
#   - Cada chamada ao modelo cria uma NOVA janela de contexto
#   - EXCEÇÃO: tentativas de EXECUTE da mesma tarefa REUTILIZAM a janela
#     (contexto de verificação é separado; ao falhar, execute retoma a janela)
#   - Síntese Final (C) compartilha uma janela entre as etapas de compilação
#
# context_size: tokens acumulados na janela atual (reseta ao trocar de contexto)
# total_tokens: soma de todos os tokens desde o início (nunca decresce)

# Planejamento
_CTX_SETUP  = "b5a9c2e"   # A.1 — Configuração (critérios gerais)
_CTX_TASKS  = "4f8d3c1"   # A.2 — Decomposição em tarefas
# Tarefa 1
_CTX_T1_EX  = "3a7f2b1"   # T1 — execute + reasoning
_CTX_T1_VP  = "8c2e5a9"   # T1 — verify_pass
_CTX_T1_ST  = "1d6b8f4"   # T1 — store
_CTX_T1_LN  = "7a3c9e2"   # T1 — learn
_CTX_T1_RS  = "5b8d2f7"   # T1 — reset
# Tarefa 2 — execute da tentativa 1 e da tentativa 2 COMPARTILHAM a mesma janela
_CTX_T2_EX  = "9c4d8e5"   # T2 — execute (tentativa 1 e 2 reutilizam este contexto)
_CTX_T2_VF  = "2f1a7b3"   # T2 — verify_fail (verificação cria nova janela)
_CTX_T2_VP  = "6e9c3d8"   # T2 — verify_pass
_CTX_T2_ST  = "4b7a1f5"   # T2 — store
_CTX_T2_LN  = "3d6c8b2"   # T2 — learn
_CTX_T2_RS  = "8f4e2a9"   # T2 — reset
# Tarefa 3
_CTX_T3_EX  = "2f6a1b8"   # T3 — execute + reasoning
_CTX_T3_VP  = "7c3e9d4"   # T3 — verify_pass
_CTX_T3_ST  = "5a8b2c6"   # T3 — store
_CTX_T3_LN  = "1e4f7a3"   # T3 — learn
# Síntese Final
_CTX_SYNTH  = "7e3c9d4"   # C — todas as etapas de compilação compartilham

_TOKEN_META = [
    # msg 00  setup A.1      ── CTX_SETUP começa
    (_CTX_SETUP,  148,   148),
    # msg 01  tasks A.2      ── CTX_TASKS começa (nova chamada)
    (_CTX_TASKS,  312,   460),
    # msg 02  execute T1     ── CTX_T1_EX começa
    (_CTX_T1_EX,  182,   642),
    # msg 03  reasoning T1   ── mesmo contexto de execução
    (_CTX_T1_EX,  399,   859),
    # msg 04  verify_pass T1 ── CTX_T1_VP começa (verificação → nova janela)
    (_CTX_T1_VP,  156,  1015),
    # msg 05  store T1       ── CTX_T1_ST começa
    (_CTX_T1_ST,   89,  1104),
    # msg 06  learn T1       ── CTX_T1_LN começa
    (_CTX_T1_LN,  213,  1317),
    # msg 07  reset          ── CTX_T1_RS começa
    (_CTX_T1_RS,   72,  1389),
    # msg 08  execute T2     ── CTX_T2_EX começa  ← início de 9c4d8e5
    (_CTX_T2_EX,  195,  1584),
    # msg 09  reasoning T2   ── mesmo contexto de execução
    (_CTX_T2_EX,  421,  1810),
    # msg 10  verify_fail T2 ── CTX_T2_VF começa (verificação → nova janela)
    (_CTX_T2_VF,  178,  1988),
    # msg 11  execute T2 retry ── CTX_T2_EX retomado! (mesma tarefa → mesmo contexto)
    (_CTX_T2_EX,  486,  2474),
    # msg 12  reasoning T2 retry ── mesmo contexto de execução
    (_CTX_T2_EX,  702,  2690),
    # msg 13  verify_pass T2 ── CTX_T2_VP começa (verificação → nova janela)
    (_CTX_T2_VP,  164,  2854),
    # msg 14  store T2       ── CTX_T2_ST começa
    (_CTX_T2_ST,   92,  2946),
    # msg 15  learn T2       ── CTX_T2_LN começa
    (_CTX_T2_LN,  247,  3193),
    # msg 16  reset          ── CTX_T2_RS começa
    (_CTX_T2_RS,   78,  3271),
    # msg 17  execute T3     ── CTX_T3_EX começa
    (_CTX_T3_EX,  201,  3472),
    # msg 18  reasoning T3   ── mesmo contexto de execução
    (_CTX_T3_EX,  418,  3689),
    # msg 19  verify_pass T3 ── CTX_T3_VP começa
    (_CTX_T3_VP,  158,  3847),
    # msg 20  store T3       ── CTX_T3_ST começa
    (_CTX_T3_ST,   85,  3932),
    # msg 21  learn T3       ── CTX_T3_LN começa
    (_CTX_T3_LN,  231,  4163),
    # msg 22  compile 1      ── CTX_SYNTH começa
    (_CTX_SYNTH,  321,  4484),
    # msg 23  compile 2      ── mesmo contexto de síntese
    (_CTX_SYNTH,  467,  4630),
    # msg 24  compile 3
    (_CTX_SYNTH,  589,  4752),
    # msg 25  result
    (_CTX_SYNTH,  623,  4786),
]

def _with_tokens(idx: int, msg: dict) -> dict:
    ctx_id, ctx_size, total = _TOKEN_META[idx]
    return {
        **msg,
        "total_tokens": total,
        "context_window": {
            "context_id": ctx_id,
            "context_size": ctx_size,
        },
    }


_RAW_MESSAGES = [
    # ── A. Setup ──────────────────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "setup",
        "task": "setup",
        "content": """\
## 🔧 Configuração — Critérios de Aceite Gerais

- A pergunta deve ser respondida em **Português do Brasil**
- Responder somente a **alternativa**, sem explicações adicionais
- O valor final deve corresponder a **uma das alternativas fornecidas**
""",
    },
    {
        "type": "thinking",
        "subtype": "tasks",
        "task": "setup",
        "content": """\
## 📋 Decomposição — Tarefas Geradas

### Tarefa 1 — Números primos
Dadas as opções `(2, 4, 6)`, identificar quais são **primos**.

**Critérios:**
- Retornar a lista de primos encontrados
- Incluir breve explicação da regra
- ⚠️ Não resolver a questão final
- ⚠️ Não avaliar outras condições

---

### Tarefa 2 — Números pares
Dadas as opções `(2, 4, 6)`, identificar quais são **pares**.

**Critérios:**
- Retornar a lista de pares encontrados
- Incluir breve explicação da regra
- ⚠️ Não resolver a questão final
- ⚠️ Não avaliar outras condições

---

### Tarefa 3 — Maiores que 2
Dadas as opções `(2, 4, 6)`, identificar quais são **estritamente maiores que 2**.

**Critérios:**
- Retornar a lista de números `> 2`
- Incluir justificativa matemática
- ⚠️ Não resolver a questão final
- ⚠️ Não avaliar outras condições
""",
    },
    # ── B. Loop — Tarefa 1 ───────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "execute",
        "task": "T1",
        "content": """\
## ⚙️ Execução — Tarefa 1

**Enunciado:**
> Dadas as opções `(2, 4, 6)`, identifique quais desses números são **primos**.

**Aprendizados disponíveis:** nenhum
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
        "task": "T1",
        "content": """\
## 💭 Raciocínio — Tarefa 1

Analisando cada número:

| Número | Divisores | Primo? |
|--------|-----------|--------|
| `2` | 1, 2 | ✅ Sim |
| `4` | 1, 2, 4 | ❌ Não |
| `6` | 1, 2, 3, 6 | ❌ Não |

> **Resultado parcial:** `[2]`
""",
    },
    {
        "type": "thinking",
        "subtype": "verify_pass",
        "task": "T1",
        "content": """\
## ✅ Verificação — Tarefa 1

- [x] Retornou a lista de primos encontrados
- [x] Incluiu explicação da regra de identificação
- [x] Não tentou resolver a questão final
- [x] Não avaliou outras condições

> **Status: APROVADO**
""",
    },
    {
        "type": "thinking",
        "subtype": "store",
        "task": "T1",
        "content": """\
## 💾 Armazenamento — Tarefa 1

Resultado aprovado registrado na memória de contexto:

> Entre `(2, 4, 6)`, somente o número `2` é primo.
> **Primos:** `[2]`
""",
    },
    {
        "type": "thinking",
        "subtype": "learn",
        "task": "T1",
        "content": """\
## 💡 Aprendizados Extraídos — Tarefa 1

- Um número primo é divisível **apenas por 1 e por ele mesmo**
- Primos entre `(2, 4, 6)`: `[2]`
""",
    },
    {
        "type": "thinking",
        "subtype": "reset",
        "task": "T1",
        "content": """\
## 🔄 Reinicialização de Contexto

Contexto anterior **descartado**. Novo contexto criado.

**Aprendizados reinjetados:**
- Um número primo é divisível apenas por 1 e por ele mesmo
- Primos entre `(2, 4, 6)`: `[2]`
""",
    },
    # ── B. Loop — Tarefa 2 ───────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "execute",
        "task": "T2",
        "content": """\
## ⚙️ Execução — Tarefa 2

**Enunciado:**
> Dadas as opções `(2, 4, 6)`, identifique quais desses números são **pares**.

**Aprendizados disponíveis:**
- Um número primo é divisível apenas por 1 e por ele mesmo
- Primos entre `(2, 4, 6)`: `[2]`
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
        "task": "T2",
        "content": """\
## 💭 Raciocínio — Tarefa 2 *(tentativa 1)*

Todos os números 2, 4 e 6 são divisíveis por 2, logo são pares.

⚠️ Como apenas `2` é primo e não é maior que 2, nenhuma alternativa satisfaz
simultaneamente todas as condições — portanto a resposta é **D**.

> **Resultado parcial:** `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "verify_fail",
        "task": "T2",
        "content": """\
## ❌ Verificação — Tarefa 2 *(tentativa 1)*

- [x] Retornou a lista de pares encontrados
- [x] Incluiu explicação da regra de identificação
- [ ] ~~Não tentou resolver a questão final~~ — **VIOLADO**
- [ ] ~~Não avaliou outras condições~~ — **VIOLADO**

> **Status: REPROVADO** — reiniciando tarefa com feedback
""",
    },
    {
        "type": "thinking",
        "subtype": "execute",
        "task": "T2",
        "content": """\
## ⚙️ Nova Tentativa — Tarefa 2

**Enunciado:**
> Dadas as opções `(2, 4, 6)`, identifique quais desses números são **pares**.

**Feedback recebido:**
- Não resolver a questão final antes do momento correto
- Não utilizar informações pertencentes a outras tarefas
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
        "task": "T2",
        "content": """\
## 💭 Raciocínio — Tarefa 2 *(tentativa 2)*

Analisando cada número:

| Número | Divisível por 2? | Par? |
|--------|-----------------|------|
| `2` | 2 ÷ 2 = 1 (resto 0) | ✅ Sim |
| `4` | 4 ÷ 2 = 2 (resto 0) | ✅ Sim |
| `6` | 6 ÷ 2 = 3 (resto 0) | ✅ Sim |

> **Resultado parcial:** `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "verify_pass",
        "task": "T2",
        "content": """\
## ✅ Verificação — Tarefa 2 *(tentativa 2)*

- [x] Retornou a lista de pares encontrados
- [x] Incluiu explicação da regra de identificação
- [x] Não tentou resolver a questão final
- [x] Não avaliou outras condições

> **Status: APROVADO**
""",
    },
    {
        "type": "thinking",
        "subtype": "store",
        "task": "T2",
        "content": """\
## 💾 Armazenamento — Tarefa 2

> Entre `(2, 4, 6)`, todos os números são pares.
> **Pares:** `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "learn",
        "task": "T2",
        "content": """\
## 💡 Aprendizados Extraídos — Tarefa 2

- Um número **par** é divisível por 2 sem deixar resto
- Pares entre `(2, 4, 6)`: `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "reset",
        "task": "T2",
        "content": """\
## 🔄 Reinicialização de Contexto

Contexto anterior **descartado**. Novo contexto criado.

**Aprendizados reinjetados:**
- Um número primo é divisível apenas por 1 e por ele mesmo
- Primos entre `(2, 4, 6)`: `[2]`
- Um número par é divisível por 2 sem deixar resto
- Pares entre `(2, 4, 6)`: `[2, 4, 6]`
""",
    },
    # ── B. Loop — Tarefa 3 ───────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "execute",
        "task": "T3",
        "content": """\
## ⚙️ Execução — Tarefa 3

**Enunciado:**
> Dadas as opções `(2, 4, 6)`, identifique quais desses números são **estritamente maiores que 2**.

**Aprendizados disponíveis:**
- Primos entre `(2, 4, 6)`: `[2]`
- Pares entre `(2, 4, 6)`: `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
        "task": "T3",
        "content": """\
## 💭 Raciocínio — Tarefa 3

Analisando cada número:

| Número | Condição `n > 2` | Satisfaz? |
|--------|-----------------|-----------|
| `2` | 2 > 2 → **falso** | ❌ Não |
| `4` | 4 > 2 → **verdadeiro** | ✅ Sim |
| `6` | 6 > 2 → **verdadeiro** | ✅ Sim |

> **Resultado parcial:** `[4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "verify_pass",
        "task": "T3",
        "content": """\
## ✅ Verificação — Tarefa 3

- [x] Retornou a lista de números maiores que 2
- [x] Incluiu justificativa matemática
- [x] Não tentou resolver a questão final
- [x] Não avaliou outras condições

> **Status: APROVADO**
""",
    },
    {
        "type": "thinking",
        "subtype": "store",
        "task": "T3",
        "content": """\
## 💾 Armazenamento — Tarefa 3

> Maiores que 2 entre `(2, 4, 6)`: `[4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "learn",
        "task": "T3",
        "content": """\
## 💡 Aprendizados Extraídos — Tarefa 3

- Maiores que 2 entre `(2, 4, 6)`: `[4, 6]`
""",
    },
    # ── C. Síntese ────────────────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "compile",
        "task": "synthesis",
        "content": """\
## 📊 Compilação dos Resultados

| Tarefa | Condição | Resultado |
|--------|----------|-----------|
| T1 | Números primos | `[2]` |
| T2 | Números pares | `[2, 4, 6]` |
| T3 | Maiores que 2 | `[4, 6]` |

**Cálculo da interseção:**

```
[2] ∩ [2, 4, 6] ∩ [4, 6] = ∅
```

Nenhum número satisfaz **simultaneamente** as três condições.
→ Alternativa correspondente: **D) Nenhuma das anteriores**
""",
    },
    {
        "type": "thinking",
        "subtype": "compile",
        "task": "synthesis",
        "content": """\
## 🔍 Verificação Global

- [x] Respondido em Português do Brasil
- [x] Resposta limitada à alternativa, sem explicações adicionais
- [x] Valor corresponde a uma das alternativas fornecidas (`D`)

> **Status: APROVADO**
""",
    },
    {
        "type": "thinking",
        "subtype": "compile",
        "task": "synthesis",
        "content": """\
## 🏁 Construção da Resposta Final

Todos os critérios gerais foram satisfeitos.
Resposta construída utilizando **exclusivamente** os resultados armazenados.
Nenhum fato novo foi introduzido.
""",
    },
    # ── Resultado ─────────────────────────────────────────────────────────────
    {
        "type": "result",
        "subtype": "compile",
        "task": "synthesis",
        "content": "D) Nenhuma das anteriores",
    },
]

_MOCK_MESSAGES = [_with_tokens(i, msg) for i, msg in enumerate(_RAW_MESSAGES)]


class SendReasoningMessageUsecase:
    def __init__(self):
        ...

    async def execute(self, _user_input: str) -> AsyncGenerator[str, None]:
        for message in _MOCK_MESSAGES:
            yield json.dumps(message, ensure_ascii=False)
            await asyncio.sleep(1.2)
