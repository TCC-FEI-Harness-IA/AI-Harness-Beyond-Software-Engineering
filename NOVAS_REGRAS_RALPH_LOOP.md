# Novas regras do Ralph Wiggum Loop adaptado

## Finalidade deste relatório

Este documento registra as alterações feitas no fluxo implementado depois da versão descrita na seção **Metodologia** do paper. Ele serve de base para atualizar o paper oficial: cada alteração traz o problema que a motivou, a regra nova, a expressão no formato usado na Metodologia, exemplos com o *input* de referência do paper, o que deixa de valer no texto atual e a validação na implementação.

A explicação geral do fluxo está em [`RALPH_LOOP_ADAPTADO.md`](RALPH_LOOP_ADAPTADO.md). Aquele arquivo mantém a transcrição literal da Metodologia e traz a nova etapa numa seção separada, **Extensões ao método do paper**.

## Resumo das alterações

| # | Alteração | Fase | Efeito principal |
|---|---|---|---|
| 1 | Nova etapa **A.3 — Aprendizados pontuais do enunciado** | A. Planejamento | Dados importantes da pergunta (valores com unidades, alternativas, fórmulas, condições) deixam de depender de a descrição das tarefas os repetir. |
| 2 | Área **Aprendizados Pontuais** em todo prompt das fases B e C | B. Execução em Loop e C. Criação da Resposta Final | Todos os aprendizados do fluxo chegam a B.1, B.2, B.4, C.1, C.2 e C.3, e não só a B.1. |
| 3 | **Temperatura 1 nas retentativas** | B e todas as fases com correção de saída | Retentativas deixam de repetir a mesma saída reprovada até esgotar as tentativas. |

As alterações 2 e 3 vieram de uma segunda rodada de testes. A alteração 2 **substitui** a regra de escopo da alteração 1 (e do paper), segundo a qual os aprendizados ficavam restritos a B.1; os pontos afetados da seção 1 estão marcados com *(atualizado pela alteração 2)*.

---

## 1. A.3 — Aprendizados pontuais do enunciado

### 1.1 Problema

Testes com o fluxo implementado mostraram **perda de contexto importante**, em especial das alternativas disponíveis ao longo da execução das fases.

A causa está na combinação de duas regras do paper:

1. Cada tarefa é resolvida em um **contexto novo** (*Fresh Context*). Ela enxerga apenas a própria descrição e os aprendizados acumulados. Não enxerga a pergunta original.
2. O primeiro aprendizado só existe depois da primeira tarefa concluída (B.4). A Metodologia diz que, na primeira tarefa, "não há aprendizados acumulados".

Se o decompositor (A.2) não repetir na descrição de uma tarefa um dado essencial do enunciado, essa tarefa não tem como recuperá-lo. Isso é provável porque A.2 foi instruído a criar tarefas de objetivo único, curtas e sem resolução antecipada. Os dados mais sujeitos a se perder são:

- as **alternativas** de uma questão de múltipla escolha, citadas por uma tarefa que só precisa de parte delas;
- **valores numéricos e suas unidades de medida**, copiados sem a unidade ou convertidos por engano;
- **fórmulas** fornecidas pelo enunciado;
- **condições que valem ao mesmo tempo**, como "primo, par e maior que 2", analisadas por tarefas que enxergam só uma delas.

O Planejamento Adicional (C.2) sofre do mesmo problema: as tarefas novas também começam em contexto novo.

### 1.2 Regra nova

O Planejamento passa a ter **três etapas**. A terceira, **A.3**, é executada logo depois de A.2 e salva os **aprendizados pontuais do enunciado**. Funciona como as "anotações internas" do fluxo de *thinking* (como em B.4), mas feitas sobre a pergunta, **antes** de qualquer tarefa.

A relação de entrada e saída, no formato das expressões da Metodologia, é:

> *Pergunta do usuário* + *Template A.3* → *Aprendizados Pontuais do Enunciado*

Regras da etapa:

1. **Entrada.** Somente a pergunta original e o Template A.3. A etapa não recebe os critérios de A.1 nem as tarefas de A.2. Ela anota o que o enunciado afirma e não depende de como o problema foi decomposto.
2. **Contexto.** Janela própria, inicializada para a etapa. Nenhum histórico de A.1 ou A.2 é herdado.
3. **O que anotar.** Todo dado que deveria "chamar a atenção" de quem for trabalhar numa tarefa sem ter lido a pergunta:
   - valores fornecidos, **sempre com as unidades de medida**;
   - alternativas oferecidas, copiadas **literalmente**, com a letra ou o número que as identifica e sem omitir nenhuma;
   - fórmulas, equações e relações informadas;
   - condições, restrições e definições impostas pelo enunciado, inclusive as simultâneas;
   - nomes, datas, códigos e qualquer dado que mudaria o resultado se fosse trocado.
4. **Formato.** Fatos secos, sucintos e atômicos, copiados como aparecem no enunciado, sem reescrever, converter unidades ou arredondar. Cada fato é útil sem o enunciado por perto.
5. **O que não anotar.** A resolução, o resultado ou qualquer palpite de resposta; a repetição do enunciado inteiro; relato de processo ou justificativas. **A etapa não resolve a pergunta.**
6. **Lista vazia.** É uma saída válida (enunciado sem nada a anotar). Nesse caso, nenhum bloco de aprendizados é injetado nas tarefas.
7. **Destino.** Os fatos entram na mesma **Memória Acumulada** de B.4, **antes** de qualquer aprendizado de tarefa. Assim:
   - a **primeira tarefa** já recebe as anotações do enunciado;
   - toda tarefa seguinte as recebe, seguidas dos aprendizados de B.4 das tarefas anteriores;
   - as tarefas criadas pelo Planejamento Adicional (C.2) também as recebem.
