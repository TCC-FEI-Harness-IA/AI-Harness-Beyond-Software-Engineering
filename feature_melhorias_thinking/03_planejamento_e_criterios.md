## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem acesso à conversa anterior. Execute a implementação deste prompt, inclusive testes e documentação, usando o workspace atual.
- Esta é a etapa 03 de sete. Pode ser implementada em worktree própria em paralelo a 01 e 02; não presuma que suas mudanças já estejam presentes. Seu escopo principal é A.1/A.2/C.2 e alinhamento de B.1. A etapa 01 é responsável pela recuperação integral e suas instruções; a 02, por A.3/B.4 e memória. Leia suas seções de documentação quando disponíveis. Os três resultados serão integrados antes da etapa 04.
- O harness é generalista; foi rejeitada a injeção de `question.options` ou dados exclusivos do benchmark. Aproximações e interpretação fundamentada continuam válidas.

## O problema

O planejamento pode transformar uma resposta ainda não calculada em premissa da tarefa ou em critério obrigatório. Nesse caso, B.2 passa a aprovar concordância com um erro criado pelo próprio planejador.

Casos que motivam a mudança:

- Colisões: A.2 planejou comparar força e energia, mas escreveu na tarefa seguinte que a força era maior nos blocos e que a energia dissipada era igual. As duas análises executadas encontraram o contrário e estavam corretas; a tarefa posterior seguiu as premissas falsas.
- Tacho: uma tarefa deveria investigar a origem da energia, mas seu critério já afirmava que ela vinha da vaporização do produto. A execução obedeceu ao critério errado apesar de outra tarefa identificar corretamente resfriamento e condensação como fonte.
- Microscópio: A.2 impôs aumento angular e imagem final no infinito numa pergunta de aumento linear, introduzindo uma hipótese não sustentada e antecipando uma referência espacial errada.
- Geografia: o critério exigiu que a alternativa explicitasse simultaneamente dois aspectos e incorporou linguagem de um distrator. Uma escolha correta, fundamentada no texto, acabou reprovada.
- Marte: depois de recuperação de contrato, restou só uma tarefa para razão de distâncias, embora o pedido fosse período orbital. Cobertura não pode ser inferida pela validade do JSON.

Os prompts atuais já contêm proibições de antecipação, mas coexistem com instruções que podem conflitar: tarefas independentes em uma sequência que consome aprendizados, proibição genérica de resolver a questão final mesmo para a tarefa encarregada da determinação final e orientações divergentes sobre comparar alternativas.

## Sua tarefa

### Leitura e pontos de intervenção

Leia `apps/backend/README.md`, `RALPH_LOOP_ADAPTADO.md` e `NOVAS_REGRAS_RALPH_LOOP.md`. Inspecione:

- `apps/backend/src/infra/templates/a1_general_criteria.md`;
- `apps/backend/src/infra/templates/a2_task_decomposition.md`;
- `apps/backend/src/infra/templates/c2_additional_planning.md`;
- `apps/backend/src/infra/templates/b1_task_resolution.md`, para alinhar escopo;
- montagem de variáveis, limites e recuperação em `apps/backend/src/application/usecases/ralph_thinking_usecase.py` e `application/phases/base_thinking_phase.py`;
- `apps/backend/tests/application/usecases/test_ralph_scope_sufficiency_integration.py`, testes de templates/providers, parser e fases;
- `apps/backend/tests/doubles/ralph_scenario.py`.

### Comportamento a implementar

1. A.1 deve extrair obrigações reais do pedido: conteúdo a determinar, idioma, formato e restrições. Não introduzir gabarito, interpretação de um distrator, exigência de demonstração não pedida ou tolerância numérica arbitrária. Distinguir conteúdo obrigatório de apresentação opcional.
2. A.2 deve planejar investigações com objetivo único e critérios verificáveis, sem fixar conclusão, classificação ou valor ainda não obtidos. A regra vale para afirmações qualitativas, fórmulas cuja aplicabilidade depende de hipótese ainda não estabelecida e supostos resultados de tarefas anteriores.
3. É permitido planejar métodos pertinentes, como usar conservação de energia ou uma lei física. Não confundir escolha fundamentada de método com antecipação de resultado. Quando a aplicabilidade depender de uma condição, a tarefa deve verificá-la, sem assumi-la por conveniência.
4. Separe dados literais fornecidos e resultados a obter. Tarefas posteriores devem buscar conclusões anteriores nos aprendizados, sem adivinhar seu conteúdo. Cada descrição precisa conservar os dados e referências relevantes para seu objetivo.
5. Em C.2, usar resultados já obtidos como entradas é permitido; inventar o resultado da nova investigação continua proibido. A regra de não refazer o que já está resolvido deve admitir investigação direcionada quando a validação global aponta contradição ou erro concreto. Não determine qual conclusão está errada antes da execução da tarefa corretiva.
6. Exija uma revisão final do plano, dentro da própria geração A.2/C.2, verificando que o conjunto cobre o que foi pedido até a última determinação. Se o pedido é período em meses, calcular só razão de distâncias não basta. A etapa 01 reforça essa obrigação nas instruções de recuperação de contrato: não edite `base_thinking_phase.py` em paralelo. Registre os requisitos de alinhamento para conferência quando as branches forem integradas.
7. Objetivo único não significa ausência de dependência lógica: a tarefa pode consumir um resultado anterior pela memória, mas deve ter escopo claro. Evite tarefas redundantes só para transcrever dados, imprimir marcador ou redigir a resposta.
8. Harmonize A.2/C.2/B.1 sobre a tarefa final: ela pode realizar a última análise, integração ou comparação necessária. Proibir antecipação de outras tarefas não pode proibir o próprio objetivo final. C.3 fica responsável por apresentação e pareamento literal já sustentado, não por completar análise ausente.
9. Critérios devem ser complementares e verificáveis. Não exigir presença literal de palavras quando o pedido admite paráfrase; não incluir termos de uma opção como obrigação analítica por preferência do planejador. Resultado interno explicado continua obrigatório mesmo quando o usuário pede apenas uma resposta curta.
10. Preserve aproximações legítimas e escolhas fundamentadas por melhor ajuste. Remova no planejamento a equivalência entre “escolheu alguma opção” e “resolveu corretamente”. O agente da próxima etapa revisará a política completa de validação; não deixe comandos contraditórios nos arquivos sob seu escopo.
11. Não implemente heurística que decide por contagem de tarefas, busca de palavras ou coincidência com o gabarito que um plano é completo ou correto. Não acrescente fase de LLM de revisão de plano nem campos especializados em vestibular.

