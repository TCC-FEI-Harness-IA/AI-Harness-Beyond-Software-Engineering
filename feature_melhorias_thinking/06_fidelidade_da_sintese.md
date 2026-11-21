## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem acesso à conversa anterior. Implemente as correções deste prompt, com testes e documentação, considerando os contratos atuais do workspace.
- Esta é a etapa 06 de sete. Execute após recuperação integral, aprendizados completos, planejamento sem antecipações, validação equilibrada e revisão auditável de resultados. Leia as seções **Melhorias do thinking — 01 a 05** e preserve suas decisões.
- A aplicação é generalista. Identificação de alternativas é um exemplo de fidelidade; nomes, códigos, entidades, unidades e qualificações também precisam ser preservados em perguntas abertas.

## O problema

C.1 aprova a suficiência e a coerência de um conjunto de resultados; C.3 o apresenta no idioma e formato pedidos. Mesmo com boa análise, C.3 pode alterar o sentido, trocar uma identificação, apagar uma hipótese, transformar aproximação em igualdade ou inventar uma conclusão que não estava sustentada.

Casos reais:

- Química Q094: o resultado aprovado era `teste 1 — cálcio`. As alternativas originais eram `A) 1, B) 2, C) 3, D) 4, E) 5`. A.3 omitiu esse mapeamento e C.3 escreveu `B (1-Cálcio)`. O conteúdo químico estava correto e a apresentação introduziu erro.
- Colisões Q105: a síntese apresentou fórmulas que implicavam força maior nos pneus, mas concluiu força maior nos blocos; também selecionou uma opção de energia igual e explicou dissipação maior nos blocos.
- FUVEST Q034: uma análise calculou 47 e a resposta escolheu 44. Seleção por aproximação pode ser válida, mas não é permitido declarar que 47 é exatamente 44. A síntese deve preservar a natureza da escolha aprovada, não inventar equivalência.
- Marte Q005: apresentar uma razão de distâncias e acrescentar uma opção de período não completa a análise. Lacuna de determinação deve ser identificada antes, em C.1/C.2, em vez de preenchida por C.3.

As melhorias anteriores tratam das fontes, da análise e dos resultados vigentes. Esta etapa trata da fidelidade entre esses resultados e o texto efetivamente entregue.

## Sua tarefa

### Leitura e pontos de intervenção

Inspecione a metodologia atualizada e:

- `apps/backend/src/infra/templates/c3_final_answer.md`;
- templates C.1/B.4 e as regras novas de resultados vigentes;
- `apps/backend/src/application/usecases/ralph_thinking_usecase.py`, em `__synthesis_variables`, renderização, `__run_synthesis` e `__run_final_answer`;
- `apps/backend/src/domain/entities/thinking/global_approval.py`;
- `apps/backend/src/application/phases/final_answer_phase.py` e contrato de saída de C.3 no parser;
- `apps/backend/tests/application/usecases/test_ralph_scope_sufficiency_integration.py`, testes de fases/parser e `tests/doubles/ralph_scenario.py`.

### Comportamento a implementar

1. Reforce o template C.3 para identificar o conteúdo aprovado que responderá ao pedido e conferir sua fidelidade antes de produzir `final_answer`, dentro da mesma chamada. Não acrescente nova fase, nova chamada de revisor ou pós-validador depois de C.3.
2. Preserve significado, direção de comparações, sinais, unidades, referências, hipóteses, condições e qualificações como `aproximadamente`, `sob hipótese X` ou `melhor ajuste`. Tradução e concisão não podem alterar esses aspectos.
3. Diferencie claramente resultado calculado e escolha aprovada por aproximação/eliminações. Se a escolha está sustentada pelos resultados, C.3 pode apresentá-la mesmo sem igualdade numérica e sem um cálculo direto que produza o valor escolhido. Não refaça a validação com maior rigidez nem exija exatidão inexistente.
4. Identificadores devem corresponder aos objetos já determinados: letra e texto da alternativa, número do teste, nome da entidade, código de produto, mês ou outro rótulo. Quando as associações estiverem nas notas originais, use-as para conferência literal. Não introduza `question.options` nem outra entrada especializada do benchmark.
5. A análise e a escolha por melhor ajuste pertencem aos resultados aprovados. C.3 pode aplicar o pareamento literal e a apresentação que não exigem análise nova; não pode escolher por proximidade por conta própria quando essa comparação ainda falta, completar um cálculo, resolver conflito residual ou inventar identificador ausente.
6. Harmonize C.1 para que a falta de informação indispensável à apresentação fiel, como um vínculo não recuperável entre item e identificador, não seja declarada automaticamente coberta. Se o pedido só exige o conteúdo e não um identificador, não invente uma lacuna. Uma ausência apenas de linha final, idioma ou formatação continua sendo resolvida em C.3.
7. Se a análise ou uma associação essencial realmente não está disponível, corrija sua detecção no caminho anterior C.1/C.2. Não contorne fabricando uma resposta, exibindo erro técnico ao usuário como resultado válido, injetando dados do benchmark ou adicionando revisão ilimitada de C.3.
8. Garanta programaticamente que C.3 recebe os resultados vigentes exatamente como aprovados na última C.1, após eventuais revisões. Não ressuscite conclusões substituídas, tentativas rejeitadas ou histórico de mensagens. Memória e critérios seguem em áreas próprias.
9. Respeite idioma, formato e justificativa opcional/obrigatória do pedido. Resultado interno explicado não obriga explicação final. Não invente limites de linhas, novo formato ou menção a detalhes internos do harness na resposta ao usuário.
10. Preserve schema `final_answer`, diagnóstico, recuperação existente de saída inválida, orçamento e contabilização. Não adicione um parser de verdade factual por regex nem prometa garantia semântica absoluta em texto livre.

