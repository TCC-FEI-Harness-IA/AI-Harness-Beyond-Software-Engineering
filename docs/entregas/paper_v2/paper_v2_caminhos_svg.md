# Sistemas Compostos de IA: Otimização de Respostas em Benchmarks Objetivos Através de uma Arquitetura Híbrida de Inferência e Validação com Multi-Agentes, Ferramentas e Orquestração Cognitiva



## Resumo

Os *Large Language Models* (*LLMs*)[1] têm, há algum tempo, deixado de ser apenas modelos voltados à geração de texto, consolidando-se como softwares e ferramentas completas. Essa evolução amplia significativamente seu escopo de aplicação, viabilizando funcionalidades como “pensamento prolongado”, acesso à internet e até mesmo suporte ao desenvolvimento de software por meio de interfaces especializadas, frequentemente referidas como *harnesses*, como CLIs — a exemplo de *Cloud Code*[2] (Anthropic), *Codex*[3] (OpenAI) e *OpenCLI*[4] (Open Source) — e *Integrated Development Environment* (IDEs), como *Cursor* e *Windsurf*. Em comum, essas soluções utilizam técnicas já consolidadas na literatura, muitas delas conhecidas há anos, como o princípio de “dividir para conquistar”, além de releituras dessas abordagens, com o objetivo de aproximar os resultados gerados do que é esperado, seja na construção de artefatos mais complexos ou na produção de respostas textuais mais precisas e alinhadas ao usuário. Nesse contexto, este estudo propõe a construção e análise desse conjunto de mecanismos e ferramentas que operam “ao redor” dos modelos de LLM, buscando verificar, na prática, se essas estratégias realmente melhoram a qualidade das respostas geradas. Para isso, serão utilizados como benchmark conjuntos de questões de múltipla escolha que abrangem diferentes áreas do conhecimento, como história, matemática, lógica, filosofia e relações públicas, desde níveis básicos de escolaridade até tópicos avançados em nível de doutorado (PhD).

## Palavras-chave
- Esperar ate o fim do desenvolvimento do glossario, e deposi colocar aqui

## Introdução

Os modelos de linguagem de grande porte (*Large Language Models* — *LLMs*)[1] deixaram de ser meramente geradores de texto e hoje funcionam como plataformas compostas por camadas de processamento, coordenação e ferramentas auxiliares. Essa transição viabiliza capacidades como raciocínio em múltiplas etapas, orquestração de subagentes e uso de ferramentas externas, porém também revela limitações estruturais: nem sempre a melhoria observada no comportamento final advém apenas do modelo base, mas das arquiteturas que organizam e abstraem o processo de inferência.

Este trabalho parte de dois problemas centrais observados na prática e documentados na literatura: (1) a aparente discordância entre respostas iniciais e respostas revisadas por um mesmo modelo — uma sensação comum em interações com modelos mais antigos (por exemplo, no período de popularização do GPT-3.5) de que perguntas de confirmação como “Tem certeza?”, “revise sua resposta” ou mesmo o simples apontamento de erro (“você errou”) induziam o modelo a corrigir-se —, e (2) a forma como fluxos de pensamento (prompting encadeado, agentes e pipelines) são atualmente implementados, incluindo suas fragilidades frente ao crescimento do contexto.

O primeiro problema decorre do fato de que, em tarefas não-triviais, a resposta “de primeira” tende a ser apenas uma primeira tentativa, sujeita a erros e omissões, que pode ser significativamente aprimorada quando a inferência é estruturada em fases explícitas e curtas, com feedback intermediário (muitas vezes com quebra ou reinicialização parcial do contexto entre etapas). Trabalhos como *Chain-of-Thought*[5] e *Tree of Thoughts*[9] mostram ganhos ao induzir o modelo a produzir e avaliar passos intermediários; *ReAct*[6] evidencia a utilidade de alternar raciocínio e ações/observações; e linhas mais diretamente iterativas, como *Reflexion*[7] (reflexão após julgamento externo) e abordagens de *Self-Debugging*[8] (correção guiada por testes), demonstram que ciclos de tentativa–avaliação–revisão podem elevar a taxa de acerto ao transformar “repetir a pergunta” em um mecanismo sistemático de melhoria. Em paralelo, métodos de decomposição e planejamento — como *Least-to-Most Prompting*[10], *Decomposed Prompting*[11] e *Plan-and-Solve Prompting*[12] — reforçam empiricamente que quebrar objetivos complexos em subtarefas, separar planejamento de execução e limitar o escopo contextual de cada passo reduz erros de lógica e omissões de etapas, especialmente quando combinado com verificação automática. Assim, a melhoria não se explica apenas por “mais tokens” ou por uma chamada mais longa, mas pelo desenho de um pipeline que controla o que entra no contexto, quando o modelo planeja, e como a resposta é validada e reescrita.