### TDD e critérios de aceite

Construa primeiro uma matriz de exemplos e testes dos templates reais/entradas:

- Planejamento de colisões pergunta qual força/energia é maior, sem conter as respostas antecipadas. Um cenário com respostas roteirizadas mostra tarefas posteriores consumindo resultados da memória.
- Planejamento de transferência de energia distingue investigar origem e efeito, sem prescrever a conclusão no critério.
- Investigação óptica deve considerar grandeza pedida, referência das distâncias e condições de aplicabilidade, sem exigir hipótese não fornecida como fato.
- Plano com resultado intermediário ainda deve cobrir a determinação final; A.2/C.2 orientam revisar essa cobertura sem impor número fixo de tarefas. Os testes específicos das instruções de recuperação pertencem à etapa 01 e serão conferidos no conjunto integrado antes de 04.
- Tarefa de interpretação admite inferência contextual; critério não exige repetir palavras de um distrator.
- Pergunta aberta exige apenas o conteúdo realmente solicitado; justificativa opcional e marcador de resposta não viram obrigações internas conflitantes.
- C.2 recebe uma lacuna concreta e planeja a investigação correspondente, sem criar uma etapa apenas para escrever a resposta nem resolver o problema dentro do planejamento.

Teste contratos de instrução e o transporte de dados com fakes; não finja que o parser é capaz de identificar semanticamente qualquer resposta antecipada. Evite testes que apenas procuram a frase “não antecipe” e a apresentam como garantia de que o modelo obedecerá. Mantenha contratos claros e uma matriz de avaliação semântica versionável para inspeção posterior.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: primeiro testes, confirmação da falha pertinente e depois código/templates corrigidos.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown, mantendo o JSON exigido por cada fase e o idioma final solicitado pelo usuário.
- Faça alterações coerentes e concisas. Reescreva orientações conflitantes em vez de empilhar exceções no fim do prompt. Preserve isolamento entre fases, critérios identificados, budgets, retentativas e auditoria.
- Não injete alternativas de `question.options`, gabaritos, IDs de questões ou lógica exclusiva do benchmark.
- Execute testes focados e, na pasta `apps/backend`, `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`. Não enfraqueça a cobertura nem apague regressões válidas para acomodar o texto novo.
- Não execute chamadas pagas a modelos. Declare os limites dos testes com saídas roteirizadas e diferencie validação de contrato de avaliação semântica.
- Em execução paralela, concentre as alterações de produção nos templates de sua responsabilidade e prefira arquivos próprios para novos testes de integração. Não altere A.3/B.4 ou contratos/helpers compartilhados sem necessidade; qualquer dependência nova de contrato deve ser registrada e integrada antes de concluir o trecho que a utiliza. Preserve as seções documentais das outras frentes na integração.

## Documentação das alterações:
- Documente detalhadamente qualquer mudança na lógica ou responsabilidade das fases, fornecendo exemplos e a motivação metodológica.
- Acrescente ao `NOVAS_REGRAS_RALPH_LOOP.md` já existente na raiz a seção **Melhorias do thinking — 03: planejamento sem respostas antecipadas e cobertura do pedido**. Preserve o restante; crie o arquivo `.md` apenas se estiver ausente.
- Explique a diferença entre método, hipótese, dado literal e resultado; entre dependência lógica e objetivo único; e entre determinação final e apresentação. Inclua exemplos quantitativos e de pergunta aberta.
- Atualize as extensões de `RALPH_LOOP_ADAPTADO.md` e o README técnico afetado, preservando a transcrição literal do paper.
- Registre testes executados, resultados e limitações. Explicite que cobertura semântica é orientada no planejamento e posteriormente julgada em C.1, não certificada por quantidade de tarefas ou aceitação do JSON.
