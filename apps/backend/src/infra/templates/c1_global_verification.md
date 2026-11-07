# C.1 — Compilação e verificação dos critérios gerais

Avalie se a **união** dos resultados armazenados é suficiente para satisfazer cada critério geral
da resposta final.

## Resultados armazenados

{{stored_results}}

## Critérios de aceite gerais

{{general_acceptance_criteria}}

## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. Use-as apenas como
referência para conferir os dados do enunciado.
Os aprendizados **não são critérios** e **não contam como cobertura**: um critério geral só está
atendido quando os resultados armazenados o cobrem.

{{learnings}}

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

Lembre-se de que os resultados armazenados são o **insumo analítico** para a síntese final (`C.3`), e
não a resposta final já formatada:

- Critérios gerais de formatação da resposta final (por exemplo, "responder apenas com a letra da
  alternativa, sem justificativas") devem ser marcados como **atendidos (`met: true`)** desde que os
  resultados armazenados permitam identificar qual é a resposta a ser formatada em `C.3` (o fato de
  os resultados das tarefas conterem explicações não viola esse critério).
- Em questões de múltipla escolha, considere atendidos os critérios de aderência e sustentação pelo
  enunciado quando os resultados apontarem a **alternativa relativamente mais coerente por
  eliminação das demais**, admitindo paráfrases, sínteses ou inferências interpretativas razoáveis
  sem exigir correspondência 100% literal palavra por palavra. Da mesma forma, quando os resultados
  selecionarem explicitamente a alternativa de valor mais próximo do calculado, considere atendidos
  os critérios de seleção: aproximações são permitidas desde que uma alternativa seja escolhida.
- Confira se os resultados armazenados concluíram **até o último passo lógico ou cálculo final pedido
  pela pergunta** (por exemplo: se a pergunta pede o *mês seguinte* ao de uma ultrapassagem, ou a
  *quantidade adicional* a acrescentar, não basta ter apenas o mês da ultrapassagem ou a quantidade
  inicial; se faltar essa determinação final nos resultados armazenados, marque o critério
  correspondente como `met: false` para que o planejamento adicional crie a tarefa final).

Para idioma, formato e restrições de apresentação, julgue se C.3 consegue aplicá-los ao conteúdo
aprovado sem novo raciocínio analítico. Não exija que cada resultado intermediário já seja a resposta
final. Ao justificar `met: true`, indique o conteúdo que permite a apresentação solicitada.

Para exigências de conteúdo, identifique a evidência nos resultados armazenados. A possibilidade
de formatar uma resposta não supre análise, cálculo ou fundamentação ausente. Não realize aqui a
análise que falta para então declará-la coberta; a lacuna deve seguir para C.2. Os aprendizados
permanecem referência separada e não substituem essa evidência.

## Exemplos de suficiência e lacuna real

- Aprovar o formato: os resultados identificam inequivocamente a alternativa C, com conta e
  explicação, e o pedido exige terminar com `RESPOSTA_FINAL: LETRA`. A ausência de `RESPOSTA_FINAL: C`
  nos resultados não é lacuna de conteúdo: C.3 pode escrever essa linha sem nova análise.
  Reprovar só pela ausência da linha seria incorreto.
- Aprovar a apresentação enxuta: o pedido é "apenas a letra, sem justificativa" e os resultados
  explicados já sustentam C. As explicações internas não violam o formato final; C.3 pode omiti-las.
- Aprovar seleção aproximada: os resultados obtêm 23, as alternativas são 1, 4, 20, 1 e 2, e dentro
  das tarefas é selecionado 20 como a mais próxima. O critério de seleção está atendido; a diferença de
  aproximação não é lacuna de conteúdo.
- Reprovar ausência de seleção: os resultados obtêm 12, as alternativas são 2, 4, 6, 8 e 10, e os
  resultados concluem que nenhuma alternativa serve, sem selecionar nenhuma. Marque o critério de
  seleção como `met: false` e encaminhe a lacuna a C.2. Não escolha você a letra para suprir a
  lacuna, nem considere "RESPOSTA_FINAL: NENHUMA" uma formatação possível da resposta exigida.
- Reprovar conteúdo ausente: o critério exige análise conjunta explícita de três condições e só
  há listas de verificações isoladas. Mesmo que pareça possível escolher ou formatar uma letra,
  falta a análise conjunta exigida. Marque esse critério como não atendido e encaminhe a lacuna a C.2.
- Justificativa opcional: a falta de uma explicação destinada ao usuário não é, por si, pendência
  se o pedido a permite sem exigir e a conclusão já está sustentada. Justificativa obrigatória:
  se o pedido exige fundamentação e ela não consta dos resultados, reprove o critério correspondente.
  Não invente essa exigência quando o pedido só solicita objetividade.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, preenchendo `criteria_evaluation` primeiro, `unmet_criteria_ids` em seguida e `decision` por
último, no formato:

{"criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": [], "decision": "approved"}
