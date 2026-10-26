# A.2 — Quebra em tarefas de objetivo único

Quebre o enunciado abaixo em tarefas autônomas, cada uma com **responsabilidade única**.

## Enunciado

{{user_question}}

## Instruções

Cada tarefa deve:

1. Ter **um único objetivo**, resolvível de forma independente das demais.
2. Trazer os **próprios critérios de aceite individuais**, que permitam julgar isoladamente se a
   tarefa foi bem resolvida. Os identificadores dos critérios seguem a forma `T1-AC1`. Os
   critérios de uma mesma tarefa devem ser **complementares, nunca mutuamente exclusivos**: tem de
   ser possível que uma única resposta atenda a todos eles ao mesmo tempo. Antes de fechar a lista,
   confira os critérios aos pares e elimine qualquer contradição — por exemplo, "responda somente
   a alternativa" e "a resposta deve conter explicações" se excluem e não podem coexistir.
3. Trazer, entre os critérios, **restrições de escopo que impeçam a resolução precoce da questão
   principal** — por exemplo: "a resposta não deve tentar resolver a questão final", "a resposta
   não deve avaliar nenhuma outra condição além da que esta tarefa trata".
4. Exigir que a resposta da tarefa traga o **resultado acompanhado da explicação de por que ele é
   válido**, nunca o resultado isolado. Se a tarefa envolve uma conta, a resposta deve apresentar
   as fórmulas usadas, a substituição dos valores com unidades de medida, as convenções adotadas
   (sinais, referenciais, aproximações) e a justificativa de cada passo até o valor final; se
   envolve uma classificação ou escolha, deve apresentar o raciocínio que a sustenta. Escreva essa
   exigência na descrição da tarefa e inclua um critério de aceite que a verifique.

**O contexto não será compartilhado entre as tarefas.** Cada tarefa será executada isoladamente,
sem acesso ao enunciado original, às demais tarefas ou aos resultados delas. Portanto a descrição
de cada tarefa precisa ser autossuficiente: tudo o que for necessário para resolvê-la deve estar
escrito nela.

Em conjunto, as tarefas precisam gerar insumos suficientes para sustentar a resposta final ao
enunciado.

**Limite do lote:** a sessão comporta no máximo {{max_tasks}} tarefas. Não ultrapasse esse número
e não funda tarefas independentes em uma só apenas para caber: mantenha cada uma autônoma e de
objetivo único. Um lote acima do limite é recusado e devolvido a você para correção.

Numere as tarefas a partir de `T1`.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"tasks": [{"id": "T1", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}
