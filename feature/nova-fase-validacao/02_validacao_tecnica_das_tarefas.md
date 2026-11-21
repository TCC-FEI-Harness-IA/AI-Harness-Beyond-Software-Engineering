## Contexto Geral

- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O `README.md` contém uma explicação geral de todo o repositório.
- O `RALPH_LOOP_ADAPTADO.md` contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper. Sua transcrição literal da metodologia original deve ser preservada; novas regras entram como extensões identificadas.
- Você é um agente de desenvolvimento sem acesso à conversa que originou esta solicitação. Este prompt contém as decisões necessárias para implementar a **frente 2 — validação técnica de tarefas**, concluir sua integração e atualizar testes/documentação. Execute o trabalho no workspace, não apenas uma proposta.
- Este é o segundo e último de dois prompts, executados **sequencialmente**. Sua base deve conter a implementação de `01_planejamento_com_validacao.md` já integrada. Não depende de um terceiro prompt para corrigir contratos ou concluir as duas frentes.
- O fluxo esperado nessa base é: A.1 critérios gerais → A.2 candidato → nova A.3 validação de decomposição, com retorno a A.2 se reprovado → confirmação do plano → A.4 aprendizados do enunciado → B/C. A.3 recebe pedido original, critérios gerais e somente o candidato atual; usa rubrica fixa; apenas o plano aprovado entra na fila. Sessões antigas sem versão continuam interpretando A.3 como extração, enquanto sessões novas distinguem A.3/A.4 por versão do fluxo.
- A especificação complementar está em `feature/nova-fase-validacao/README.md`. O relatório `RELATORIO_IMPLEMENTACAO_01.md`, nessa pasta, registra a primeira etapa. Consulte-os e o código real; a falta de um nome de arquivo exato não justifica ignorar uma implementação equivalente. Se o fluxo pré-requisito realmente não estiver integrado, identifique a dependência ausente antes de aplicar mudanças que pressupõem sua existência; não reimplemente silenciosamente toda a primeira frente.
- O harness continua generalista. Não usar `question.options`, gabaritos, IDs de questão, fórmulas específicas de benchmark ou fixtures para decidir respostas em produção. Dados e resultados de referência pertencem somente à avaliação externa.

## O problema

### Estado atual de B.2

B.2 recebe resultado preliminar, critérios locais, aprendizados e eventual proposta de revisão, sem a descrição da tarefa. Seu template já pede conferência técnica, mas a condição estruturada de aprovação está vinculada aos critérios gerados no planejamento.

Em `Task.verification_criteria()`, o conjunto atual contém os critérios planejados e, nas tarefas revisoras, o critério fixo `<task_id>-REV`. O orquestrador usa esse conjunto para montar B.1/B.2 e informar ao parser quais IDs devem ser avaliados.

Mesmo com explicação completa e critérios formalmente atendidos, o resultado pode usar uma premissa inventada, uma fórmula inaplicável, um referente errado ou uma inferência que não sustenta a conclusão. Foram observadas aprovações que apenas recontam a explicação de B.1 como se sua existência comprovasse correção.

### Aproximação e melhor ajuste

A política existente permite aproximação, estimativa, eliminação e inferência contextual. Isso deve continuar válido. O defeito é tratar uma comparação entre respostas ou uma hipótese explicitada como fundamento suficiente sem conferir a base analítica.

Escolher uma resposta próxima de um cálculo errado não corrige o cálculo. Uma hipótese conveniente não passa a ser sustentada só porque não foi explicitamente proibida. Por outro lado, divergência numérica não é razão universal para reprovar uma aproximação legítima.

### Mudança autorizada

B.2 passará a validar a tarefa como um todo, recebendo sua descrição e usando um **critério técnico fixo obrigatório do harness**, `<task_id>-TECH`, além de todos os critérios existentes.

O executor B.1 deve conhecer o mesmo critério antes de resolver. Uma resposta tecnicamente inválida pode ser reprovada por TECH mesmo que cumpra todos os critérios do planejador. A.2 não cria, escolhe nem remove essa condição.

