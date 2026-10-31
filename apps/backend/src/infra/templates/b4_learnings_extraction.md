# B.4 — Extração dos aprendizados pontuais

Compile os aprendizados pontuais descobertos ao longo desta tarefa, considerando tudo o que está
no contexto acima, inclusive as tentativas reprovadas.

## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. São os aprendizados
já registrados: **não repita** nenhum deles. Registre apenas fatos novos, descobertos nesta tarefa.

{{learnings}}

## Instruções

Esta etapa só ocorre após a aprovação da tarefa; portanto, a validade do resultado já é garantida.
Registre **exclusivamente fatos concretos sobre o conteúdo do problema**, em tópicos sucintos,
secos e diretos: conclusões parciais, valores calculados (com unidades), propriedades verificadas
ou relações objetivas estabelecidas na resolução desta tarefa que sejam úteis para quem for
resolver as tarefas seguintes sem acesso a este contexto.

Enuncie cada fato diretamente sobre o domínio do problema, nunca como um relato sobre a tarefa ou
sobre a sua resposta.

É proibido registrar:

- menções à própria tarefa, ao seu identificador (`T1`, `B.1`), ao que ela exigia ou às suas
  restrições de escopo (por exemplo, "A tarefa T1 exige...", "A resposta não deve avaliar...");
- menções ao validador, ao veredito de aprovação (`approved`) ou ao atendimento de critérios de
  aceite (`T1-AC1`);
- formulações indiretas como "A resposta aprovada concluiu que..." ou "Na tarefa T1 identificou-se
  que..." — escreva diretamente o fato concluído;
- conceitos redundantes, óbvios ou que apenas parafraseiem aprendizados já listados acima;
- a cópia da resposta completa da tarefa ou o relato do processo de execução.

Exemplos de aprendizado **válido**:

- "Entre as opções 2, 4 e 6, somente o número 2 é primo."
- "Um número primo é aquele que só é divisível por 1 e por ele mesmo."

Exemplos de aprendizado **inválido**:

- "Durante a execução da Tarefa 1, analisamos os números 2, 4 e 6, e depois de validarmos cada um
  deles concluímos que..."
- "O veredito do validador para a tarefa T1 foi 'approved', atendendo aos critérios T1-AC1 a T1-AC4."
- "A tarefa T1 exige listar os números primos sem resolver a questão final."

Quando a tarefa não tiver produzido nenhum fato novo sobre o problema que já não conste em
**Aprendizados Pontuais**, devolva uma lista vazia (`{"learnings": []}`).

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"learnings": ["fato seco 1", "fato seco 2"]}
