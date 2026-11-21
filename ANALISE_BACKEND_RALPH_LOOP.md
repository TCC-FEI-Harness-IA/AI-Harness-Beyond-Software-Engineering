**Auditoria de conformidade do backend com o Ralph Loop adaptado**

Data: 24/10/2026. Revisão analisada: `7cc3e120330af7faba154c2f50facd35a2649720`.

**Parecer: implementação parcialmente conforme.** A arquitetura reproduz o planejamento, o loop por tarefa, o Fresh Context, a separação entre resultados e aprendizados e o replanejamento. Entretanto, o backend não preserva todas as condições de aprovação exigidas pela metodologia: permite sintetizar respostas reprovadas, finalizar sem aprovação global e aceitar relatórios de verificação incompletos ou contraditórios. Também entrega a B.4 um histórico incompleto das verificações.

Essas diferenças impedem afirmar que todas as execuções atuais representam fielmente o método descrito no paper. Marcar uma sessão como `degraded` torna a exceção observável, mas não transforma a execução em uma execução conforme.

**Escopo e evidências**

A revisão abrangeu os 137 arquivos Python de `apps/backend/src`, incluindo interfaces e arquivos de inicialização, os oito templates, a configuração de execução, persistência, provedores, API, baseline e documentação do backend. Foram inspecionados os testes pertinentes às invariantes e aos caminhos de exceção, e executada a suíte completa. A referência normativa foi a seção Metodologia de `docs/paper/TCC.tex`, cotejada com `RALPH_LOOP_ADAPTADO.md`. A metodologia de avaliação foi examinada separadamente.

Comando executado em `apps/backend`:

```sh
.venv/bin/python -m pytest
```

Resultado: **830 testes passaram em 3,21 segundos; cobertura de 100% segundo a configuração do projeto**, que exclui interfaces, arquivos `__init__.py` e linhas abstratas. Cobertura de código não demonstra conformidade metodológica nem qualidade das respostas do LLM.

Também foram executados 11 cenários adicionais de diagnóstico, utilizando o orquestrador, fases, parser, templates e `CostGuardAdapter` reais, com respostas de LLM programadas, relógio controlado e persistência em memória. Um cenário utilizou os adapters de provedor reais com `httpx.MockTransport`. Não houve chamadas a provedores externos. O script temporário está em `/tmp/ralph_backend_audit.py`; os resultados relevantes estão registrados abaixo. Nenhum código de produção ou teste existente foi alterado.

**Conformidade por etapa**

| Etapa ou requisito | Avaliação | Evidência e ressalva |
|---|---|---|
| A.1: critérios gerais a partir da pergunta | Conforme estruturalmente | Contexto próprio; template pede idioma, formato, restrições e conteúdo; critérios mantidos em memória. |
| A.2: tarefas autônomas, ordenadas e com critérios | Conforme estruturalmente | Template exige objetivo único, entradas, saídas, autossuficiência e restrições de escopo; parser exige lista de tarefas e critérios não vazios. Qualidade semântica depende do modelo. |
| Seleção da próxima tarefa | Conforme | `TaskQueue.pop_next()` e checagem da fila são programáticos. |
| Fresh Context entre tarefas | Conforme | Nova instância de `ContextWindow`; aprendizados vêm antes do prompt da tarefa; histórico bruto da tarefa anterior não é reutilizado. |
| B.1: resolução limitada à tarefa | Conforme estruturalmente | Recebe tarefa e critérios; template proíbe antecipar a solução global. |
| B.2: reprovação e retentativa no mesmo contexto | Parcial | As tentativas e o feedback permanecem no contexto de resolução. Há falhas no aceite dos relatórios e na política de esgotamento. |
| B.3: somente resultados aprovados, indexados por tarefa | Não conforme em degradação | O dicionário é indexado por tarefa e a operação não chama LLM, mas recebe a última tentativa mesmo quando reprovada. |
| B.4: extração sobre todo o histórico da tarefa | Parcial | Inclui respostas anteriores e feedback das reprovações seguidas de retry; omite o veredito final de aprovação e a última reprovação quando há degradação. |
| Aprendizados exclusivos da execução | Conforme na separação de estados | Memória de aprendizados não é enviada a C.1, C.2 ou C.3. Resultados de B.3 são um estado separado. |
| C.1: verificar todos os critérios gerais | Parcial | Entradas e template corretos; o código aceita avaliações ausentes, IDs incorretos e contradições. |
| C.2: planejar lacunas e retornar ao loop | Conforme no caminho regular | Recebe critérios pendentes e resultados; insere tarefas no topo; preserva aprendizados. Depende da validade do relatório de C.1. |
| C.3: sintetizar somente após aprovação global | Não conforme em degradação | Template é fiel ao paper, mas a condição de entrada pode ser ignorada. |
| Mesmo modelo ao longo do harness; ausência de ferramentas externas | Conforme estruturalmente | Parâmetros da requisição são configurados em todas as fases; execução utiliza chamadas de chat, sem ferramentas externas. |
| Baseline de inferência única | Conforme estruturalmente | `DefaultMessageUseCase` realiza uma chamada com a pergunta original. |
| Avaliação MMLU/GPQA | Não implementada neste diretório | Há endpoints para executar e consultar sessões, mas não um executor de datasets, comparação com gabaritos ou cálculo de acurácia. Isso pode pertencer a um componente externo. |

