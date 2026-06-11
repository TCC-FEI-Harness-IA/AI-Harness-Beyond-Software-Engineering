from collections.abc import AsyncGenerator
import asyncio
import json

_MOCK_MESSAGES = [
    # ── A. Setup ──────────────────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "setup",
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
        "content": """\
## ⚙️ Execução — Tarefa 1

**Aprendizados disponíveis:** nenhum

**Objetivo:** Dadas as opções `(2, 4, 6)`, identificar quais são primos.
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
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
        "content": """\
## 💡 Aprendizados Extraídos — Tarefa 1

- Um número primo é divisível **apenas por 1 e por ele mesmo**
- Primos entre `(2, 4, 6)`: `[2]`
""",
    },
    {
        "type": "thinking",
        "subtype": "reset",
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
        "content": """\
## ⚙️ Execução — Tarefa 2

**Aprendizados disponíveis:**
- Um número primo é divisível apenas por 1 e por ele mesmo
- Primos entre `(2, 4, 6)`: `[2]`

**Objetivo:** Dadas as opções `(2, 4, 6)`, identificar quais são pares.
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
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
        "content": """\
## ⚙️ Nova Tentativa — Tarefa 2

**Feedback recebido:**
- Não resolver a questão final antes do momento correto
- Não utilizar informações pertencentes a outras tarefas
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
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
        "content": """\
## 💾 Armazenamento — Tarefa 2

> Entre `(2, 4, 6)`, todos os números são pares.
> **Pares:** `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "learn",
        "content": """\
## 💡 Aprendizados Extraídos — Tarefa 2

- Um número **par** é divisível por 2 sem deixar resto
- Pares entre `(2, 4, 6)`: `[2, 4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "reset",
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
        "content": """\
## ⚙️ Execução — Tarefa 3

**Aprendizados disponíveis:**
- Primos entre `(2, 4, 6)`: `[2]`
- Pares entre `(2, 4, 6)`: `[2, 4, 6]`

**Objetivo:** Dadas as opções `(2, 4, 6)`, identificar quais são **estritamente maiores que 2**.
""",
    },
    {
        "type": "thinking",
        "subtype": "reasoning",
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
        "content": """\
## 💾 Armazenamento — Tarefa 3

> Maiores que 2 entre `(2, 4, 6)`: `[4, 6]`
""",
    },
    {
        "type": "thinking",
        "subtype": "learn",
        "content": """\
## 💡 Aprendizados Extraídos — Tarefa 3

- Maiores que 2 entre `(2, 4, 6)`: `[4, 6]`
""",
    },
    # ── C. Síntese ────────────────────────────────────────────────────────────
    {
        "type": "thinking",
        "subtype": "compile",
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
        "content": """\
## 🏁 Construção da Resposta Final

Todos os critérios gerais foram satisfeitos.
Resposta construída utilizando **exclusivamente** os resultados armazenados.
Nenhum fato novo foi introduzido.
""",
    },
    # ── Resultado ────────────────────────────────────────────────────────────
    {
        "type": "result",
        "subtype": "result",
        "content": "D) Nenhuma das anteriores",
    },
]


class SendReasoningMessageUsecase:
    def __init__(self):
        ...

    async def execute(self, _user_input: str) -> AsyncGenerator[str, None]:
        for message in _MOCK_MESSAGES:
            yield json.dumps(message, ensure_ascii=False)
            await asyncio.sleep(1)
