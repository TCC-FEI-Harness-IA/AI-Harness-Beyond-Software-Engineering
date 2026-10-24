**Plano de correção do backend para conformidade com o Ralph Loop adaptado**

Data: 24/10/2026. Base analisada: revisão `7cc3e120330af7faba154c2f50facd35a2649720`.

**Status: planejamento. Nenhuma alteração de implementação está incluída nesta entrega.** As mudanças, contratos e testes descritos abaixo são trabalho futuro. O documento complementa a [auditoria do backend](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/ANALISE_BACKEND_RALPH_LOOP.md).

O objetivo é fazer com que toda sessão concluída pelo harness preserve as condições de aprovação, isolamento de contexto e separação de informações previstas na metodologia. O plano cobre os nove problemas confirmados na auditoria, explicita o vínculo de cada um com o paper e distingue correções de conformidade de melhorias operacionais e experimentais.

**1. Referências normativas e classificação dos problemas**

O texto acadêmico prevalece sobre o guia operacional quando houver divergência. A numeração abaixo usa os templates A.1–C.3 do texto, pois a legenda do diagrama e a descrição da seleção/resolução não usam exatamente a mesma numeração.

| Referência | Trecho do paper | Obrigação relevante |
|---|---|---|
| M-A1 | [Critérios gerais — TCC.tex:399](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:399) | Extrair e armazenar critérios de idioma, formato, restrições e conteúdo da resposta final. |
| M-A2 | [Decomposição — TCC.tex:430](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:430) | Criar tarefas autônomas de objetivo único, ordenadas e com pelo menos um critério individual. |
| M-B1 | [Resolução — TCC.tex:499](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:499) | Reinicializar contexto entre tarefas e injetar aprendizados antes da tarefa. |
| M-B2 | [Verificação local — TCC.tex:525](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:525) | Avaliar todos os critérios; reprovação exige nova tentativa no mesmo contexto da tarefa. |
| M-B3 | [Armazenamento — TCC.tex:575](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:575) | Armazenar somente a resposta aprovada, indexada por tarefa, sem nova chamada ao modelo. |
| M-B4 | [Aprendizados — TCC.tex:601](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:601) | Extrair fatos do histórico completo, incluindo interações com o validador; usar aprendizados somente no loop. |
| M-C1 | [Verificação global — TCC.tex:657](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:657) | Avaliar individualmente todos os critérios gerais sobre o conjunto de resultados aprovados. |
| M-C2 | [Planejamento adicional — TCC.tex:712](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:712) | Gerar tarefas para lacunas identificadas e retornar ao loop até o aceite global. |
| M-C3 | [Resposta final — TCC.tex:759](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:759) | Sintetizar após aprovação global, usando resultados aprovados e critérios gerais, sem fatos novos. |
| M-AV | [Avaliação — TCC.tex:787](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/docs/paper/TCC.tex:787) | Comparar inferência direta e harness nos datasets e modelos definidos, tendo acurácia como métrica principal. |

| ID | Problema | Natureza | Prioridade | Relação com o paper |
|---|---|---|---|---|
| P01 | Resultado reprovado entra em B.3 e na síntese | Violação direta | Alta | M-B2, M-B3, M-C1, M-C3 |
| P02 | C.3 executa após reprovação global | Violação direta | Alta | M-C1, M-C2, M-C3 |
| P03 | Relatórios vazios, incompletos ou contraditórios são aceitos | Violação direta | Alta | M-B2, M-C1; prejudica M-C2 |
| P04 | B.4 não recebe todos os vereditos | Violação direta | Média | M-B4 |
| P05 | Reserva e encerramento por orçamento são inconsistentes | Defeito operacional | Alta | O paper não exige reserva; a política atual pode contornar ou interromper suas etapas de modo inconsistente. |
| P06 | Teto de tarefas não vale para A.2 | Defeito operacional | Média | O paper não fixa teto; a correção deve preservar a integridade do planejamento de M-A2/M-C2. |
| P07 | Chamadas e custos de fases malsucedidas são subcontados | Defeito de medição | Média | Afeta rastreabilidade do experimento; não é violação de uma fórmula de custo exigida pelo paper. |
| P08 | Completion vazia perde consumo e não conta para o limite | Defeito operacional e de medição | Média | Afeta orçamento e rastreabilidade, não uma etapa metodológica específica. |
| P09 | Temperatura zero se transforma em 0,7 | Defeito de configuração experimental | Média | M-AV exige comparação controlada; o paper não impõe temperatura zero. |