Referências de implementação: `src/application/usecases/ralph_thinking_usecase.py`, `src/application/phases/`, `src/domain/services/`, `src/infra/templates/` e `src/infra/startups/ralph_thinking_startup.py`, todos sob `apps/backend`.

**1. Alta prioridade — Resultados explicitamente reprovados entram na síntese**

O paper exige que somente a resposta aprovada em B.2 seja armazenada em B.3 e consumida pela fase C. Ver [TCC.tex:575](docs/paper/TCC.tex).

Em `ralph_thinking_usecase.py:356–367`, esgotar as tentativas marca a tarefa como `DEGRADED` e retorna normalmente. O chamador executa B.3 incondicionalmente, em `:294`, e `__store_result`, em `:391–395`, armazena a última tentativa. `__render_results`, em `:996–1005`, inclui todos os resultados e nem sequer transmite a marca `degraded` ao modelo de C.1/C.3.

Reprodução: com uma tentativa permitida e B.2 retornando `reproved`, o texto `RESULTADO_REPROVADO` apareceu tanto na entrada de C.1 quanto na de C.3; a sessão terminou como `degraded`.

Impacto: a síntese perde a garantia de usar exclusivamente insumos homologados. C.1 verifica critérios globais, não substitui a aprovação dos critérios locais que falharam.

Correção recomendada: condicionar B.3 à aprovação efetiva. Ao atingir um limite, registrar uma execução incompleta/falha ou definir uma política explícita de recuperação, mantendo resultados reprovados fora da coleção de aprovados. Uma variante que sintetiza material não aprovado deve ser descrita e avaliada como variante do método.

**2. Alta prioridade — C.3 é executada mesmo com C.1 reprovada**

O paper condiciona a construção da resposta final ao atendimento integral dos critérios gerais; uma reprovação deve conduzir a planejamento adicional. Referências: `TCC.tex:653`, `:714` e `:761`.

Em `ralph_thinking_usecase.py:469–484`, quando `can_run_additional_planning()` retorna falso, o fluxo registra degradação, sai do loop e executa `__run_final_answer()` mesmo sem aprovação global. C.3 não recebe a lista de pendências nem o motivo da degradação; recebe os mesmos resultados e critérios do caminho aprovado.

Reprodução: uma rodada adicional permitida, duas reprovações consecutivas de C.1 e nenhum aceite global. C.3 foi executada e entregou uma resposta; status final `degraded`.

Correção recomendada: tornar a aprovação global uma precondição explícita de C.3 no modo que implementa o paper. Limites operacionais são razoáveis, mas precisam encerrar a execução como não concluída ou conduzir a uma variante de fallback identificada e documentada. Aumentar os limites apenas adia o problema.

**3. Alta prioridade — O aceite não garante que todos os critérios foram avaliados e satisfeitos**

B.2 e C.1 devem avaliar cada critério e aprovar somente quando todos são atendidos (`TCC.tex:527` e `:659–670`).

`structured_response_parser_adapter.py:189–231` valida os tipos e a relação entre `decision` e a presença de itens em `unmet_criteria_ids`. Porém, permite `criteria_evaluation` vazia; não cruza `met` com a decisão; não verifica cobertura, unicidade ou pertencimento dos IDs aos critérios esperados. `VerificationReport.approved`, em `verification_report.py:28`, consulta apenas o enum da decisão.

Estas duas saídas foram aceitas tanto em B.2 quanto em C.1 e produziram sessões `completed`:

```json
{"decision":"approved","criteria_evaluation":[],"unmet_criteria_ids":[]}
```