8. **Escopo** *(atualizado pela alteração 2)*. As anotações de A.3 seguem a regra dos aprendizados pontuais. Na primeira versão desta etapa, isso as restringia à Execução em Loop (B.1). Com a alteração 2, elas chegam à área **Aprendizados Pontuais** de todo prompt das fases B e C (B.1, B.2, B.4, C.1, C.2 e C.3), sempre separadas dos resultados armazenados.
9. **Sem efeito sobre a fila.** A.3 não cria nem altera tarefas e não consome o limite de tarefas da sessão.

### 1.3 Posição no fluxo

```text
A. Planejamento
   A.1  Critérios de aceite gerais
   A.2  Quebra em tarefas de objetivo único
   A.3  Aprendizados pontuais do enunciado   ← nova etapa
B. Execução em Loop      (todo prompt de B recebe as anotações de A.3 — alteração 2)
C. Criação da Resposta Final   (todo prompt de C recebe as anotações de A.3 — alteração 2)
```

Ordem das chamadas ao modelo no caso de três tarefas aprovadas de primeira: A.1, A.2, **A.3**, e depois (B.1, B.2, B.4) por tarefa, C.1 e C.3. A.3 acrescenta **uma** chamada ao modelo por sessão, independente do número de tarefas.

### 1.4 Exemplo com o *input* de referência do paper

**Input**

> Qual dos seguintes números é simultaneamente primo, par e maior que 2?
> A) 2 B) 4 C) 6 D) Nenhuma das anteriores

**Saída esperada de A.3**

> - “Alternativas: A) 2; B) 4; C) 6; D) Nenhuma das anteriores.”
> - “Condições exigidas simultaneamente: ser primo, ser par e ser maior que 2.”

Note o que a saída **não** contém: "o único primo é 2" e "a resposta é D" seriam conclusões. Também ficam de fora definições óbvias de número primo e de número par, que não são dado do enunciado.

**Efeito sobre as tarefas.** O decompositor produz as três tarefas do paper, cada uma com uma descrição curta (por exemplo, "Dadas as opções (2, 4, 6), identifique quais são pares"). Antes, o contexto da Tarefa 1 continha só a descrição dela. Agora o prompt de B.1 traz *(formato atualizado pela alteração 2)*:

```text
## Aprendizados Pontuais

(...)

- Alternativas: A) 2; B) 4; C) 6; D) Nenhuma das anteriores.
- Condições exigidas simultaneamente: ser primo, ser par e ser maior que 2.
```

Mesmo que a descrição da Tarefa 1 omita a alternativa D, a tarefa sabe que ela existe. Ao fim da Tarefa 1, B.4 acrescenta seus fatos à memória, **depois** dessas duas linhas. A Tarefa 2 recebe as anotações do enunciado e os aprendizados da Tarefa 1.

### 1.5 Exemplo com valores e unidades

**Input**

> Um carro viaja a 72 km/h durante 30 minutos. Qual a distância percorrida, em metros?
> A) 36 000 m B) 2 160 m C) 36 m D) 21 600 m

**Saída esperada de A.3**

> - “Velocidade: 72 km/h.”
> - “Tempo: 30 minutos.”
> - “Unidade pedida para a distância: metros (m).”
> - “Alternativas: A) 36 000 m; B) 2 160 m; C) 36 m; D) 21 600 m.”

A relação entre distância, velocidade e tempo não foi fornecida pelo enunciado, então não é anotada. Isso a distingue de um enunciado como "use d = v · t", em que a fórmula entraria como fato.

**Por que importa.** Com a decomposição em tarefas (converter a velocidade, converter o tempo, calcular a distância), uma tarefa que recebe só "calcule a distância para 20 m/s e 1800 s" perde a unidade final pedida e as alternativas. Com A.3, toda tarefa sabe que o resultado deve ser comparado a quatro valores em metros.

### 1.6 Exemplo de saída inválida

> *Inválido:* “Como o número 2 é o único primo par e não é maior que 2, nenhuma alternativa satisfaz as três condições; a resposta é D.”

A saída antecipa a resolução e contraria a regra 5. O Template A.3 proíbe expressamente esse conteúdo. O sistema não detecta esse tipo de violação semântica automaticamente: o controle é feito pelo prompt, como ocorre em B.4. A validação estrutural (JSON com a lista de textos) é automática.

### 1.7 O que muda no texto do paper

| Trecho atual da Metodologia | Ajuste necessário |
|---|---|
| "O planejamento [...] compreendendo duas etapas [...]" | Passa a três etapas: critérios gerais (A.1), decomposição em tarefas (A.2) e aprendizados pontuais do enunciado (A.3). |
| Visão geral do fluxo (Figura do fluxo adaptado) | Incluir a etapa A.3 depois de A.2, alimentando a Memória Acumulada. |
| Apresentação dos termos dos *prompts* ("Template A.1", "Resultado Fase A.1") | Incluir "Template A.3" e "Resultado Fase A.3". |
| Seção B: "Na primeira tarefa do ciclo, não há aprendizados acumulados" e o exemplo da Tarefa 1 "o contexto não contém aprendizados acumulados" | Corrigir: a primeira tarefa recebe as anotações de A.3 quando existirem. Sem anotações (lista vazia), a afirmação continua válida. |
| Definição de "Aprendizados Acumulados" ("anotações internas compactas sintetizadas nas iterações anteriores (que se inicia vazio)") | A memória deixa de iniciar sempre vazia: pode iniciar com as anotações de A.3. |
| "Os aprendizados pontuais têm papel restrito à Execução em Loop" | *(Atualizado pela alteração 2)* Deixa de valer: os aprendizados, inclusive as anotações de A.3, chegam a todo prompt das fases B e C. Ver seção 2.6. |
| Planejamento Adicional: "agora com o contexto dos aprendizados acumulados de todas as tarefas anteriores" | Acrescentar que as anotações de A.3 também estão no contexto. |