O segundo problema refere-se às práticas correntes de “thinking” em LLMs e às limitações impostas por janelas de contexto longas. Em arquiteturas populares de agentes, como *ReAct*[6] (*Synergizing Reasoning and Acting*) já mencionado, o modelo tende a operar acumulando em uma única janela um histórico crescente de raciocínios, ações e observações — um desenho que facilita o encadeamento narrativo do processo, mas que também amplia o risco de degradação conforme o volume de contexto aumenta. Esse tipo de limitação é consistente com evidências empíricas sobre o uso de contextos longos: em “*Lost in the Middle*”[13] (Liu et al.), por exemplo, observa-se degradação de desempenho em cenários nos quais o modelo precisa recuperar e utilizar informações relevantes em sequências extensas, especialmente quando esses trechos ficam “perdidos” no meio do contexto. Na prática, a comunidade de engenharia costuma descrever esse acúmulo progressivo e suas consequências como “esgotamento de contexto”, “compactação” e “context rot”: à medida que o histórico cresce, parte do conteúdo relevante perde saliência, compete por atenção com ruído e pode ser “diluída” por resumos implícitos, levando a omissões, inconsistências e aumento de alucinações.

Frente a essas propostas, adotamos como referência prática a implementação do *Ralph Wiggum Loop* popularizada por Geoffrey Huntley no contexto de desenvolvimento de software, na qual um agente é conduzido por um ciclo rígido de execução e verificação para produzir artefatos corretos (p. ex., código) sob restrições operacionais claras. O objetivo deste trabalho é adaptar essa arquitetura — originalmente aplicada a tarefas de engenharia de software — para investigar se os mesmos princípios melhoram a resolução de questões objetivas em benchmarks de múltipla escolha. Em termos gerais, o *Ralph Wiggum Loop* pode ser entendido como um pipeline em que (i) ocorre uma quebra inicial do objetivo em subtarefas e fases, e (ii) cada fase é executada de maneira isolada e “stateless”, isto é, sem carregar diretamente o histórico completo da fase anterior: em vez de continuidade conversacional, o sistema preserva apenas artefatos controlados (como instruções, respostas intermediárias ou resultados de validação) e reinicializa o contexto a cada iteração (“*Fresh Context*”). Embora o nome e o formato operacional sejam recentes, a lógica do loop se apoia em linhas acadêmicas já discutidas — decomposição (*Least-to-Most*[10]; *Decomposed Prompting*[11]), separação entre planejamento e execução (*Plan-and-Solve*[12]) e ciclos de reflexão/autodepuração guiados por avaliação externa (*Reflexion*[7]; *Self-Debugging*[8]) — oferecendo um arcabouço pragmático para aplicar esses achados em orquestrações reproduzíveis.

Neste trabalho, adotamos a hipótese de que a qualidade objetiva de saídas em tarefas de múltipla escolha depende tanto do LLM quanto do “*Harness*” que governa seu uso — isto é, do ferramental e do conjunto de políticas de decomposição, verificação e orquestração aplicadas entre prompt inicial e resposta final. Para testar essa hipótese, buscamos medir o quanto esse *Harness* melhora resultados frente a chamadas simples, comparando cinco modelos (MODELO_1, MODELO_2, MODELO_3, MODELO_4 e MODELO_5) escolhidos para cobrir uma progressão de complexidade — de modelos mais simples, com menos parâmetros, até incluir ao menos um modelo considerado “moderno”. Para cada um desses modelos, comparamos duas configurações: (i) uma inferência “linear”, por meio de uma única requisição direta ao modelo, e (ii) a mesma inferência mediada pelo nosso *Harness* (um pipeline estruturado inspirado no *Ralph Wiggum Loop*, com validações intermediárias e possibilidade de uso de ferramentas externas quando necessário). A comparação de desempenho é realizada por meio de benchmarks construídos sobre as bases GPQA e MMLU, que fornecem questões de múltipla escolha com alternativas e gabaritos; nesses conjuntos, a métrica primária adotada é a acurácia obtida pela correspondência entre a alternativa selecionada pelo sistema e o gabarito.




## METODOLOGIA

### Análise macro do processo de *thinking*

