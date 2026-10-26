# C.2 — Planejamento adicional

Crie novas tarefas independentes **apenas** para suprir as lacunas apontadas abaixo.

## Critérios gerais ainda não atendidos

{{unmet_criteria}}

## Resultados já armazenados

{{stored_results}}

## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. Use-as para escrever
descrições autossuficientes: copie para a descrição de cada nova tarefa os dados do enunciado de que
ela precisa (alternativas, valores com unidades de medida, fórmulas, condições).

{{learnings}}

## Instruções

As novas tarefas existem para cobrir **somente** os critérios não atendidos. Não crie tarefas que
refaçam o que já está nos resultados armazenados e não reabra o que já foi verificado.

Cada tarefa deve:

1. Ter **um único objetivo**, resolvível de forma independente das demais.
2. Trazer os **próprios critérios de aceite individuais**, que permitam julgar isoladamente se a
   tarefa foi bem resolvida. Os critérios de uma mesma tarefa devem ser **complementares, nunca
   mutuamente exclusivos**: tem de ser possível que uma única resposta atenda a todos eles ao mesmo
   tempo. Antes de fechar a lista, confira os critérios aos pares e elimine qualquer contradição —
   por exemplo, "responda somente a alternativa" e "a resposta deve conter explicações" se excluem
   e não podem coexistir.
3. Trazer, entre os critérios, **restrições de escopo que impeçam a resolução precoce da questão
   principal**.
4. Exigir que a resposta da tarefa traga o **resultado acompanhado da explicação de por que ele é
   válido**, nunca o resultado isolado. Se a tarefa envolve uma conta, a resposta deve apresentar
   as fórmulas usadas, a substituição dos valores com unidades de medida, as convenções adotadas
   (sinais, referenciais, aproximações) e a justificativa de cada passo até o valor final; se
   envolve uma classificação ou escolha, deve apresentar o raciocínio que a sustenta. Escreva essa
   exigência na descrição da tarefa e inclua um critério de aceite que a verifique.

**O contexto não será compartilhado entre as tarefas.** Cada descrição precisa ser autossuficiente.

**Limite do lote:** a sessão comporta no máximo {{max_tasks}} tarefas novas. Não ultrapasse esse
número e não funda tarefas independentes em uma só apenas para caber: mantenha cada uma autônoma
e de objetivo único. Um lote acima do limite é recusado e devolvido a você para correção.

Continue a numeração das tarefas a partir de `T{{next_task_number}}`, para que os identificadores
não colidam com os das tarefas já existentes.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"tasks": [{"id": "T1", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}
