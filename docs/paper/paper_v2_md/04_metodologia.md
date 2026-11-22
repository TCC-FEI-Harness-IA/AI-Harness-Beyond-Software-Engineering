# III. Metodologia: Adaptação do *Ralph Wiggum Loop*

A transposição do *Ralph Wiggum Loop*~\cite{ghuntley2025ralph} da engenharia de software para a resolução generalista de perguntas em linguagem natural impõe alterações estruturais profundas em relação ao paradigma original ([FIGURA 1: Diagrama do Ralph Wiggum Loop original]). Em desenvolvimento de software, o artefato final constrói-se incrementalmente no repositório de código e cada história de usuário dispõe de testes automatizados determinísticos como oráculo de validação. Em perguntas abertas ou de múltipla escolha em linguagem natural, não há compilador nem suíte de testes executáveis: tanto a decomposição do problema quanto a verificação local e global dependem de inferência estruturada, e ao término das tarefas é indispensável sintetizar uma resposta final coesa, fiel e compatível com as restrições do enunciado.

A [FIGURA 2: Visão geral do Ralph Wiggum Loop adaptado (`flow_version = 2`), contemplando planejamento validado em quatro etapas (A.1–A.4), execução isolada com critérios fixos -TECH/-REV, ResultsLedger, memória transversal LearningsMemory, fase C com revisões auditáveis e guardrails fail-closed] apresenta a visão geral da arquitetura implementada e auditada (`flow_version = 2`), que evoluiu a partir da formulação conceitual inicial em três macrofases: **A. Planejamento**, **B. Execução em Loop** e **C. Criação da Resposta Final**, articuladas em torno de dois repositórios explícitos de estado — o livro de resultados (`ResultsLedger`) e a memória transversal de aprendizados (`LearningsMemory`).

[FIGURA 2: Visão geral do Ralph Wiggum Loop adaptado (`flow_version = 2`) — atualizar `docs/paper/diagrams/ralph_loop_adaptado_png.png` conforme Seção 1.2 de `00_auditoria_figuras.md`]

Para ilustrar concretamente o comportamento de cada etapa ao longo desta seção, adota-se o seguinte enunciado de referência:

> **Exemplo de referência (Entrada do usuário):**
> *Qual dos seguintes números é simultaneamente primo, par e maior que 2?*
> A) 2  B) 4  C) 6  D) Nenhuma das anteriores

As expressões apresentadas nas subseções a seguir formalizam os componentes lógicos que compõem o *prompt* de entrada e a saída estruturada de cada fase. O termo *Pergunta do usuário* designa o enunciado original; *Template X* refere-se ao *prompt* de instrução fixo da fase correspondente (implementado em inglês no *harness*, preservando o idioma original do enunciado na resposta final); elementos entre colchetes `[...]` denotam entradas condicionais presentes apenas em cenários específicos (como revisões ou retentativas).

---

## A. Planejamento (Etapas A.1 a A.4)

Na implementação consolidada (`flow_version = 2`), a fase de Planejamento é composta por **quatro subetapas estritamente sequenciais**, com um laço de auditoria semântica entre `A.2` e `A.3` antes que qualquer tarefa ingresse na fila de execução.

### 1. Definição dos critérios de aceite gerais (`A.1`)

Como a conclusão das tarefas individuais não entrega automaticamente uma resposta formatada ao usuário, a etapa `A.1` estabelece o contrato global que a resposta final deverá cumprir: conteúdo obrigatório a determinar, idioma esperado (sempre o do enunciado original, salvo instrução explícita em contrário), formato de apresentação e restrições reais declaradas no pedido. Diretrizes de objetividade genérica não autorizam inventar limites artificiais de palavras ou linhas, e justificativas opcionais não são convertidas em obrigatórias. A transformação lógica é dada por:

$$\text{\textit{Pergunta do usuário}} + \text{\textit{Template A.1}} \longrightarrow \text{\textit{Critérios de Aceite Gerais (A.1)}}$$

