# Fluxo de execução do app



## Notas gerais

- Devemos ter controle de alguns pontos:

    - Pontos variaveis:
        - Se usar quebra de pensamento:
            - Tipo de quebra de fases:
                - Autonomo
                - Pre definido
            - Tipo de escolha para a proxima fase:
                - IA Based
                - Algoritimo interno
        - Se nao for usar quebra de pensamento:

    - Pontos fixos:
        - User input
        - Max tokens
        - Escolha do modelo:
            - Local
            - Open router


## Nomenclaturas:

- phase_breaking_strategy
- next_phase_strategy
- max_tokens




---

## Send Message API — Input Contract

Este documento descreve o **contrato de entrada** do endpoint `send_message`, responsável por receber a mensagem do usuário e as configurações de execução do modelo e do fluxo de raciocínio da IA.

O contrato segue o padrão **JSON com snake_case**.

---
# Send Message API — Input Contract

Este documento descreve o **contrato de entrada** do endpoint `send_message`, responsável por receber a mensagem do usuário e as configurações de execução do modelo e do fluxo de raciocínio da IA.

O contrato segue o padrão **JSON com snake_case**.

---

# Estrutura Geral

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
    "phase_breaking_enabled": true,
    "phase_breaking_strategy": "autonomous | predefined",
    "strategies": {
      "predefined": {
        "number_of_phases": 5
      }
    },
    "next_phase_strategy": "ai_based | algorithmic"
  }
}
