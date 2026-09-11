# C.2 — Planejamento adicional

Crie novas tarefas independentes **apenas** para suprir as lacunas apontadas abaixo.

## Critérios gerais ainda não atendidos

{{unmet_criteria}}

## Resultados já armazenados

{{stored_results}}

## Instruções

As novas tarefas existem para cobrir **somente** os critérios não atendidos. Não crie tarefas que
refaçam o que já está nos resultados armazenados e não reabra o que já foi verificado.

Cada tarefa deve:

1. Ter **um único objetivo**, resolvível de forma independente das demais.
2. Declarar as **entradas** de que precisa e a **saída** que produz.
3. Trazer os **próprios critérios de aceite individuais**.
4. Trazer, entre os critérios, **restrições de escopo que impeçam a resolução precoce da questão
   principal**.

**O contexto não será compartilhado entre as tarefas.** Cada descrição precisa ser autossuficiente.

Continue a numeração das tarefas a partir de `T{{next_task_number}}`, para que os identificadores
não colidam com os das tarefas já existentes.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"tasks": [{"id": "T1", "title": "...", "description": "...", "expected_input": "...",
"expected_output": "...", "acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}
