# Message API — Input Contracts

Este documento descreve os **contratos de entrada** dos endpoints responsáveis por enviar mensagens para o sistema de IA.

A API possui dois modos de execução:

1. **Execução com raciocínio estruturado (multi-fase)**
2. **Execução simples (uma única geração)**

Todos os contratos seguem:

- Formato **JSON**
- Convenção **snake_case**

---

# Endpoints

| Endpoint | Descrição |
|--------|--------|
| `/message/reasoning` | Executa o modelo usando **raciocínio em múltiplas fases** |
| `/message/default` | Executa o modelo de forma **direta (single step)** |

---

# Pontos Conceituais do Fluxo

## Pontos Fixos

Sempre fazem parte da execução:

- `user_input`
- `max_tokens`
- escolha do **modelo**
- escolha do **provider**

Esses elementos permitem que o modelo gere a resposta.

---

## Pontos Variáveis

A API permite controlar o comportamento do raciocínio:

- tipo de **quebra de pensamento**
- estratégia de **escolha da próxima fase**

Essas configurações existem apenas no endpoint de **reasoning**.

---

# Endpoint — `/message/reasoning`

Executa o modelo utilizando **quebra de pensamento em múltiplas fases**.

Nesse endpoint, assume-se que **phase breaking sempre está ativo**, portanto o campo `phase_breaking_enabled` não existe.

## Estrutura

```json
{
  "message": {
    "user_input": "string"
  },
  "model_config": {
    "provider": "local | open_router",
    "provider_config": {
      "model_name": "string",
      "endpoint": "string"
    },
    "max_tokens": 1000
  },
  "reasoning_config": {
    "phase_breaking_strategy": "autonomous | predefined",
    "strategies": {
      "predefined": {
        "number_of_phases": 5
      }
    },
    "next_phase_strategy": "ai_based | algorithmic"
  }
}


---

## Módulos

### message

Contém a mensagem enviada pelo usuário.

```json
"message": {
  "user_input": "string"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|----------|
| user_input | string | ✅ | Texto enviado pelo usuário |

---

### model_config

Define qual modelo será utilizado e os limites de geração.

```json
"model_config": {
  "provider": "local | open_router",
  "provider_config": {},
  "max_tokens": 1000
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|----------|
| provider | string | ✅ | Origem do modelo |
| provider_config | object | ⚠️ | Configuração específica do provider |
| max_tokens | integer | ✅ | Limite máximo de tokens da resposta |

---

### provider_config

A estrutura depende do provider.

#### OpenRouter

```json
"provider_config": {
  "model_name": "anthropic/claude-3.5-sonnet"
}
```

| Campo | Obrigatório |
|-------|-------------|
| model_name | ✅ |

#### Modelo Local

```json
"provider_config": {
  "model_name": "llama3",
  "endpoint": "http://localhost:11434"
}
```

| Campo | Obrigatório |
|-------|-------------|
| model_name | ✅ |
| endpoint | ⚠️ |

O endpoint representa o servidor que expõe o modelo local (ex: Ollama, LM Studio, vLLM).

---

### reasoning_config

Define como o sistema executa o raciocínio em múltiplas fases.

```json
"reasoning_config": {
  "phase_breaking_strategy": "autonomous | predefined",
  "strategies": {},
  "next_phase_strategy": "ai_based | algorithmic"
}
```

---

### phase_breaking_strategy

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| phase_breaking_strategy | string | ✅ |

Define como as fases de raciocínio são organizadas.

| Valor | Descrição |
|-------|----------|
| autonomous | O sistema decide dinamicamente o número de fases |
| predefined | O número de fases é definido manualmente |

---

### strategies

Objeto contendo configurações específicas para cada estratégia.

```json
"strategies": {
  "predefined": {
    "number_of_phases": 5
  }
}
```

---

### predefined

Utilizado quando:

```
phase_breaking_strategy = predefined
```

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| number_of_phases | integer | ✅ |

Define o número total de fases de raciocínio.

---

### next_phase_strategy

Define como a próxima fase será escolhida.

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| next_phase_strategy | string | ⚠️ |

| Valor | Descrição |
|-------|----------|
| ai_based | A própria IA decide a próxima fase |
| algorithmic | Um algoritmo interno decide a próxima fase |

---

# Endpoint — `/message/default`

Executa o modelo sem raciocínio multi-fase.

Esse endpoint ignora qualquer configuração de reasoning.

## Estrutura

```json
{
  "message": {
    "user_input": "string"
  },
  "model_config": {
    "provider": "local | open_router",
    "provider_config": {
      "model_name": "string",
      "endpoint": "string"
    },
    "max_tokens": 1000
  }
}
```

---

## Módulos

### message

```json
"message": {
  "user_input": "string"
}
```

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| user_input | string | ✅ |

---

### model_config

```json
"model_config": {
  "provider": "local | open_router",
  "provider_config": {},
  "max_tokens": 1000
}
```

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| provider | string | ✅ |
| provider_config | object | ⚠️ |
| max_tokens | integer | ✅ |

---

# Exemplo — Reasoning

```json
{
  "message": {
    "user_input": "Explique como funciona um motor elétrico."
  },
  "model_config": {
    "provider": "open_router",
    "provider_config": {
      "model_name": "openai/gpt-4o"
    },
    "max_tokens": 800
  },
  "reasoning_config": {
    "phase_breaking_strategy": "predefined",
    "strategies": {
      "predefined": {
        "number_of_phases": 4
      }
    },
    "next_phase_strategy": "ai_based"
  }
}
```

---

# Exemplo — Default

```json
{
  "message": {
    "user_input": "Explique como funciona um motor elétrico."
  },
  "model_config": {
    "provider": "open_router",
    "provider_config": {
      "model_name": "openai/gpt-4o"
    },
    "max_tokens": 800
  }
}
```


