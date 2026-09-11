# C.1 — Compilação e verificação dos critérios gerais

Avalie se a **união** dos resultados armazenados é suficiente para satisfazer cada critério geral
da resposta final.

## Resultados armazenados

{{stored_results}}

## Critérios de aceite gerais

{{general_acceptance_criteria}}

## Instruções

A avaliação é **global**, não por tarefa: considere os resultados em conjunto e decida, critério
por critério, se o que já foi produzido basta para satisfazê-lo. Justifique cada veredito.

Emita `approved` quando **todos** os critérios gerais estiverem cobertos, e `reproved` caso
contrário, listando em `unmet_criteria_ids` os identificadores dos critérios ainda descobertos.

**Não construa a resposta final aqui.** Esta etapa apenas julga a suficiência do material
disponível.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"decision": "approved", "criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": []}