Parágrafo sugerido para a subseção de A.3 no paper, no estilo da Metodologia:

> Uma terceira etapa do planejamento registra os aprendizados pontuais do enunciado. Como cada tarefa é executada em um contexto novo, os dados da pergunta original que a descrição da tarefa não repetir deixariam de estar disponíveis ao modelo, o que afeta em especial as alternativas de questões de múltipla escolha, os valores com suas unidades de medida e as fórmulas fornecidas. Esta etapa associa a pergunta do usuário ao Template A.3, que orienta o modelo a anotar, em tópicos secos e sem resolver o problema, todo dado do enunciado que deve chamar a atenção. As anotações são anexadas à Memória Acumulada antes da primeira tarefa e, assim como os aprendizados de B.4, são injetadas no início do contexto de cada tarefa, sem participar da construção da resposta final.

### 1.8 Decisões de projeto

| Decisão | Justificativa |
|---|---|
| A.3 roda **depois** de A.2, e não antes. | Mantém A.1 e A.2 idênticas ao paper. A.3 não depende do resultado delas, então a ordem não altera o conteúdo. A posição final deixa A.1 e A.2 como estão. |
| A.3 recebe **só a pergunta**. | As anotações descrevem o que o enunciado afirma. Se dependessem do plano, mudariam conforme a decomposição escolhida pelo modelo. |
| As anotações vão para a **mesma memória** de B.4. | Aproveita o mecanismo de injeção que já existe (*Fresh Context*), sem criar um segundo canal. A ordem de inserção garante que o enunciado vem primeiro. |
| ~~As anotações **não** vão para B.2, C.1 e C.3.~~ *(Substituída pela alteração 2.)* | A separação entre resultados armazenados e aprendizados é mantida de outra forma: os aprendizados chegam a essas fases numa área própria do template, nunca dentro dos resultados. |
| Lista vazia é válida. | Evita forçar o modelo a inventar anotações quando o enunciado é simples. |
| Cada chamada de A.3 conta no orçamento da sessão. | A.3 é uma chamada ao modelo como as demais: entra nos limites de chamadas, de tokens e de tempo, e é registrada como uma invocação. |

### 1.9 Ponto em aberto para decisão *(resolvido pela alteração 2)*

> Este ponto foi resolvido pela alteração 2: as anotações de A.3 passaram a chegar a C.1 e C.3, como previsto no último parágrafo abaixo, e a segunda extensão foi registrada na seção 2. O texto original é mantido como histórico.

A regra de escopo dos aprendizados do paper foi mantida: as anotações de A.3 não chegam a C.3. Se um dado do enunciado (por exemplo, a lista de alternativas) não estiver presente nos resultados das tarefas aprovadas, a construção da resposta final não terá como recuperá-lo. Hoje isso é contido pelo critério geral de A.1 ("o valor deve corresponder a uma das alternativas") e pela verificação global C.1. Se os testes mostrarem perdas também na fase C, a alternativa é injetar as anotações de A.3 em C.1 e C.3. Isso **alteraria** a separação definida no paper e exigiria registrar uma segunda extensão.

### 1.10 Validação na implementação

A etapa foi implementada com TDD: os testes foram escritos antes do código e descrevem o comportamento esperado. A suíte do backend passa por completo (1198 testes, cobertura de 100%, exigida pelo projeto) e o código passa no lint (`flake8`) do projeto. Os testes cobrem:

- **Ordem do fluxo:** A.1, A.2, A.3 e só então as tarefas; A.3 emite um evento `learn` e roda em janela própria.
- **Entrada isolada:** o Template A.3 recebe apenas a pergunta do usuário.
- **Injeção:** a primeira tarefa e todas as seguintes recebem as anotações antes dos aprendizados de B.4; as tarefas de C.2 também. *(Desde a alteração 2, a injeção é feita pela área **Aprendizados Pontuais** do Template B.1, e não por um bloco no início do contexto.)*
- **Escopo:** na primeira versão, o validador de tarefa (B.2) e as fases C.1 e C.3 não recebiam as anotações. Esses testes foram invertidos pela alteração 2 (seção 2.9).
- **Lista vazia:** nenhum bloco é injetado, e o evento informa que nada foi extraído do enunciado.
- **Memória:** os aprendizados de A.3 ficam sem tarefa de origem; os de B.4 mantêm a tarefa.
- **Falhas:** saída inválida de A.3 é devolvida ao modelo para correção, e erro técnico encerra a sessão atribuído à fase A.3.
- **Orçamento e registro:** A.3 entra nos limites de chamadas e de tokens, na contagem de invocações e nas mensagens persistidas da sessão (`phase = A3`).
- **Contrato do Template A.3:** o arquivo `a3_planning_learnings.md` instrui a preservar valores com unidades, alternativas literais, fórmulas e restrições, proíbe resolver a pergunta e prevê a lista vazia.

Arquivos principais:

| Arquivo | Papel |
|---|---|
| `apps/backend/src/infra/templates/a3_planning_learnings.md` | Template A.3. |
| `apps/backend/src/application/phases/planning_learnings_phase.py` | Fase A.3. |
| `apps/backend/src/application/usecases/ralph_thinking_usecase.py` | Orquestração: A.3 depois de A.2, antes do loop. |
| `apps/backend/src/domain/enums/thinking_phase_enum.py` | Nova fase `A3`. |
| `apps/backend/src/domain/entities/thinking/learning.py` | Aprendizado sem tarefa de origem (`source_task_id` opcional). |