```json
{"decision":"approved","criteria_evaluation":[{"criterion_id":"INEXISTENTE","met":false,"justification":"nao atende"}],"unmet_criteria_ids":[]}
```

Também é possível reprovar um ID desconhecido. Em `ralph_thinking_usecase.py:813–818`, esse ID é filtrado e C.2 recebe uma lista vazia de pendências, apesar da reprovação.

Correção recomendada: validar cada relatório contra os critérios esperados da chamada. Exigir uma avaliação por ID, sem omissões, repetições ou IDs extras; exigir que `unmet_criteria_ids` corresponda exatamente às avaliações com `met=false`; derivar ou validar a decisão a partir dessas avaliações. Validar também a unicidade dos IDs produzidos por A.1/A.2/C.2. Relatórios inválidos devem provocar correção estruturada, não aprovação.

Essa validação é determinística e não exige um segundo LLM. Ela não garante que o julgamento semântico do modelo esteja correto, mas impede que uma estrutura contraditória seja tratada como verificação bem-sucedida.

**4. Média prioridade — B.4 não recebe todas as interações com o validador**

O paper define a entrada de B.4 como o contexto completo, incluindo interações com o validador (`TCC.tex:603–612`).

B.2 roda em uma janela separada (`ralph_thinking_usecase.py:331–337`). Essa separação, por si só, é compatível com a expressão conceitual de entrada de B.2 e não foi classificada como erro. O problema é que o relatório só é copiado para o contexto da tarefa em `:369–379`, após os retornos por aprovação e por esgotamento de tentativas. B.4 recebe esse contexto em `:427`.

Reprodução: uma reprovação seguida de aprovação. O histórico enviado a B.4 continha as duas respostas e a justificativa da reprovação, mas não a justificativa da aprovação. Se a tarefa é aprovada na primeira tentativa, B.4 não recebe nenhum relatório de B.2. A última reprovação de uma tarefa degradada também fica de fora.

Correção recomendada: anexar o relatório de cada verificação ao histórico da tarefa antes de qualquer retorno, ou construir explicitamente a entrada completa de B.4. É possível preservar o isolamento do verificador e, simultaneamente, manter o histórico exigido para a extração.

**5. Alta prioridade operacional — A reserva não garante a conclusão e a degradação pode terminar em erro**

Essa é uma falha da política adicional de resiliência implementada pelo backend, não uma exigência de orçamento presente no paper. O README afirma que o fluxo sempre degrada e conclui e que a reserva garante C.3.

Após interromper o loop por orçamento, `__run_synthesis()` ainda chama C.1 (`ralph_thinking_usecase.py:451–454`). `CostGuardAdapter` aplica a C.1 o mesmo teto sem reserva que bloqueou B.1 (`cost_guard_adapter.py:165–179`). A fase levanta `BudgetExceededError` e o caso de uso termina como `failed`. Esgotamento durante B.1, B.2 ou B.4 também sobe como exceção, sem tratamento específico de transição para encerramento.

Reprodução: orçamento total 100, reserva 25 e chamadas de 15 tokens. Após A.1, A.2, B.1, B.2 e B.4, foram consumidos 75 tokens. A tarefa seguinte foi descartada e uma degradação foi registrada; C.1 foi bloqueada, a sessão terminou `failed` e C.3 nunca rodou, embora a reserva de 25 tokens permanecesse disponível.

Além disso, C.3 continua sujeita aos limites de tempo e quantidade de chamadas, para os quais não existe reserva. A autorização verifica apenas consumo passado, sem estimar a próxima entrada e saída; uma chamada autorizada também pode ultrapassar o saldo restante.

Correção recomendada: definir primeiro a política metodológica de encerramento. No modo estrito, registrar a interrupção de forma consistente, sem fingir conclusão. Se houver modo de fallback, reservar capacidade para todo o caminho necessário, incluindo chamadas e contexto, e tratar esgotamento em qualquer fase. A mensagem de `BudgetExceededError` também deve distinguir esgotamento do orçamento de trabalho de esgotamento da reserva.

Há uma imprecisão adicional: `__planning_limit()` (`ralph_thinking_usecase.py:669–680`) só distingue falta de slots e limite de rodadas; quando C.2 é negada por tokens, chamadas ou tempo, o motivo registrado pode ser incorreto.

**6. Média prioridade operacional — O limite total de tarefas não restringe o plano inicial**

`ralph_thinking_usecase.py:206–208` enfileira todas as tarefas de A.2 e só depois registra a quantidade. `CostGuardAdapter.authorize()` não consulta esse limite. O corte por slots existe somente em C.2 (`:500–502`).