O diagrama a seguir apresenta o fluxo macro do pipeline de *thinking* proposto neste trabalho, oferecendo uma visão consolidada de todas as fases que o compõem.

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/fluxo_macro}
\end{figure}
```

O pipeline é iniciado a partir de um *prompt* de entrada fornecido pelo usuário. A partir desse insumo, o processo percorre as seguintes etapas em sequência: (i) definição dos critérios de aceitação da resposta final e do formato de saída esperado; (ii) decomposição do problema em tarefas atômicas e independentes; (iii) resolução iterativa de cada tarefa por meio de um ciclo de execução e verificação inspirado no *Ralph Wiggum Loop*; (iv) avaliação dos resultados consolidados frente aos critérios de aceitação estabelecidos; e, por fim, (v) composição da resposta final ao usuário. Caso a avaliação dos critérios indique que nem todos foram atendidos, o pipeline não descarta o trabalho realizado — em vez disso, cria um plano adicional complementar voltado exclusivamente para cobrir as lacunas identificadas, retornando à fase de resolução de tarefas. Esse comportamento confere ao sistema um caráter iterativo e convergente.

Um aspecto central da arquitetura é a separação deliberada entre as fases de execução: cada etapa opera de forma *stateless* em relação às demais, no sentido de que não carrega diretamente o histórico de raciocínio das fases anteriores. Em vez disso, o sistema preserva apenas artefatos estruturados — em especial os arquivos `planning.json` e `tasks_results.json` — que funcionam como memória persistente e controlada entre as etapas. Essa decisão de projeto tem dois objetivos complementares: por um lado, mitigar os problemas de degradação discutidos na Introdução, nos quais o crescimento progressivo do contexto leva ao fenômeno frequentemente referido como *context rot* — o acúmulo de informação irrelevante, resumos implícitos e ruído que diluem o conteúdo útil e prejudicam a qualidade das respostas —; por outro, garantir que cada chamada ao LLM opere com o menor contexto possível, reduzindo o risco de que informações e raciocínios de tarefas anteriores contaminem a execução da tarefa corrente, introduzindo inconsistências ou "lixo de contexto" nas respostas geradas.

---

### Análise micro das fases

A seguir, cada fase do pipeline é detalhada individualmente. Para cada fase, são descritos: os agentes de LLM envolvidos, os dados de entrada e saída, e o fluxo de controle interno. Essa granularidade tem o objetivo de tornar o processo inteiramente replicável por pesquisadores externos.

#### Agentes de LLM

Neste trabalho, adota-se uma definição restrita de *agente*: trata-se de um componente composto exclusivamente por um *prompt* pré-definido e uma chamada ao modelo de linguagem (*LLM_CALL*). Diferentemente de arquiteturas que atribuem a agentes acesso a ferramentas externas, chamadas a APIs, servidores MCP ou capacidades de navegação, os agentes aqui descritos operam de forma isolada — recebem um contexto de entrada estruturado, processam via LLM e retornam uma saída textual ou estruturada em JSON. Essa restrição é intencional: ao eliminar dependências externas, torna-se possível avaliar de forma mais direta o impacto da orquestração e do *prompting* sobre a qualidade das respostas, isolando as variáveis de interesse do estudo.

Todos os *prompts* de agentes são redigidos em inglês. Estudos como o de Huang et al. [14] e Shi et al. [15] mostram que modelos de linguagem multilíngues tendem a produzir resultados de maior qualidade quando instruídos no idioma em que foram mais amplamente treinados — predominantemente o inglês —, independentemente do idioma da questão de entrada. Qin et al. [16] reforçam esse achado ao demonstrar que a combinação de *prompting* em inglês com raciocínio *zero-shot* em cadeia produz ganhos consistentes mesmo em línguas de menor representação nos dados de treinamento. A adoção do inglês como idioma padrão dos *prompts* de agentes visa, portanto, maximizar a qualidade do raciocínio interno do modelo, sem prejuízo ao idioma da resposta entregue ao usuário — que é determinado separadamente, conforme descrito na seção seguinte.

Adicionalmente, todos os *prompts* são construídos utilizando a sintaxe *Markdown*, com delimitadores explícitos de seção para separar instruções gerais, contexto de entrada e especificações de saída. Estudos como o de He et al. [17] e Liu et al. [18] mostram que a formatação do *prompt* afeta de forma mensurável o desempenho dos modelos, e que otimizações conjuntas de conteúdo e formato produzem ganhos adicionais sobre a otimização exclusiva do conteúdo textual. A adoção de *Markdown* visa, portanto, tornar delimitadores, hierarquias e restrições mais salientes durante a inferência, contribuindo para respostas mais consistentes com as instruções fornecidas.

---

#### Definição dos critérios de aceite da resposta final

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/definicao_criterios_de_aceite_da_resposta_final}
\end{figure}
```

Esta fase é responsável por transformar o *prompt* bruto do usuário em dois artefatos que guiarão todo o processo posterior: (i) uma lista de critérios de aceitação que a resposta final deverá satisfazer, e (ii) uma especificação do formato de saída esperado. Para isso, dois agentes são acionados em sequência a partir da mesma entrada.

O `acceptance_criteria_agent` recebe o *prompt* de entrada do usuário e é responsável por identificar e listar, de forma explícita, os critérios objetivos e verificáveis que uma resposta satisfatória deve cumprir. Em seguida, o `expected_output_format_agent` analisa o mesmo *prompt*, buscando por indicações explícitas de formato de saída — como "retorne somente a alternativa correta", "responda em JSON" ou "elabore uma justificativa". Caso nenhuma indicação seja encontrada, o agente infere o formato mais adequado ao tipo de tarefa: para questões de múltipla escolha, o padrão é "retornar somente a letra da alternativa correta, sem explicações adicionais"; para questões abertas, "texto corrido em formato Markdown". O idioma da resposta final é tratado como parte integrante do formato de saída: se o usuário o especificou explicitamente, essa instrução é acatada; caso contrário, o agente infere o idioma a partir do idioma utilizado na entrada e o registra como especificação. Quando exemplos de saída são fornecidos pelo usuário, estes são incorporados ao campo correspondente.

Os resultados dessas duas chamadas são então consolidados em um arquivo JSON denominado `planning.json`, que servirá de artefato central de memória estruturada para todas as fases subsequentes. A estrutura do `planning.json` é inspirada no `prd.json` do *Ralph Wiggum Loop* original, porém estendida para incorporar as informações de critérios de aceitação e formato de saída — dimensões ausentes no contexto original de desenvolvimento de software, mas essenciais para a avaliação de respostas em benchmarks de múltipla escolha. O formato inicial desse arquivo é o seguinte:

