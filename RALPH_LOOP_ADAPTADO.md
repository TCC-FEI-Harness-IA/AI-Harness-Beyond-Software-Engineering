# Ralph Wiggum Loop adaptado para perguntas em linguagem natural

## Resumo

Este documento contextualiza uma adaptação do **Ralph Wiggum Loop**, originalmente empregado em engenharia de software, para responder perguntas gerais em linguagem natural, incluindo questões de múltipla escolha. A arquitetura utiliza planejamento, decomposição em tarefas atômicas, execução e validação iterativas, reinicialização de contexto entre tarefas (*Fresh Context*) e síntese final sujeita a critérios de aceite globais. A seção **Metodologia original** abaixo é uma transcrição literal do trecho fornecido no paper, sem correções ou reformulações. Depois da transcrição do paper, o fluxo implementado recebeu uma extensão, a etapa **A.3 — Aprendizados pontuais do enunciado**, descrita na seção **Extensões ao método do paper** e detalhada em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md).

## O que é o Ralph Wiggum Loop?

O Ralph Wiggum Loop é um paradigma de orquestração iterativa atribuído a Geoffrey Huntley, originalmente voltado ao desenvolvimento de software. Requisitos são decompostos em histórias ou tarefas pequenas, cada uma executada e validada contra critérios de aceite. Se uma tentativa falha, ela é revista e repetida. Ao passar para uma tarefa diferente, inicia-se um contexto novo, preservando apenas aprendizados relevantes de forma compacta, para reduzir a degradação associada ao crescimento do histórico (*context rot*).

Na adaptação proposta pelo paper, histórias de usuário tornam-se **tarefas autônomas de raciocínio**. Como o produto esperado deixa de ser código versionado e passa a ser uma resposta ao usuário, acrescenta-se uma fase explícita de **Criação da Resposta Final**.

## Guia de implementação para agentes de desenvolvimento CLI

> **Nota de procedência:** esta seção é uma orientação operacional derivada da Metodologia, não faz parte da transcrição literal. Em caso de divergência, prevalece a Metodologia original abaixo, com uma única exceção: a etapa **A.3** (item 3), que é uma extensão posterior ao paper e está registrada em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md).

1. **A.1 — Critérios gerais:** receber a pergunta original e executar um prompt fixo `Template A.1` para definir idioma, formato, restrições e condições da resposta final; persistir esses critérios.
2. **A.2 — Planejamento:** executar `Template A.2` sobre a pergunta original para criar uma lista ordenada de tarefas de objetivo único, cada uma com descrição, escopo, entradas/saídas esperadas e critérios individuais de aceite; persistir a lista.
3. **A.3 — Aprendizados pontuais do enunciado (extensão):** executar `Template A.3` sobre a pergunta original, em janela própria, para anotar os pontos que chamam a atenção no enunciado: valores com unidades de medida, alternativas, fórmulas, condições e restrições. Acrescentar essas anotações à memória de aprendizados **antes** de qualquer tarefa; uma lista vazia é válida. Não resolver a pergunta.
4. **B.1 — Seleção e resolução:** selecionar programaticamente a próxima tarefa; iniciar um contexto novo com os aprendizados compactos acumulados (as anotações de A.3 e os aprendizados de B.4 das tarefas anteriores, se houver), a tarefa e `Template B.1`. Não antecipar a solução global.
5. **B.2 — Validação:** avaliar a resposta preliminar contra todos os critérios individuais usando `Template B.2`. Se reprovar, reenviar o feedback e repetir **no mesmo contexto da tarefa**, preservando tentativas anteriores.
6. **B.3 — Resultado aprovado:** persistir somente a resposta aprovada, indexada pelo identificador da tarefa. Não enviar tentativas reprovadas para a síntese final.
7. **B.4 — Aprendizados pontuais:** executar `Template B.4` sobre o histórico completo da tarefa e extrair fatos compactos úteis para tarefas seguintes. **Não** incluir esses aprendizados na construção da resposta final.
8. **Fresh Context:** ao avançar para outra tarefa, descartar o histórico da tarefa anterior; criar uma nova chamada/contexto e injetar os aprendizados compactos (inclusive as anotações de A.3) antes da tarefa seguinte. A checagem de existência de tarefas pendentes é programática.
9. **C.1 — Validação global:** reunir apenas os resultados aprovados e os critérios gerais de A.1; executar `Template C.1` para verificar a suficiência do conjunto.
10. **Planejamento adicional:** se a validação global reprovar, identificar critérios pendentes, gerar novas tarefas específicas e retornar ao loop de execução.
11. **Resposta final:** após aprovação global, sintetizar a resposta a partir dos resultados aprovados, obedecendo idioma, formato e restrições gerais.

**Separação de estados:** mantenha, no mínimo, `original_question`, `general_acceptance_criteria`, `task_queue`, `approved_task_results`, `accumulated_learnings` e `current_task_context`. `accumulated_learnings` recebe primeiro as anotações de A.3 e depois os aprendizados de B.4, na ordem em que surgem. Os nomes são sugestões de implementação, não nomes exigidos pelo paper. O texto acadêmico define o comportamento conceitual dos templates, mas não fornece seus prompts completos; eles precisam ser implementados de acordo com as responsabilidades descritas, sem alegar que são transcrições do trabalho.

## Extensões ao método do paper

> **Nota de procedência:** as regras desta seção **não constam** da transcrição literal da Metodologia. Elas foram introduzidas depois de testes com o fluxo implementado e, por isso, aparecem separadas do texto do paper. O relatório completo, com exemplos, está em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md).

