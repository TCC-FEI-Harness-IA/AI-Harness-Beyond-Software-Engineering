# B.1 — Resolução da tarefa

Resolva **unicamente** a tarefa descrita abaixo.

## Tarefa

{{task_description}}

## Critérios de aceite desta tarefa

{{task_acceptance_criteria}}

## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. Use-as como contexto de apoio —
por exemplo, para conferir alternativas, valores e unidades de medida —, sem ampliar o escopo desta
tarefa.

{{learnings}}

## Tentativas anteriores desta tarefa

Quando esta tarefa já foi tentada e reprovada, as tentativas anteriores e os vereditos do
validador aparecem abaixo, delimitados por `<tentativas_anteriores>`. São o feedback desta nova
tentativa: corrija exatamente os critérios não satisfeitos, sem repetir o que foi reprovado. Esta
é uma resolução nova e completa da tarefa, e não a continuação de uma conversa anterior.

{{previous_attempts}}

## Instruções

Limite estrito de escopo:

- **Não** resolva a questão final da qual esta tarefa faz parte.
- **Não** avalie condições que pertençam a outras tarefas.
- **Não** antecipe conclusões que dependam de resultados que você não tem.

Produza apenas o que esta tarefa pede, satisfazendo cada um dos critérios de aceite listados.
Quando esta tarefa depender de valores, grandezas ou conclusões obtidos em etapas anteriores, utilize
os fatos registrados em **Aprendizados Pontuais**. Se a descrição da tarefa ou algum critério de
aceite citar um valor estimado no planejamento que divirja dos dados literais do enunciado ou do valor
efetivamente calculado em **Aprendizados Pontuais**, execute o cálculo com os valores reais e registre
explicitamente a divergência na justificativa, sem forçar uma conta matematicamente incorreta.
Quando a tarefa envolver avaliar ou comparar afirmações ou opções frente a um texto, avalie por
**melhor aderência relativa (eliminação)**: diferencie contradições ou extrapolações graves de
paráfrases, sínteses e inferências razoáveis, sem descartar todas as opções por exigir
correspondência 100% literal palavra por palavra.
A resolução vai no campo `result`, em markdown.

No campo `conclusion`, escreva **apenas a conclusão final** da resolução, em uma ou poucas frases
autossuficientes: o resultado obtido (com valor e unidade de medida, quando houver) ou a afirmação
a que a tarefa chegou, sem fórmulas intermediárias, passos ou justificativas. A conclusão deve ser
idêntica, em conteúdo, à conclusão apresentada em `result` — por exemplo: "A velocidade média do
trajeto é 20 m/s."

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"task_id": "...", "result": "markdown com a resolucao", "conclusion": "conclusao final, sem o raciocinio"}