Os critérios gerados são persistidos em estado próprio da sessão para auditar a cobertura do plano em `A.3`, a suficiência global em `C.1` e a apresentação final em `C.3`.

> **Exemplo (`A.1`):** Para o enunciado de referência, `A.1` produz critérios gerais estruturados (em JSON), especificando: (i) responder em Português do Brasil; (ii) identificar inequivocamente qual alternativa atende simultaneamente às condições de ser primo, par e maior que 2; e (iii) garantir correspondência exata com uma das alternativas oferecidas (`A` a `D`), apresentando apenas o formato solicitado.

### 2. Geração do plano candidato (`A.2`)

A etapa `A.2` decompõe a pergunta em uma lista ordenada de tarefas de objetivo único, cada uma composta por identificador (`T1`, `T2`, ...), título, descrição autossuficiente, lista de critérios individuais de aceite (`T1-AC1`, ...) e, quando pertinente, dependências lógicas explícitas (`depends_on`) sobre tarefas anteriores. Diferentemente da concepção inicial do fluxo, a saída de `A.2` constitui um **plano candidato** que ainda não entra na fila de execução nem consome o limite de tarefas da sessão.

As regras de redação impostas pelo `Template A.2` determinam que: (i) os campos redundantes de "entradas esperadas" e "saída esperada" são omitidos para não competir com os critérios de aceite; (ii) os critérios de uma mesma tarefa devem ser **complementares entre si** e nunca mutuamente exclusivos; (iii) toda tarefa exige que o resultado venha **acompanhado de explicação fundamentada** (fórmulas, substituição com unidades, convenções ou justificativa lógica), verificável em `B.2`; (iv) títulos, descrições e critérios devem manter conclusões, valores, classificações e ordenações **em aberto**, evitando respostas antecipadas; e (v) tarefas podem declarar dependência lógica (`depends_on`) via memória de aprendizados, sem abdicar do objetivo único. Quando um candidato é reprovado por `A.3`, `A.2` executa novamente em **janela nova**, recebendo apenas o último candidato reprovado e o respectivo relatório de validação:

$$\text{\textit{Pergunta do usuário}} + [\text{\textit{Último Plano Reprovado}} + \text{\textit{Relatório A.3}}] + \text{\textit{Template A.2}} \longrightarrow \text{\textit{Plano Candidato (A.2)}}$$

Para evitar ciclos repetitivos quando a temperatura base da sessão é nula (`0,0`), a revisão semântica de `A.2` adota escalonamento progressivo de temperatura: o candidato 1 utiliza a temperatura da sessão; o candidato 2 utiliza `0,5`; e os candidatos 3 a 5 utilizam `1,0`.

> **Exemplo (`A.2`):** Para o enunciado de referência, um plano candidato adequado define quatro tarefas: `T1` (identificar quais valores dentre 2, 4 e 6 são primos, com justificativa), `T2` (identificar quais são pares, com justificativa), `T3` (identificar quais são estritamente maiores que 2, com justificativa) e `T4` (com `depends_on: ["T1", "T2", "T3"]`, determinar a interseção dos três conjuntos e mapear o resultado às alternativas A–D, com explicação). Cada tarefa inclui critérios complementares exigindo explicação e restringindo ações analíticas externas ao seu escopo.

### 3. Validação da decomposição (`A.3`)

Observações empíricas durante o desenvolvimento mostraram que a validação sintática do *parser* é incapaz de impedir que `A.2` omita condições do enunciado ou imponha conclusões antecipadas nos próprios critérios, levando o loop a aprovar soluções formalmente conformes a uma especificação defeituosa. Por isso, a arquitetura `flow_version = 2` introduz a etapa `A.3` (*Task Decomposition Validator*), executada em janela nova e sempre na temperatura da sessão, que audita o plano candidato atual frente à pergunta original (referência soberana) e aos critérios de `A.1`:

