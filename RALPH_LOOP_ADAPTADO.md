# Ralph Wiggum Loop adaptado para perguntas em linguagem natural

## Resumo

Este documento contextualiza uma adaptação do **Ralph Wiggum Loop**, originalmente empregado em engenharia de software, para responder perguntas gerais em linguagem natural, incluindo questões de múltipla escolha. A arquitetura utiliza planejamento, decomposição em tarefas atômicas, execução e validação iterativas, reinicialização de contexto entre tarefas (*Fresh Context*) e síntese final sujeita a critérios de aceite globais. A seção **Metodologia original** abaixo é uma transcrição literal do trecho fornecido no paper, sem correções ou reformulações. Depois da transcrição do paper, o fluxo implementado recebeu cinco extensões: a etapa **A.3 — Aprendizados pontuais do enunciado**, a área de **Aprendizados Pontuais em todo prompt das fases B e C**, a **temperatura 1 nas retentativas**, as **regras de redação das tarefas em A.2 e C.2** (sem entradas e saída declaradas, critérios complementares entre si e resultado sempre acompanhado da explicação) e o **registro dos resultados parciais em B.4** (todo resultado parcial novo da tarefa aprovada vira um aprendizado com fato compacto e breve explicação, extraído numa janela própria com entradas explícitas). Elas estão descritas na seção **Extensões ao método do paper** e detalhadas, com exemplos, em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md).

## O que é o Ralph Wiggum Loop?

O Ralph Wiggum Loop é um paradigma de orquestração iterativa atribuído a Geoffrey Huntley, originalmente voltado ao desenvolvimento de software. Requisitos são decompostos em histórias ou tarefas pequenas, cada uma executada e validada contra critérios de aceite. Se uma tentativa falha, ela é revista e repetida. Ao passar para uma tarefa diferente, inicia-se um contexto novo, preservando apenas aprendizados relevantes de forma compacta, para reduzir a degradação associada ao crescimento do histórico (*context rot*).

Na adaptação proposta pelo paper, histórias de usuário tornam-se **tarefas autônomas de raciocínio**. Como o produto esperado deixa de ser código versionado e passa a ser uma resposta ao usuário, acrescenta-se uma fase explícita de **Criação da Resposta Final**.

## Guia de implementação para agentes de desenvolvimento CLI

> **Nota de procedência:** esta seção é uma orientação operacional derivada da Metodologia, não faz parte da transcrição literal. Em caso de divergência, prevalece a Metodologia original abaixo, com as exceções da seção **Extensões ao método do paper**: a etapa **A.3** (item 3), a área de **Aprendizados Pontuais** em todo prompt das fases B e C (itens 4 a 11), a **temperatura das retentativas** (item 12), as **regras de redação das tarefas** (itens 2 e 10) e o **registro dos resultados parciais em B.4** (item 7). Todas são posteriores ao paper e estão registradas em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md).