```json
{
    "general_infos": {
        "acceptance_criteria": [],
        "expected_output_format": {
            "format": "",
            "response_language": ""
        }
    },
    "tasks": []
}
```

A título de exemplo, um `planning.json` preenchido para uma questão de múltipla escolha em português teria o seguinte aspecto:

```json
{
    "general_infos": {
        "acceptance_criteria": [
            "A resposta deve identificar a alternativa correta",
            "A resposta deve ser objetiva, sem explicações adicionais"
        ],
        "expected_output_format": {
            "format": "Retornar somente a letra da alternativa correta (A, B, C, D ou E), sem explicações adicionais.",
            "response_language": "Portuguese"
        }
    },
    "tasks": []
}
```

O campo `tasks` é inicialmente vazio e será preenchido pela fase seguinte. A separação entre `general_infos` e `tasks` é proposital: as informações gerais são invariantes ao longo de todo o pipeline, enquanto as tarefas podem ser adicionadas iterativamente por planos complementares.

##### Prompts dos agentes

**`acceptance_criteria_agent`**

```markdown
# Agent: Acceptance Criteria Definer

## Goal
You are a specialized agent that analyzes user requests and derives clear, objective, and
verifiable acceptance criteria for the expected final response.

## Instructions
Based on the user prompt provided below, identify and list all criteria that a satisfactory
response must fulfill.

### Rules
- Each criterion must be atomic and independently verifiable
- Criteria must be derived from what the user requested, not from external assumptions
- Express each criterion as a positive statement (e.g., "The response must contain X")
- List between 2 and 6 criteria

## Input

### User prompt
{{USER_PROMPT}}

## Expected output
Return exclusively a JSON array with the acceptance criteria, with no additional text,
no wrapping code blocks, and no explanations.

### Empty example
    ```json
    []
    ```

### Populated example
    ```json
    [
        "The response must identify the correct answer option",
        "The response must be concise and free of unnecessary explanations"
    ]
    ```
```

**`expected_output_format_agent`**

```markdown
# Agent: Output Format Definer

## Goal
You are a specialized agent that identifies or infers the expected output format and response
language for a user's request.

## Instructions
Analyze the user prompt below and determine the appropriate output format and response
language for the final answer.

### Rules
- If the user explicitly specified a format (JSON, Markdown, plain text, single option, etc.),
  use that format
- If the user provided output examples, include them in the format description
- If no format was specified, infer the most appropriate format for the task type:
  - For multiple-choice questions: "Return only the letter of the correct answer option,
    with no additional explanation"
  - For open-ended questions: "Continuous text in Markdown format"
- For the response language:
  - If the user explicitly specified a language, use it
  - If not, infer the language from the user's input and use that same language

## Input

### User prompt
{{USER_PROMPT}}

## Expected output
Return exclusively a JSON object in the following format, with no additional text,
no wrapping code blocks, and no explanations.

### Empty example
    ```json
    {
        "format": "",
        "response_language": ""
    }
    ```

### Populated example
    ```json
    {
        "format": "Return only the letter of the correct answer option (A, B, C, D or E), with no additional explanation.",
        "response_language": "Portuguese"
    }
    ```
```

---