$$\text{\textit{Pergunta do usuário}} + \text{\textit{Critérios Gerais (A.1)}} + \text{\textit{Plano Candidato Atual (A.2)}} + \text{\textit{Template A.3}} \longrightarrow \text{\textit{Relatório A.3 (Aprovado / Reprovado)}}$$

A auditoria aplica uma **rubrica fixa de sete regras** pertencente ao *harness*:
1. **Fidelidade:** preservação de referentes, unidades, relações temporais, condições simultâneas e restrições do pedido, sem omissão de condições nem troca de grandezas;
2. **Neutralidade:** ausência de resultados, classificações, comparações ou prioridades impostas ("mais geral", "mais simples", etc.) não fornecidas pelo enunciado;
3. **Aplicabilidade:** verificação explícita ou justificativa prevista para toda fórmula ou método planejado;
4. **Critérios:** verificabilidade, complementaridade e exigência de resultado fundamentado;
5. **Coerência:** delimitação de escopo, ordem executável e dependências `depends_on` válidas;
6. **Cobertura:** suficiência do conjunto de tarefas — inclusive na integração entre elas — para atingir a determinação solicitada, deixando apenas formatação e pareamento literal para `C.3`;
7. **Necessidade:** ausência de tarefas burocráticas, redundantes ou dedicadas apenas a transcrever dados ou imprimir marcadores finais.

Em caso de reprovação (`approved = false`), `A.3` emite problemas estruturados apontando tarefa, critério, defeito bloqueante e ajuste investigativo, devolvendo o fluxo a `A.2` até o teto configurável de tentativas de planejamento (`max_planning_attempts = 5`). Esgotado o limite sem aprovação, a sessão encerra em modo *fail-closed* sem executar tarefas. Somente quando `A.3` aprova (`approved = true`), o plano é confirmado **uma única vez** na fila de execução.

### 4. Extração de aprendizados pontuais do enunciado (`A.4`)

Uma vez confirmado o plano, a etapa `A.4` opera em janela isolada recebendo **exclusivamente a pergunta original**, sem acesso aos critérios de `A.1` nem às tarefas de `A.2`:

$$\text{\textit{Pergunta do usuário}} + \text{\textit{Template A.4}} \longrightarrow \text{\textit{Aprendizados do Enunciado [Question]}}$$

Seu papel é extrair dados literais e atômicos do enunciado — valores acompanhados de unidades de medida, alternativas literais com suas letras, fórmulas fornecidas, tabelas, definições e condições simultâneas — sem realizar cálculos, conversões ou deduções. Esses fatos pré-populam a memória transversal `LearningsMemory` com o rótulo de procedência `[Question]` **antes** da execução da Tarefa 1, evitando que o isolamento de *Fresh Context* ocasione perda de dados literais caso alguma descrição de tarefa omita parte do enunciado. Uma lista vazia constitui saída válida quando o enunciado não contém dados específicos a anotar.

> **Exemplo (`A.4`):** Para o enunciado de referência, `A.4` registra:
> - `[Question] Alternativas: A) 2; B) 4; C) 6; D) Nenhuma das anteriores.`
> - `[Question] Condições exigidas simultaneamente: ser primo, ser par e ser maior que 2.`

---

## B. Execução em Loop (Etapas B.1 a B.4)

A fase de Execução em Loop processa sequencialmente a fila de tarefas confirmadas, aplicando **isolamento total de contexto (*Fresh Context*) a cada invocação de fase**: não apenas na transição entre tarefas distintas, mas também nas transições `B.1` $\rightarrow$ `B.2`, `B.2` $\rightarrow$ `B.1` (retentativas), `B.1` $\rightarrow$ `B.4` e para toda a fase C. Apenas chamadas de correção de saída estruturalmente inválida reutilizam a janela da mesma invocação de fase. O conhecimento transversal entre etapas trafega exclusivamente pela seção fixa `## Key Learnings`, injetada em todos os seis *templates* das fases B e C (`B.1`, `B.2`, `B.4`, `C.1`, `C.2` e `C.3`) em área explicitamente separada dos resultados armazenados.