1. **A.1 — Critérios gerais:** receber a pergunta original e executar um prompt fixo `Template A.1` para definir idioma, formato, restrições e condições reais da resposta final; persistir esses critérios. Objetividade genérica não autoriza inventar limites de linhas ou palavras; justificativa opcional não se torna obrigatória.
2. **A.2 — Planejamento:** executar `Template A.2` sobre a pergunta original para criar uma lista ordenada de tarefas de objetivo único, cada uma com título, descrição autossuficiente e critérios individuais de aceite; persistir a lista. *(Regras de redação, extensão:)* a tarefa **não** declara entradas e saída esperadas; seus critérios são **complementares entre si**, nunca mutuamente exclusivos; e a tarefa exige que o resultado venha **acompanhado da explicação** (fórmulas, substituição de valores com unidades, convenções e justificativa de cada passo), com um critério de aceite que verifique isso.
3. **A.3 — Aprendizados pontuais do enunciado (extensão):** executar `Template A.3` sobre a pergunta original, em janela própria, para anotar os pontos que chamam a atenção no enunciado: valores com unidades de medida, alternativas, fórmulas, condições e restrições. Acrescentar essas anotações à memória de aprendizados **antes** de qualquer tarefa; uma lista vazia é válida. Não resolver a pergunta.
4. **B.1 — Seleção e resolução:** selecionar programaticamente a próxima tarefa; iniciar um contexto novo com a tarefa e `Template B.1`, cuja área **Aprendizados Pontuais** traz os aprendizados compactos acumulados (as anotações de A.3 e os aprendizados de B.4 das tarefas anteriores, ou o aviso de que ainda não há nenhum). Não antecipar a solução global.
5. **B.2 — Validação:** avaliar a resposta preliminar contra todos os critérios individuais usando `Template B.2`, que também traz a área **Aprendizados Pontuais**, só como referência para conferir dados (os aprendizados não são critérios). Se reprovar, reenviar o feedback e repetir **no mesmo contexto da tarefa**, preservando tentativas anteriores.
6. **B.3 — Resultado aprovado:** persistir somente a resposta aprovada, indexada pelo identificador da tarefa. Não enviar tentativas reprovadas para a síntese final.
7. **B.4 — Aprendizados pontuais:** executar `Template B.4` sobre o histórico completo da tarefa e extrair fatos compactos úteis para tarefas seguintes. A área **Aprendizados Pontuais** do template mostra os aprendizados já registrados, para que não sejam repetidos. Os aprendizados nunca se misturam aos resultados armazenados. *(Resultados parciais, extensão:)* B.4 roda numa **janela própria**, sem herdar a conversa de B.1, e recebe como entradas explícitas a tarefa, o resultado aprovado, o histórico das tentativas (com os vereditos do validador) e os aprendizados já registrados. Registra **todo resultado parcial novo** da tarefa aprovada, cada um como um **fato compacto** seguido de uma **breve explicação**, sem copiar a resolução, sem valores refutados nas tentativas e sem instruções, critérios, vereditos ou relatos do processo. A memória descarta aprendizados repetidos.
8. **Fresh Context:** ao avançar para outra tarefa, descartar o histórico da tarefa anterior e criar uma nova chamada/contexto. Os aprendizados compactos (inclusive as anotações de A.3) chegam à tarefa seguinte pela área **Aprendizados Pontuais** do `Template B.1`. A checagem de existência de tarefas pendentes é programática.
9. **C.1 — Validação global:** reunir apenas os resultados aprovados e os critérios gerais de A.1; executar `Template C.1` para verificar se o conteúdo permite construir a resposta solicitada. Explicações internas e ausência da linha final formatada não são lacunas quando C.3 pode aplicar a apresentação sem nova análise. Exigências de conteúdo, como análise conjunta explícita, precisam estar cobertas nos resultados. A área **Aprendizados Pontuais** traz todos os aprendizados do fluxo, como referência: eles não contam como cobertura de critério.
10. **Planejamento adicional:** se a validação global reprovar, identificar critérios pendentes, gerar novas tarefas específicas e retornar ao loop de execução. O `Template C.2` traz a área **Aprendizados Pontuais**, para que as descrições das novas tarefas repitam os dados do enunciado de que precisam. As novas tarefas seguem as mesmas **regras de redação** de A.2 (item 2).
11. **Resposta final:** após aprovação global, sintetizar a resposta a partir dos resultados aprovados, obedecendo idioma, formato e restrições gerais. O `Template C.3` traz a área **Aprendizados Pontuais** só para conferir dados do enunciado (por exemplo, a letra da alternativa); o conteúdo da resposta continua vindo apenas dos resultados aprovados.
12. **Temperatura das retentativas (extensão):** toda chamada de retentativa sai com temperatura `1`: a nova tentativa de B.1 depois de uma reprovação em B.2 e a correção de uma saída inválida (JSON ilegível, relatório inconsistente, lote de tarefas inválido) ou vazia, em qualquer fase. Assim que as retentativas acabam, as chamadas voltam à temperatura pedida pelo usuário.

