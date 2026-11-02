# C.3 — Construção da resposta final

Organize e apresente os resultados já produzidos como a resposta final ao usuário.

## Resultados armazenados

{{stored_results}}

## Critérios de aceite gerais

{{general_acceptance_criteria}}

## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. Use-as apenas para
conferir os dados do enunciado ao apresentar a resposta — por exemplo, a letra da alternativa que
corresponde ao valor obtido nos resultados.
Os aprendizados **não substituem os resultados armazenados**: o conteúdo da resposta continua vindo
exclusivamente deles.

{{learnings}}

## Instruções

Escreva a resposta no **idioma** e na **estrutura** definidos pelos critérios gerais, respeitando
os termos e restrições que eles impõem.

Esta etapa é de **apresentação, não de raciocínio**. É terminantemente proibido:

- introduzir fatos novos que não estejam nos resultados armazenados;
- especular, supor ou inferir o que os resultados não sustentam;
- realizar novo raciocínio analítico sobre o problema.

Use exclusivamente o material dos resultados armazenados. A resposta final vai no campo
`final_answer`, em markdown.

Aplique idioma, formato e restrições finais sem novo raciocínio analítico. Os resultados internos
podem conter explicações mesmo quando o pedido final só admite a letra. Omita ou apresente a
justificativa conforme os critérios gerais: opcional não significa obrigatória, e uma justificativa
explicitamente exigida deve vir da fundamentação já aprovada. Não invente limites de linhas ou
palavras a partir de uma orientação genérica de objetividade.

## Exemplos de apresentação válida e inválida

- Resultados já identificam C e explicam o cálculo; pedido "apenas a letra". Válido: `C`.
  Inválido: copiar a explicação interna para a resposta apesar dessa restrição.
- Mesmos resultados; pedido "termine com RESPOSTA_FINAL: LETRA". Válido: aplicar a linha
  `RESPOSTA_FINAL: C`, ainda que ela não apareça literalmente nos resultados internos.
- Pedido "justifique": apresentar a fundamentação aprovada. Pedido "pode justificar": ela é
  opcional, respeitadas as demais restrições. Inválido: inventar uma prova ou um cálculo para
  preencher justificativa ausente.
- Inválido: realizar a interseção de condições só verificadas isoladamente ou selecionar uma
  alternativa ainda não sustentada. Isso seria novo conteúdo analítico, não formatação.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"final_answer": "markdown da resposta ao usuario"}
