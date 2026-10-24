# B.2 — Verificação dos critérios de aceite da tarefa

Avalie se o resultado preliminar abaixo atende aos critérios de aceite da tarefa.

## Resultado preliminar

{{preliminary_result}}

## Critérios de aceite desta tarefa

{{task_acceptance_criteria}}

## Instruções

Percorra os critérios **um por um**. Para cada critério, decida se ele foi atendido e escreva a
justificativa do veredito. Em seguida emita a decisão final: `approved` somente quando **todos** os
critérios foram atendidos, `reproved` caso contrário.

Regras de consistência do relatório, verificadas automaticamente — um relatório que as violar é
recusado e devolvido a você para correção:

- Faça **exatamente uma avaliação para cada critério** listado acima, usando o identificador
  exato do critério em `criterion_id`. Não omita nenhum critério. Não repita um critério. Não
  invente identificadores que não estejam na lista.
- Marque `met` igual a `false` em todo critério não atendido e `true` nos atendidos.
- `unmet_criteria_ids` deve conter exatamente os identificadores dos critérios com `met` igual a
  `false`, sem repetições. A lista fica vazia somente quando a decisão é `approved`.
- A decisão `approved` somente quando todos os critérios têm `met` igual a `true`; basta um
  critério com `met` igual a `false` para a decisão ser `reproved`.

A avaliação é **local**: julgue apenas os critérios desta tarefa. Não julgue se o resultado
responde à questão final do usuário, não julgue a qualidade da resposta final e não considere
nada além dos critérios listados acima.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"decision": "approved", "criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": []}
