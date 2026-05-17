

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
    - atomic_tasks_revisor_agent: Revisa as tarefas, para garantir que nenhuma precisa reaprovveitgar contexto de resultado de outra. Ele vai retonrar um json contendo uam booleada que diz se esta tudo certo e uma justificativa. Se as tarefas tiverem problemas, eler deve explciar os problemas na justificativa
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
                "passes": false
            }
        ]
    }
    ```

### Resolução das tarefas - Ralph Loop
- Agentes:
    - task_outcome_reviewer_agent:

### Avaliação de criterios de aceitação
- Agentes:
    - avaliador_criterios_aceitação


### Criação de plano adicional complementar
- Agentes:
    - criacao_pompt_criterios_faltantes
    - criador_tarefas_atomicas

### Criação da resposta final
- Agentes:
    - final_response_creator