## Sua tarefa

### 1. Leitura e pontos de intervenção

Leia a metodologia atualizada, as extensões vigentes e o resultado da primeira etapa. Inspecione, pelo menos:

- `apps/backend/src/domain/entities/thinking/task.py`, `acceptance_criterion.py`, `verification_report.py`, `validation_context.py` e os contratos de revisão;
- `apps/backend/src/application/usecases/ralph_thinking_usecase.py`, especialmente `__resolution_variables`, `__verification_variables`, `__resolve_task`, montagem do histórico, B.3 e B.4;
- `apps/backend/src/infra/templates/b1_task_resolution.md` e `b2_task_verification.md`;
- templates A.2, nova A.3, A.4, B.4, C.1/C.2/C.3, para preservar a divisão de responsabilidades e os contratos da primeira etapa;
- `apps/backend/src/infra/adapters/structured_response_parser_adapter.py`, principalmente critérios dos lotes A.2/C.2, IDs reservados e cobertura/coerência dos relatórios;
- providers, fases de resolução/verificação, diagnóstico, memória, livro de resultados, recorder e persistência;
- testes de domínio de tarefa/relatório, parser, fases, templates, `test_ralph_scope_sufficiency_integration.py`, `test_ralph_five_fronts_integration.py` e os testes novos do planejamento;
- `tests/doubles/ralph_scenario.py`, completions roteirizadas, fixtures e auxiliares que montam relatórios, além dos testes de leitura de sessões antigas e exportação/importação.

O código pode ter sido reorganizado na primeira etapa: localize os pontos por responsabilidade. Preserve alterações do usuário e os contratos já concluídos, incluindo versão do fluxo, A.3/A.4 e candidatos fora da fila.

### 2. Definição e geração de TECH

Acrescente programaticamente a toda tarefa um critério fixo com identificador **`<task_id>-TECH`**; exemplo: `T2-TECH`.

Seu conteúdo, redigido em inglês no código/template, deve exigir que o resultado resolva **o objetivo daquela tarefa** com fundamento compatível com dados, métodos e condições aplicáveis. Deve abranger:

- Premissas fornecidas ou justificadas, sem transformar hipótese em fato.
- Referentes, unidades, condições e estágio temporal preservados.
- Aplicabilidade do método e contribuições/condições relevantes à análise.
- Encadeamento que efetivamente sustenta a conclusão, além da presença de explicação.
- Consistência entre cálculo, texto e conclusão.
- Aproximação, hipótese ou melhor ajuste com suporte pertinente, quando usados.

Use uma única definição para construir o critério. O conjunto efetivo de verificação deve ser composto deterministicamente pelos critérios planejados, TECH e REV quando aplicável. Prefira estender o mecanismo de `Task.verification_criteria()` existente, mantendo o conjunto de critérios de autoria do planejador separado dos critérios acrescentados pelo harness.

Não copie TECH para dentro do array de autoria de A.2 como se tivesse sido gerado pelo modelo. Não deixe o critério depender de uma palavra-chave, disciplina, formato de alternativas ou presença de cálculo.

Apresente o mesmo conjunto efetivo em B.1, B.2 e `ValidationContext.expected_criteria_ids`; o solver deve conhecer TECH antes de produzir a resposta. Garanta inclusão única em toda retentativa e em tarefas criadas por A.2 ou C.2, comuns ou revisoras.

### 3. Identificador reservado e compatibilidade

O planejador não pode fornecer, substituir ou duplicar o identificador técnico reservado. Valide a colisão tanto no domínio da tarefa quanto no parser dos lotes A.2/C.2, mantendo a recuperação estrutural já existente.

A validação no domínio deve funcionar em tarefas comuns também: o `__post_init__` atual tem um retorno antecipado quando `review is None`, que não pode impedir a checagem de TECH. Preserve as regras de REV, dependências e revisão.

