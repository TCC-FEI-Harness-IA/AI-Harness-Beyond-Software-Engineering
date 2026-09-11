# B.2 — Verificação dos critérios de aceite da tarefa

Avalie se o resultado preliminar abaixo atende aos critérios de aceite da tarefa.

## Resultado preliminar

{{preliminary_result}}

## Critérios de aceite desta tarefa

{{task_acceptance_criteria}}

## Instruções

Percorra os critérios **um por um**. Para cada critério, decida se ele foi atendido e escreva a
justificativa do veredito. Em seguida emita a decisão final: `approved` quando **todos** os
critérios foram atendidos, `reproved` caso contrário. Liste em `unmet_criteria_ids` os
identificadores dos critérios não atendidos — a lista fica vazia quando a decisão é `approved`.

A avaliação é **local**: julgue apenas os critérios desta tarefa. Não julgue se o resultado
responde à questão final do usuário, não julgue a qualidade da resposta final e não considere
nada além dos critérios listados acima.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"decision": "approved", "criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": []}