#### Quebra de Tasks Independentes

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/quebra_de_tasks_independentes}
\end{figure}
```

Esta fase é, em termos de responsabilidade lógica, a mais crítica de todo o pipeline: é aqui que se implementa o princípio central do *Ralph Wiggum Loop* — a decomposição do problema em unidades mínimas e independentes de execução. O agente `atomic_tasks_planner_agent` recebe como entrada o *prompt* do usuário e o campo `general_infos` do `planning.json` gerado na fase anterior, e a partir disso constrói um plano de tarefas atômicas.

O conceito de *atomicidade* empregado é preciso: uma tarefa é considerada atômica quando representa a menor unidade de trabalho possível e pode ser executada e avaliada de forma completamente independente das demais tarefas do plano, sem necessidade de acessar ou reutilizar os resultados de outras tarefas durante sua própria execução. Essa propriedade é fundamental para garantir o funcionamento correto do mecanismo de *fresh context* — se tarefas dependessem umas das outras durante a execução, seria necessário carregar contexto acumulado, o que re-introduziria os problemas de degradação que a arquitetura busca mitigar.

Após a geração do plano inicial, o agente `atomic_tasks_revisor_agent` é acionado para verificar se todas as tarefas propostas satisfazem o critério de independência, retornando um JSON com um campo booleano de aprovação e uma justificativa. Se problemas forem identificados, o agente `atomic_tasks_rewriter_agent` — que incorpora em seu *prompt* todas as regras e restrições do planejador — é acionado para reescrever o plano com base na justificativa fornecida. Esse ciclo de revisão repete-se até que o revisor valide o plano, garantindo que apenas tarefas verdadeiramente independentes avancem para a fase de execução.

Cada tarefa do plano é representada no `planning.json` no seguinte formato:

```json
{
    "general_infos": {
        "acceptance_criteria": [],
        "expected_output_format": {
            "format": "",
            "response_language": ""
        }
    },
    "tasks": [
        {
            "id": "",
            "title": "",
            "description": "",
            "acceptance_criteria": [],
            "pass_phase": false
        }
    ]
}
```

A título de exemplo, um `planning.json` com tarefas preenchidas teria o seguinte aspecto:

```json
{
    "general_infos": {
        "acceptance_criteria": [
            "A resposta deve identificar a alternativa correta",
            "A resposta deve ser objetiva, sem explicações adicionais"
        ],
        "expected_output_format": {
            "format": "Retornar somente a letra da alternativa correta (A, B, C, D ou E), sem explicações adicionais.",
            "response_language": "Portuguese"
        }
    },
    "tasks": [
        {
            "id": "1",
            "title": "Identify the knowledge domain and key concepts",
            "description": "Read the following question and identify: (1) its primary knowledge domain, and (2) the key concepts required to answer it. Question: 'Which of the following best describes the concept of entropy in thermodynamics? A) A measure of disorder or randomness in a system. B) The total kinetic energy of all molecules. C) The energy available to do work. D) The rate of heat transfer between systems.'",
            "acceptance_criteria": [
                "The response must identify the primary domain",
                "The response must list the key concepts required to evaluate each answer option"
            ],
            "pass_phase": false
        },
        {
            "id": "2",
            "title": "Evaluate each answer option independently",
            "description": "Evaluate each of the four options below against the standard thermodynamic definition of entropy and determine whether each is correct or incorrect. Standard definition: entropy is a measure of the disorder or randomness of a system, related to the number of possible microscopic configurations. Options: A) A measure of disorder or randomness in a system. B) The total kinetic energy of all molecules. C) The energy available to do work. D) The rate of heat transfer between systems.",
            "acceptance_criteria": [
                "Each option must be individually assessed as correct or incorrect",
                "The assessment must include a brief justification for each option"
            ],
            "pass_phase": false
        }
    ]
}
```

O campo `pass_phase` é inicializado como `false` para todas as tarefas e atualizado para `true` ao final da execução bem-sucedida de cada uma, funcionando como marcador de progresso para o mecanismo de iteração descrito na seção seguinte.

##### Prompts dos agentes

**`atomic_tasks_planner_agent`**

```markdown
# Agent: Atomic Task Planner

## Goal
You are a specialized agent that decomposes complex problems into minimal, atomic, and
completely independent execution units.

## Core Concept: Atomicity and Independence
A task is **atomic** when it represents the smallest possible unit of work needed to
make progress toward solving the problem.
A task is **independent** when it can be executed and evaluated without requiring the
results of any other task in the plan.

### Independence Rule (CRITICAL)
Each task must be self-contained. This means:
- A task MUST NOT assume it will have access to the result of another task during its execution
- All context needed to solve the task must be present within the task's own description
- If information that would be produced by another task is needed, it must be re-specified
  directly in this task's description

## Input

### User prompt
{{USER_PROMPT}}

### General information (planning.json > general_infos)
{{GENERAL_INFOS}}

## Expected output
Return exclusively a JSON array with the tasks, with no additional text, no wrapping code
blocks, and no explanations.

### Empty example
    ```json
    []
    ```

### Populated example
    ```json
    [
        {
            "id": "1",
            "title": "Identify the knowledge domain and key concepts",
            "description": "Read the following question and identify: (1) its primary knowledge domain, and (2) the key concepts required to answer it. Question: 'Which of the following best describes entropy in thermodynamics?'",
            "acceptance_criteria": [
                "The response must identify a single primary domain",
                "The response must list the key concepts required to evaluate the answer options"
            ],
            "pass_phase": false
        }
    ]
    ```
```

**`atomic_tasks_revisor_agent`**

```markdown
# Agent: Atomic Task Reviewer

## Goal
You are a specialized agent that reviews task plans to ensure all tasks are truly independent
and atomic.

## Review Criterion
Check whether any task in the plan, in order to be executed, would need to consult or reuse
the result of another task in the same plan. If so, the plan is incorrect and must be rejected.

## Input

### Task plan to review
{{TASKS_PLAN}}

## Expected output
Return exclusively a JSON object in the following format, with no additional text, no wrapping
code blocks, and no explanations.

### Empty example
    ```json
    {
        "approved": null,
        "justification": ""
    }
    ```

### Populated example — approval
    ```json
    {
        "approved": true,
        "justification": "All tasks are independent and atomic."
    }
    ```

### Populated example — rejection
    ```json
    {
        "approved": false,
        "justification": "Task 2 ('Calculate the average of the results') depends on the output of task 1 ('Collect the data'). The description of task 2 must include the necessary data directly, or both tasks must be merged into a single self-contained task."
    }
    ```
```

**`atomic_tasks_rewriter_agent`**

```markdown
# Agent: Atomic Task Rewriter

## Goal
You are a specialized agent that corrects task plans with dependency issues between tasks,
rewriting them to ensure full atomicity and independence.

## Core Concept: Atomicity and Independence
A task is **atomic** when it represents the smallest possible unit of work.
A task is **independent** when it can be executed and evaluated without requiring the results
of any other task in the plan.

### Independence Rule (CRITICAL)
- A task MUST NOT assume it will have access to the result of another task during its execution
- All context needed must be present within the task's own description
- If information from another task is needed, it must be re-specified directly in this
  task's description