### 1. Seleção da tarefa e resolução (`B.1`)

O orquestrador seleciona programaticamente a próxima tarefa pendente na fila e abre uma nova janela de contexto para `B.1`. O *template* entrega a descrição da tarefa, o **conjunto efetivo de critérios** que será verificado em `B.2` (critérios planejados mais o critério técnico fixo `<id>-TECH` e, em tarefas revisoras, `<id>-REV`), a área `## Key Learnings` com rótulos de procedência (`[Question]`, `[Task T1]`, `[Tasks T1, T3]`), eventuais resultados sob revisão (`results_under_review`, quando originada em `C.2`) e, a partir da segunda tentativa, o bloco delimitado `<previous_attempts>` contendo as tentativas reprovadas e os respectivos vereditos de `B.2`:

$$\text{\textit{Aprendizados Pontuais}} + \text{\textit{Tarefa Selecionada (Critérios Efetivos)}} + [\text{\textit{Resultados sob Revisão}}] + [\text{\textit{Tentativas Anteriores}}] + \text{\textit{Template B.1}} \longrightarrow \text{\textit{Resultado Preliminar B}}$$

A saída estruturada de `B.1` separa explicitamente o desenvolvimento detalhado (`result`, em Markdown) da conclusão autossuficiente (`conclusion`, sem o desenvolvimento completo), além de emitir o campo opcional `revision` com vereditos individuais (`confirmed` ou `superseded`, acompanhados de justificativa) quando a tarefa é revisora. O *template* compartilha com `B.2` e `C.1` uma política única de evidência e consistência (*Evidence and consistency policy*): aceita resultados exatos e aproximações ou escolhas por melhor ajuste devidamente fundamentadas, mantém distintos o valor calculado e a alternativa escolhida (proibindo igualdades falsas) e exige conferência da base analítica antes de qualquer aproximação. Retentativas de `B.1` após reprovação de `B.2` ocorrem sempre em **janela nova** e com **`temperature = 1,0`**, instruindo o modelo a enfrentar a objeção concreta apontada e preservar conclusões não refutadas.

> **Exemplo (`B.1` — Tarefa 1):** Em janela limpa contendo os dois aprendizados `[Question]` de `A.4`, `B.1` resolve `T1` retornando `result` com a verificação dos divisores de 2, 4 e 6 e `conclusion`: *"Entre as alternativas numéricas (2, 4, 6), apenas o número 2 é primo, pois admite exatamente dois divisores positivos distintos (1 e 2), enquanto 4 (divisível por 2) e 6 (divisíveis por 2 e 3) são compostos."*

### 2. Verificação local da tarefa inteira (`B.2`)

A etapa `B.2` executa em janela nova, retornando à temperatura da sessão, para auditar a resolução preliminar contra o **conjunto efetivo de critérios** da tarefa. Além dos critérios elaborados pelo planejador, o *harness* injeta deterministicamente dois critérios fixos reservados:
- **`<task_id>-TECH` (em toda tarefa):** exige validade técnica obrigatória compatível com o objetivo da tarefa — premissas fornecidas ou justificadas sem tratar hipóteses como fatos, preservação de referentes/unidades/condições, aplicabilidade do método, verificação real da relação decisiva (além da mera presença de explicação ou plausibilidade), consistência entre cálculo, texto e conclusão e simetria de suporte entre candidatos comparados;
- **`<task_id>-REV` (em tarefas revisoras criadas por `C.2`):** exige que cada resultado sob investigação receba exatamente um veredito (`confirmed` ou `superseded`) efetivamente demonstrado pela investigação, vedando substituições motivadas apenas por recência ou reformulação.