**Separação de estados:** mantenha, no mínimo, `original_question`, `general_acceptance_criteria`, `task_queue`, `approved_task_results`, `accumulated_learnings` e `current_task_context`. `accumulated_learnings` recebe primeiro as anotações de A.3 e depois os aprendizados de B.4, na ordem em que surgem, sem repetições, e é renderizado na área **Aprendizados Pontuais** de cada template das fases B e C. O histórico da tarefa (tentativas e vereditos) é um dado da própria tarefa, entregue a B.4 como entrada explícita; não faz parte de `accumulated_learnings` nem de `current_task_context` de outra tarefa. A temperatura do usuário é um parâmetro fixo da sessão; a temperatura de retentativa vale só para a chamada que repete um pedido que falhou. Os nomes são sugestões de implementação, não nomes exigidos pelo paper. O texto acadêmico define o comportamento conceitual dos templates, mas não fornece seus prompts completos; eles precisam ser implementados de acordo com as responsabilidades descritas, sem alegar que são transcrições do trabalho.

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
- Os fatos entram na mesma memória de aprendizados de B.4, **antes** de qualquer tarefa. Portanto chegam a **toda** tarefa, inclusive a primeira e as criadas pelo Planejamento Adicional (C.2), antes dos aprendizados que B.4 for acrescentando.
- Valem para A.3 as mesmas regras dos demais aprendizados. Desde a extensão **Aprendizados Pontuais em todo prompt das fases B e C** (abaixo), isso significa que as anotações também chegam a B.2, B.4, C.1, C.2 e C.3, sempre numa área própria e nunca misturadas aos resultados armazenados.

**Consequência na primeira tarefa.** Na versão do paper, "na primeira tarefa do ciclo não há aprendizados acumulados". Com A.3, a primeira tarefa já recebe as anotações do enunciado, quando A.3 as produz.

### Aprendizados Pontuais em todo prompt das fases B e C

**Problema observado.** Na versão do paper (e na primeira versão de A.3), os aprendizados só chegavam ao contexto de B.1, como um bloco no início da janela da tarefa. O validador de tarefa (B.2), a extração de aprendizados (B.4) e toda a fase C não os recebiam. Nos testes, isso fez dados do enunciado se perderem ao longo do *thinking*: B.2 julgava um resultado sem saber quais eram as alternativas, C.2 criava tarefas sem os dados de que elas precisavam e C.3 não tinha como associar o valor obtido à letra da alternativa.

**Regra.** Todo template enviado ao modelo nas fases B e C tem a área **Aprendizados Pontuais**, preenchida com **todos** os aprendizados acumulados até o momento da chamada: as anotações de A.3 seguidas dos aprendizados de B.4, na ordem em que surgiram.

| Template | O que a área traz | Como deve ser usada |
|---|---|---|
| B.1 | Tudo o que foi acumulado antes da tarefa (repetido em cada nova tentativa) | Contexto de apoio, sem ampliar o escopo da tarefa. |
| B.2 | Idem | Referência para conferir dados; **não** são critérios de aceite. |
| B.4 | Tudo o que foi acumulado antes da tarefa, sem os aprendizados dela própria | Mostra o que já foi registrado, para que não seja repetido. |
| C.1 | Todos os aprendizados do fluxo | Referência; **não** contam como cobertura de critério geral. |
| C.2 | Todos os aprendizados do fluxo | Copiar para as novas tarefas os dados do enunciado de que precisam. |
| C.3 | Todos os aprendizados do fluxo | Só para conferir dados (por exemplo, a letra da alternativa); o conteúdo da resposta continua vindo apenas dos resultados armazenados. |

