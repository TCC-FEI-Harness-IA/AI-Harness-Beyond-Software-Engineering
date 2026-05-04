# Fluxo de Thinking da aplicação

- Definição geral do fluxo da Deep Thinkg da aplicação
- Regras gerais:
    - Todo o fluxo de pensamento deve ser feito em inglês:
        - Perguntas em outras linguas são aceitas, vai ser feito o processo de tradução na entrada e saida da lingua usada como entrada para ingles, e vice-versa
    - Todos os promtps intermediarios devem ser feitos usando as seguintes regras:
        - Devem usar linguagem de marcação "markdown"
        - Todos os prompts devem fornecer o formato de saida obrigatorio no prompt:
            - Prompts internos da aplicação:
                - Devem solcitar resposta em formato json obrigatoriamente
            - Promtp de retorno pro ususario:
                - Se for solicitação de contexto extra ou respota final:
                    - Deve obrigatoriamente usar formato markdown
                - Se for qualquer tipo de solicitação, como de aprovação de comandos
                    - Deve usar obrigatoriamente o formato json

- Todo:
    - Criar os templates de json interno e markdown de saida para o usuario



- Tecnicas que preciso buscar referencias para basear minhas implementações:
    - Estudo se existe melhoras em usar prompts em ingles, quando comparado com outrs linguas
    - Ver se existe alguma tecnica de uso de prompts para tardução de texto com LLMs
    - Buscar se existe algum estudo do ralph loop ou que baseou o ralph loop

- Tecnicas e papers de referencias para assuntos especificos:
    - Uso de promtps em ingles internamente
        - tem 3 estudos, pagina dedicada somente a isso
        
    - Tecnicas para tradução de prompts com LLM
    - Tecnicas para quebra de planos
        - Ralph Loop:
            - https://github.com/snarktank/ralph
            - https://ghuntley.com/ralph/




## Fluxo Macro:

1. Verificação de falta de contexto
    - Recebe o prompt
    - Criação de prompt intermediario
        - Cria um prompt que da contexto geral da aplicação de chat, especifica oque é dados passado pelo ususario, e qual a verificação que a LLM deve fazer
        ```markdown
        ## Contexto Geral
        Essa é uma aplicação de chat com uso deepthinking entre usuario e agentes de LLM

        ## Sua tarefa
        - Analise o promtp de entrada passado pelo usuario, informado no topico "Prompt Usuario".
        - Execute as validações presentes no topico "Validações".
        - Ao fim, retorne um objeto json contexto as seguintes informações:
        ```json
        {
            ""
        }
        ```

        ## Validações
        ```
    - Recebe o promtp e valida se falta coisa para executar a tarefa
    - Se necessario, retorna ao usuario

- Definição de objetivo e criterios de aceite:
    - Identificação do tipo de prompt
    - Definição de objetivo final
    - Definição dos criterios de aceite
- Fase de quebra de tarefas:
    - Estrategia de quebra de tasks
    - Faz a quebra e monta o plano
- Fase de execução do plano:
    - Executa as tarefas em loop
    - Faz as verificações necessarias de tempos em tempos:
        - Precisa mudar alguma fase? 
        - Precisa compactar o contexto atual?
    - Existe mecanismo de "panico", onde se existe deadlock, forca a resposta
- Fase de compilação de respostas do plano
    - Compila tudo oq foi feito nas fases

- Verificação de informações geradas
    - Verifica se é possivel atender o objetivo final e criterios de aceite
        - Se puder, vai para a prox fase
        - Se nao, volta para execução de plani
- Fase de plano extra:
    - Identificas os criterios nao atendidos
    - Caso o plano original nao contemple tudo oq é necessario para responder, monta um plano para ster oq falta
    - O plano segue o mesmo formato do plano original