**2. Decisões propostas para orientar a implementação**

Adotar um único comportamento de execução fiel ao método: nenhuma resposta reprovada pode ser promovida por esgotamento de recursos e nenhuma síntese pode acontecer sem aprovação global. Um modo que responde com material incompleto seria outra variante experimental e não integra este plano.

O paper descreve repetição até aprovação, mas não especifica limites nem estados de interrupção. Para viabilizar uma execução finita, a política proposta é conservar limites operacionais e encerrar a sessão sem conclusão quando forem atingidos. Essa decisão deve ser documentada como tratamento operacional adicional, sem alegar que consta do paper.

Para reduzir mudanças no contrato existente, usar o estado `FAILED` já disponível para execuções encerradas sem conclusão, com `final_answer=null` e um motivo estruturado que diferencie limite de recursos de erro técnico. Preservar a leitura de sessões antigas `DEGRADED`; o novo fluxo não deve produzir respostas finais por degradação. Um eventual estado público `INCOMPLETE` pode ser considerado em evolução futura, mas não é necessário para corrigir os desvios.

| Situação | Comportamento planejado |
|---|---|
| B.2 aprova um relatório completo e consistente | Armazenar resultado em B.3 e executar B.4. |
| B.2 reprova e ainda há recursos | Registrar feedback e repetir B.1 no mesmo contexto. |
| B.2 reprova e acabam as tentativas | Encerrar sem B.3, sem nova tarefa e sem síntese. Preservar histórico e causa da interrupção. |
| B.2/C.1 devolve estrutura inválida | Corrigir a saída do verificador dentro do limite de parsing; não tratar como veredito válido. |
| C.1 reprova e há recursos para continuar | Executar C.2 e retornar ao loop. |
| C.1 reprova e não há recursos | Encerrar sem C.3, registrando critérios pendentes e limite responsável. |
| C.1 aprova e C.3 está autorizada | Executar síntese e concluir após persistir sua saída válida. |
| C.1 aprova, mas C.3 falha ou não pode executar | Encerrar sem resposta final; aprovação global não equivale à conclusão da sessão. |
| Provedor, parsing ou persistência falha | Preservar o que puder ser registrado e não emitir sucesso. Registrar o diagnóstico disponível. |

Manter a seleção de tarefas e B.3 programáticas; Fresh Context por tarefa; retentativas de resolução na mesma janela; verificação local isolada; memória de aprendizados fora de C.1/C.2/C.3; mesma configuração de modelo nas fases; baseline com uma única inferência. Não acrescentar ferramentas externas ou uma nova fase de validação após C.3 como requisito de conformidade.

**3. P01 — Impedir que resultados reprovados sejam armazenados como aprovados**

**Problema e evidência.** Em [ralph_thinking_usecase.py:356](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/application/usecases/ralph_thinking_usecase.py:356), o limite de tentativas encerra a resolução normalmente. O chamador continua para B.3, que armazena a última tentativa em `:391`, ainda que reprovada. A marca `degraded` não é transmitida ao sintetizador.

**O que fere.** M-B3 determina que somente a resposta aprovada seja armazenada. A regra também é precondição das entradas de M-C1 e M-C3. Uma verificação global não substitui a verificação local que falhou.

**Mudanças planejadas:**

1. Tornar explícitos os desfechos da resolução: aprovação válida, repetição ou interrupção. A interrupção não poderá retornar pelo caminho de sucesso que chama B.3.
2. Exigir em B.3 que a tarefa esteja aprovada e que sua última tentativa tenha relatório validado e aprovado. A condição deve existir na fronteira de armazenamento, além do controle do orquestrador.
3. Manter a coleção de resultados aprovada separada do histórico de tentativas. Respostas reprovadas permanecem disponíveis para correção e auditoria, sem alimentar a síntese.
4. Remover do novo fluxo a promoção de `TaskResult` por `degraded`. Rever o campo e seus consumidores; não apagar registros históricos de degradação.
5. Ao esgotar tentativas, registrar tarefa, última avaliação e limite atingido; finalizar conforme a política da seção 2. Não iniciar B.4 apenas para consumir recursos depois de uma interrupção terminal.

**Arquivos afetados.** `application/usecases/ralph_thinking_usecase.py`; `domain/entities/thinking/task_result.py`, `task_attempt.py` e `task.py`; erros de domínio usados para interrupção; testes do caso de uso e das entidades afetadas. Todos os caminhos de código deste plano são relativos a `apps/backend/src`, salvo indicação contrária.

