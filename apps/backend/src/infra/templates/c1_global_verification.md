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

Emita `approved` somente quando **todos** os critérios gerais estiverem cobertos, e `reproved` caso
contrário.

Regras de consistência do relatório, verificadas automaticamente — um relatório que as violar é
recusado e devolvido a você para correção:

- Faça **exatamente uma avaliação para cada critério geral** listado acima, usando o identificador
  exato do critério em `criterion_id`. Não omita nenhum critério. Não repita um critério. Não
  invente identificadores que não estejam na lista.
- Marque `met` igual a `false` em todo critério ainda descoberto e `true` nos cobertos.
- `unmet_criteria_ids` deve conter exatamente os identificadores dos critérios com `met` igual a
  `false`, sem repetições. A lista fica vazia somente quando a decisão é `approved`.
- A decisão `approved` somente quando todos os critérios têm `met` igual a `true`; basta um
  critério com `met` igual a `false` para a decisão ser `reproved`.

**Não construa a resposta final aqui.** Esta etapa apenas julga a suficiência do material
disponível.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"decision": "approved", "criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": []}