### A.3 — Aprendizados pontuais do enunciado

**Problema observado.** Cada tarefa roda em contexto novo (*Fresh Context*) e só enxerga a própria descrição e os aprendizados acumulados. Na versão do paper, o primeiro aprendizado só nasce em B.4, depois da primeira tarefa. Se o decompositor (A.2) não repetir na descrição de uma tarefa um dado importante do enunciado, como as alternativas de uma questão de múltipla escolha, um valor com sua unidade ou uma fórmula, esse dado se perde para a tarefa.

**Regra.** A terceira etapa do Planejamento, executada logo depois de A.2, salva os aprendizados pontuais do enunciado:

> *Pergunta do usuário* + *Template A.3* → *Aprendizados Pontuais do Enunciado*

- A entrada é **somente a pergunta original**, em janela de contexto própria. A etapa não vê os critérios de A.1 nem as tarefas de A.2.
- A saída é uma lista de fatos secos e atômicos, copiados como aparecem no enunciado: valores **com unidades de medida**, **alternativas** (com sua letra ou número, sem omitir nenhuma), **fórmulas**, **condições e restrições** (inclusive as simultâneas) e qualquer outro dado que chamaria a atenção de quem não leu a pergunta.
- A etapa **não resolve** a pergunta: conclusões, cálculos e palpites de resposta são proibidos.
- Uma lista vazia é válida (enunciado sem nada a anotar); nesse caso nenhum bloco é injetado.
- Os fatos entram na mesma memória de aprendizados de B.4, **antes** de qualquer tarefa. Portanto são injetados no início do contexto novo de **toda** tarefa, inclusive a primeira e as criadas pelo Planejamento Adicional (C.2), antes dos aprendizados que B.4 for acrescentando.
- Valem para A.3 as mesmas separações dos demais aprendizados: o validador de tarefa (B.2) não os recebe e eles **não** participam da validação global (C.1) nem da resposta final (C.3).

**Consequência na primeira tarefa.** Na versão do paper, "na primeira tarefa do ciclo não há aprendizados acumulados". Com A.3, a primeira tarefa já recebe as anotações do enunciado, quando A.3 as produz.

## Metodologia original — transcrição literal

> **Atenção:** o bloco abaixo descreve o Planejamento em duas etapas (A.1 e A.2) e afirma que a primeira tarefa não tem aprendizados acumulados. Ambas as afirmações valem para o paper, mas **não** para o fluxo implementado, que inclui a etapa A.3 (ver **Extensões ao método do paper**). O texto abaixo permanece inalterado de propósito.

O bloco abaixo preserva exatamente os caracteres do trecho original enviado, inclusive marcação LaTeX/Markdown, fórmulas, exemplos, referências a figuras e eventuais erros tipográficos. Referências a imagens permanecem como caminhos do documento de origem; os arquivos das figuras não foram fornecidos. A seção separada **“Métodologia de avaliação”** não foi incluída, pois não faz parte da seção intitulada **“Metodologia”** no arquivo original.

### Metodologia

<!-- ================================================= -->

![Visão geral do Ralph Wiggum Loop adaptado para resolução de perguntas em linguagem natural.](diagrams/ralph_loop_adaptado_png)

Visão geral do *Ralph Wiggum Loop* adaptado para resolução de perguntas em linguagem natural.

<a id="fig-ralph_loop_adaptado"></a>

<!-- ============================================================= -->

<!-- METODOLOGIA — Adaptação do Ralph Wiggum Loop -->

<!-- ============================================================= -->

A adaptação do *Ralph Wiggum Loop* para um contexto generalista de resolução de perguntas em linguagem natural exige ajustes estruturais em relação à formulação original, que foi concebida exclusivamente para fluxos de engenharia de software. A Figura [fig:ralph_loop_adaptado](#fig-ralph_loop_adaptado) apresenta uma visão geral do fluxo proposto, que preserva os princípios centrais do paradigma original, representado na Figura fig:ralph_loop_original.

Em linhas gerais, propomos uma conversão do conceito de histórias de usuário para tarefas, o que nos permite manter um fluxo muito próximo do original, contendo as etapas de “Planejamento” e “Execução em Loop”. Entretanto, passa a ser necessário considerar a criação de um retorno ao usuário, algo que não constitui uma preocupação no *Ralph Wiggum Loop* original. Dessa forma, incorporamos uma nova fase após o fluxo de execução, denominada “Criação da Resposta Final”, que contém toda a lógica necessária para agrupar os resultados produzidos pelas tarefas anteriores em uma resposta que apresente o conteúdo e o formato esperados pelo usuário.

Para ilustrar concretamente cada etapa do fluxo, adota-se ao longo desta seção o seguinte *input* de referência:

**Exemplo**

Qual dos seguintes números é simultaneamente primo, par e maior que 2?

- A) 2

- B) 4

- C) 6

- D) Nenhuma das anteriores

Ao longo da descrição de cada fase, são apresentadas expressões que indicam quais informações compõem a entrada submetida ao modelo e qual saída é esperada. As nomenclaturas adotadas nessas expressões, como “Pergunta do usuário” ou “Template A.1”, representam os componentes lógicos necessários para montar o *prompt* de cada fase. O termo “Pergunta do usuário” refere-se ao *input* original fornecido ao sistema. Os termos na forma “Template X” referem-se a *prompts* fixos de instrução, cuja função é orientar o modelo sobre o que deve fazer naquela etapa específica. Já os termos na forma “Resultado Fase X” referem-se à saída produzida pelo modelo em uma etapa anterior, que pode ser reutilizada como entrada em etapas seguintes. Essas expressões não descrevem uma implementação concreta, mas sim a organização conceitual das informações que devem ser reunidas para que cada etapa do fluxo cumpra sua função.

