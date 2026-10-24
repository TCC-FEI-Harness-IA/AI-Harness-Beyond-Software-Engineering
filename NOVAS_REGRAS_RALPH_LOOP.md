# Novas regras do Ralph Wiggum Loop adaptado

## Finalidade deste relatório

Este documento registra as alterações feitas no fluxo implementado depois da versão descrita na seção **Metodologia** do paper. Ele serve de base para atualizar o paper oficial: cada alteração traz o problema que a motivou, a regra nova, a expressão no formato usado na Metodologia, exemplos com o *input* de referência do paper, o que deixa de valer no texto atual e a validação na implementação.

A explicação geral do fluxo está em [`RALPH_LOOP_ADAPTADO.md`](RALPH_LOOP_ADAPTADO.md). Aquele arquivo mantém a transcrição literal da Metodologia e traz a nova etapa numa seção separada, **Extensões ao método do paper**.

## Resumo das alterações

| # | Alteração | Fase | Efeito principal |
|---|---|---|---|
| 1 | Nova etapa **A.3 — Aprendizados pontuais do enunciado** | A. Planejamento | Dados importantes da pergunta (valores com unidades, alternativas, fórmulas, condições) deixam de depender de a descrição das tarefas os repetir. |

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
8. **Escopo.** As anotações de A.3 seguem a regra dos aprendizados pontuais: têm papel restrito à Execução em Loop. Não são enviadas ao validador de tarefa (B.2), nem à validação global (C.1), nem à construção da resposta final (C.3).
9. **Sem efeito sobre a fila.** A.3 não cria nem altera tarefas e não consome o limite de tarefas da sessão.

### 1.3 Posição no fluxo

```text
A. Planejamento
   A.1  Critérios de aceite gerais
   A.2  Quebra em tarefas de objetivo único
   A.3  Aprendizados pontuais do enunciado   ← nova etapa
B. Execução em Loop      (cada tarefa recebe as anotações de A.3 no início do contexto)
C. Criação da Resposta Final   (não recebe as anotações de A.3)
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

**Efeito sobre as tarefas.** O decompositor produz as três tarefas do paper, cada uma com uma descrição curta (por exemplo, "Dadas as opções (2, 4, 6), identifique quais são pares"). Antes, o contexto da Tarefa 1 continha só a descrição dela. Agora começa com:

```text
## Aprendizados acumulados

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
| "Os aprendizados pontuais têm papel restrito à Execução em Loop" | Mantém-se, e agora inclui as anotações de A.3. |
| Planejamento Adicional: "agora com o contexto dos aprendizados acumulados de todas as tarefas anteriores" | Acrescentar que as anotações de A.3 também estão no contexto. |

Parágrafo sugerido para a subseção de A.3 no paper, no estilo da Metodologia:

> Uma terceira etapa do planejamento registra os aprendizados pontuais do enunciado. Como cada tarefa é executada em um contexto novo, os dados da pergunta original que a descrição da tarefa não repetir deixariam de estar disponíveis ao modelo, o que afeta em especial as alternativas de questões de múltipla escolha, os valores com suas unidades de medida e as fórmulas fornecidas. Esta etapa associa a pergunta do usuário ao Template A.3, que orienta o modelo a anotar, em tópicos secos e sem resolver o problema, todo dado do enunciado que deve chamar a atenção. As anotações são anexadas à Memória Acumulada antes da primeira tarefa e, assim como os aprendizados de B.4, são injetadas no início do contexto de cada tarefa, sem participar da construção da resposta final.

### 1.8 Decisões de projeto

| Decisão | Justificativa |
|---|---|
| A.3 roda **depois** de A.2, e não antes. | Mantém A.1 e A.2 idênticas ao paper. A.3 não depende do resultado delas, então a ordem não altera o conteúdo. A posição final deixa A.1 e A.2 como estão. |
| A.3 recebe **só a pergunta**. | As anotações descrevem o que o enunciado afirma. Se dependessem do plano, mudariam conforme a decomposição escolhida pelo modelo. |
| As anotações vão para a **mesma memória** de B.4. | Aproveita o mecanismo de injeção que já existe (*Fresh Context*), sem criar um segundo canal. A ordem de inserção garante que o enunciado vem primeiro. |
| As anotações **não** vão para B.2, C.1 e C.3. | Preserva a separação do paper entre resultados armazenados (alimentam a resposta final) e aprendizados (guiam o loop). |
| Lista vazia é válida. | Evita forçar o modelo a inventar anotações quando o enunciado é simples. |
| Cada chamada de A.3 conta no orçamento da sessão. | A.3 é uma chamada ao modelo como as demais: entra nos limites de chamadas, de tokens e de tempo, e é registrada como uma invocação. |

### 1.9 Ponto em aberto para decisão

A regra de escopo dos aprendizados do paper foi mantida: as anotações de A.3 não chegam a C.3. Se um dado do enunciado (por exemplo, a lista de alternativas) não estiver presente nos resultados das tarefas aprovadas, a construção da resposta final não terá como recuperá-lo. Hoje isso é contido pelo critério geral de A.1 ("o valor deve corresponder a uma das alternativas") e pela verificação global C.1. Se os testes mostrarem perdas também na fase C, a alternativa é injetar as anotações de A.3 em C.1 e C.3. Isso **alteraria** a separação definida no paper e exigiria registrar uma segunda extensão.

### 1.10 Validação na implementação

A etapa foi implementada com TDD: os testes foram escritos antes do código e descrevem o comportamento esperado. A suíte do backend passa por completo (1198 testes, cobertura de 100%, exigida pelo projeto) e o código passa no lint (`flake8`) do projeto. Os testes cobrem:

- **Ordem do fluxo:** A.1, A.2, A.3 e só então as tarefas; A.3 emite um evento `learn` e roda em janela própria.
- **Entrada isolada:** o Template A.3 recebe apenas a pergunta do usuário.
- **Injeção:** a primeira tarefa e todas as seguintes recebem as anotações no início do contexto, antes dos aprendizados de B.4; as tarefas de C.2 também.
- **Escopo:** o validador de tarefa (B.2) e as fases C.1 e C.3 não recebem as anotações.
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
- **O frontend ainda não conhece a fase `A3`** (esta alteração cobriu apenas o backend). Em `apps/frontend`, o parser de sessões persistidas (`src/api/parsers/sessionDocument.ts`) lança `ContractError` para uma mensagem com `phase = A3`, o que impede abrir pelo frontend uma sessão nova do fluxo harness. Para frames ao vivo, `reasoningFrame.ts` usa fallback para B1 e registra um aviso no console. Para exibir A.3 corretamente, o frontend precisa de `A3` em `THINKING_PHASE`, em `PHASE_LABEL` e no mapeamento de fases da trilha.