**Critérios de aceite.** Uma tarefa reprovada em todas as tentativas nunca produz evento B.3, resultado aprovado, chamada C.1/C.3 ou evento final `result`. Se a segunda tentativa for aprovada, somente ela entra em B.3. A tentativa anterior continua visível durante a correção, sem aparecer na síntese.

**4. P02 — Tornar a aprovação global obrigatória para C.3**

**Problema e evidência.** [ralph_thinking_usecase.py:469](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/application/usecases/ralph_thinking_usecase.py:469) abandona o replanejamento quando o guardião nega sua execução e, em seguida, chama C.3 mesmo após reprovação.

**O que fere.** M-C1 e M-C2 exigem corrigir as lacunas antes de avançar. M-C3 começa com todos os critérios gerais satisfeitos.

**Mudanças planejadas:**

1. Remover a transição de reprovação sem recursos para síntese. Esse caso deve ir para encerramento sem conclusão.
2. Representar explicitamente a aprovação global válida que autoriza C.3. Passar o relatório validado, ou um estado equivalente, à operação de síntese; não depender apenas de um `break` dentro do loop.
3. Associar essa aprovação ao conjunto de resultados avaliado. Qualquer alteração nos resultados invalida o aceite anterior e exige nova C.1.
4. Preservar C.1 → C.2 → loop → C.1 enquanto houver pendências e recursos. Manter as novas tarefas no topo da fila, na ordem gerada.
5. Persistir a causa de encerramento e os critérios não atendidos; concluir a persistência antes de emitir o evento terminal. Não reutilizar `result` para avisos de falha ou respostas parciais.
6. Adaptar o tratamento do WebSocket para emitir o desfecho terminal uma única vez, sem tentar finalizar novamente uma sessão já encerrada. Usar o contrato de erro existente sempre que suficiente e documentar a mudança de comportamento.

**Arquivos afetados.** Orquestrador; `domain/entities/session/session.py`; recorder e sua interface; mapper; `infra/routes/v1/message/router.py`; testes de eventos, sessões, mapeamento e rota. Acrescentar o motivo estruturado como campo opcional, preservando leitura de documentos antigos.

**Critérios de aceite.** Duas ou mais reprovações globais nunca conduzem a C.3 sem um aceite posterior. Esgotar rodadas ou orçamento termina com `final_answer=null`. Uma aprovação seguida de falha em C.3 não gera sucesso. Uma aprovação válida seguida de síntese válida gera uma única conclusão persistida.

**5. P03 — Validar os relatórios contra os critérios esperados**

**Problema e evidência.** [structured_response_parser_adapter.py:189](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/infra/adapters/structured_response_parser_adapter.py:189) permite avaliações vazias e não verifica cobertura nem coerência de `met`. `VerificationReport.approved` consulta apenas o enum. IDs desconhecidos podem ainda ser filtrados e desaparecer das pendências entregues a C.2.

**O que fere.** M-B2 e M-C1 exigem avaliar todos os critérios e aprovar somente quando todos são satisfeitos. M-C2 depende de um mapeamento real e preciso das pendências.

**Mudanças planejadas:**

1. Fornecer ao mecanismo de validação os IDs esperados como dados estruturados. Para B.2, derivá-los da tarefa corrente; para C.1, dos critérios gerais persistidos em A.1. Não reconstruí-los analisando o Markdown do prompt.
2. Estender os contratos de execução/parsing com um contexto de validação tipado, obrigatório nas fases de verificação. Propagar esse contexto pelo orquestrador, `IThinkingPhase`, `BaseThinkingPhase` e `IStructuredResponseParser`.
3. Exigir exatamente uma avaliação para cada ID esperado. Recusar avaliações vazias, IDs ausentes, desconhecidos ou repetidos.
4. Exigir que `unmet_criteria_ids` seja exatamente o conjunto dos IDs com `met=false`, também sem repetições ou IDs extras.
5. Aceitar `approved` somente quando todas as avaliações forem verdadeiras e a lista de pendências estiver vazia. Aceitar `reproved` somente quando houver pelo menos uma avaliação falsa e a lista corresponder a ela. Recusar contradições; não corrigi-las silenciosamente.
6. Executar essas verificações dentro do ciclo de correção de parsing de `BaseThinkingPhase`, antes de produzir `PhaseOutcome`. Um relatório inválido deve fazer o verificador corrigir sua saída, sem consumir uma nova tentativa de resolução B.1.
7. Proteger a entidade `VerificationReport` contra combinações internamente contraditórias; a cobertura contra os critérios esperados deve ser verificada antes de sua aceitação pelo fluxo.
8. Exigir IDs únicos nos critérios de A.1 e dentro de cada tarefa. Validar unicidade de tarefas no lote e contra tarefas já criadas na sessão antes de alterar a fila. Registrar o lote de forma atômica para uma rejeição não deixar IDs parcialmente inseridos.
9. Não filtrar silenciosamente critérios desconhecidos em C.2. A fase só deve receber pendências de um relatório contextualizado e válido.
10. Reforçar B.2/C.1 nos templates com a exigência de cobertura exata; isso complementa, mas não substitui, a validação programática.