### 1.11 Limitações

- A qualidade das anotações depende do modelo seguir o Template A.3. Anotar uma conclusão em vez de um dado do enunciado não é detectado automaticamente.
- A.3 aumenta em uma o número de chamadas por sessão, com custo e latência correspondentes. Em enunciados simples, a etapa pode devolver lista vazia, mas a chamada já foi feita.
- O ganho em acurácia não foi medido. Os testes automatizados verificam o comportamento do fluxo (o que é injetado, onde e quando), não a qualidade das respostas. A medição exige rodar o experimento de avaliação do paper com e sem A.3.
- O frontend reconhece a fase `A3`: o evento aparece no Modo Chat (etiqueta "A.3 · Aprendizados do enunciado") e como nó da trilha macro do Modo Gráfico, ao vivo e no histórico, sem criar faixa de tarefa. Sessões gravadas antes da A.3 continuam abrindo, com o nó marcado como "não foi necessária". Essa parte foi validada por testes automatizados, não por inspeção visual no navegador.

---

## 2. Aprendizados Pontuais em todo prompt das fases B e C

### 2.1 Problema

Uma segunda rodada de testes mostrou que os aprendizados gerais **não chegavam a todos os prompts** ao longo do *thinking*. Pela regra do paper, mantida na alteração 1, os aprendizados pontuais "têm papel restrito à Execução em Loop": eram injetados como um bloco no início do contexto de cada tarefa e só a resolução (B.1) os enxergava. As demais etapas ficavam sem eles:

| Etapa | O que faltava |
|---|---|
| B.2 — Verificação da tarefa | Julgava o resultado preliminar sem saber, por exemplo, quais eram as alternativas ou as unidades pedidas no enunciado. |
| B.4 — Extração de aprendizados | Rodava sobre a janela da tarefa e via o bloco de B.1, mas o template não indicava o que já estava registrado, o que permitia repetir aprendizados de tarefas anteriores. |
| C.1 — Verificação global | Avaliava o critério "o valor deve corresponder a uma das alternativas" sem a lista de alternativas, quando os resultados não a repetiam. |
| C.2 — Planejamento adicional | Criava tarefas novas (que rodam em contexto novo) sem os dados do enunciado de que elas precisavam. |
| C.3 — Resposta final | Não tinha como associar o valor encontrado à letra da alternativa, se os resultados só traziam o valor. |

O ponto em aberto da seção 1.9 descrevia exatamente o caso de C.3.

### 2.2 Regra nova

**Todo template de prompt enviado ao modelo nas fases B e C tem a área "Aprendizados Pontuais"**, preenchida com **todos** os aprendizados acumulados no fluxo até o momento daquela chamada.

A relação de entrada e saída de cada etapa ganha um termo comum:

> *Aprendizados Pontuais* + *Entradas da etapa X* + *Template X* → *Resultado Fase X*, para X ∈ {B.1, B.2, B.4, C.1, C.2, C.3}

Regras:

1. **Conteúdo.** A área traz as anotações de A.3 seguidas dos aprendizados de B.4 de cada tarefa concluída, na ordem em que foram extraídos, um por linha.
2. **Momento.** O conteúdo é o da memória **no instante da chamada**. Uma tarefa só vê os aprendizados das tarefas concluídas antes dela; a fase C vê todos.
3. **Área sempre presente.** Sem nenhum aprendizado, a área traz o aviso "Nenhum aprendizado pontual registrado até o momento." O modelo sabe que a área existe e está vazia.
4. **Sem duplicação.** A janela da tarefa deixa de receber o bloco avulso "Aprendizados acumulados" no início: os aprendizados chegam pelo próprio Template B.1. A cada nova tentativa, o template de B.1 é enviado de novo e traz a área outra vez.
5. **Separação preservada.** Os aprendizados ocupam uma área própria do template e **nunca** entram nos "Resultados Armazenados". Os resultados continuam sendo a única base da resposta final; os aprendizados servem de referência.
6. **Fase A sem a área.** A.1, A.2 e A.3 rodam antes de existir qualquer aprendizado, então seus templates não têm a área.

### 2.3 Como cada template usa a área

Cada template diz ao modelo como usar os aprendizados, para que a área não mude o papel da etapa:

| Template | Aprendizados recebidos | Instrução no template |
|---|---|---|
| B.1 — Resolução | Os acumulados antes da tarefa | Contexto de apoio (conferir alternativas, valores, unidades), **sem ampliar o escopo** da tarefa. |
| B.2 — Verificação | Os acumulados antes da tarefa | Só referência para conferir dados. Os aprendizados **não são critérios** de aceite: a avaliação continua restrita aos critérios da tarefa. |
| B.4 — Extração | Os acumulados antes da tarefa (sem os dela, que ainda vão ser extraídos) | São os aprendizados já registrados: **não repita** nenhum deles; registre só fatos novos. |
| C.1 — Verificação global | Todos os do fluxo | Só referência. Os aprendizados **não são critérios** e **não contam como cobertura**: um critério geral só é atendido quando os resultados armazenados o cobrem. |
| C.2 — Planejamento adicional | Todos os do fluxo | Usar para escrever descrições autossuficientes, copiando para cada nova tarefa os dados do enunciado de que ela precisa. |
| C.3 — Resposta final | Todos os do fluxo | Só para conferir dados do enunciado (por exemplo, a letra da alternativa). Os aprendizados **não substituem os resultados armazenados**: o conteúdo da resposta vem só deles. |

As instruções de B.2, C.1 e C.3 protegem as garantias do método: um validador não aprova por causa de um aprendizado e a síntese não introduz fatos que os resultados não sustentam.

### 2.4 Exemplo com o *input* de referência do paper

**Input**