## Input

### Original task plan
{{TASKS_PLAN}}

### Rejection justification
{{REJECTION_JUSTIFICATION}}

### General information (planning.json > general_infos)
{{GENERAL_INFOS}}

## Instructions
Correct the task plan based on the rejection justification provided, ensuring all resulting
tasks are atomic and independent.

## Expected output
Return exclusively the corrected JSON array with the tasks, with no additional text, no
wrapping code blocks, and no explanations. Maintain the same format as the original plan.

### Empty example
    ```json
    []
    ```

### Populated example
    ```json
    [
        {
            "id": "1",
            "title": "Identify domain and evaluate all answer options",
            "description": "Read the following question, identify its primary knowledge domain, and evaluate each answer option independently. Standard definition of entropy: a measure of the disorder or randomness of a system. Question: 'Which of the following best describes entropy in thermodynamics? A) A measure of disorder. B) Total kinetic energy. C) Energy available to do work. D) Rate of heat transfer.'",
            "acceptance_criteria": [
                "The response must identify the primary domain",
                "Each answer option must be individually assessed as correct or incorrect with justification"
            ],
            "pass_phase": false
        }
    ]
    ```
```

---

#### Resolução das tarefas — Ralph Loop

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/resolucao_das_tarefas_ralph_loop}
\end{figure}
```

Esta fase implementa o núcleo iterativo do *Ralph Wiggum Loop* adaptado ao contexto deste trabalho. O processo inicia pela verificação do `planning.json`: enquanto existirem tarefas com `pass_phase: false`, o pipeline seleciona a próxima tarefa pendente e inicia um ciclo de tentativa–avaliação–revisão.

Cada iteração do ciclo consiste em: (i) uma chamada ao LLM contendo exclusivamente o conteúdo da tarefa atual — sem histórico acumulado de outras tarefas —, seguida de (ii) uma chamada ao agente `task_outcome_reviewer_agent`, que compara a resposta gerada com os `acceptance_criteria` da tarefa. O revisor retorna um JSON com um campo booleano de aprovação e uma justificativa. Se o revisor aprovar a resposta, ela é salva no arquivo `tasks_results.json` e o campo `pass_phase` da tarefa é atualizado para `true`. Se reprovar, a justificativa é incorporada à próxima chamada ao LLM, que recebe como contexto a última tentativa (prompt + resposta gerada) e a razão de não-aceitação — configurando um ciclo de refinamento guiado, análogo ao mecanismo de *Reflexion* [7] e *Self-Debugging* [8] discutidos na Introdução.

No que diz respeito à persistência dos resultados, adota-se uma adaptação do princípio original do *Ralph Wiggum Loop*, que preconiza que *"All memory lives in files and git — not the model"*. Como o presente trabalho aplica o pipeline a cenários distintos do desenvolvimento de software, o mecanismo de *commit* em repositório Git é substituído pelo arquivo `tasks_results.json`, que acumula exclusivamente as respostas finais aprovadas de cada tarefa — sem registrar histórico de raciocínio, tentativas anteriores ou qualquer metadado do ciclo iterativo. É importante destacar que nenhuma fase do pipeline possui acesso ao conteúdo desse arquivo durante a execução das tarefas: o `tasks_results.json` permanece opaco ao longo de toda a fase de resolução, sendo recuperado somente ao final do pipeline, na fase de criação da resposta final. Esse isolamento reforça o princípio *stateless* entre iterações — cada tarefa é executada com um contexto limpo (*fresh context*), sem visibilidade sobre o que foi produzido pelas tarefas anteriores.

Para mitigar o risco de *deadlock* — situação na qual o modelo entra em ciclo indefinido sem conseguir satisfazer os critérios de uma tarefa —, implementa-se um mecanismo de controle denominado *pânico*. Um contador `task_interactions` é incrementado a cada chamada ao LLM dentro do ciclo de uma tarefa. Quando esse contador atinge o valor de `max_iterations` (parâmetro configurável do pipeline), a fase encerra automaticamente e a resposta disponível no momento é salva no `tasks_results.json`, mesmo que os critérios não tenham sido plenamente atendidos. Esse mecanismo garante a terminação do processo em cenários adversos, impedindo que uma tarefa de difícil convergência bloqueie indefinidamente o pipeline.

##### Prompts dos agentes

**`task_outcome_reviewer_agent`**

```markdown
# Agent: Task Outcome Reviewer

## Goal
You are a specialized agent that evaluates whether the response generated for a task fully
satisfies its acceptance criteria.

## Instructions
Compare the provided response against the task's acceptance criteria. Evaluate each criterion
independently and determine whether all of them have been met.

## Input

### Task description
{{TASK_DESCRIPTION}}

### Task acceptance criteria
{{TASK_ACCEPTANCE_CRITERIA}}

### Generated response
{{TASK_RESPONSE}}

## Expected output
Return exclusively a JSON object in the following format, with no additional text, no wrapping
code blocks, and no explanations.

### Empty example
    ```json
    {
        "approved": null,
        "justification": ""
    }
    ```

### Populated example — approval
    ```json
    {
        "approved": true,
        "justification": "All acceptance criteria have been met."
    }
    ```

### Populated example — rejection
    ```json
    {
        "approved": false,
        "justification": "The criterion 'Identify the correct answer option' was not met: the response selected option B, but the analysis indicates the correct answer is C based on the thermodynamic definition of entropy. The criterion 'Be concise' was met."
    }
    ```
```