**Arquivos afetados.** Interfaces de fase e parser; novo contrato tipado de contexto de validação; fase base; parser; `verification_report.py`; orquestrador; fila; templates B.2/C.1; doubles e testes correspondentes.

**Critérios de aceite.** Recusar relatório vazio, avaliação faltante, duplicada ou desconhecida, `approved` com `met=false`, lista de pendências incompatível e `reproved` sem pendências reais. Aceitar relatórios completos mesmo que a ordem das avaliações difira da ordem dos critérios. A correção estruturada deve operar dentro do limite configurado e consumir chamadas contabilizadas. Se as correções se esgotarem, encerrar sem B.3/C.3.

A validação estrutural não certifica a verdade semântica do julgamento do LLM. Esse limite permanece o mesmo da metodologia proposta, que utiliza o próprio modelo como verificador.

**6. P04 — Completar o histórico usado por B.4**

**Problema e evidência.** O relatório de B.2 só é copiado para o contexto de resolução depois das saídas por aprovação e por limite de tentativas, em [ralph_thinking_usecase.py:331](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/application/usecases/ralph_thinking_usecase.py:331). B.4 recebe um histórico sem o último veredito.

**O que fere.** M-B4 exige o contexto completo da tarefa, incluindo as interações com o validador.

**Mudanças planejadas:**

1. Manter B.2 em sua janela isolada, preservando sua entrada local.
2. Após cada verificação, acrescentar ao histórico da tarefa o relatório completo: decisão, avaliações, justificativas e pendências, antes de decidir entre aprovar, repetir ou interromper.
3. Distinguir o registro do relatório da instrução de correção. Acrescentar a instrução de refazer somente quando houver reprovação e uma nova tentativa for autorizada; evitar duplicar a resposta preliminar e o mesmo relatório desnecessariamente.
4. Quando houver correção de parsing dentro do verificador, preservar também esse intercâmbio no histórico da tarefa, claramente identificado como saída inválida e posterior correção. Somente o relatório validado terá efeito de controle.
5. Executar B.4 sobre esse histórico completo após o armazenamento de uma tarefa aprovada. Em interrupção terminal, preservar o histórico para auditoria, sem executar B.4 nem continuar o loop.
6. Na tarefa seguinte, injetar somente os aprendizados extraídos. Não carregar esse histórico ampliado para a próxima tarefa nem para a fase C.

**Arquivos afetados.** Orquestrador; `BaseThinkingPhase` e `PhaseOutcome` ou contrato equivalente para expor o intercâmbio da verificação; `ContextWindow`; testes de fases e do caso de uso. Não é necessário alterar a finalidade do template B.4.

**Critérios de aceite.** B.4 vê aprovação na primeira tentativa; vê reprovação e aprovação numa tarefa com retry; vê correções de saída estruturada quando existentes. Tarefa interrompida mantém o último relatório na auditoria. A próxima tarefa recebe apenas a memória compacta, e C.1/C.2/C.3 continuam sem aprendizados ou histórico de tentativas.

**7. P05 — Tornar o encerramento por orçamento consistente com o método**

**Problema e evidência.** O backend promete conclusão garantida, mas a reserva só é liberada para C.3. C.1 pode ser bloqueada antes dela; esgotamento em fases intermediárias termina por uma exceção genérica. O motivo de negação de C.2 pode ser registrado como limite de rodadas mesmo quando a causa real é tempo, chamadas ou tokens.

**O que fere.** O paper não obriga a responder quando os recursos acabam e não define uma reserva. A contradição é operacional. A correção deve preservar M-B3/M-C3, evitando usar orçamento como justificativa para ignorar validações.

**Mudanças planejadas:**