- A área existe mesmo sem aprendizados: nesse caso traz o aviso "Nenhum aprendizado pontual registrado até o momento."
- A janela da tarefa deixa de receber o bloco avulso "Aprendizados acumulados": os aprendizados chegam pelo próprio Template B.1, sem duplicação.
- A separação entre resultado armazenado e aprendizado continua: os aprendizados chegam numa área própria do template e **nunca** entram nos resultados armazenados que alimentam C.1 e C.3.
- Os templates de A.1, A.2 e A.3 não têm a área, porque rodam antes de existir qualquer aprendizado.

> *Aprendizados Pontuais* + *Entradas do Template X* + *Template X* → *Resultado Fase X*, para X ∈ {B.1, B.2, B.4, C.1, C.2, C.3}

### Temperatura das retentativas

**Problema observado.** Nos testes apareceram muitas retentativas em "loop": o modelo repetia a mesma saída reprovada (ou o mesmo JSON inválido) até esgotar as tentativas. Repetir um pedido que acabou de falhar com a mesma temperatura do usuário, em geral baixa, tende a reproduzir a mesma resposta.

**Regra.** Toda chamada de **retentativa** é feita com temperatura `1`. Assim que as retentativas acabam, as chamadas voltam à temperatura fornecida pelo usuário na entrada.

| Situação | Chamada com temperatura `1` | Volta à temperatura do usuário |
|---|---|---|
| B.2 reprova a tentativa de uma tarefa | A nova tentativa de B.1 (e as correções de saída dentro dela) | Na verificação B.2 dessa nova tentativa |
| Saída inválida ou vazia em qualquer fase (JSON ilegível, relatório inconsistente, lote de tarefas acima do teto, completion vazia) | Cada correção pedida ao modelo | Na primeira chamada da fase seguinte |
| C.1 reprova o conjunto de resultados | Nenhuma: C.2 e as novas tarefas são trabalho novo, não a repetição de um pedido | — |

- A temperatura do usuário nunca é sobrescrita: a de retentativa vale só para a chamada que repete um pedido que falhou.
- O número de retentativas não muda: os limites de tentativas por tarefa e de correções de saída continuam valendo.
- Cada invocação registra na sessão a temperatura efetivamente enviada (`temperature`), o que permite auditar quais chamadas foram retentativas.

### Regras de redação das tarefas (A.2 e C.2)

**Problema observado.** Três pontos dos templates de planejamento prejudicavam as tarefas geradas:

1. A diretriz "declarar as **entradas** de que precisa e a **saída** que produz" levava o modelo a preencher os campos `expected_input` e `expected_output`. Como cada tarefa é autossuficiente e roda em contexto novo, a "entrada" já está na descrição, e a "saída" competia com os critérios de aceite como definição do que a tarefa deve entregar. Em especial, uma "saída esperada" curta, como "a lista de primos, por exemplo [2, 3, 5, 7]", sugeria uma resposta sem justificativa.
2. Nada impedia critérios **mutuamente exclusivos** na mesma tarefa, como "responda somente a alternativa" e "a resposta deve conter explicações". Nenhum resultado atende aos dois ao mesmo tempo, e a tarefa fica reprovada em B.2 a cada tentativa, até esgotar o limite.
3. Nada exigia que o resultado da tarefa viesse **justificado**. Um resultado que só traz o valor final, sem a fórmula, as unidades ou o porquê de cada passo, não permite que B.2, C.1 e C.3 confiram de onde ele veio.

**Regra.** Cada tarefa criada por A.2 ou C.2 deve:

1. Ter **um único objetivo**, resolvível de forma independente das demais *(inalterado)*.
2. Trazer os **próprios critérios de aceite individuais**, com identificadores no formato `T1-AC1`, **complementares entre si e nunca mutuamente exclusivos**: tem de ser possível que uma única resposta atenda a todos os critérios ao mesmo tempo. O modelo confere os critérios aos pares antes de fechar a lista.
3. Trazer, entre os critérios, **restrições de escopo** que impeçam a resolução precoce da questão principal *(inalterado)*.
4. Exigir que o resultado venha **acompanhado da explicação de por que ele é válido**, nunca isolado. Numa conta: as fórmulas usadas, a substituição dos valores com unidades de medida, as convenções adotadas (sinais, referenciais, aproximações) e a justificativa de cada passo. Numa classificação ou escolha: o raciocínio que a sustenta. A exigência aparece na descrição da tarefa **e** num critério de aceite, para que B.2 a verifique.