Diferentemente da versão inicial do método, `B.2` recebe explicitamente a identificação, o título e a descrição da tarefa (para enquadramento do escopo), além da seção `## Key Learnings` (apenas como referência para conferência de dados, nunca como critério de aceite):

$$\text{\textit{Tarefa (ID, Título, Descrição)}} + \text{\textit{Resultado Preliminar B}} + \text{\textit{Critérios Efetivos}} + [\text{\textit{Proposta de Revisão}}] + \text{\textit{Aprendizados Pontuais}} + \text{\textit{Template B.2}} \longrightarrow \text{\textit{Decisão (Aprovado / Reprovado)}}$$

A aprovação exige o atendimento simultâneo de **todos** os critérios efetivos; uma resposta que satisfaça formalmente os critérios planejados pode ser reprovada exclusivamente por `<id>-TECH`. Os critérios `-TECH` e `-REV` são avaliados de modo independente. Caso algum critério falhe, `B.2` aponta a falha concreta e o que investigar sem fornecer a solução corrigida, e o fluxo abre nova tentativa de `B.1` em janela nova (`temperature = 1,0`) até o limite de cinco tentativas (`max_task_attempts = 5`). Esgotadas as cinco tentativas sem aprovação, o *harness* interrompe a sessão em política *fail-closed*.

> **Exemplo (`B.2` — Tarefa 2, cenário de reprovação e recuperação):** Suponha que na Tentativa 1 de `T2` (*identificar números pares*), o modelo antecipe a resposta final afirmando que *"como apenas 2 é primo e não é maior que 2, a resposta é D"*. Em janela isolada, `B.2` marca atendidos os critérios de identificação de pares e `T2-TECH` quanto à paridade, mas reprova os critérios de restrição de escopo (`decision = reproved`). O orquestrador abre então uma **nova janela** para a Tentativa 2 de `B.1`, injeta o bloco `<previous_attempts>` com a Tentativa 1 e o veredito de `B.2`, e eleva a temperatura para `1,0`. O modelo refaz `T2` restrito à divisibilidade por 2 (`[2, 4, 6]`), submetido a nova chamada de `B.2` (na temperatura base), que agora aprova todos os critérios, incluindo `T2-TECH`.

### 3. Armazenamento estruturado e livro de resultados (`B.3`)

Uma vez aprovada a tarefa em `B.2`, a etapa `B.3` persiste deterministicamente o resultado aprovado — descartando todas as tentativas reprovadas do conjunto vigente — no **Livro de Resultados (`ResultsLedger`)**, sem chamada adicional ao LLM:

$$\text{\textit{Resposta Aprovada}} + [\text{\textit{Vereditos de Revisão Aprovados}}] \longrightarrow \text{\textit{ResultsLedger}} + \text{\textit{Sincronização de LearningsMemory}}$$

Diferentemente de um dicionário passivo, o `ResultsLedger` gerencia uma máquina de estados por tarefa composta por três estados: **`CURRENT`** (vigente), **`SUPERSEDED`** (substituído sem exclusão do histórico auditável) e **`AWAITING_REVALIDATION`** (suspenso aguardando revalidação). Quando a tarefa aprovada é revisora e traz vereditos homologados em `<id>-REV`, `B.3` aplica os vereditos **atomicamente**: resultados marcados como `superseded` deixam o estado vigente e todos os seus dependentes transitivos declarados via `depends_on` transitam para `AWAITING_REVALIDATION`; resultados marcados como `confirmed` permanecem ou são restaurados ao estado vigente, sendo registrados no histórico de confirmações para evitar reabertura indevida de conflitos em `C.1`. Simultaneamente, `B.3` invoca `withdraw()` ou `restore()` sobre a `LearningsMemory` para retirar fatos cujas fontes deixaram de ser vigentes (ou restaurá-los), preservando sempre as notas de `[Question]` oriundas de `A.4`.

### 4. Extração de aprendizados pontuais (`B.4`)