1. Aplicar a política de interrupção a todas as fases e retentativas, inclusive A.1, A.2, B.1, B.2, B.4, C.1, C.2 e C.3. Registrar fase real, tarefa, limite, consumo conhecido e pendências disponíveis.
2. Substituir a consulta booleana de planejamento adicional por um veredito com causa, aproveitando `BudgetVerdict`. Não deduzir posteriormente o motivo por uma segunda consulta parcial.
3. Usar uma única operação de autorização e registro do início de chamada para impedir divergência entre quantidade autorizada e quantidade contabilizada. A integração depende de P07/P08.
4. Tratar a reserva de C.3 como uma margem de melhor esforço, nunca como promessa de conclusão. Mantê-la fora do orçamento de trabalho e documentar que C.1 também precisa de recursos antes de C.3; a falta desses recursos deve interromper corretamente.
5. Antes de chamar o provedor, verificar saldo de chamadas, tempo restante e orçamento aplicável. Levar em conta o tamanho estimado da entrada e o teto de saída quando houver estimativa confiável; explicitar que a contabilização real pode divergir da estimativa. Sem contabilização exata antecipada, não prometer um teto estrito de tokens por requisição.
6. Limitar o timeout efetivo de uma chamada ao tempo restante da sessão quando esse controle for implementado. Uma negação não pode disparar uma nova chamada apenas para explicar o encerramento.
7. Diferenciar esgotamento do orçamento de trabalho e esgotamento do orçamento total na mensagem e no motivo estruturado; remover a afirmação incondicional de que a reserva também acabou.
8. Atualizar README e comentários que afirmam que o fluxo nunca aborta e sempre produz resposta.

**Arquivos afetados.** `cost_guard_interface.py`, `cost_guard_adapter.py`, `cost_budget.py`, `budget_verdict.py`, `budget_exceeded_error.py`; orquestrador e fase base; configuração, contratos de timeout quando necessários, recorder e testes com guardião real.

**Critérios de aceite.** No cenário de orçamento 100, reserva 25 e consumo 75 antes da próxima tarefa, encerrar sem nova inferência, com causa correta e sem C.3 forçada. Exercitar também limites em B.2, B.4 e C.3, teto de chamadas e tempo esgotado. Toda interrupção termina uma única vez, sem sucesso e sem consumir chamadas posteriores ao bloqueio.

**8. P06 — Aplicar o limite de tarefas ao plano inteiro, desde A.2**

**Problema e evidência.** A.2 enfileira todas as tarefas em [ralph_thinking_usecase.py:206](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/application/usecases/ralph_thinking_usecase.py:206); o corte por slots existe somente em C.2 e descarta silenciosamente parte do plano.

**O que fere.** Não existe teto de tarefas no paper. Trata-se de falha do limite configurado. Uma correção que simplesmente corta tarefas pode comprometer a decomposição de M-A2 e a cobertura das lacunas de M-C2.

**Mudanças planejadas:**

1. Calcular slots disponíveis antes de solicitar A.2/C.2 e informar o máximo aceito no contexto de validação e nos respectivos templates.
2. Validar o tamanho do lote antes de alterar fila e contadores. Aplicar a mesma regra nas duas fases, incluindo unicidade dos IDs e atomicidade previstas em P03.
3. Se o modelo exceder o limite, pedir correção do plano dentro do limite de saídas estruturadas. Orientar a preservar autonomia e objetivo único; não exigir que tarefas independentes sejam fundidas artificialmente para caber.
4. Se não for possível obter um plano válido dentro dos recursos, interromper sem enfileirar um subconjunto silencioso. Tratar isso como limitação operacional do experimento, não como prova de que a pergunta não possui decomposição válida.
5. Eliminar o truncamento silencioso de C.2. Se não houver slots, nem chamar o planejador; registrar o limite responsável.
6. Contabilizar somente tarefas de lotes aceitos, preservando o total de tarefas já criadas mesmo depois de executadas.

**Arquivos afetados.** Orquestrador; parser/contexto de validação; fila; guardião; templates A.2/C.2; testes desses componentes.

**Critérios de aceite.** Com teto 1 e lote de duas tarefas, não executar duas tarefas nem selecionar a primeira silenciosamente. Aceitar lote corrigido dentro do teto; interromper se não houver correção válida. Rejeição de um lote não altera fila, IDs conhecidos ou contadores. C.2 respeita os slots remanescentes após A.2.

**9. P07 — Registrar cada chamada, inclusive quando a fase falha**