<!-- ────────────────────────────────────────────────────────────── -->

<!-- A. Planejamento -->

<!-- ────────────────────────────────────────────────────────────── -->

#### Planejamento

O planejamento é o início de todo o fluxo, compreendendo duas etapas que preparam toda a estrutura de execução: a definição dos critérios que a resposta final deverá respeitar e a decomposição da pergunta em tarefas autônomas e verificáveis.

<!-- ———————————————————————— -->

<a id="subsec-PlanejamentoA1"></a>

##### Definição dos critérios de aceite gerais

Essa etapa representa uma adição em relação ao paradigma original. No contexto de engenharia de software, cada tarefa concluída resultava em um *commit* que preservava o progresso diretamente no repositório, de modo que, ao término de todas as histórias de usuário, o produto final já estava pronto. No fluxo adaptado, entretanto, a conclusão de todas as tarefas não produz automaticamente uma saída utilizável: após todas as tarefas serem concluídas, é necessário construir uma resposta final que consolide os resultados gerados. Os critérios de aceite gerais definem as regras que essa resposta deverá respeitar, abrangendo aspectos como o idioma a ser utilizado, o formato de apresentação esperado e os tópicos-chave que devem constar no conteúdo final.

A execução desta etapa envolve a associação da pergunta do usuário com instruções estruturadas, representadas pelo Template A.1. Este gabarito orienta o modelo a analisar o enunciado recebido e produzir as diretrizes gerais que a resposta final precisará satisfazer. Especificamente, as instruções orientam o modelo a identificar o idioma de resposta adequado, a estrutura ideal do formato de saída (como seleção de alternativas ou desenvolvimento textual) e os termos e restrições obrigatórios definidos no enunciado. A relação de entrada e saída que formaliza essa transformação de prompts é descrita na expressão ([eq:fluxo_a1](#eq-fluxo_a1)):

<a id="eq-fluxo_a1"></a>

> *Pergunta do usuário* + *Template A.1* → *Resultado Fase A.1*

Nesta expressão, “Pergunta do usuário” representa o enunciado inicial e as opções de escolha inseridas no sistema, enquanto “Template A.1” constitui o prompt fixo de instrução que orienta a análise. O “Resultado Fase A.1” corresponde à lista final de critérios de aceite gerais que deverão ser satisfeitos para que a resposta final seja homologada.

Os critérios de aceite estruturados gerados no Resultado Fase A.1 são persistidos localmente (em disco ou em memória) para posterior validação global na fase de Criação da Resposta Final.

**Exemplo**

Considerando o *input* de referência, o modelo deveria retornar uma lista de critérios como os seguintes.

**Saída LLM**

> “A pergunta deve ser respondida em Português do Brasil.”
>
> “Responda somente a alternativa, sem conter explicações adicionais.”
>
> “Garanta que o valor encontrado ao final corresponde a uma das alternativas fornecidas.”

<!-- ———————————————————————— -->

<a id="subsec-PlanejamentoA2"></a>

##### Quebra em tarefas de objetivo único com critérios de aceite individuais

A segunda etapa do planejamento é responsável por quebrar a pergunta do usuário em pequenas tarefas autônomas. Cada tarefa precisa ter pelo menos um critério de aceite, isto é, uma condição que define o conteúdo esperado para que a tarefa possa ser considerada concluída. A ideia central é criar tarefas que gerem insumos capazes de, em conjunto, sustentar a construção da resposta final.

Esta etapa é operacionalizada ao submeter a pergunta do usuário juntamente com o Template A.2, cuja finalidade é instruir o modelo a realizar a decomposição em tarefas de responsabilidade única. O template orienta a caracterização detalhada de cada tarefa (como as respectivas entradas e saídas esperadas), deixando explícito que o contexto não será compartilhado diretamente entre as iterações subsequentes para mitigar o *context rot*. Adicionalmente, exige-se que cada tarefa traga seus próprios critérios de aceite individuais e restrições de escopo que evitem resoluções precoces do problema principal. A relação operacional de transformação é formalizada na expressão ([eq:fluxo_a2](#eq-fluxo_a2)):

<a id="eq-fluxo_a2"></a>

> *Pergunta do usuário* + *Template A.2* → *Resultado Fase A.2*

Na formulação descrita, “Pergunta do usuário” corresponde ao enunciado principal que orienta a resolução, “Template A.2” identifica o prompt estruturado que instrui o modelo a realizar a divisão em tarefas, e “Resultado Fase A.2” é o cronograma resultante contendo a lista ordenada de tarefas e as condições de aceitação individuais de cada uma delas. O Resultado Fase A.2 gerado é armazenado localmente para posterior coordenação na fase de Execução em Loop.

**Exemplo**

Considerando o *input* de referência, o modelo deveria retornar uma decomposição como a seguinte.

**Saída LLM**

**Tarefa 1**

- Tarefa: “Dadas as opções (2, 4, 6), identifique quais desses números são primos.”

- Critérios de aceite:

    - “Deve retornar a lista de números primos encontrados nas alternativas.”

    - “Deve incluir uma breve explicação da regra de identificação de números primos.”

    - “A resposta não deve tentar resolver a questão final.”

    - “A resposta não deve avaliar nenhuma outra condição.”

**Tarefa 2**

- Tarefa: “Dadas as opções (2, 4, 6), identifique quais desses números são pares.”

- Critérios de aceite:

    - “Deve retornar a lista de números pares encontrados nas alternativas.”

    - “Deve incluir uma breve explicação da regra de identificação de números pares.”

    - “A resposta não deve tentar resolver a questão final.”

    - “A resposta não deve avaliar nenhuma outra condição.”

**Tarefa 3**

- Tarefa: “Dadas as opções (2, 4, 6), identifique quais desses números são estritamente maiores que 2.”

- Critérios de aceite:

    - “Deve retornar a lista de números maiores que 2 encontrados nas alternativas.”

    - “Deve incluir uma breve justificativa matemática para a comparação estabelecida.”

    - “A resposta não deve tentar resolver a questão final.”

    - “A resposta não deve avaliar nenhuma outra condição.”

<!-- ────────────────────────────────────────────────────────────── -->

<!-- B. Execução em Loop -->

<!-- ────────────────────────────────────────────────────────────── -->

#### Execução em Loop

A fase de execução preserva a estrutura iterativa do paradigma original, mas adapta o mecanismo de conclusão de cada unidade de trabalho. Na formulação original, a conclusão de uma história de usuário é verificada por meio da execução de testes automatizados e da análise dos critérios de aceite associados ao código produzido. No fluxo adaptado, como não há código a ser testado, o modelo simplesmente resolve a tarefa selecionada e, em seguida, verifica se o resultado satisfaz os critérios de aceite individuais definidos no planejamento. Caso os critérios não sejam atingidos, o modelo repete a resolução da mesma tarefa até que sejam satisfeitos.

Ao concluir uma tarefa com sucesso, o modelo realiza dois registros distintos com finalidades diferentes: **(i)** persiste a resposta aprovada em armazenamento local ou na memória da aplicação, em formato suficientemente estruturado para que cada resultado possa ser recuperado individualmente, servindo de insumo para a fase de Criação da Resposta Final; e **(ii)** extrai os aprendizados pontuais da execução, isto é, informações objetivas descobertas ao longo das tentativas, que serão injetados no contexto da próxima tarefa como mecanismo de *Fresh Context*. É fundamental ressaltar que esses dois registros têm escopos completamente distintos: os resultados armazenados alimentam exclusivamente a fase de Criação da Resposta Final; os aprendizados pontuais têm papel restrito à Execução em Loop e não participam da construção da resposta final. Antes de iniciar a execução da tarefa seguinte, o contexto é reinicializado, ou seja, o contexto é descartado e, atravez de uma nova chamada ao modelo, é recriado e os aprendizados acumulados são injetados como primeira entrada do novo contexto, de forma estruturada e explícita. Esse mecanismo garante que o conhecimento relevante seja preservado sem que o ruído e as redundâncias das etapas anteriores sejam herdados, mitigando ativamente o fenômeno de *context rot* [hong2025context].

Após cada tarefa concluída, o fluxo verifica programaticamente se ainda existem tarefas disponíveis na lista produzida pelo planejamento. Caso haja, uma nova iteração é iniciada: o contexto é reinicializado, os aprendizados acumulados são injetados e a próxima tarefa é selecionada. Caso contrário, o fluxo avança para a fase de Criação da Resposta Final, levando consigo apenas os resultados armazenados, sem os aprendizados pontuais. Essa verificação é puramente programática e não envolve chamada ao LLM.

<!-- ———————————————————————— -->

<a id="subsec-ExecucaoB1"></a>

##### Seleção da tarefa e resolução

Essa subseção corresponde às etapas B.1 e B.2 do fluxo ilustrado na Figura [fig:ralph_loop_adaptado](#fig-ralph_loop_adaptado): a seleção da próxima tarefa disponível na lista gerada pelo planejamento (B.1) e sua subsequente resolução pelo modelo (B.2). Ao iniciar uma nova tarefa, e somente nesse momento, o contexto é reinicializado. Os aprendizados pontuais acumulados nas tarefas anteriores são injetados no início do novo contexto, antes da descrição da tarefa atual, garantindo continuidade do conhecimento relevante sem carregar o ruído das execuções anteriores. Na primeira tarefa do ciclo, não há aprendizados acumulados, de modo que o contexto inicial contém apenas a tarefa a ser resolvida.

Para processar esta etapa, a descrição da tarefa selecionada é enviada ao modelo em conjunto com o Template B.1 e, caso existam iterações anteriores concluídas, com a memória de aprendizados acumulados. O Template B.1 impõe um limite estrito ao modelo, instruindo-o a focar unicamente no escopo demarcado para a tarefa e a abster-se de resolver a questão final prematuramente. O fluxo lógico de processamento de entradas e geração de respostas preliminares é modelado na expressão ([eq:fluxo_b1](#eq-fluxo_b1)):

<a id="eq-fluxo_b1"></a>

> *Aprendizados Acumulados* + *Tarefa Selecionada* + *Template B.1* → *Resultado Preliminar B*

Nessa relação operacional, “Aprendizados Acumulados” refere-se ao conjunto de anotações internas compactas sintetizadas nas iterações anteriores (que se inicia vazio), “Tarefa Selecionada” consiste no bloco descritivo e critérios individuais definidos em Resultado Fase A.2, e “Template B.1” é o prompt estruturado de instrução. A variável “Resultado Preliminar B” denota a resposta preliminar produzida que será submetida à validação. O Resultado Preliminar B gerado por esta operação é subsequentemente direcionado à fase de controle de qualidade para validação individual dos critérios.

**Exemplo**

Considerando a Tarefa 1 como primeira tarefa do ciclo, o contexto não contém aprendizados acumulados.

**Saída LLM**

> “Entre as alternativas (2, 4, 6), somente o número 2 é primo. Um número primo é aquele divisível exclusivamente por 1 e por ele mesmo. O número 4 possui divisores adicionais (1, 2 e 4) e o 6 também (1, 2, 3 e 6), portanto nenhum dos dois é primo. Resultado: [2].”

<!-- ———————————————————————— -->

<a id="subsec-ExecucaoB2"></a>

##### Verificação dos critérios de aceitação da tarefa

Essa etapa verifica se o Resultado Preliminar B produzido na etapa anterior atende a todos os critérios de aceite individuais associados à tarefa em execução. Trata-se de um mecanismo de controle de qualidade interno: se todos os critérios forem atendidos, o fluxo avança para o armazenamento do resultado; caso contrário, a tarefa é reapresentada ao modelo para uma nova tentativa. É importante destacar que, ao contrário do que ocorre na transição entre tarefas distintas, o contexto *não* é reinicializado durante as tentativas de repetição de uma mesma tarefa. Essa escolha é intencional e tambem é usada no *Ralph Loop* original: a tentativa anterior, com os critérios não satisfeitos explicitamente sinalizados, permanece no contexto e auxilia o modelo a identificar o que deve ser corrigido na próxima execução.

Esta validação lógica é formalizada na expressão ([eq:fluxo_b2](#eq-fluxo_b2)), onde se cruzam os resultados da inferência com os critérios estabelecidos:

<a id="eq-fluxo_b2"></a>

> *Resultado Preliminar B* + *Critérios da Tarefa* + *Template B.2* → *Decisão (Aprovado / Reprovado)*

Nesta expressão, “Resultado Preliminar B” é a resposta candidata produzida pelo modelo, “Critérios da Tarefa” corresponde às condições específicas indexadas no Resultado Fase A.2, e “Template B.2” é o prompt estruturado de validação que define as regras do processo de qualidade, culminando na “Decisão (Aprovado / Reprovado)”. Esta etapa de validação operacionaliza-se por meio do Template B.2, o **Cenário de reprovação e nova tentativa.**

**Exemplo**

Considere a Tarefa 2 (“identifique quais números são pares”). O aprendizado acumulado da Tarefa 1 já está no contexto: “O único número primo entre as alternativas é o 2”. Suponha que o modelo produza na primeira tentativa:

**Saída LLM**

> “Todos os números 2, 4 e 6 são pares, pois são divisíveis por 2. No entanto, como apenas o 2 é primo (identificado anteriormente) e o 2 não é maior que 2, nenhuma alternativa satisfaz simultaneamente as três condições. Portanto, a resposta é D) Nenhuma das anteriores.”

Avaliando esse resultado contra os critérios da Tarefa 2:

**Saída LLM**

> - “Deve retornar a lista de números pares.”  *Atendido*: os três números foram identificados.
>
> - “Deve incluir explicação da regra de identificação de pares.”  *Atendido*: a divisibilidade por 2 foi mencionada.
>
> - “A resposta não deve tentar resolver a questão final.”  **Não atendido**: o modelo antecipou a resposta final.
>
> - “A resposta não deve avaliar nenhuma outra condição.”  **Não atendido**: o modelo cruzou condições de outras tarefas.
>
> Decisão: **Reprovado**.

O fluxo retorna à resolução da Tarefa 2, mantendo o contexto com a tentativa reprovada e os critérios não satisfeitos identificados. Na segunda tentativa, com o *feedback* anterior no contexto, o modelo retorna:

**Saída LLM**

> “Entre as alternativas (2, 4, 6), todos os três números são pares, pois cada um deles é divisível por 2 sem deixar resto (2÷2=1, 4÷2=2, 6÷2=3). Resultado: [2, 4, 6].”

Todos os critérios da Tarefa 2 são agora atendidos. Decisão: **Aprovado**. O fluxo avança.

<!-- ———————————————————————— -->

<a id="subsec-ExecucaoB3"></a>

##### Armazenamento do resultado

Quando a resposta de uma tarefa é aprovada na verificação dos critérios de aceite, ela é persistida localmente. Somente essa resposta aprovada é armazenada: todo o ruído gerado pelos ciclos de tentativa anteriores (incluindo respostas reprovadas, histórico de verificações e *feedback* intermediário) é descartado na reinicialização do contexto. O armazenamento é indexado por tarefa, de modo que cada resultado possa ser recuperado individualmente como insumo exclusivo da fase de Criação da Resposta Final. A persistência é meramente operacional e não envolve novas chamadas ao modelo, sendo formalizada na expressão ([eq:fluxo_b3](#eq-fluxo_b3)):

<a id="eq-fluxo_b3"></a>

> *Resposta Aprovada* → *Armazenamento local*

Nesta expressão, “Resposta Aprovada” representa a solução da tarefa que atendeu satisfatoriamente a todos os critérios na etapa anterior, a qual é direcionada para o “Armazenamento local”, que consiste na persistência física (em disco ou memória) indexada pelo identificador da tarefa correspondente.

**Exemplo**

A Tarefa 2 exigiu duas tentativas antes de ser aprovada. Somente a segunda é armazenada. A primeira tentativa reprovada, aquela que antecipou indevidamente a resposta final, permanece apenas no contexto ativo durante o ciclo de repetição e é descartada na reinicialização.

Ao término da Execução em Loop, o armazenamento contém exclusivamente as respostas aprovadas de cada tarefa:

- Tarefa 1: “Entre as alternativas (2, 4, 6), somente o número 2 é primo. Um número primo é aquele divisível exclusivamente por 1 e por ele mesmo. O número 4 possui divisores adicionais (1, 2 e 4) e o 6 também (1, 2, 3 e 6), portanto nenhum dos dois é primo. Resultado: [2].”

- Tarefa 2: “Entre as alternativas (2, 4, 6), todos os três números são pares, pois cada um deles é divisível por 2 sem deixar resto (2÷2=1, 4÷2=2, 6÷2=3). Resultado: [2, 4, 6].”

- Tarefa 3: “Os números estritamente maiores que 2 entre as alternativas são 4 e 6. O número 2 não satisfaz essa condição pois 2 > 2 é falso. Resultado: [4, 6].”

Esse conjunto é entregue à fase de Criação da Resposta Final como base exclusiva para a construção da resposta.

<!-- ———————————————————————— -->

<a id="subsec-ExecucaoB4"></a>

##### Armazenamento dos aprendizados pontuais

Os aprendizados pontuais funcionam como as “anotações internas” do fluxo de *thinking*: são fatos secos e objetivos descobertos durante a execução de uma tarefa que podem ser úteis para guiar as tarefas subsequentes. Esses aprendizados não devem ser conceitos redundantes ou óbvios, mas sim dados de controle, metadados operacionais e restrições práticas descobertas na execução, como, por exemplo, registrar uma versão da linguagem específica disponível no ambiente. A extração de aprendizados considera o contexto completo da tarefa, incluindo as tentativas reprovadas, pois fatos úteis podem ter emergido mesmo em execuções que não passaram na verificação de critérios. Os aprendizados pontuais têm escopo estritamente restrito à Execução em Loop: são injetados no início do contexto de cada nova tarefa para subsidiar a resolução, mas não são incluídos, em nenhuma hipótese, na fase de Criação da Resposta Final.

A extração de conhecimento é estruturada ao aplicar o Template B.4 sobre o histórico completo de execução da tarefa. A instrução exige que o modelo compile exclusivamente fatos concretos descobertos durante as tentativas (aprovadas ou não), registrando-os em formato de tópicos sucintos e secos, sem justificativas ou descrições narrativas de processo. A geração dessas anotações internas é representada na expressão ([eq:fluxo_b4](#eq-fluxo_b4)):

<a id="eq-fluxo_b4"></a>

> *Contexto Completo da Tarefa* + *Template B.4* → *Aprendizados Pontuais*

Nessa expressão, “Contexto Completo da Tarefa” compreende todo o histórico acumulado no contexto (incluindo tentativas anteriores reprovadas e interações com o validador), “Template B.4” representa o prompt fixo que rege a compilação puramente factual, e “Aprendizados Pontuais” representa os tópicos secos resultantes anexados à Memória Acumulada. Os aprendizados pontuais resultantes são anexados à Memória Acumulada da aplicação. Diferente dos resultados estruturados de B.3, esses fatos acumulados destinam-se unicamente a guiar os novos contextos das tarefas subsequentes e não alimentam a resposta do usuário.

**Exemplo**

Após a conclusão da Tarefa 1 (identificação de números primos), a Memória Acumulada conteria um único aprendizado pontual realmente útil para guiar as etapas subsequentes, em vez de uma cópia da resposta completa gerada na etapa anterior ou de definições óbvias:

**Saída LLM**

> “Um número primo é aquele que só é divisível por 1 e por ele mesmo.”
>
>  
>
> “um numero par é aquele que é divisível por 2 sem deixar resto”
>
>  
>
> “Primos entre (2,4,6): [2]”
>
>  
>
> “Pares entre(2,4,6): [2, 4,6]”
>
>  
>
> “Maiores que 2 entre(2,4, 6): [4, 6]”

Esse bloco compacto de fatos atômicos é injetado no início do contexto das tarefas subsequentes para auxiliá-las, sem carregar a descrição e o formato verbal da resposta completa gerada anteriormente.

Como contraponto, o trecho a seguir ilustra o formato **inválido** de aprendizado, por ser excessivamente verboso, conter contexto processual irrelevante e não focar na restrição operacional útil:

> *Inválido:* “Durante a execução da Tarefa 1, analisamos os números 2, 4 e 6, e depois de validarmos os divisores de cada um deles, concluímos que apenas o 2 é primo pois é divisível apenas por 1 e por ele mesmo.”

O aprendizado pontual válido extrai puramente a informação útil: “Um número primo é aquele que só é divisível por 1 e por ele mesmo.”.

A distinção entre resultado armazenado (etapa anterior) e aprendizado pontual é estrutural e intencional. O resultado é a resposta completa e verificada da tarefa, destinada à síntese da fase de Criação da Resposta Final. O aprendizado é um fragmento seco de fato, destinado exclusivamente a subsidiar a execução das tarefas seguintes dentro do loop.

<!-- ────────────────────────────────────────────────────────────── -->

<!-- C. Criação da Resposta Final -->

<!-- ────────────────────────────────────────────────────────────── -->

#### Criação da Resposta Final

A terceira fase constitui uma adição exclusiva do fluxo adaptado, sem correspondência direta na formulação original. No *Ralph Wiggum Loop* concebido para engenharia de software, o produto final é o próprio código implementado e versionado ao longo das histórias; não há, portanto, necessidade de uma etapa de síntese do conteúdo e geração de resposta. No fluxo adaptado, os resultados das tarefas individuais são fragmentos de raciocínio que precisam ser compilados em uma resposta coesa e completa.

Após o encerramento do loop, o modelo compila os resultados armazenados e verifica se as informações produzidas são suficientes para satisfazer todos os critérios de aceite gerais definidos no planejamento. Se os critérios forem integralmente atendidos, o modelo constrói a resposta final e a retorna ao usuário. Caso contrário, o sistema infere que o planejamento inicial foi insuficiente para cobrir todos os aspectos da pergunta e inicia uma fase de Planejamento Adicional: o modelo identifica os critérios ainda não atendidos, cria novas tarefas individuais para supri-los e retorna à fase de Execução em Loop. Esse mecanismo garante que lacunas de planejamento sejam identificadas e corrigidas antes que a resposta final seja construída, preservando a completude e a coerência da saída.

<!-- ———————————————————————— -->

<a id="subsec-RespostaC1"></a>

##### Compilação dos resultados e verificação dos critérios gerais

Essa etapa reúne todos os resultados armazenados durante a Execução em Loop e verifica se o conjunto de informações produzido é suficiente para satisfazer cada um dos critérios de aceite gerais definidos na etapa A.1. A distinção central em relação à verificação realizada na fase de Execução em Loop reside no escopo da avaliação: na etapa anterior, a verificação possui caráter local, avaliando cada tarefa individualmente frente aos seus próprios critérios; nesta etapa, por outro lado, a avaliação é global, considerando se a união dos dados acumulados atende plenamente ao enunciado geral.

A validação global é efetuada ao associar os resultados consolidados com os critérios de A.1 sob as diretrizes do Template C.1. O modelo avalia individualmente as condições e emite um veredito estruturado (aprovado ou reprovado), apontando as eventuais pendências. A dinâmica de controle global é formalizada na expressão ([eq:fluxo_c1](#eq-fluxo_c1)):

<a id="eq-fluxo_c1"></a>

> *Resultados Armazenados* + *Critérios Gerais (A.1)* + *Template C.1* → *Decisão (Aprovado / Reprovado)*

Nesta formulação global, “Resultados Armazenados” refere-se ao conjunto de respostas das tarefas que foram homologadas individualmente, “Critérios Gerais (A.1)” denota as diretrizes gerais de aceitação mapeadas no Resultado Fase A.1, e “Template C.1” é o prompt estruturado de validação global que orienta o modelo a tomar a “Decisão (Aprovado / Reprovado)”. Em caso de conformidade de todas as diretrizes, o fluxo prossegue diretamente para a consolidação e resposta; caso contrário, é deflagrada a etapa de Planejamento Adicional.

**Exemplo**

**Cenário de aprovação.** Com os três resultados disponíveis ao término do loop, a avaliação contra os critérios gerais de A.1 produz:

**Saída LLM**

> Resultados disponíveis:
>
> - Tarefa 1: “Entre as alternativas (2, 4, 6), somente o número 2 é primo. Um número primo é aquele divisível exclusivamente por 1 e por ele mesmo. O número 4 possui divisores adicionais (1, 2 e 4) e o 6 também (1, 2, 3 e 6), portanto nenhum dos dois é primo. Resultado: [2].”
>
> - Tarefa 2: “Entre as alternativas (2, 4, 6), todos os três números são pares, pois cada um deles é divisível por 2 sem deixar resto (2÷2=1, 4÷2=2, 6÷2=3). Resultado: [2, 4, 6].”
>
> - Tarefa 3: “Os números estritamente maiores que 2 entre as alternativas são 4 e 6. O número 2 não satisfaz essa condição pois 2 > 2 é falso. Resultado: [4, 6].”
>
> Avaliação dos critérios gerais:
>
> - “A pergunta deve ser respondida em Português do Brasil.”  *Atendível*: todos os resultados estão em português.
>
> - “Responda somente a alternativa, sem explicações adicionais.”  *Atendível*: os dados disponíveis permitem identificar a alternativa correta.
>
> - “O valor encontrado deve corresponder a uma das alternativas.”  *Atendível*: primo ∩ par ∩ maior que 2 = ∅, o que corresponde à alternativa D.
>
> Decisão: **Aprovado**.

O fluxo avança para a construção da resposta final.

**Cenário de reprovação.** Considere uma variação em que os critérios gerais incluam: “A resposta deve ser sustentada por uma verificação explícita de qual conjunto de alternativas satisfaz simultaneamente todas as condições enunciadas.” Os três resultados cobrem cada condição individualmente, mas nenhuma tarefa realizou a análise de interseção.

**Saída LLM**

> - “Verificação explícita da interseção dos conjuntos.”  **Não atendido**: nenhuma tarefa realizou a verificação combinada das três condições.
>
> Decisão: **Reprovado**.

O fluxo avança para o Planejamento Adicional.

<!-- ———————————————————————— -->

<a id="subsec-RespostaC2"></a>

##### Planejamento Adicional

Quando os critérios gerais não são atendidos, o Planejamento Adicional funciona como uma extensão da fase A.2: identifica as lacunas específicas nos resultados disponíveis e cria novas tarefas individuais para supri-las. Diferentemente do planejamento inicial, que parte da pergunta do usuário sem qualquer contexto de execução, o Planejamento Adicional tem acesso ao conjunto de resultados já produzidos e ao mapeamento preciso dos critérios que ainda não foram satisfeitos. Essa informação torna as novas tarefas mais pontuais e direcionadas, evitando retrabalho sobre o que já foi verificado. As novas tarefas são adicionadas à fila de execução e o fluxo retorna à etapa B.1, agora com o contexto dos aprendizados acumulados de todas as tarefas anteriores disponível.

O planejamento adicional atua de forma cirúrgica para suprir as lacunas apontadas pela verificação global. Ao conjugar os critérios não satisfeitos e as saídas previamente geradas com o Template C.2, o modelo é induzido a planejar novos subproblemas independentes capazes de complementar o conteúdo em falta. Esse processo de expansão do escopo é delineado na expressão ([eq:fluxo_c2](#eq-fluxo_c2)):

<a id="eq-fluxo_c2"></a>

> *Critérios Não Atendidos* + *Resultados Armazenados* + *Template C.2* → *Novas Tarefas*

Nesta expressão, “Critérios Não Atendidos” são os critérios gerais identificados como não satisfeitos na etapa anterior, “Resultados Armazenados” são as respostas aprovadas de todas as tarefas já concluídas, e “Template C.2” é o prompt fixo de instrução descrito acima que direciona o modelo a produzir as “Novas Tarefas”. As novas tarefas, estruturadas com critérios individuais de aceite próprios, são inseridas no topo da fila e processadas no ciclo de Execução em Loop, garantindo que o planejamento convirja para o aceite global.

**Exemplo**

A partir da reprovação identificada no cenário anterior, o modelo produziria novas tarefas como a seguinte.

**Saída LLM**

> **Tarefa 4**
>
> - Tarefa: “Dadas as listas já identificadas — primos: [2]; pares: [2, 4, 6]; maiores que 2: [4, 6] —, determine quais números aparecem simultaneamente nas três listas.”
>
> - Critérios de aceite:
>
>     - “Deve retornar o resultado da interseção das três listas, podendo ser um conjunto vazio.”
>
>     - “Deve apresentar justificativa explicitando a presença ou ausência de cada candidato em cada lista.”
>
>     - “A resposta não deve construir a resposta final ao usuário.”

Essa nova tarefa é enviada à Execução em Loop. Com os aprendizados de T1, T2 e T3 injetados no contexto, o modelo executa a Tarefa 4.

**Saída LLM**

> “Verificando a interseção: primos [2] ∩ pares [2, 4, 6] ∩ maiores que 2 [4, 6]. O número 2 está em {primos} e {pares}, mas não em {maiores que 2} (pois 2 > 2 é falso). Os números 4 e 6 estão em {pares} e {maiores que 2}, mas não em {primos}. Resultado da interseção: {} (conjunto vazio — nenhum número satisfaz simultaneamente as três condições).”

Após a aprovação da Tarefa 4, o fluxo retorna à compilação dos resultados para nova verificação. Desta vez, com quatro resultados disponíveis, todos os critérios gerais são atendidos e o fluxo avança para a construção da resposta final.

O mecanismo de Planejamento Adicional pode ocorrer mais de uma vez caso as novas tarefas criadas ainda não sejam suficientes para satisfazer todos os critérios gerais. A cada retorno à compilação, o conjunto de resultados disponíveis é maior, convergindo progressivamente para a completude.

<!-- ———————————————————————— -->

<a id="subsec-RespostaC3"></a>

##### Construção da resposta final

Com todos os critérios gerais satisfeitos, o modelo compõe a resposta final ao usuário. Essa etapa não realiza um novo raciocínio analítico sobre o problema: seu objetivo é exclusivamente organizar e apresentar os resultados já produzidos no formato e idioma definidos pelos critérios gerais (Resultado Fase A.1). A distinção entre esta etapa e as anteriores é deliberada: ao separar o raciocínio analítico, realizado de forma incremental e verificada durante a Execução em Loop, da síntese da resposta final, reduz-se o risco de que a fase de apresentação introduza inferências não verificadas ou contradiga os resultados produzidos.

A síntese final é operacionalizada ao mesclar os resultados consolidados e os critérios gerais com as diretrizes do Template C.3, que proíbe terminantemente a inserção de novos fatos ou especulações que não estejam fundamentados na base de conhecimento gerada pelas tarefas. A relação operacional é expressa na expressão ([eq:fluxo_c3](#eq-fluxo_c3)):

<a id="eq-fluxo_c3"></a>

> *Resultados Compilados* + *Critérios Gerais (A.1)* + *Template C.3* → *Resposta Final*

Nessa expressão, “Resultados Compilados” são as respostas aprovadas de todas as tarefas resolvidas e acumuladas, “Critérios Gerais (A.1)” são os critérios gerais definidos no Resultado Fase A.1, e “Template C.3” é o prompt fixo de instrução que orienta a compilação e formatação para produzir a “Resposta Final”. Esta resposta compilada é finalmente entregue ao usuário, concluindo todo o ciclo do harness de IA.

**Exemplo**

Em ambos os cenários (aprovação direta com três tarefas ou com Planejamento Adicional em quatro tarefas), os resultados indicam que primo ∩ par ∩ maior que 2 = ∅. Respeitando os critérios gerais, a resposta final produzida é:

**Saída LLM**

> **D) Nenhuma das anteriores**

Essa resposta é então retornada ao usuário, encerrando o fluxo.

<!-- ------------------------------------------------- -->