Imediatamente após `B.3`, a etapa `B.4` executa em **janela própria e isolada** — sem herdar a conversa bruta de `B.1` — recebendo como entradas delimitadas a descrição da tarefa, o resultado aprovado (`<approved_result>`), o histórico estruturado das tentativas e vereditos (`<task_history>`) e os aprendizados já registrados (para evitar redundância):

$$\text{\textit{Tarefa}} + \text{\textit{Resultado Aprovado}} + \text{\textit{Histórico da Tarefa}} + \text{\textit{Aprendizados Já Registrados}} + \text{\textit{Template B.4}} \longrightarrow \text{\textit{Novos Aprendizados Pontuais [Task Tx]}}$$

Cada aprendizado extraído deve registrar um resultado parcial novo da tarefa aprovada em uma única frase contendo dois elementos: o **fato compacto** (nomeando explicitamente objeto, grandeza, valor, unidade, sinal, condições ou caráter aproximado) seguido de uma **breve explicação** da propriedade ou justificativa que o sustenta. Valores refutados em tentativas anteriores, instruções, critérios de aceite e relatos procedimentais são proibidos. Caso a tarefa restabeleça independentemente um fato já presente na memória, `B.4` pode emiti-lo para que `LearningsMemory` anexe a nova fonte de procedência; repetições literais (normalizadas apenas por espaços, preservando diferenciação entre maiúsculas e minúsculas para símbolos científicos) são deduplicadas programaticamente.

> **Exemplo (`B.4` — Tarefa 1):** Após a aprovação de `T1`, `B.4` extrai um único fato novo autossuficiente (sem repetir definições triviais nem antecipar tarefas futuras):
> - `[Task T1] Entre (2, 4, 6), somente o número 2 é primo, pois 4 e 6 possuem divisores próprios além de 1 e si mesmos.`
> Ao concluir `T2`, `T3` e `T4`, cada execução acrescenta apenas seu respectivo fato novo (`[Task T2] Todos os números (2, 4, 6) são pares...`; `[Task T3] Entre (2, 4, 6), somente 4 e 6 são estritamente maiores que 2...`; `[Task T4] A interseção {2} ∩ {2, 4, 6} ∩ {4, 6} é vazia, correspondendo à alternativa D.`), que passa a compor a seção `## Key Learnings` das etapas seguintes.

Encerrada `B.4`, o orquestrador verifica programaticamente a existência de tarefas pendentes na fila. Havendo tarefas restantes, inicia-se novo ciclo em `B.1` com *Fresh Context*; esgotada a fila, o fluxo avança para a Fase C.

---

## C. Criação da Resposta Final (Etapas C.1 a C.3)

A terceira macrofase verifica a suficiência e a consistência global dos resultados vigentes, aciona investigações ou revisões corretivas quando necessário e sintetiza a resposta final de forma auditável.

### 1. Verificação global de suficiência e consistência (`C.1`)

A etapa `C.1` reúne exclusivamente os resultados em estado `CURRENT` no `ResultsLedger`, o registro de revisões aplicadas e confirmadas (`result_revisions`), os critérios gerais de `A.1` e a seção `## Key Learnings` (fornecida apenas como referência, sendo vedado contá-la como cobertura de critério):

$$\text{\textit{Resultados Vigentes}} + \text{\textit{Registro de Revisões}} + \text{\textit{Critérios Gerais (A.1)}} + \text{\textit{Aprendizados Pontuais (Ref.)}} + \text{\textit{Template C.1}} \longrightarrow \text{\textit{Decisão Global (Aprovado / Reprovado)}}$$

O papel de `C.1` é duplo: verificar se o conteúdo vigente permite construir integralmente a resposta solicitada (separando lacunas reais de conteúdo de aspectos meramente de formatação delegados a `C.3`) e auditar a **consistência da união** entre os resultados das diferentes tarefas, apontando contradições sobre o mesmo objeto, erros identificáveis sob uma seleção, igualdades falsas ou vínculos de identificador ausentes. Ao aprovar, o *harness* gera um *snapshot* imutável (`GlobalApproval`) contendo exatamente os resultados vigentes e aprendizados avaliados naquela chamada; ao reprovar, aciona `C.2` com o diagnóstico das pendências.

