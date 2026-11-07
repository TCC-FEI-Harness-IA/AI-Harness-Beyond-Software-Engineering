# C.2 — Planejamento adicional

Crie novas tarefas independentes **apenas** para suprir as lacunas de conteúdo apontadas abaixo.

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

Exceção: quando o critério pendente exige selecionar uma alternativa disponível e os resultados
anteriores não sustentam nenhuma delas, a divergência é uma lacuna de conteúdo. Planeje a
investigação da interpretação do enunciado, dos dados e dos cálculos ou conclusões responsáveis
pela incompatibilidade, mesmo que tenham sido aprovados anteriormente. Não trate essas conclusões
como premissas imutáveis nem crie apenas uma tarefa para escolher uma letra. A nova tarefa deve
produzir uma conclusão explicada compatível com as alternativas e explicitar qual resultado
anterior corrige, quando houver correção. Não escolha por proximidade numérica sem que o enunciado
admita aproximação.

Cada tarefa deve:

1. Ter **um único objetivo**, resolvível de forma independente das demais.
2. Trazer os **próprios critérios de aceite individuais**, que permitam julgar isoladamente se a
   tarefa foi bem resolvida. Os critérios de uma mesma tarefa devem ser **complementares, nunca
   mutuamente exclusivos**: tem de ser possível que uma única resposta atenda a todos eles ao mesmo
   tempo. Antes de fechar a lista, confira os critérios aos pares e elimine qualquer contradição —
   por exemplo, "responda somente a alternativa" e "a resposta deve conter explicações" se excluem
   e não podem coexistir.
3. Trazer, entre os critérios, **restrições de escopo que impeçam a resolução precoce da questão
   principal**, redigidas de forma **afirmativa e delimitadora** — por exemplo: "o escopo da
   resposta restringe-se exclusivamente a [escopo da tarefa], sem antecipar etapas posteriores nem
   escolher a alternativa final". Evite formular o critério com negativas ambíguas ("não concluir
   se...", "não afirmar que não...") que possam ser confundidas pelo verificador quando a própria
   conclusão técnica da tarefa for uma impossibilidade ou negação.
4. Exigir que a resposta da tarefa traga o **resultado acompanhado da explicação de por que ele é
   válido**, nunca o resultado isolado. Se a tarefa envolve uma conta, a resposta deve apresentar
   as fórmulas usadas, a substituição dos valores com unidades de medida, as convenções adotadas
   (sinais, referenciais, aproximações) e a justificativa de cada passo até o valor final; se
   envolve uma classificação ou escolha, deve apresentar o raciocínio que a sustenta. Escreva essa
   exigência na descrição da tarefa e inclua um critério de aceite que a verifique. Mesmo quando um
   critério geral pendente pedir que a resposta final ao usuário contenha "apenas a letra da
   alternativa, sem justificativa", **nunca** transponha essa restrição de formato para a tarefa:
   a formatação enxuta pertence exclusivamente à síntese final (`C.3`), enquanto toda tarefa precisa
   explicitar a justificativa do resultado para ser verificável.
5. **Jamais pré-calcular resultados da nova tarefa nos critérios de aceite.** Não resolva a nova
   tarefa dentro de `description` ou `acceptance_criteria` (`T*-AC*`), nem crave de antemão o valor
   numérico que a nova tarefa ainda deverá calcular: apoie-se apenas nos dados literais de
   **Aprendizados Pontuais** e nos resultados já aprovados em **Resultados já armazenados**. Garanta
   que a última tarefa planejada conclua o cálculo ou a determinação exata da grandeza final pedida
   pela questão, deixando apenas a apresentação e a escolha da letra da alternativa para `C.3`.

Não transforme idioma, formato ou concisão finais em tarefas de apresentação. A ausência de uma
linha final formatada ou a presença de explicações internas não são, sozinhas, lacunas de conteúdo.
Use os critérios pendentes para identificar qual informação ainda falta, sem os reescrever ou
revisar. Toda nova tarefa continua exigindo resultado explicado, mesmo para resposta final enxuta.

## Exemplos de planejamento válido e inválido

- Lacuna real: exige-se análise conjunta, mas há apenas verificações isoladas. Válido: tarefa
  autossuficiente com os dados já obtidos, para determinar e explicar a interseção das condições.
  Inválido: pedir só uma letra, proibir a justificativa ou proibir a análise conjunta que falta.
- Se a alternativa C já está sustentada e só falta `RESPOSTA_FINAL: C`, criar uma tarefa para
  escrever a linha seria indevido: C.3 aplica o formato. Se falta identificar a alternativa,
  a tarefa deve produzir a análise e a identificação explicada, não apenas a linha final.
- Válido para massa total: "não calcular a massa por colher". Inválido: "não mencionar colheres".
  A referência contextual é permitida; executar o cálculo adicional é uma violação real de escopo.
- "Seja objetivo" não autoriza impor duas linhas ou limite de palavras. Uma justificativa
  opcional na resposta final não elimina a explicação obrigatória do resultado interno.

Em **questões de múltipla escolha** (especialmente quando os resultados anteriores descartaram todas
as opções por rigor literal), crie uma única tarefa comparativa que avalie as opções por **melhor
aderência relativa e eliminação dos distratores mais graves**, admitindo paráfrases, sínteses ou
inferências interpretativas razoáveis, sem repetir proibições hiper-literais que inviabilizem todas
as alternativas.

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