**Problema e evidência.** [base_thinking_phase.py:125](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/application/phases/base_thinking_phase.py:125) agrega várias chamadas em um resultado de fase. [session_totals.py:46](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/domain/entities/session/session_totals.py:46) conta mensagens com tokens como chamadas. Fases sem resultado válido não gravam seu consumo na sessão.

**O que fere.** O paper define acurácia como métrica principal e não exige esses contadores. O problema afeta a fidelidade dos registros e análises auxiliares de custo, além da verificação dos limites operacionais.

**Mudanças planejadas:**

1. Separar o registro de invocação do registro de mensagem/evento de fase. Definir um registro por chamada com ID, fase, tarefa, contexto, modelo/provedor, início, duração, desfecho e uso de tokens quando conhecido.
2. Registrar início após autorização e antes do envio ao provedor; completar o registro ao receber resposta ou erro. Recusas locais antes do envio não contam como invocação externa.
3. Gravar consumo e tempo conhecidos antes de interpretar JSON ou avaliar sua consistência. Falha de parsing não pode eliminar custo.
4. Derivar `total_llm_calls` dos registros de invocação, não da presença de tokens em uma mensagem. Uso ausente deve ser identificável como desconhecido, sem presumir custo real zero.
5. Definir uma única fonte para somar tokens e tempo da sessão. Se `PhaseOutcome` mantiver agregados para exibição, não somá-los novamente nos totais persistidos.
6. Fazer o guardião e a sessão acompanhar os mesmos inícios e consumos, com IDs que evitem registros duplicados. O guardião limita a execução; o recorder persiste a auditoria desse mesmo consumo.
7. Aplicar o registro ao baseline também, preservando sua única chamada. Não acrescentar retries automáticos ao baseline para simetrizar o harness.
8. Atualizar mapper e leitura de sessões com compatibilidade: documentos antigos sem registros individuais continuam legíveis e mantêm seus totais históricos, identificados como legados. Não inventar as chamadas ausentes de execuções passadas.

**Arquivos afetados.** Novos registros de invocação no domínio; fase base e baseline; interfaces/adapter de recorder e guardião; `PhaseOutcome`; entidades de sessão e totais; mapper; startups; testes de persistência JSON/Mongo e consulta.

**Critérios de aceite.** Uma execução mínima com um retry de parsing registra oito chamadas, não sete. Três respostas inválidas em A.1 preservam três chamadas e os 45 tokens conhecidos na sessão falha. Chamada com uso desconhecido ainda conta como chamada. Guardião e sessão concordam quanto aos consumos conhecidos. Eventos agregados não duplicam tokens nem chamadas. Sessões antigas continuam consultáveis.

**10. P08 — Preservar custo e tempo de completions vazias**

**Problema e evidência.** [base_chat_completions_service.py:123](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/infra/services/base_chat_completions_service.py:123) descarta os dados de uso ao lançar `EmptyCompletionError`. A fase repete a chamada sem registrar esses dados nem consumir o contador de chamadas.

**O que fere.** Não há uma etapa específica do paper violada por texto vazio. A implementação perde custos reais e permite exceder um limite configurado; essa lacuna afeta tanto a operação quanto a rastreabilidade experimental.

**Mudanças planejadas:**

1. Extrair e preservar os dados da resposta do provedor antes de rejeitar conteúdo vazio: uso conhecido, `finish_reason` e identificadores disponíveis.
2. Ampliar o erro tipado de completion vazia para transportar esses metadados, ou disponibilizá-los pelo contrato de resultado da invocação de P07. A rejeição de conteúdo vazio deve continuar explícita.
3. Completar o registro da chamada e atualizar o guardião antes de decidir pelo retry. Registrar duração mesmo quando não houver texto.
4. Não anexar uma mensagem de assistente vazia ao contexto. Preservar os metadados na auditoria, sem inventar conteúdo ou tokens que o provedor não forneceu.
5. Autorizar o retry como outra chamada e aplicar os limites normalmente. No baseline, preservar a chamada única e encerrar com erro após uma completion vazia, mantendo seu consumo conhecido.

**Arquivos afetados.** Serviço base de provedores; `EmptyCompletionError`; contratos de resposta/adapters LLM; fase base; baseline; registros de chamada; testes de contrato de provedores e integração.