Harmonize as instruções dos planejadores para não emitirem IDs reservados. Na nova A.3, TECH não é algo que precisa estar escrito no candidato: ele será acrescentado pelo harness na execução. Não faça A.3 reprovar um plano por ausência do critério sintético.

Não altere relatórios históricos ou injete TECH em sessões gravadas anteriormente. O parser valida a cobertura esperada de **novas chamadas**; a leitura de documentos antigos não deve exigir um critério que nunca existiu neles. Preserve a versão e os significados de A.3/A.4 introduzidos pela primeira etapa, sem nova renumeração.

### 4. Entradas explícitas e responsabilidades de B.2

Acrescente uma área com identificação, título e descrição/objetivo da tarefa ao template B.2. A descrição explica o escopo; não se torna substituta da resposta ou um novo conjunto de critérios.

Mantenha em áreas separadas:

1. Descrição e objetivo da tarefa.
2. Resultado preliminar de B.1.
3. Critérios efetivos de verificação: planejados + TECH + REV quando houver.
4. Proposta explícita de revisão, no contrato atual.
5. Aprendizados de referência, sem misturá-los aos critérios.

Não encaminhe toda a conversa de B.1 ou o histórico do planejamento a B.2. Toda verificação continua em contexto novo. Os dados e aprendizados são as entradas explícitas previstas, não uma restauração de janela anterior.

B.2 avalia todos os critérios e também a sustentação técnica por TECH. Não deve produzir a solução corrigida, completar uma etapa ausente ou editar silenciosamente os critérios. Um defeito concreto deve gerar reprovação e feedback para B.1.

Uma tarefa intermediária pode estar tecnicamente correta sem responder a pergunta inteira. TECH não pode cobrar análises de outras tarefas, formato final, justificativa externa não solicitada ou exatidão incompatível com estimativa fundamentada.

### 5. Relatório e condição de aprovação

Mantenha o schema atual de B.2: `criteria_evaluation`, `unmet_criteria_ids` e `decision` com `approved`/`reproved`. A nova A.3 continua com seu próprio booleano `approved` e `issues`; não confundir os contratos.

Exemplo de B.2 em que o critério planejado foi atendido, mas a validade técnica falhou:

```json
{
  "criteria_evaluation": [
    {
      "criterion_id": "T2-AC1",
      "met": true,
      "justification": "The requested calculation steps are present."
    },
    {
      "criterion_id": "T2-TECH",
      "met": false,
      "justification": "The rate is applied outside its stated interval. Investigate the interval used before recomputing the quantity."
    }
  ],
  "unmet_criteria_ids": ["T2-TECH"],
  "decision": "reproved"
}
```

O relatório só é aprovado quando **todos** os critérios efetivos forem atendidos. TECH e REV são independentes: uma revisão pode demonstrar seu veredito e ainda ter erro técnico em outra parte da resposta, ou ter conteúdo técnico correto sem demonstrar a substituição proposta.

Ausência de TECH, duplicação, ID desconhecido ou decisão incompatível com os `met` é defeito de contrato. `TECH: false` com relatório coerente é reprovação semântica válida. O parser não corrige vereditos, fabrica avaliações ou decide se a justificativa é verdadeira.

### 6. Fundamentação, hipóteses e aproximações

Reorganize as instruções de B.1/B.2 para que a conferência da base analítica preceda a aceitação de uma aproximação ou decisão por melhor ajuste.

O validador deve apontar o dado ou trecho relevante, a premissa decisiva e a relação efetivamente conferida. Não basta dizer que a explicação está completa ou repetir sua conclusão.

Quando simples e pertinente ao escopo, conferir por outro ângulo: direção de uma variação, limite, compatibilidade entre partes do texto, relação temporal, referente/unidade ou consequência de uma generalização. Não tornar esses exemplos uma lista obrigatória de técnicas para toda tarefa nem exigir uma segunda solução completa.

Preserve as seguintes distinções:

- Dado fornecido não é resultado inferido. Ausência de informação não demonstra sua negação; uma hipótese favorável não pode virar fato sem suporte.
- Coerência narrativa não comprova atribuição a uma fonte. Não inventar referência verificável; também não exigir consulta externa ou citação bibliográfica em toda tarefa. Esta mudança não acrescenta ferramentas de pesquisa.
- Selecionar a resposta mais próxima de um valor não estabelece que o valor de origem foi calculado por um modelo válido.
- Uma hipótese deve ser compatível com o cenário e justificada; ser concebível ou não proibida não basta para adotá-la apenas no candidato favorecido.
- Aplicar o mesmo padrão de conteúdo implícito e de suporte às hipóteses comparadas. Preservar inferências contextuais pertinentes, sem literalismo que rejeita uma opção por omitir palavra e aceita a mesma omissão em outra.
- Aproximações, estimativas, eliminação e melhor ajuste continuam aceitos quando sustentados. Não inventar tolerância percentual universal, proibir aproximação em todo problema discreto ou exigir cálculo direto até toda resposta.
- Restrições explícitas do usuário, inclusive precisão/exatidão quando realmente exigidas, continuam valendo; não transformar uma antecipação do planejador em obrigação do usuário.

Preserve a política de consistência compartilhada e seus controles positivos. Prefira ajustes nas instruções de resolução e verificação técnica locais; **não acrescente novas verificações ou ciclos em C.1** para completar esta tarefa. Os contratos atuais de C.1/C.2/C.3 e a divisão entre análise e apresentação devem continuar coerentes.

### 7. Retentativas, armazenamento e limites

B.2 deve produzir feedback concreto: qual dado, relação, hipótese ou passo falhou e o que investigar. B.1 recebe o relatório pelo mecanismo atual de tentativas anteriores, em contexto novo, corrige o defeito e preserva conclusões que não foram refutadas.

Mantenha **cinco tentativas totais por tarefa**, inicial mais até quatro retentativas. B.1 retentada após reprovação usa temperatura `1`; a B.2 seguinte volta à temperatura da sessão. Recuperação de JSON/contrato mantém suas janelas, temperaturas, diagnósticos e limites atuais.

O contador das tarefas não se mistura com as cinco tentativas de planejamento A.2/A.3. Preserve limites de C.2, chamadas, tokens, reserva e tempo. Não aumente tetos para fazer a integração passar.

Somente resultado aprovado pode chegar a B.3 e depois à extração B.4. Reprovação por TECH não altera resultados vigentes ou memória, e a proposta de revisão só é aplicada quando todos os critérios, incluindo TECH e REV, forem aprovados.

Se B.2 identificar um critério de planejamento inviável que A.3 deixou passar, registre o defeito. Não acrescente um novo retorno B.2 → A.2 nem autorize ignorar critérios arbitrariamente. Se as tentativas não resolverem o problema, a sessão pode encerrar com a falha estruturada existente, sem síntese de conteúdo reprovado.

### 8. Integração final das duas frentes

Conclua a integração dentro desta etapa. Confirme que:

- O planejamento novo e sua versão continuam funcionando depois da inclusão de TECH.
- A.3 audita o candidato, não os critérios técnicos sintéticos de B.2; A.4 só roda após aprovação.
- A composição de critérios é única e consistente em B.1/B.2/parser/retentativa, com coexistência correta de REV.
- B.4 não transforma TECH, REV, instruções ou vereditos em fatos do problema. Preserve sua entrada e política de extração atuais, sem implementar a apresentação de proveniência adiada.
- C.1 continua avaliando seus critérios gerais, sem receber TECH como novo critério global. C.3 continua apresentando somente os resultados vigentes da última aprovação global.
- Sessões antigas, inferência direta, exportação/importação, custos e falhas permanecem compatíveis. Se alguma apresentação genérica de relatório precisar ajustar-se ao ID TECH, faça somente a compatibilidade necessária.
- Cenários novos dos testes/fakes contêm os relatórios esperados completos. Não injete `TECH: true` indiscriminadamente em toda completion para esconder uma falta de avaliação.