Reprodução: `max_tasks_per_session=1`, A.2 gerando duas tarefas, orçamento suficiente. As duas tarefas foram executadas e a sessão terminou `completed`.

Correção recomendada: validar o tamanho do plano inicial contra os slots disponíveis e definir uma resposta explícita para excesso. Um plano truncado não deve ser tratado silenciosamente como plano completo; a insuficiência precisa permanecer visível para o controle global.

**7. Média prioridade experimental — Sessões subcontam chamadas e perdem consumo de fases que falham**

`BaseThinkingPhase.execute()` acumula tokens de várias tentativas de parsing em um único `PhaseOutcome` (`base_thinking_phase.py:125–166`). O caso de uso grava uma única mensagem por fase concluída (`ralph_thinking_usecase.py:704`). `SessionTotals.add_message()` incrementa `total_llm_calls` apenas uma vez por mensagem com tokens (`session_totals.py:46–47`).

Reprodução: uma resposta JSON inválida seguida de correção e conclusão normal resultou em **8 chamadas reais e 7 chamadas persistidas**. Nesse caso, os tokens das chamadas com texto foram corretamente somados: 120.

Se a fase esgota as retentativas, ela não retorna `PhaseOutcome` e seu consumo não é gravado na sessão. Reprodução: três respostas inválidas em A.1 consumiram 45 tokens reportados pelo dublê; a sessão `failed` persistiu **0 chamadas e 0 tokens**. Chamadas bem-sucedidas com uso de tokens ausente/zero também não são contadas pelo critério atual.

Correção recomendada: registrar cada invocação e seu consumo independentemente de o parsing ou a fase concluírem, e contar chamadas explicitamente. Manter o evento de fase como uma agregação separada. Isso melhora rastreabilidade e permite comparar custos sem ocultar falhas.

**8. Média prioridade operacional e experimental — Completions vazias descartam uso de tokens e escapam do contador de chamadas**

`BaseChatCompletionsService.generate_response()` lê `usage`, mas rejeita texto vazio antes de construir `LLMProviderResponse` (`base_chat_completions_service.py:123–138`). A exceção não carrega o consumo. `BaseThinkingPhase` repete a chamada sem contabilizar custo (`base_thinking_phase.py:132–136`); `register_call()` só é executado após retorno normal do adapter (`:215`).

Reprodução com HTTP simulado e adapters reais: uma resposta sem conteúdo com `usage` de 140 tokens, seguida das sete respostas válidas de uma execução mínima. Mesmo com teto de sete chamadas, ocorreram **8 requisições HTTP**, a sessão terminou `completed` e registrou **105 tokens em vez dos 245 informados pelo provedor**.

Correção recomendada: preservar o uso e o tempo da chamada mesmo quando o conteúdo é inutilizável; contar a invocação antes da validação de conteúdo e de schema. A decisão de repetir uma completion vazia não deve apagar o custo da chamada anterior.

**9. Média prioridade experimental — Temperatura zero é alterada para 0,7**

Em `model_config_dto.py:35–36`, `if not value` trata `0` como ausência. Reprodução: uma requisição com `temperature=0` gerou DTO com `temperature=0.7`.

Isso afeta tanto baseline quanto harness e impede executar a configuração de temperatura zero pela API como solicitada. Não é uma divergência direta do algoritmo do paper, que não fixa essa temperatura, mas compromete o controle dos parâmetros experimentais.

Correção recomendada: distinguir ausência/`None` de zero. Rever também o arredondamento obrigatório para uma casa decimal nos DTOs/adapters se o experimento precisar preservar o valor exato solicitado.

**Observações metodológicas e de medição que não devem ser confundidas com os defeitos acima**

A separação entre resultados e aprendizados está correta. O dicionário de resultados e a memória de aprendizados são estados diferentes; `__synthesis_variables()` só inclui resultados e critérios gerais. Registrar tentativas no histórico de auditoria da sessão não equivale a injetá-las na síntese. O desvio demonstrado é a entrada da tentativa reprovada na própria coleção de resultados de B.3.

As instruções de A.2, B.1, B.4 e C.3 traduzem adequadamente as responsabilidades descritas no paper. A autonomia das tarefas, a qualidade dos fatos extraídos e a proibição de novos fatos em C.3 dependem também do comportamento do modelo. O paper propõe essa orientação por templates; não exige um validador pós-C.3. Portanto, a ausência dessa fase adicional não foi classificada como uma etapa obrigatória faltante.

