

## Diretrizes gerais do projeto:
NOTAS GERAIS:

- Todos os agentes usados, devem ter seus prompts escritos no paper. Nos vamos mostrar o prompt de TODOS os agentes
- Explicar que para a escrita de promtps vamos usar MARKDOWN. Aqui pode ser legal colcoar alguma referencia de paper que mostre que promtps com markdown tem resultados melhores



## Analise macro do processo
- Aqui vai vir o desenho explicando o fluxo macro
- OQUE QUERO EXPLICAR AQUI:
    - Trazer somente um texto de apois para o desenho, que possui boa parte da logica

## Analise micro das fases
- OQUE QUERO EXPLICAR AQUI:
    - A seguir vai vir uma analise individual de cada parte relevante do fluxo.
    - É importante que cada uma das explicações dos "platos", seja autosuficiente. Aqui precisa ficxar muito claro de onde vem a informação de entrada da fase, e como vai ficar a informação de saida. Em geral, isso é, expecificar o formato do texto de saida, e se ele vai ser salvo em algum arquivo, ou ficar somente em memoria.


### Agentes de LLM
- OQUE QUERO EXPLICAR AQUI:
    - Quero dar um overview doque entendemos como agentes no paper:
        - Oque é um agente para esse paper.
            - No nosso caso, é somente um prompt pré definido, que vai servir como bases para "inputarmos" informações
            - No nosso caso, agentes NÃO possuem acesso a tools, mcps, nada do tipo, somente ao prompt pré definido
        - Como montamos um prompt:
            - Todos os prompts de agentes vão ser construidos usando Markdown e delimitadores claros de texto
            - Alguns estudos ja mostram que a maneira como formatamos e construimos um prompt pode afetar diretamente no resultado, e por isso usamos essa regra. Fontes de papers a incluir:
                - "Does Prompt Formatting Have Any Impact on LLM Performance?" Jia He, Mukund Rungta, David Koleczek, Arshdeep Sekhon, Franklin X Wang, Sadid Hasan (https://arxiv.org/abs/2411.10541?utm_source=chatgpt.com)
                - "Beyond Prompt Content: Enhancing LLM Performance via Content-Format Integrated Prompt Optimization" Yuanye Liu, Jiahang Xu, Li Lyna Zhang, Qi Chen, Xuan Feng, Yang Chen, Zhongxin Guo, Yuqing Yang, Peng Cheng (https://arxiv.org/abs/2502.04295)


### Definição critérios de aceite da resposta final

- Agentes da fase:
    - acceptance_criteria_agent: agente responsavel por analisar o prompt passado pelo usuario, e apartir disso definir criterios de aceite claros para que ao fim do processo de "thinkig" possa ser gerada uma resposta final.
    - expected_output_format_agent: vai definir qual é o formato que o usuario espera de output do processo. Para isso, analisa se o usuario passou alguma especificação. CVaso não tenha passado, infere um formato por conta propria. Se for inferido, o formato de saida é algo como "texto corrifo em formato markdown", ou "retornar somente a alternativa contento a resposta correta da pergunta, sem explicações aidcionais". Se o usuario tiver forncido algum tipo de explicação de formato esperado de saida, e tiver incluid exemplos, os exemplos devem estar nesse campo

- OQUE QUERO EXPLICAR AQUI:
    - Quero explicar o "planning.json":
        - Mostrar que nos baseamos no "prd.json" do ralph loop, porem queriamos introduzir algumas iformações aidicionais, como essa de criterios de aceite da resposta final.
        - Mostrar o formato que o "planning.json" vai ter:
        ```json
        {
            "general_infos": {
                "acceptance_criteria": ["criterio_1", ],
                "expected_output_format": "explicação do formato de saida."
            },
            "tasks": [
                # depois é alimentado com as tasks do ralph loop
            ]
        }
        ```

### Quebra de Tasks Independentes

- Agentes:
    - atomic_tasks_planner_agent: vai ser o agente que faz toda a logica de entender a entrada do ususario e montar tarefas que sejam atomicas, no sentido de "menor quebra possivel", para que seja possivel resolve-las usando ralph loop, que consiste em garantir que cada tarefa seja idenpendente a ponto de não usar o contexto de resultados das demais. Ao fim vai atgualizar o "planning.json" no campo tasks. Esse agente vai receber como entrada o prompt do ususario e os "general_infos" do "planning.json"
    - atomic_tasks_revisor_agent: Revisa as tarefas, para garantir que nenhuma precisa reaprovveitgar contexto de resultado de outra. Ele vai retonrar um json contendo uam booleada que diz se esta tudo certo e uma justificativa. Se as tarefas tiverem problemas, eler deve explciar os problemas na justificativa. MOstrar prompt com exempl ode retorno
    - atomic_tasks_rewriter_agent: Só é chamado quandfo o atomic_tasks_revisor_agent diz que alguma tarefa não esta correta. Deve verificar oque não esta correto e reescrever o plano, seguindo a correção indicada. Ele tem imbutido toda a logica de regras e formatoções que o "atomic_tasks_planner_agent" possui para poder fazer isso.

- OQUE QUERO EXPLICAR AQUI:
    - Quero que fique bem claro que o atomic_tasks_planner_agent tem a maior resposabilidade de todo o fluxo de thinking, e que esse é o cara que vai implementar a primeira logica usada no ralph loop.
    - Quero mostrar o formato usado em cada task que vai ficar dentro do "planning.json":
    ```json
    {
        "general_infos": {
            "acceptance_criteria": ["criterio_1", ],
            "expected_output_format": "explicação do formato de saida."
        },
        "tasks": [
            {
                "id": "numero da task",
                "title": "Add priority field to database",
                "description": "Add a new field to the database using the format...",
                "acceptanceCriteria": [
                    "Add priority column to tasks table",
                    "Generate and run migration",
                    "Typecheck passes"
                ],
                "pass_phase": false
            }
        ]
    }
    ```

### Resolução das tarefas - Ralph Loop
- Agentes:
    - task_outcome_reviewer_agent: agente responsavel por receber o resultado de uma tarefa e comparar com seus criterios de aceite. Retorna json contendo uam booleana que diz se os criterrios de aceite foram todos cumpridos e uma justificativa. Se a resposta nao cumprir os criterios, oque não foi cumprido vai ser justificado dentro do cxampo "justificativa". MOstrar prompt com exempl ode retorno

- OQUE QUERO EXPLICAR AQUI:
    - Originalmente o ralph loop, a ideia é que cada tarefa, tenha sua resposta commitada no github, na pratica "All memory lives in files and git — not the model", porem aqui a ideia é iumplementar o ralph loop para outros cenarios, que são diferentes de desenvolvimento de software, por isso demos uma leva adapdata:
        - Para nos, cada resultado de tarefa fica em um arquivo "tasks_results.json", que na pratica, salva a resposta final gertada por cada fase de e xecução do plano gerado. É importante lembrar aque a ideia é manter cada fase "livre de estado/ stateless" entre outras fases, por isso essas respostas só vão ser recuparadas na parte de "resposta final".
    - OUtro ponto a ser explicado é o macanismo de "panico" implementado. Como a arquitetura funciona em loop, gerando respostas, e enviado a um agente que verifica os criterios de aceite, para saber se precuisa continuar pensando, ou se pode encerrar, existe risco desse "thinking" ficar em deadlock, e travar o processo. Para mitigar isso, implementamos contadores de quantas iterações com o LLM (chamadas feitas para a LLM) ocorreram, alem de definir um "max_iterations". Se "task_iteractions" ultrapassar "max_iterations", essa fase do plano se encerra automaticamente, e a resposta atual é salva no "tasks_results.json"
    - De resto é explicar que cada task vai ser feito de manieira individual, e fica em loop até cumprir todos os critertios de aceite, assim como no ralph loop original


### Avaliação de criterios de aceitação
- Agentes:
    - final_response_acceptance_criteria_reviewer_agent: muito parecidos com todos os "reviewers" até agora. Esse vai alanliser todo o arquivo "tasks_results.json", e va icruzar com o campo "general_infos.acceptance_criteria" do "planning.json". Com isso ele tem insumos parea dizer se todas as informações geradas até agora são o suficiente para contruir uma resposta que contena todos os crtiterios de aceitação corretamente. retorna no mesmo formato, uma booleana que diz se os criterrios de aceite foram todos cumpridos e uma justificativa. Se não cumprir, o campo justificativa fala o porque

- OQUE QUERO EXPLICAR AQUI:
    - Aqui é bem simples, ja que a maior parte de explicação vai estar no prompt do agente.
    - So precisa deixar claro que podem ter 2 fluxos:
        - Resposta final
        - Criação de plano adicional complementar

### Criação de plano adicional complementar
- Agentes:
    - acceptance_gap_prompt_creator: agente responsavel pro reproduzir um prompt "de ususario", porem agora pedindo para ser feito somente oque falta para completar todfos os criterios de aceite. A ideia aqui é que seja retornado um prompt que vai ser usado para montar um novo plano, no mesmo formatp que a entrada, por isso ele deve ser um prompt no estilo "usuario"
    - atomic_tasks_planner_agent: aqui é o mesmo agente de "Quebra de Tasks Independentes", basta fazer a referencia.

- OQUE QUERO EXPLICAR AQUI:
    - Quero que fique claro, que na pratica isso tambem é um loop, vamos mais um vez, forcar a criação de tarefas extarr, que vão seguir op mesmo fluxo que foi feito no incio, porem sempre "afunilando" o conteudo e fazendo com que fique mais perto de chegar em um resultado ideial


### Criação da resposta final
- Agentes:
    - final_response_composert_agent: vai analisar todo o tasks_results.json para ter os insumos para construir as respostas, e dessa vez olha para o campo "general_infos.expected_output_format" do "planning.json", para saber qual o formato correto que deve ser retornado. Alem disso, essa agente recupera o input de entrada do usuario, tambem afim de garantir o formato de resposta correto

- OQUE QUERO EXPLICAR AQUI:
    - SO mostar que aqui ja assumimos que existem todos os dados necessario para construir uma resposta final, e que é so juntar tudo e montar resposta pro ususario