> Qual dos seguintes números é simultaneamente primo, par e maior que 2?
> A) 2 B) 4 C) 6 D) Nenhuma das anteriores

**Memória ao longo do fluxo.** A.3 anota as alternativas e as condições (seção 1.4). Cada tarefa acrescenta o seu aprendizado:

| Momento | Conteúdo da área "Aprendizados Pontuais" |
|---|---|
| B.1, B.2 e B.4 da Tarefa 1 | `- Alternativas: A) 2; B) 4; C) 6; D) Nenhuma das anteriores.`<br>`- Condições exigidas simultaneamente: ser primo, ser par e ser maior que 2.` |
| B.1, B.2 e B.4 da Tarefa 2 | as duas linhas acima<br>`- O único número primo entre as alternativas é o 2.` |
| B.1, B.2 e B.4 da Tarefa 3 | as três linhas acima<br>`- Todos os números das alternativas (2, 4, 6) são pares.` |
| C.1, C.2 e C.3 | as quatro linhas acima<br>`- O número 2 não é maior que 2.` |

**B.2 da Tarefa 2.** Antes, o prompt do validador tinha só o resultado preliminar e os critérios da tarefa. Agora tem também:

```text
## Aprendizados Pontuais

Anotações compactas acumuladas ao longo do fluxo: os pontos de atenção do enunciado e os fatos
registrados pelas tarefas já concluídas, na ordem em que surgiram. Use-as apenas como
referência para conferir os dados envolvidos (alternativas, valores, unidades de medida).
Os aprendizados **não são critérios** de aceite: a avaliação continua restrita aos critérios desta
tarefa.

- Alternativas: A) 2; B) 4; C) 6; D) Nenhuma das anteriores.
- Condições exigidas simultaneamente: ser primo, ser par e ser maior que 2.
- O único número primo entre as alternativas é o 2.
```

O validador consegue conferir que a lista "[2, 4, 6]" cobre todas as alternativas numéricas. A decisão continua dependendo só dos critérios da Tarefa 2. No exemplo de reprovação do paper, a tentativa que "antecipou a resposta final" segue reprovada pelo critério "A resposta não deve tentar resolver a questão final", e o aprendizado sobre o número primo não muda isso.

**B.4 da Tarefa 2.** A área mostra que "O único número primo entre as alternativas é o 2." já está registrado. O modelo não o repete e registra só o fato novo da tarefa ("Todos os números das alternativas (2, 4, 6) são pares.").

**C.1.** O critério geral "O valor encontrado deve corresponder a uma das alternativas" é julgado com a lista de alternativas à vista. O julgamento continua sendo sobre os resultados: se nenhuma tarefa tivesse calculado a interseção, o critério seguiria **não atendido**, porque os aprendizados não contam como cobertura.

**C.2.** No cenário de reprovação do paper, o planejador cria a Tarefa 4 (interseção das três listas). Com a área, o modelo pode copiar para a descrição da tarefa o dado de que ela precisa, por exemplo: "Dadas as listas já identificadas — primos: [2]; pares: [2, 4, 6]; maiores que 2: [4, 6] — e as alternativas A) 2; B) 4; C) 6; D) Nenhuma das anteriores, determine quais números aparecem simultaneamente nas três listas."

**C.3.** Os resultados dizem que primo ∩ par ∩ maior que 2 = ∅. A área traz "D) Nenhuma das anteriores", e o modelo apresenta **D) Nenhuma das anteriores** sem inventar nada: o conteúdo (conjunto vazio) vem dos resultados, e a letra é conferida nos aprendizados.

### 2.5 Exemplo sem nenhum aprendizado

**Input**

> Traduza "bom dia" para o inglês.

A.3 devolve lista vazia, e a única tarefa não produz aprendizado. Todos os prompts de B e C trazem a área com o aviso:

```text
## Aprendizados Pontuais

(...)

Nenhum aprendizado pontual registrado até o momento.
```

### 2.6 O que muda no texto do paper

| Trecho atual da Metodologia | Ajuste necessário |
|---|---|
| Expressão de B.1: *Aprendizados Acumulados* + *Tarefa Selecionada* + *Template B.1* → *Resultado Preliminar B* | Mantém-se. Esclarecer que os aprendizados chegam pela área "Aprendizados Pontuais" do template, e não como um bloco à parte no contexto. |
| Expressão de B.2: *Resultado Preliminar B* + *Critérios da Tarefa* + *Template B.2* → *Decisão* | Acrescentar *Aprendizados Pontuais* à entrada, com a ressalva de que não são critérios. |
| Expressão de B.4: *Contexto Completo da Tarefa* + *Template B.4* → *Aprendizados Pontuais* | Acrescentar *Aprendizados Pontuais (já registrados)* à entrada, para evitar repetição. |
| Expressões de C.1, C.2 e C.3 | Acrescentar *Aprendizados Pontuais* à entrada de cada uma. |
| "Os aprendizados pontuais têm papel restrito à Execução em Loop" e "O aprendizado é um fragmento seco de fato, destinado exclusivamente a subsidiar a execução das tarefas seguintes dentro do loop" | Substituir: os aprendizados acompanham todas as etapas das fases B e C como referência, mas continuam separados dos resultados armazenados, que são a única base da resposta final. |
| Seção C.3: o Template C.3 "proíbe terminantemente a inserção de novos fatos" | Mantém-se. Acrescentar que os aprendizados servem só para conferir dados do enunciado já presentes. |
| Figura do fluxo adaptado | A Memória Acumulada passa a alimentar todas as etapas de B e de C, e não só B.1. |

Parágrafo sugerido para o paper, no estilo da Metodologia:

> Os aprendizados pontuais acompanham todas as etapas da Execução em Loop e da Criação da Resposta Final. Cada template dessas fases contém uma área dedicada, preenchida com todos os aprendizados acumulados até o momento da chamada — as anotações do enunciado seguidas dos fatos extraídos das tarefas concluídas. A área é usada como referência, conforme a etapa: na resolução, apoia a tarefa sem ampliar seu escopo; nas verificações, permite conferir os dados envolvidos, sem que os aprendizados sejam tratados como critérios ou como cobertura de critérios; no planejamento adicional, fornece os dados que as novas tarefas devem repetir; e na construção da resposta final, permite conferir dados do enunciado, enquanto o conteúdo da resposta continua derivado exclusivamente dos resultados armazenados.

### 2.7 Decisões de projeto

| Decisão | Justificativa |
|---|---|
| Uma área com título fixo ("Aprendizados Pontuais") em cada template, e não um bloco no início da janela. | Fica no mesmo lugar em todo prompt, inclusive em B.2 e na fase C, que têm janelas próprias. Evita duplicar o bloco quando o template de B.1 é reenviado a cada tentativa. |
| A área sempre presente, com aviso quando vazia. | O modelo sabe que não há aprendizados, em vez de não saber se a área existe. O formato dos prompts fica estável. |
| Todos os aprendizados, sem filtro por relevância. | É o que foi pedido e evita outra chamada ao modelo só para filtrar. Os aprendizados são curtos por construção (A.3 e B.4 exigem fatos secos). |
| Instrução de uso específica em cada template. | Receber os aprendizados não pode mudar o papel da etapa: um validador não aprova por causa deles e a síntese não os usa como resultado. |
| B.4 recebe os aprendizados anteriores, sem os da própria tarefa. | Os da tarefa ainda não existem no momento da chamada. Ver os anteriores permite não repeti-los. |
| A fase A não recebe a área. | A.1, A.2 e A.3 rodam antes de qualquer aprendizado existir. |

### 2.8 Limitações

- Os aprendizados agora estão em mais chamadas, o que aumenta os tokens de entrada de cada sessão, na proporção do tamanho da memória.
- A instrução de usar os aprendizados só como referência é um controle feito pelo prompt. O sistema não detecta automaticamente um validador que aprovou por causa de um aprendizado, nem uma síntese que usou um aprendizado como resultado.
- O ganho em acurácia não foi medido: os testes verificam o que é injetado, onde e quando, não a qualidade das respostas.

### 2.9 Validação na implementação

A alteração foi feita com TDD: os testes foram escritos antes do código, rodados para confirmar que falhavam e só então o código foi alterado. A suíte do backend passa por completo (1458 testes, cobertura de 100%, exigida pelo projeto) e o código passa no lint (`flake8`). Os testes cobrem:

- **Templates reais:** os seis templates de B e C têm a área "Aprendizados Pontuais" com o placeholder `{{learnings}}`, antes do formato de saída; os de A não têm. B.2 e C.1 dizem que os aprendizados não são critérios, C.1 que não contam como cobertura, C.3 que não substituem os resultados armazenados, B.4 que não devem ser repetidos.
- **Integração com os templates reais:** num fluxo com reprovação em B.2 e uma rodada de C.2, todo prompt de B e C enviado ao modelo contém a área e as anotações do enunciado.
- **Conteúdo por momento:** cada nova tentativa de B.1 recebe os aprendizados; B.2 recebe os acumulados antes da tarefa; B.4 não recebe os da própria tarefa; C.1, C.2 e C.3 recebem todos, na ordem de extração.
- **Área vazia:** sem aprendizados, a área traz o aviso.
- **Sem duplicação:** a janela da tarefa não recebe mais o bloco avulso; o único prompt inicial é o de B.1.
- **Separação:** os aprendizados nunca aparecem nos resultados armazenados de C.1 e C.3, e os resultados nunca aparecem nos aprendizados.

Arquivos principais:

| Arquivo | Papel |
|---|---|
| `apps/backend/src/infra/templates/b1_task_resolution.md`, `b2_task_verification.md`, `b4_learnings_extraction.md`, `c1_global_verification.md`, `c2_additional_planning.md`, `c3_final_answer.md` | Área "Aprendizados Pontuais" e instrução de uso em cada template. |
| `apps/backend/src/domain/services/learnings_memory.py` | Renderiza o conteúdo da área (lista ou aviso). |
| `apps/backend/src/application/usecases/ralph_thinking_usecase.py` | Entrega a variável `learnings` a todos os templates de B e C; deixa de injetar o bloco avulso. |

---

## 3. Temperatura 1 nas retentativas

### 3.1 Problema

Os testes mostraram muitas retentativas em "loop": a cada nova tentativa, o modelo devolvia praticamente a mesma saída e falhava pelo mesmo motivo, até esgotar o limite. Isso acontecia tanto com a reprovação de uma tarefa em B.2 quanto com saídas inválidas (por exemplo, um JSON que não podia ser extraído).

A causa provável é a temperatura. A chamada repetida usava a mesma temperatura informada pelo usuário, em geral baixa (as baterias de benchmark usam 0, para respostas mais estáveis). Com temperatura baixa e um contexto quase igual, o modelo tende a reproduzir a resposta que acabou de ser recusada. O *feedback* de reprovação no contexto ajuda, mas não basta para tirar o modelo da mesma saída.

### 3.2 Regra nova

**Toda chamada de retentativa é feita com temperatura 1.** É uma temperatura **temporária**: assim que as retentativas acabam, as chamadas voltam à temperatura fornecida pelo usuário na entrada.

Uma **retentativa** é uma chamada que repete um pedido porque a resposta anterior não passou numa verificação:

1. **Reprovação em critério de aceite (B.2).** A nova tentativa de B.1, depois de B.2 reprovar a anterior, é feita com temperatura 1.
2. **Erro de saída, em qualquer fase.** Cada correção pedida ao modelo é feita com temperatura 1: JSON ilegível ou fora do formato, relatório de verificação inconsistente (B.2 ou C.1), lote de tarefas inválido (A.2 ou C.2) e resposta vazia do provedor.

Regras:

- **Volta à temperatura do usuário.** A primeira chamada que não é retentativa volta à temperatura do usuário: a verificação B.2 da nova tentativa, a fase seguinte depois de uma correção de saída, a próxima tarefa.
- **Nada é sobrescrito.** A temperatura do usuário continua registrada na sessão e configurada em todas as fases; a temperatura 1 vale só para a chamada de retentativa.
- **Limites inalterados.** O número máximo de tentativas por tarefa e de correções de saída não muda. Muda só a temperatura com que cada repetição é pedida.
- **Registro.** Cada invocação registra na sessão a temperatura efetivamente enviada (campo `temperature`), o que permite auditar e medir as retentativas.

### 3.3 O que é e o que não é retentativa

| Situação | É retentativa? | Temperatura |
|---|---|---|
| Primeira tentativa de B.1 de uma tarefa | Não | Usuário |
| Nova tentativa de B.1 depois de reprovação em B.2 | **Sim** | **1** |
| Correção de saída inválida dentro de uma nova tentativa de B.1 | **Sim** | **1** |
| B.2 que verifica a nova tentativa | Não: é a primeira verificação daquela tentativa | Usuário |
| Correção de relatório inválido de B.2 ou C.1 | **Sim** | **1** |
| Correção de JSON inválido em A.1, A.2, A.3, B.4 ou C.3 | **Sim** | **1** |
| Repetição depois de resposta vazia do provedor | **Sim** | **1** |
| C.2 depois de C.1 reprovar | Não: cria tarefas novas, não repete um pedido | Usuário |
| Tarefas criadas por C.2 e a nova rodada de C.1 | Não: trabalho novo sobre um conjunto maior de resultados | Usuário |

### 3.4 Exemplo: a Tarefa 2 reprovada do paper

No exemplo do paper, a primeira tentativa da Tarefa 2 antecipa a resposta final e é reprovada. O usuário pediu temperatura 0,3. Chamadas da Tarefa 2:

| # | Chamada | Motivo | Temperatura |
|---|---|---|---|
| 1 | B.1 — tentativa 1 | Primeira tentativa | 0,3 |
| 2 | B.2 — verifica a tentativa 1 | Primeira verificação | 0,3 |
| — | *Reprovado: critérios "não deve tentar resolver a questão final" e "não deve avaliar nenhuma outra condição"* | | |
| 3 | B.1 — tentativa 2 | **Retentativa** depois da reprovação | **1** |
| 4 | B.2 — verifica a tentativa 2 | Primeira verificação desta tentativa | 0,3 |
| — | *Aprovado* | | |
| 5 | B.4 — aprendizados da Tarefa 2 | Fase seguinte | 0,3 |
| 6 | B.1 — tentativa 1 da Tarefa 3 | Próxima tarefa | 0,3 |

Na chamada 3, o contexto é o mesmo de sempre: a tentativa reprovada e o veredito do validador continuam na janela da tarefa (regra do paper). A diferença é a temperatura mais alta, que torna menos provável repetir a resposta que antecipou a conclusão.

### 3.5 Exemplo: JSON inválido seguido de nova tentativa

Mesma Tarefa 2, mas a tentativa 2 vem com um JSON que não pode ser extraído:

| # | Chamada | Motivo | Temperatura |
|---|---|---|---|
| 1 | B.1 — tentativa 1 | Primeira tentativa | 0,3 |
| 2 | B.2 — verifica a tentativa 1 | Primeira verificação | 0,3 |
| 3 | B.1 — tentativa 2 | Retentativa depois da reprovação | **1** |
| — | *Saída sem JSON válido: o modelo recebe a mensagem de correção* | | |
| 4 | B.1 — correção da tentativa 2 | Retentativa de saída inválida | **1** |
| 5 | B.2 — verifica a tentativa 2 | Primeira verificação desta tentativa | 0,3 |

### 3.6 Exemplo: relatório inválido na verificação global

C.1 devolve um relatório que não avalia todos os critérios gerais:

| # | Chamada | Motivo | Temperatura |
|---|---|---|---|
| 1 | C.1 | Primeira verificação global | 0,3 |
| — | *Relatório recusado: faltam avaliações de critérios gerais* | | |
| 2 | C.1 — correção do relatório | Retentativa de saída inválida | **1** |
| 3 | C.3 | Fase seguinte | 0,3 |

Se, em vez disso, C.1 devolvesse um relatório válido que **reprova** um critério geral, nenhuma chamada seria feita com temperatura 1: C.2 e as tarefas que ele criar são trabalho novo (seção 3.3).

### 3.7 Registro na sessão

Cada invocação passa a ter o campo `temperature`, com a temperatura efetivamente enviada. Trecho das invocações da Tarefa 2 do exemplo 3.4:

```json
[
  {"phase": "B1", "task_id": "T2", "outcome": "success", "temperature": 0.3},
  {"phase": "B2", "task_id": "T2", "outcome": "success", "temperature": 0.3},
  {"phase": "B1", "task_id": "T2", "outcome": "success", "temperature": 1.0},
  {"phase": "B2", "task_id": "T2", "outcome": "success", "temperature": 0.3},
  {"phase": "B4", "task_id": "T2", "outcome": "success", "temperature": 0.3}
]
```