---

#### Avaliação dos critérios de aceitação

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/avaliacao_de_criterios_de_aceitacao}
\end{figure}
```

Ao término da resolução de todas as tarefas do plano, o pipeline consolida os resultados armazenados no `tasks_results.json` e os submete a uma avaliação global frente aos critérios de aceitação definidos em `general_infos.acceptance_criteria` do `planning.json`. Essa fase é executada pelo agente `final_response_acceptance_criteria_reviewer_agent`, que recebe ambos os artefatos como entrada.

A lógica é análoga à dos revisores de tarefa individual, porém operando em um nível de abstração superior: em vez de avaliar uma resposta pontual contra critérios locais de uma tarefa, o agente avalia se o conjunto total de resultados gerados fornece insumos suficientes para construir uma resposta final que atenda a todos os critérios globais. Dois fluxos de saída são possíveis a partir dessa avaliação: caso todos os critérios sejam considerados atendidos, o pipeline avança para a criação da resposta final; caso contrário, avança para a criação de um plano adicional complementar.

##### Prompts dos agentes

**`final_response_acceptance_criteria_reviewer_agent`**

```markdown
# Agent: Global Acceptance Criteria Reviewer

## Goal
You are a specialized agent that evaluates whether the set of task results generated throughout
the process contains sufficient information to build a final response that meets all global
acceptance criteria.

## Instructions
Analyze the task results and the global acceptance criteria. Determine whether, based on the
available information, it is possible to build a final response that fully satisfies all
criteria. Do not evaluate the quality of a potential final response — only assess whether
the necessary inputs are present.

## Input

### Global acceptance criteria (planning.json > general_infos > acceptance_criteria)
{{ACCEPTANCE_CRITERIA}}

### Task results (tasks_results.json)
{{TASKS_RESULTS}}

## Expected output
Return exclusively a JSON object in the following format, with no additional text, no wrapping
code blocks, and no explanations.

### Empty example
    ```json
    {
        "approved": null,
        "justification": ""
    }
    ```

### Populated example — approval
    ```json
    {
        "approved": true,
        "justification": "All global acceptance criteria can be met with the available results."
    }
    ```

### Populated example — gap identified
    ```json
    {
        "approved": false,
        "justification": "The criterion 'Present a comparative analysis between options A and C' cannot be met because none of the tasks produced a direct comparison between these two options. Additional information covering this specific comparison would need to be generated."
    }
    ```
```

---

#### Criação de plano complementar

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/criacao_de_plano_complementar}
\end{figure}
```

Quando a avaliação global indica que os critérios de aceitação não foram plenamente atendidos, o pipeline não retorna ao início — o que implicaria descartar e reprocessar etapas já concluídas. Em vez disso, adota-se uma estratégia de afunilamento progressivo: o agente `acceptance_gap_prompt_creator` analisa a justificativa retornada pelo revisor global e produz um novo *prompt* no estilo de entrada de usuário, descrevendo exclusivamente o que ainda precisa ser resolvido para cobrir as lacunas identificadas. Esse *prompt* é então submetido ao `atomic_tasks_planner_agent` — o mesmo agente da fase de Quebra de Tasks Independentes —, que gera um novo conjunto de tarefas complementares. Essas novas tarefas são concatenadas ao campo `tasks` do `planning.json` original, e o pipeline retorna à fase de Resolução das Tarefas para executá-las.

Esse mecanismo constitui, na prática, um segundo nível de loop que garante a convergência iterativa do pipeline: a cada ciclo, o conteúdo gerado aproxima-se do que é necessário para satisfazer todos os critérios de aceitação, sem desperdiçar o trabalho já realizado nas iterações anteriores. O reaproveitamento do `atomic_tasks_planner_agent` nesta fase não é acidental — ao reutilizar o mesmo agente, garante-se que as novas tarefas complementares seguem exatamente as mesmas regras de atomicidade e independência estabelecidas para o plano original.

##### Prompts dos agentes

**`acceptance_gap_prompt_creator`**

```markdown
# Agent: Acceptance Gap Prompt Creator

## Goal
You are a specialized agent that analyzes gaps between the results obtained and the unmet
acceptance criteria, generating a new user-style prompt that requests exclusively what is
still missing.

## Instructions
Based on the rejection justification provided by the global reviewer, create a prompt in the
style of a natural user request that clearly and objectively describes only what needs to be
generated to cover the identified gaps.

### Rules
- The generated prompt must read as a natural user request
- It must reference only what is missing, not what has already been produced
- It must be self-contained and must not reference internal pipeline artifacts
  (planning.json, tasks_results.json, etc.)
- It must be specific enough for the task planner to correctly decompose it into atomic tasks

## Input

### Original user prompt
{{ORIGINAL_USER_PROMPT}}

### Rejection justification
{{REJECTION_JUSTIFICATION}}

### Summary of available results
{{TASKS_RESULTS_SUMMARY}}

## Expected output
Return exclusively the text of the new prompt, with no JSON, no code blocks,
and no additional formatting.

### Populated example
Analyze the following multiple-choice question and provide a detailed comparison between
answer options A and C, explaining the key differences and which one better fits the
standard thermodynamic definition of entropy: "Which of the following best describes the
concept of entropy in thermodynamics? A) A measure of the disorder or randomness in a
system. B) The total kinetic energy of all molecules in a system. C) The energy available
to do work in a thermodynamic process. D) The rate at which heat is transferred between
two systems."
```