`ContextWindow.context_size` (`context_window.py:32–55`) mede consumo acumulado das chamadas daquela janela, somando novamente tokens do histórico reenviado. Isso não é o tamanho corrente do contexto. Exemplo contábil: usos de 100+20 e 150+10 produzem 280 no campo; a última chamada teve 150 tokens de entrada e 10 de saída. O reset continua funcionando, mas esse indicador não deve ser usado como medida direta de comprimento da janela ou de mitigação de context rot. Seria melhor separar consumo acumulado e tamanho estimado/medido da entrada corrente.

A memória de aprendizados acumula os itens retornados pelo modelo, sem deduplicação ou limite próprio. A concisão é solicitada pelo template, não garantida programaticamente. O paper também não define uma política quantitativa de compactação; isso é uma oportunidade de robustez, não uma não conformidade inequívoca.

A própria especificação contém ambiguidades: o exemplo de B.4 proíbe conceitos óbvios, mas aceita uma definição elementar de número primo, e atribui ao momento após T1 fatos sobre pares e maiores que 2. Em C.1, o exemplo permite inferir a interseção dos conjuntos, enquanto C.3 é proibida de realizar raciocínio novo e não recebe a justificativa de C.1. Também não há um contrato explícito garantindo que A.1 preserve o mapeamento completo das alternativas para a síntese, que não recebe a pergunta original. Esses pontos devem ser esclarecidos no paper e nos exemplos; não foram imputados ao backend como violações isoladas.

**Por que os testes atuais não detectam os desvios**

Os testes confirmam corretamente Fresh Context, preservação de retentativas, separação de aprendizados, ordem das fases e persistência. Entretanto, algumas expectativas incorporam os próprios desvios:

| Teste | Comportamento atualmente esperado |
|---|---|
| `test_ralph_thinking_usecase.py:476` | A última resposta reprovada aparece em C.1 após esgotar tentativas. |
| `test_ralph_thinking_usecase.py:510` | O fluxo entrega resposta após esgotar planejamento, ainda com reprovação global. |
| `test_structured_response_parser_adapter.py:220` | Um relatório aprovado com avaliações vazias é aceito. |
| `test_ralph_thinking_usecase.py:753` | Um ID de critério desconhecido vira uma lista vazia de pendências em C.2. |
| `test_ralph_thinking_usecase.py:783` | B.4 contém o feedback de uma reprovação, sem exigir o relatório final de aprovação. |
| `test_ralph_thinking_usecase.py:572` | O orçamento de tokens usa `FakeCostGuard`, cujo `authorize()` continua aprovando quando `tokens_left` é zerado. |
| `test_ralph_thinking_usecase.py:592` | O teste reativa manualmente a autorização depois do evento de degradação, comportamento inexistente no guardião real. |

Além disso, o roteiro feliz do teste do caso de uso usa uma avaliação `AC1` para dois critérios gerais e reutiliza `T1-AC1` em verificações de outras tarefas. Portanto, também precisa ser ajustado ao endurecer a validação. Os testes de ponta a ponta usam respostas programadas: verificam integração e persistência, não o desempenho semântico dos prompts.

**Ordem recomendada para adequação**

1. Estabelecer um modo fiel ao paper: B.3 somente após aprovação local, C.3 somente após aprovação global e encerramento explícito quando limites impedirem continuar. Documentar qualquer fallback como extensão do método.
2. Validar cobertura e consistência dos critérios em B.2/C.1 e corrigir os roteiros de teste que hoje aceitam relatórios inválidos.
3. Completar o histórico de B.4 com todos os vereditos e verificar que essa informação continua restrita ao loop.
4. Corrigir a política de orçamento, o teto de A.2 e o registro por chamada, incluindo parsing malsucedido e completions vazias. Exercitar esses caminhos com o `CostGuardAdapter` real.
5. Preservar temperatura zero e registrar os parâmetros necessários para reprodução. Para uma auditoria experimental mais forte, incluir versão dos templates, configuração de limites, provedor efetivo e identificação de amostra/dataset; a sessão atual guarda apenas parte desse contexto.
6. Implementar ou conectar o executor MMLU/GPQA e estabelecer previamente como execuções degradadas e falhas entram no cálculo de acurácia. Simplesmente excluí-las após observar o resultado pode enviesar a comparação.

O backend oferece uma base coerente para o harness proposto, mas as garantias centrais de aprovação ainda precisam ser corrigidas antes de apresentar suas execuções, sem ressalvas, como implementação fiel da metodologia.