O `temperature` da sessão continua sendo o pedido pelo usuário (0,3). Invocações gravadas antes desta alteração voltam com `temperature: null`. A inferência direta (baseline) também registra a temperatura da sua única chamada, que nunca é repetida.

### 3.8 O que muda no texto do paper

| Trecho atual da Metodologia | Ajuste necessário |
|---|---|
| Seção B.2: "caso contrário, a tarefa é reapresentada ao modelo para uma nova tentativa" e "o contexto *não* é reinicializado durante as tentativas de repetição de uma mesma tarefa" | Acrescentar que cada nova tentativa é feita com temperatura 1, e que a verificação seguinte volta à temperatura do usuário. |
| Exemplo da Tarefa 2 ("Na segunda tentativa, com o *feedback* anterior no contexto, o modelo retorna") | Acrescentar que a segunda tentativa é feita com temperatura 1. |
| O paper não trata de saídas inválidas (JSON) | Se o tratamento de saídas inválidas for descrito no paper, registrar que as correções também são pedidas com temperatura 1. |
| Metodologia de avaliação | Registrar que a temperatura configurada no experimento vale para as chamadas que não são retentativas. |

Parágrafo sugerido para o paper, no estilo da Metodologia:

> Toda chamada de retentativa é realizada com temperatura 1, independentemente da temperatura configurada pelo usuário. Isso inclui a nova tentativa de resolução de uma tarefa reprovada na verificação dos critérios de aceite e a correção de saídas que não puderam ser interpretadas. Repetir um pedido recusado com a mesma temperatura, em geral baixa, tende a reproduzir a mesma resposta e a mesma falha; a temperatura mais alta aumenta a variação entre as tentativas, enquanto o contexto preservado da tarefa mantém visíveis a tentativa anterior e os critérios não satisfeitos. A temperatura do usuário volta a ser usada assim que as retentativas terminam, a começar pela verificação da nova tentativa.

### 3.9 Decisões de projeto

| Decisão | Justificativa |
|---|---|
| Valor fixo de 1, e não configurável. | É a regra pedida, e um valor fixo deixa o experimento reprodutível. O valor está numa constante única (`_RETRY_TEMPERATURE` em `base_thinking_phase.py`). Também é o maior valor aceito pela API do projeto, que limita a temperatura a `[0, 1]`. |
| A verificação B.2 da nova tentativa usa a temperatura do usuário. | B.2 não está repetindo um pedido: é a primeira verificação daquela tentativa. Um validador estável (temperatura baixa) é desejável. |
| C.1 reprovado não ativa a temperatura 1. | C.2 cria tarefas novas, que rodam em contextos novos; C.1 seguinte avalia um conjunto maior de resultados. Nenhum dos dois repete um pedido recusado. |
| Correções de saída inválida em qualquer fase usam temperatura 1. | A regra pede temperatura 1 sempre que "ocorrer um erro (como ao extrair um JSON)", em qualquer fase. |
| A temperatura efetiva é registrada por invocação. | Permite auditar quais chamadas foram retentativas e medir o efeito da regra no benchmark. |

### 3.10 Limitações

- Temperatura 1 aumenta a variação das respostas. Uma nova tentativa pode sair mais criativa e também menos aderente ao formato pedido; nesse caso, a correção de saída também é pedida com temperatura 1.
- Alguns modelos de raciocínio ignoram ou não aceitam o parâmetro `temperature`; neles, a regra não tem efeito.
- A regra reduz a chance de repetir a mesma saída, mas não elimina o limite: se a tarefa continuar reprovada, a execução é interrompida quando as tentativas acabam, como antes.
- O efeito sobre a quantidade de retentativas e sobre a acurácia não foi medido. Os testes verificam a temperatura enviada em cada chamada; a medição exige rodar o benchmark antes e depois da alteração.

### 3.11 Validação na implementação

A alteração foi feita com TDD, na mesma rodada da alteração 2 (1458 testes passando, cobertura de 100%, lint sem erros). Os testes cobrem:

- **Fase base:** a correção de JSON inválido, de relatório inconsistente e a repetição depois de resposta vazia saem com temperatura 1; correções seguidas continuam com 1; a validação local da requisição também recebe 1; uma execução sem falha nunca usa 1; uma execução marcada como retentativa já começa com 1; a execução seguinte da mesma fase volta à temperatura do usuário, que nunca é sobrescrita.
- **Fluxo completo:** a nova tentativa depois de reprovação em B.2 usa 1, e a verificação dela, B.4, C.1 e C.3 voltam à temperatura do usuário; com duas reprovações seguidas, as duas novas tentativas usam 1 e as verificações entre elas não; uma correção de JSON dentro de uma nova tentativa continua com 1; correções em A.3 e em C.1 usam 1 só na chamada de correção; C.1 reprovado seguido de C.2 não usa 1 em nenhuma chamada.
- **Registro:** cada invocação grava a temperatura efetiva; o documento da sessão a persiste e lê documentos antigos sem o campo como `null`; a inferência direta registra a sua temperatura.

Arquivos principais:

| Arquivo | Papel |
|---|---|
| `apps/backend/src/application/phases/base_thinking_phase.py` | Constante `_RETRY_TEMPERATURE`; temperatura 1 nas correções e quando `is_retry` é verdadeiro. |
| `apps/backend/src/domain/interfaces/thinking_phase_interface.py` | Parâmetro `is_retry` de `execute`. |
| `apps/backend/src/application/usecases/ralph_thinking_usecase.py` | Marca como retentativa toda tentativa de B.1 depois da primeira. |
| `apps/backend/src/domain/entities/session/llm_invocation.py`, `apps/backend/src/infra/adapters/session_recorder_adapter.py`, `apps/backend/src/infra/mappers/session_document_mapper.py` | Registro e persistência da temperatura efetiva de cada invocação. |