### 2. Planejamento adicional e revisão corretiva (`C.2`)

Quando `C.1` reprova o conjunto vigente, a etapa `C.2` gera tarefas complementares ou **tarefas revisoras** destinadas a sanar as lacunas ou contradições apontadas. Para evitar explosão de contexto e preservar fidelidade ao pedido original, `C.2` recebe a pergunta original (`user_question`), os critérios gerais não atendidos, o *feedback* textual de `C.1` (`global_verification_feedback`), resumos compactos dos resultados armazenados (`statement` + `conclusion`, e não a resolução integral), o registro de revisões (incluindo conclusões em estado `AWAITING_REVALIDATION`) e a área `## Key Learnings`:

$$\text{\textit{Pergunta Original}} + \text{\textit{Critérios Não Atendidos}} + \text{\textit{Feedback C.1}} + \text{\textit{Resumos do ResultsLedger}} + \text{\textit{Registro de Revisões}} + \text{\textit{Aprendizados Pontuais}} + \text{\textit{Template C.2}} \longrightarrow \text{\textit{Novas Tarefas / Tarefas Revisoras}}$$

Além de criar novas tarefas com `depends_on`, `C.2` pode declarar o campo estruturado `review: {task_ids, reason}` para submeter resultados já aprovados a investigação corretiva em `B.1`/`B.2` sem decidir antecipadamente qual conclusão está errada. As novas tarefas retornam à fila da Fase B (sujeitas aos limites globais de no máximo duas rodadas de `C.2` e doze tarefas por sessão), após o que o fluxo retorna obrigatoriamente a `C.1`.

### 3. Construção fiel da resposta final (`C.3`)

Aprovado o conjunto em `C.1`, a etapa `C.3` sintetiza a resposta final a partir do *snapshot* imutável `GlobalApproval` — verificado programaticamente via `approval.ensure_current()` para garantir que nenhuma mutação ocorreu após a aprovação global —, dos critérios gerais de `A.1` e da área `## Key Learnings`, utilizada estritamente para conferência literal de identificadores e alternativas do enunciado:

$$\text{\textit{Snapshot GlobalApproval}} + \text{\textit{Critérios Gerais (A.1)}} + \text{\textit{Aprendizados Pontuais (Conf. Literal)}} + \text{\textit{Template C.3}} \longrightarrow \text{\textit{Resposta Final}}$$

O `Template C.3` veda qualquer novo raciocínio analítico e incorpora um **checklist interno de fidelidade em sete pontos** (*Fidelity check before answering*), instruindo o modelo a verificar, na própria geração: (1) cobertura de cada parte do pedido sobre conteúdo aprovado; (2) preservação de sentido, sinais, unidades, condições e qualificadores; (3) distinção entre resultado calculado e escolha aprovada por aproximação ou melhor ajuste; (4) pareamento literal correto de identificadores frente às notas do enunciado; (5) fronteira entre pareamento literal e seleção analítica (proibindo escolhas novas); (6) coerência entre eventual justificativa e conclusão; e (7) conferência final de todo identificador escrito, inclusive na linha marcadora exigida pelo usuário ou *benchmark*.

> **Exemplo (`C.3`):** Com `T1`–`T4` aprovadas em `C.1`, o *snapshot* estabelece que a interseção é vazia e corresponde à opção de negação das anteriores; conferindo o identificador literal `[Question] D) Nenhuma das anteriores`, `C.3` apresenta **D) Nenhuma das anteriores** (ou, sob protocolo de *benchmark*, a linha final padronizada `RESPOSTA_FINAL: D`), concluindo a sessão sem mencionar etapas internas do *harness*.