**Critérios de aceite.** Com uma completion vazia de 140 tokens e sete respostas válidas de 15 tokens, um orçamento suficientemente alto registra oito chamadas e 245 tokens. Com teto de sete chamadas, a oitava não é enviada; a execução termina sem sucesso, preservando o consumo das sete invocações realizadas. Executar esses cenários com transporte HTTP simulado e `CostGuardAdapter` real.

**11. P09 — Respeitar a temperatura solicitada**

**Problema e evidência.** [model_config_dto.py:35](/Users/vitorvianna/programs/fei/tcc/AI-Harness-Beyond-Software-Engineering/apps/backend/src/infra/routes/v1/message/dtos/model_config_dto.py:35) usa `if not value`, confundindo zero com ausência. Outras camadas também arredondam a temperatura para uma casa decimal.

**O que fere.** Não viola uma temperatura exigida pelo paper, que não existe. Viola a configuração solicitada e prejudica o controle dos parâmetros usado na comparação de M-AV. Baseline e harness sofrem a mesma alteração, o que não torna a transformação correta.

**Mudanças planejadas:**

1. Aplicar o default somente ao campo ausente ou `None`, conforme o contrato público escolhido; preservar zero.
2. Remover arredondamentos silenciosos do DTO, do adapter e de `LLMProviderRequest`, mantendo o valor validado até o payload do provedor.
3. Preservar a faixa atualmente suportada sem ampliá-la neste trabalho. Recusar valores não finitos e entradas inválidas de modo consistente.
4. Registrar a configuração efetivamente enviada à inferência e atualizar a documentação do endpoint.

**Arquivos afetados.** DTO de modelo; `llm_completions_adapter.py`; `llm_provider_request.py`; documentação; testes do DTO, adapter, payloads e caminhos baseline/harness.

**Critérios de aceite.** `0` chega como `0` ao provedor em ambos os fluxos; `0.25` continua `0.25`; ausência recebe o default documentado. Valores inválidos são rejeitados. A sessão registra a configuração utilizada.

**12. Sequência de execução futura e dependências**

| Lote | Trabalho | Dependências | Condição para encerrar o lote |
|---|---|---|---|
| L0 | Fixar política da seção 2, invariantes e cenários de regressão | Nenhuma | Comportamentos esperados inequívocos; reproduções dos desvios documentadas. |
| L1 | P03: contratos de validação, consistência e correção dos roteiros de teste | L0 | Nenhum relatório incompleto ou contraditório autoriza avanço. |
| L2 | P01/P02: armazenamento condicionado, síntese condicionada e encerramento | L1 | Nenhuma reprovação ou interrupção produz resposta final homologada. |
| L3 | P04: histórico completo, mantendo isolamento | L1/L2 | B.4 recebe todos os intercâmbios previstos; demais contextos continuam isolados. |
| L4 | P07/P08: registro por chamada e completions vazias | L0; compatível com L1–L3 | Contagem e consumo preservados, inclusive nas falhas, sem duplicação. |
| L5 | P05/P06: orçamento, causas de negação e integridade dos planos | L2/L4; validação de L1 | Guardião real respeita limites e encerra sem contornar validações. |
| L6 | P09: parâmetros experimentais | Independente; consolidar após L4 | Payload, configuração persistida e valor solicitado coincidem. |
| L7 | Integração completa, compatibilidade e atualização da documentação | L1–L6 | Matriz de aceite satisfeita e verificações do projeto aprovadas. |

A implementação deve ser dividida em mudanças revisáveis por lote. A sequência é uma proposta de execução futura; este documento não inicia nenhum desses lotes.

**13. Plano de testes e evidências de conclusão**

Os 830 testes e a cobertura de 100% foram resultados da auditoria anterior, não prova de que as correções já existem. Ao implementar, alterar as expectativas que hoje consolidam os desvios: aceitação de tarefa degradada, síntese sem aceite global, avaliações vazias e filtragem silenciosa de critérios desconhecidos. Corrigir o roteiro feliz para avaliar todos os critérios gerais e usar os IDs próprios de cada tarefa.

