# B.2 — Verificação dos critérios de aceite da tarefa

Avalie se o resultado preliminar abaixo atende aos critérios de aceite da tarefa.

## Resultado preliminar

{{preliminary_result}}

## Critérios de aceite desta tarefa

{{task_acceptance_criteria}}

## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. Use-as apenas como
referência para conferir os dados envolvidos (alternativas, valores, unidades de medida).
Os aprendizados **não são critérios** de aceite: a avaliação continua restrita aos critérios desta
tarefa.

{{learnings}}

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

**Não ignore, reescreva ou dispense nenhum critério recebido**, mesmo que pareça mal formulado.
A interpretação de escopo deve seguir a ação que o critério restringe: citar um termo como
referência contextual não equivale a calcular outra grandeza, avaliar outra condição ou antecipar
uma solução. Se houver uma proibição explícita de palavras, ela também deve ser verificada como
foi recebida; esta etapa não tem autorização para corrigir os critérios do planejador.

Exemplos para um critério "não calcular a massa por colher":

- Atendido: "O enunciado cita colheres; a massa total é 2 g + 4 g = 6 g". A menção é contextual,
  e o resultado vem explicado dentro do escopo.
- Não atendido: "A massa total é 6 g; dividindo por duas colheres, são 3 g por colher".
  A conta adicional executa uma ação proibida, mesmo que esteja correta.
- Se o critério recebido fosse "não mencionar colheres", a primeira frase o violaria.
  Não substitua esse critério por "não calcular a massa por colher" durante a avaliação.

Uma conclusão fundamentada sobre o objetivo da própria tarefa não é antecipação indevida.
Resolver condições externas ao objetivo ou anunciar a solução global quando o critério o proíbe
é violação. Explicações internas não devem ser julgadas pelo formato da resposta final, salvo
quando tal restrição constar nos critérios locais recebidos; todos continuam obrigatórios.

Evite o **hiper-literalismo**: quando um critério exigir que uma análise, conclusão ou opção seja
sustentada pelo texto ou enunciado, considere o critério **atendido** se o resultado demonstrar a
**melhor aderência relativa (por eliminação dos distratores mais graves)** ou uma paráfrase e
inferência interpretativa coerente, sem exigir correspondência 100% literal palavra por palavra. Da
mesma forma, se um critério de aceite trouxer um número ou expressão pré-calculados indevidamente no
planejamento que divirjam da dedução matemática/física correta a partir dos dados do enunciado e de
**Aprendizados Pontuais**, considere o critério **atendido (`met: true`)** quando o resultado
demonstrar e justificar o cálculo correto daquela grandeza.

**Aproximações na seleção de alternativas são permitidas.** Quando um critério exigir selecionar a
alternativa que corresponde ao valor ou à conclusão obtidos — mesmo que redigido como
"corresponde exatamente" ou "a única que coincide" —, considere-o **atendido (`met: true`)** se o
resultado **selecionar explicitamente uma única alternativa** como a de valor mais próximo ou de
melhor aderência, ainda que registre a diferença entre o valor obtido e o da alternativa. A falta de
correspondência exata não é motivo de reprovação. O critério só **não é atendido** quando nenhuma
alternativa é selecionada, quando o resultado conclui "nenhuma" ou cria uma opção inexistente, ou
quando outra alternativa disponível é evidentemente mais próxima do valor obtido.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, preenchendo `criteria_evaluation` primeiro, `unmet_criteria_ids` em seguida e `decision` por
último, no formato:

{"criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": [], "decision": "approved"}