Não implemente os itens adiados: novas verificações de C.1, recuperação de contrato específica por campo, renderização da proveniência, mudanças funcionais extras de dependências, validação de lotes C.2 por A.3, fallback simples, votação, revisor após C.3 ou resolução especializada por domínio.

## Metodo de desenvolvimento:

- A aplicação deve ser desenvolvida usando **TDD**: construa primeiro testes que garantam o comportamento corrigido, confirme as falhas pertinentes e depois implemente o código que os satisfaz.
- Preserve arquitetura por camadas, interfaces e injeção. Não transforme o parser em juiz factual nem use heurísticas de domínio para preencher TECH.
- Prompts internos e mensagens ao modelo devem ser escritos em **inglês e Markdown**, com envelopes JSON. A resposta final segue o idioma e o formato solicitados pelo usuário.
- Use templates, parser, fila, memória, livro, contextos, recorder e custos reais nos testes de integração, substituindo a rede por completions roteirizadas. Verifique `prompt_input`, critérios esperados, estado persistido e transições.
- Atualize cenários de execução nova para o conjunto efetivo de critérios. Preserve fixtures históricas sem TECH e seus significados de fase/versão; não as reescreva como sessões novas para esconder incompatibilidade.
- Não execute inferências pagas ou benchmarks reais. Testes roteirizados demonstram protocolo, não melhoria de acurácia. Exemplos semânticos novos podem ser preparados para avaliação posterior, com resultados esperados fora das entradas do modelo.

### Matriz mínima de testes e critérios de aceite

1. **Critério fixo:** tarefa comum, adicional C.2 e revisora recebem TECH exatamente uma vez; conjunto contém também REV quando aplicável. Critérios originais permanecem identificáveis como planejados.
2. **Colisão:** domínio e parser recusam TECH emitido pelo planejador em tarefa comum/revisora, incluindo caminhos antes afetados pelo retorno antecipado de `review is None`. A.2/C.2 usam a recuperação estrutural existente; nenhuma remoção silenciosa resolve a colisão.
3. **Entradas reais:** título/descrição, resultado, critérios efetivos e aprendizados aparecem corretamente separados nos prompts enviados; B.1 e B.2 veem o mesmo TECH e o parser recebe exatamente esses IDs.
4. **Falha técnica isolada:** todos os critérios planejados `met: true`, TECH `met: false`, decisão `reproved`; B.1 recebe o feedback e é retentada; nada de B.3/B.4 antes da aprovação.
5. **Aprovação completa:** todos os critérios, TECH e REV quando houver, aprovados; armazenamento e revisão ocorrem pelos caminhos existentes, sem chamada extra de verificação.
6. **Relatório inconsistente:** TECH ausente/repetido, ID desconhecido, `approved` com TECH falso, `reproved` com pendências vazias ou lista de pendências incompatível são recusados e recuperados sem mudar vereditos localmente.
7. **TECH e REV independentes:** uma reprovação em qualquer um impede aplicar a revisão; ambos aprovados permitem aplicação auditada. Critério técnico não substitui a obrigação de demonstrar a revisão.
8. **Escopo e controles positivos:** tarefa intermediária correta não precisa responder tudo; pergunta aberta, hipótese sustentada, aproximação legítima, inferência contextual e justificativa final opcional permanecem aceitas em cenários roteirizados coerentes.
9. **Casos negativos generalistas:** premissa não fornecida tratada como fato, método fora das condições, direção incompatível com uma tabela, causa de etapa temporal diferente e proximidade sobre cálculo inválido. Use exemplos sintéticos, sem oráculos de benchmark nos templates ou no núcleo. Distinga teste de transporte/contrato de resultado semântico real.
10. **Retentativa e temperatura:** feedback de TECH chega integralmente a B.1; B.1 nova em contexto novo, a 1; B.2 na temperatura da sessão. Históricos, tentativas e custos preservados.
11. **Cinco tentativas e falhas:** quatro reprovações seguidas de aprovação na quinta concluem; cinco reprovações encerram sem sexta tentativa e sem armazenar ou sintetizar. Orçamento/cancelamento/saída inválida continuam contabilizados e sem promoção de conteúdo reprovado.
12. **Histórico:** leitura e round-trip de sessão antiga sem TECH e sem versão, nova com A.3/A.4 e TECH, e inferência direta; exportação/importação e reconstrução de histórico não revalidam retroativamente completions antigas.
13. **Integração das frentes:** plano inicial reprovado em A.3, plano revisado aprovado, A.4 uma vez, primeira resolução reprovada só por TECH, segunda aprovada, C.1 aprova e C.3 uma vez. Inspecione isolamento, candidato correto, fila/slots, notas e resultado final aprovado.
14. **Independência dos limites:** tentativas consumidas no planejamento não reduzem as cinco da tarefa; nenhuma reprovação de B.2 reabre planejamento ou chama A.3; C.2 não ganhou nova avaliação.
15. **Regressões anteriores:** manutenção da recuperação integral, resultados/memória vigentes, revisão confirmatória/substitutiva, aproximações legítimas e snapshot da última C.1 para C.3. Preserve a compatibilidade de eventos/histórico da primeira etapa.