### TDD e critérios de aceite

Antes de implementar, crie testes com templates reais e cenários observáveis:

- Resultado aprovado `teste 1 — cálcio` e memória com `A) 1 ... E) 5`: o prompt de síntese recebe o pareamento completo; um cenário de resposta fiel entrega A. O teste não pode obter associações de `question.options` nem hardcodá-las em código de produção.
- Pergunta aberta: entidade, número, unidade e condição são preservados até `final_answer`, incluindo tradução quando pedida.
- Resultado aproximado e escolha por melhor ajuste já aprovados chegam a C.3 com essa natureza; não são apresentados como igualdade exata nem causam replanejamento só por divergência numérica.
- Conteúdo aprovado com comparação direcional correta traz a orientação para evitar texto contraditório. Teste o contrato e a informação disponível sem fingir que o fake prova consistência de qualquer modelo.
- Após revisão de resultado, a síntese recebe a versão vigente aprovada em C.1, sem a versão substituída ou aprendizados obsoletos como fatos atuais.
- Conteúdo suficiente sem marcador final vai diretamente de C.1 a C.3; análise essencial ausente ou vínculo necessário ausente percorre C.2 antes de uma nova C.1/C.3, sem chamada analítica dentro da síntese.
- Pedido “somente o resultado”, justificativa opcional e justificativa obrigatória têm apresentações distintas, apoiadas no mesmo conteúdo interno quando pertinente.
- Permanecem verdadeiros os contratos de recuperação, conclusão de sessão, evento terminal, auditoria e limites. Não há nova fase nem verificador depois da síntese.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: escreva os testes primeiro, confirme a falha do comportamento atual pertinente e depois implemente a correção.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown. O envelope de resposta continua JSON; a resposta final usa o idioma e formato solicitados pelo usuário.
- Preserve separação de contextos, critérios, notas e resultados aprovados. Não acople a solução ao benchmark, às letras A–E ou a IDs de questões.
- Faça alterações concisas e coerentes com as etapas anteriores. Uma conferência dentro das instruções de C.3 não deve ser apresentada como nova fase arquitetural ou garantia determinística da verdade do texto.
- Execute testes focados e, em `apps/backend`, `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`. Preserve a exigência de cobertura e as regressões válidas de aproximação.
- Não execute chamadas pagas a modelos. Diferencie preservação das entradas, contrato de prompt e qualidade semântica da saída.

## Documentação das alterações:
- Documente em detalhes a responsabilidade da síntese e toda alteração de lógica ou de suas entradas, com exemplos de fidelidade e de extrapolação indevida.
- Acrescente ao `NOVAS_REGRAS_RALPH_LOOP.md` existente na raiz a seção **Melhorias do thinking — 06: fidelidade da síntese final**. Preserve o conteúdo anterior; crie o arquivo `.md` apenas se estiver ausente.
- Inclua exemplos de alternativa, pergunta aberta, unidade/referencial, aproximação e resultado revisado. Explique que pareamento literal não é a mesma coisa que seleção analítica e que a aprovação global não autoriza inventar informação.
- Atualize as extensões de `RALPH_LOOP_ADAPTADO.md` e os contratos técnicos pertinentes, sem alterar a transcrição literal do paper.
- Registre os testes executados, seus resultados e as limitações. Não afirme que a fidelidade semântica está garantida para qualquer modelo por testes roteirizados.