- A diretriz de **entradas e saída** foi removida. A tarefa passa a ter só `id`, `title`, `description` e `acceptance_criteria`; o bloco da tarefa enviado a B.1 deixa de ter as linhas "Entrada esperada" e "Saída esperada".
- Se o modelo ainda enviar `expected_input` ou `expected_output`, o lote **não** é recusado: os campos são ignorados.
- As regras valem para A.2 e C.2. A fórmula de cada etapa não muda:

> *Pergunta do usuário* + *Template A.2* → *Resultado Fase A.2*
>
> *Critérios Não Atendidos* + *Resultados Armazenados* + *Aprendizados Pontuais* + *Template C.2* → *Novas Tarefas*


### B.4 — Registro dos resultados parciais da tarefa aprovada

**Problema observado.** O Template B.4 já pedia conclusões e valores, mas o modelo omitia resultados de que as tarefas seguintes precisavam. No benchmark de Matemática ITA 2024 Q037, a conclusão correta de que a afirmação I é verdadeira não foi salva nos aprendizados, e a tarefa seguinte, que roda em contexto novo, perdeu essa informação. Outros aprendizados registravam critérios e o processo de execução, e não fatos do problema. Além disso, B.4 era executado sobre a própria janela de B.1, herdando a conversa de outra fase.

**Regra.** B.4 registra **todo resultado parcial novo** da tarefa aprovada, com significado suficiente para ser usado sem o histórico anterior. Cada aprendizado é uma única frase com duas partes:

| Parte | O que é | Exemplo (Q037) |
|---|---|---|
| **Fato compacto** | A conclusão em si, nomeando explicitamente o objeto: a grandeza com valor, unidade e condições; a afirmação com sua classificação; a fórmula ou relação com suas hipóteses. | "A afirmação I é verdadeira" |
| **Breve explicação** *(nova)* | O motivo, a propriedade ou a fórmula que sustenta o fato, em poucas palavras. Não é a resolução completa. | "C ⊆ A implica A ∩ C = C, pela distributividade." |

- **Valores:** grandeza, valor, unidade e condições relevantes. **Classificações:** a afirmação, a classificação e um motivo breve. **Relações:** a fórmula ou relação e as hipóteses necessárias.
- Prevalece a **conclusão finalmente aprovada**: valores ou classificações refutados ou substituídos nas tentativas reprovadas não viram aprendizados vigentes.
- Não se registram instruções da tarefa, critérios, vereditos, relatos do processo nem fatos que já constam na memória. A memória também descarta, de forma programática, aprendizados em branco ou repetidos (a menos de maiúsculas e espaços); o evento `learn` lista os descartados.
- `{"learnings": []}` só é válido quando a tarefa não trouxe fato novo ou quando todas as conclusões já estão registradas. A simplicidade de uma conclusão nova não justifica omiti-la.
- **Isolamento de contexto:** B.4 roda numa janela própria e não herda a conversa de B.1. O histórico da tarefa exigido pelo paper continua disponível, mas como **dado delimitado** do template, separado da memória de aprendizados. O resultado aprovado é o mesmo que B.3 armazenou; B.4 só o lê. Os aprendizados continuam fora dos resultados armazenados, e nenhuma resposta completa passa de uma tarefa para outra.

> *Tarefa* + *Resultado Aprovado* + *Histórico da Tarefa* + *Aprendizados Pontuais* + *Template B.4* → *Novos Aprendizados Pontuais*