> **Nota:** O agente `atomic_tasks_planner_agent` utilizado nesta fase é idêntico ao descrito na seção "Quebra de Tasks Independentes". Consultar o *prompt* correspondente naquela seção.

---

#### Criação da resposta final

```latex
\begin{figure}[H]
  \centering
  \includesvg[width=0.50\textwidth]{diagrams/criacao_da_resposta_final}
\end{figure}
```

A fase de criação da resposta final assume que o `tasks_results.json` contém todos os insumos necessários para compor uma resposta que satisfaça integralmente os critérios de aceitação globais — premissa garantida pela fase de avaliação anterior. É nesta fase, e somente nesta, que o conteúdo do `tasks_results.json` é efetivamente recuperado e utilizado: o agente `final_response_composer_agent` recebe como entrada o arquivo completo de resultados, o campo `general_infos.expected_output_format` do `planning.json` e o *prompt* original do usuário, utilizando-os em conjunto para compor a resposta final no formato e idioma especificados. O retorno desse agente é a saída direta do pipeline ao usuário, encerrando o processo de *thinking*.

##### Prompts dos agentes

**`final_response_composer_agent`**

```markdown
# Agent: Final Response Composer

## Goal
You are a specialized agent that synthesizes partial results from multiple tasks into a
cohesive, complete final response strictly in the correct format and language expected
by the user.

## Instructions
Based on the task results and the specified output format, build the final response for
the user.

### Rules
- The response must strictly adhere to the specified output format, including the
  response language
- Do not mention the internal process (tasks, planning, decomposition, etc.)
- The response must be self-contained and understandable without any additional context
- For multiple-choice questions, return exclusively in the specified format, without
  unsolicited elaboration

## Input

### Original user prompt
{{USER_PROMPT}}

### Expected output format (planning.json > general_infos > expected_output_format)
{{EXPECTED_OUTPUT_FORMAT}}

### Task results (tasks_results.json)
{{TASKS_RESULTS}}

## Expected output
Return exclusively the final response in the specified format and language,
with no additional text.
```





## Glossario de termos

### Termos citados

[1] LLM - *Large Language Model*: modelo de inteligência artificial treinado em grandes volumes de texto para compreensão e geração de linguagem natural.
Link: https://en.wikipedia.org/wiki/Large_language_model

Ralph Wiggum Loop - *Todo*: adicionar explicação e os links para o blog do Huntey

“Harness” - *Todo*: adicionar explicação. Tb tem um estudo que fala sobnre isso em "https://arxiv.org/abs/2603.16744" (Nonstandard Errors in AI Agents)

### Ferramentas citadas

[2] Cloud Code - CLI para desenvolvimento assistido por IA, com integração a modelos da Anthropic.
Link: https://www.anthropic.com/

[3] Codex - modelo e ferramenta da OpenAI voltados à geração e compreensão de código.
Link: https://openai.com/

[4] OpenCLI - interface de linha de comando open source para integração com modelos de linguagem.
Link: https://opencli.ai/

## Referências (seleção de insumos utilizados)

[5] Chain-of-Thought prompting (ver notas em `docs/analises/vitor`).

[6] ReAct: Synergizing Reasoning and Acting (ver `docs/analises/vitor/notas_adicionais.md`).

[7] Reflexion: Language Agents with Verbal Reinforcement Learning (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[8] Teaching Large Language Models to Self-Debug (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[9] Tree of Thoughts (ver `docs/analises/vitor/notas_adicionais.md`).

[10] Least-to-Most Prompting (Zhou et al.) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[11] Decomposed Prompting — Khot et al. (2022) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[12] Plan-and-Solve Prompting — Wang et al. (2023) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[13] Lost in the Middle: How Language Models Use Long Contexts (Liu et al.) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[14] Beyond English: The Impact of Prompt Translation Strategies across Languages and Tasks in Multilingual LLMs (ver `docs/analises/vitor/dados_para_o_texto/ingles_em_promps.md`).

[15] Language Models are Multilingual Chain-of-Thought Reasoners (ver `docs/analises/vitor/dados_para_o_texto/ingles_em_promps.md`).

[16] Cross-lingual Prompting: Improving Zero-shot Chain-of-Thought Reasoning across Languages (ver `docs/analises/vitor/dados_para_o_texto/ingles_em_promps.md`).

[17] Does Prompt Formatting Have Any Impact on LLM Performance? (He et al.) (ver https://arxiv.org/abs/2411.10541).

[18] Beyond Prompt Content: Enhancing LLM Performance via Content-Format Integrated Prompt Optimization (Liu et al.) (ver https://arxiv.org/abs/2502.04295).