| Cenário obrigatório | Evidência esperada |
|---|---|
| Fluxo regular com várias tarefas | Ordem das fases preservada; síntese baseada apenas em resultados aprovados. |
| Reprovação local seguida de aprovação | Mesmo contexto de resolução; feedback visível; somente a última resposta aprovada em B.3. |
| Esgotamento de tentativas locais | Sem B.3/C.3; falha persistida com tarefa e causa. |
| Reprovação global seguida de replanejamento bem-sucedido | Novas tarefas no topo, aprendizados preservados e nova aprovação global antes da síntese. |
| Esgotamento de replanejamento | Sem resposta final; critérios pendentes disponíveis no diagnóstico. |
| Relatório vazio, omisso, duplicado, desconhecido ou contraditório | Correção estruturada ou erro terminal; nunca aprovação. |
| Histórico de B.4 e isolamento | Todos os vereditos e correções presentes; nenhum histórico bruto na próxima tarefa ou na síntese. |
| Limite atingido em cada fase e em retries | Nenhuma chamada posterior indevida; causa correta; conclusão única sem sucesso. |
| Plano inicial/adicional excedente | Correção ou interrupção, sem truncamento silencioso e sem mutação parcial da fila. |
| Parsing malsucedido e completions vazias | Chamadas, tokens conhecidos e duração preservados; guardião e sessão consistentes. |
| Temperatura zero e fracionária | Valor preservado até HTTP e na sessão, para ambos os fluxos. |
| Persistência e transmissão | JSON/Mongo preservam registros e motivos; consulta de sessão coincide com persistência; WebSocket não emite resultado em falha. |
| Compatibilidade | Sessões anteriores, inclusive `DEGRADED`, continuam legíveis sem reclassificação retroativa. |

Usar os componentes reais de parser, templates, guardião, fila e recorder nos testes de integração; simular apenas fronteiras externas, relógio e respostas de modelo quando necessário. Nos testes de orçamento, não reativar manualmente um guardião negado para permitir a conclusão.

Após cada lote, executar os testes diretamente afetados. Na integração final, executar a suíte completa e o lint exigidos pelo backend, mantendo o requisito de cobertura configurado. Não reduzir o limiar para acomodar caminhos não exercitados.

Um smoke test futuro com modelo real pode complementar a avaliação qualitativa dos prompts, mas não substitui testes determinísticos de invariantes. Chamadas externas e execução de benchmarks não fazem parte da entrega deste plano.

**14. Pontos complementares, separados das nove correções**

**Medição de contexto.** `ContextWindow.context_size` representa consumo acumulado, não comprimento atual da janela. Planejar uma mudança de nome/documentação ou introduzir campos separados para consumo, último tamanho de entrada reportado e eventual estimativa atual. Não apresentar consumo acumulado como evidência de redução de context rot. Como há consumidores do DTO de contexto, uma mudança de contrato exige avaliar compatibilidade com o frontend antes de implementá-la. Isso não impede corrigir as invariantes do loop.

**Avaliação experimental.** O backend não contém executor MMLU/GPQA nem cálculo de acurácia. Planejar essa entrega separadamente, verificando primeiro se existe executor fora de `apps/backend`. Ele deverá fixar amostras e parâmetros, comparar as duas estratégias e registrar versão dos templates, configuração de limites e identificação de dataset/amostra. Definir antes dos resultados como falhas entram no denominador; registrar taxa de conclusão separadamente. Não excluir silenciosamente falhas ou sessões degradadas do conjunto avaliado.

**Ambiguidades do paper.** Esclarecer em revisão editorial futura o exemplo de aprendizados de B.4, que inclui fatos de tarefas ainda não executadas, e a fronteira entre raciocínio permitido em C.1 e síntese sem raciocínio novo em C.3. Especificar também como preservar o enunciado necessário e o mapeamento de alternativas para a síntese. Essas decisões podem exigir ajuste de contratos/prompts, mas não devem ser introduzidas silenciosamente como se fossem exigências já claras da metodologia. O paper não será alterado por este plano.

**Compactação de aprendizados.** Deduplicação e limites próprios da memória podem ser investigados depois, com avaliação do efeito na retenção de fatos. A metodologia não define uma política quantitativa, portanto essa melhoria não será usada como condição artificial para considerar os nove problemas corrigidos.

**15. Critério final de conformidade**

A adequação estará concluída quando uma sessão `COMPLETED` representar um fluxo com resultados localmente aprovados, relatório global completo e consistente aprovado, síntese válida e persistência concluída; e quando toda execução interrompida permanecer identificada como não concluída, sem promover insumos reprovados ou emitir uma resposta final indevidamente homologada.

Os testes devem demonstrar também que o Fresh Context e a separação de aprendizados foram preservados e que os registros não ocultam chamadas ou consumo conhecido. A documentação precisa refletir essas garantias e seus limites. Esse aceite atesta fidelidade estrutural ao método; a hipótese de melhora de acurácia continua dependente dos experimentos definidos no paper.