Execute testes focados durante o TDD e, ao final, na pasta `apps/backend`, com o ambiente virtual do projeto:

```sh
python -m flake8 src tests
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

Use o Python da `.venv` se necessário. Preserve os limiares configurados; não exclua código da medição, remova controles positivos ou enfraqueça testes para obter aprovação.

Verifique também os consumidores frontend dos contratos integrados, na pasta `apps/frontend`:

```sh
npm run typecheck
npm run lint
npm run test:coverage
npm run build
```

Confira `git diff --check`. Complete as correções relacionadas à integração; diferencie problemas preexistentes com evidência. Não encerre a segunda etapa transferindo incompatibilidades resolvíveis a um terceiro prompt.

## Documentação das alterações:

- Atualize `RALPH_LOOP_ADAPTADO.md` para refletir B.2 como verificação da tarefa inteira, suas entradas, TECH, condição de aprovação e política de hipóteses/aproximações. Preserve a nova A.3/A.4 da primeira etapa e **a transcrição literal da metodologia original**.
- Use o arquivo existente **`NOVAS_REGRAS_RALPH_LOOP.md`** na raiz. Preserve o conteúdo anterior e a seção da primeira etapa; acrescente **Nova fase de validação — 02: validade técnica obrigatória das tarefas**. Não crie um arquivo duplicado sem extensão nem sobrescreva o histórico.
- Documente com detalhes a composição de critérios, IDs reservados, exemplos de todos os critérios planejados atendidos com TECH reprovado, coexistência de TECH/REV e uma retentativa que corrige o defeito. Inclua controles positivos de tarefa intermediária, pergunta aberta e aproximação fundamentada, sem tornar esses exemplos soluções de produção.
- Atualize o README técnico e contratos afetados. Explique o que muda e o que permanece no parser, persistência, histórico, memória, custos e síntese. TECH não garante verdade factual por código.
- Atualize o estado de `feature/nova-fase-validacao/README.md` para representar as duas frentes implementadas, quando de fato concluídas. Preserve a especificação, os prompts e o relatório da primeira etapa; indique separadamente avaliação semântica não executada.
- Crie `feature/nova-fase-validacao/RELATORIO_IMPLEMENTACAO_02.md`, consolidando esta etapa e a integração das duas frentes: matriz de regressões, evidência de TDD, contratos finais, comandos/resultados reais, cobertura, compatibilidade e limitações.
- Na entrega, separe **garantia programática**, **contrato de prompt** e **qualidade semântica ainda não medida**. Não declare correção dos 13 casos ou ganho de acurácia a partir de completions roteirizadas.
