# Relatório de implementação — 01: planejamento aprovado antes da execução

Implementação da frente 1 de [`README.md`](README.md), conforme o prompt
[`01_planejamento_com_validacao.md`](01_planejamento_com_validacao.md). A entrega está no commit local
`6c37126` (*feat(planning): validate task decomposition before execution (A.3) and renumber extraction to
A.4*); os ajustes posteriores da revisão estão na seção 10. A frente 2 (ampliação de B.2 e
critério `<task_id>-TECH`) **não** foi implementada nesta etapa.

## 1. Resultado

```text
A.1 — Critérios gerais
  → A.2 — Plano candidato
  → A.3 — Task Decomposition Validator
       ├─ reprovado → nova A.2 com o último candidato e o relatório → nova A.3
       └─ aprovado → confirma o plano na fila → A.4 — Key Learnings from the Question
  → B e C existentes
```

- O plano de A.2 é **candidato**: não entra na fila, não consome espaços de tarefa nem reserva IDs.
- A.3 julga **um** candidato por vez, em janela nova, com o pedido, os critérios gerais e esse candidato.
- Reprovado: nova A.2 em janela nova, temperatura `1`, com só o último candidato e o relatório dele.
- Aprovado: confirmação na fila **uma vez** (evento/mensagem `tasks` em A.3), depois A.4 (a extração que
  era a A.3), depois B/C sem alteração.
- `RALPH_MAX_PLANNING_ATTEMPTS = 5` candidatos; esgotado, a sessão termina com `planning_attempts`.
- Sessões novas gravam `flow_version = 2`; sessões Ralph antigas são lidas como versão 1 (A3 = extração).
- C.2 continua sem validador; B.1/B.2 inalterados; `RALPH_MAX_TASK_ATTEMPTS = 5` preservado.

## 2. Arquivos e contratos alterados

### Backend — domínio e aplicação

| Arquivo | Alteração |
|---|---|
| `src/domain/enums/thinking_phase_enum.py` | `A3_DECOMPOSITION_VALIDATION = "A3"`, novo `A4_PLANNING_LEARNINGS = "A4"`; sem aliases (cada valor aponta um único membro). |
| `src/domain/enums/ralph_flow_version_enum.py` (novo) | `RalphFlowVersionEnum`: `PLANNING_WITHOUT_VALIDATION = 1`, `VALIDATED_PLANNING = 2`. |
| `src/domain/enums/thinking_event_subtype_enum.py` | `plan_candidate`, `plan_approved`, `plan_rejected`. |
| `src/domain/enums/budget_limit_enum.py` | `PLANNING_ATTEMPTS = "planning_attempts"`. |
| `src/domain/entities/thinking/plan_validation_issue.py`, `plan_validation_report.py` (novos) | Relatório tipado de A.3, separado de `VerificationReport`; invariantes de coerência. |
| `src/domain/entities/thinking/validation_context.py` | `candidate_plan`: critérios por tarefa do candidato julgado, para o parser conferir referências. |
| `src/domain/entities/resilience/cost_budget.py` | `max_planning_attempts`. |
| `src/domain/entities/session/session.py`, `session_message.py` | `Session.flow_version`; `SessionMessage.subtype` (subtipo do evento emitido; `None` em registros sem evento). |
| `src/domain/entities/thinking/thinking_event.py` | `flow_version`. |
| `src/domain/interfaces/cost_guard_interface.py`, `settings_interface.py`, `session_recorder_interface.py` | `register_planning_attempt`/`can_retry_planning`; `ralph_max_planning_attempts`; `start(flow_version=)`, `subtype=` nos registros. |
| `src/application/phases/decomposition_validation_phase.py` (novo) | Fase A.3. |
| `src/application/phases/planning_learnings_phase.py` | Agora A.4. |
| `src/application/usecases/ralph_thinking_usecase.py` | Ciclo A.2 ⇄ A.3 (`__generate_candidate`, `__validate_candidate`, `__confirm_plan`), limite de planejamento, A.4, `flow_version` na sessão e nos eventos, subtipo persistido nas mensagens. |

### Backend — infraestrutura e templates

| Arquivo | Alteração |
|---|---|
| `src/infra/adapters/structured_response_parser_adapter.py` | Validador de A.3 (booleano estrito, problemas, referências nulas, critério da tarefa certa, coerência); A.4 com o contrato de aprendizados. |
| `src/infra/adapters/cost_guard_adapter.py`, `session_recorder_adapter.py` | Contador de candidatos; `flow_version` e `subtype`. |
| `src/infra/config/settings.py` | `RALPH_MAX_PLANNING_ATTEMPTS` (padrão `5`). |
| `src/infra/mappers/session_document_mapper.py` | Grava/lê `flow_version` (ausente: Ralph → 1, direta → `null`; valor desconhecido recusado) e `messages[].subtype`. |
| `src/infra/providers/file_prompt_template_provider.py` | A3 → `a3_decomposition_validation.md`, A4 → `a4_planning_learnings.md`. |
| `src/infra/routes/v1/message/dtos/reasoning_event_dto.py`, `src/infra/startups/ralph_thinking_startup.py` | Frame com 10 campos (`flow_version`); injeção da nova fase e do novo limite. |
| `src/infra/templates/a2_task_decomposition.md` | Simplificado; área `{{plan_revision}}`. |
| `src/infra/templates/a3_decomposition_validation.md` (novo) | Rubrica fixa e contrato de A.3. |
| `src/infra/templates/a4_planning_learnings.md` | Renomeado de `a3_planning_learnings.md`; só o título mudou. |
| `.env.example`, `README.md` | Nova variável, contrato de eventos e sessão, seção da nova fase. |

### Frontend

| Arquivo | Alteração |
|---|---|
| `domain/enums/flowVersion.ts` (novo), `thinkingPhase.ts`, `eventSubtype.ts`, `budgetLimit.ts` | Versão do fluxo; `A4`; `getPhaseLabel(phase, version)`; novos subtipos, rótulos e tons; `planning_attempts`. |
| `domain/types/reasoningEvent.ts`, `sessionDocument.ts`, `thinkingRun.ts` | `flow_version`; `messages[].subtype`; `ThinkingRun.flowVersion`; nó `A4`. |
| `api/parsers/reasoningFrame.ts`, `sessionDocument.ts` | Lêem a versão antes das fases (ausente no frame: 1; na sessão Ralph: 1; direta: `null`; valor desconhecido: `ContractError`) e o subtipo persistido. |
| `domain/services/reasoningRunReducer.ts` | Trilha por versão; candidatos e relatórios não criam tarefas; só `tasks` cria. |
| `domain/services/deriveSubtype.ts`, `sessionToThinkingRun.ts` | Usa o subtipo persistido; registros sem evento não viram passo na versão 2; `execute` usa o plano confirmado, nunca um candidato. |
| `domain/services/graphLayout.ts`, `components/timeline/PhaseTrack`, `LoopArc`, `PhaseTag/icons` | Rótulo do nó pela versão; arco `plan-revision` (A.3 → A.2); ícones dos novos subtipos. |
| `README.md` | Contrato de versão, trilha por versão e subtipo no histórico. |

### Documentação

`RALPH_LOOP_ADAPTADO.md` (resumo, guia operacional itens 2 e 3, nota de renumeração na extensão antiga,
nova extensão “Nova fase de validação — 01”; transcrição literal conferida byte a byte como inalterada),
`NOVAS_REGRAS_RALPH_LOOP.md` (alteração 9 no resumo e seção nova, com exemplos), `README.md` raiz,
`apps/backend/README.md`, `apps/frontend/README.md`, `apps/backend/tests/fixtures/README.md` e o estado de
[`README.md`](README.md) desta pasta.

## 3. Contratos

**Relatório de A.3:** `{"approved": true, "issues": []}` ou `{"approved": false, "issues": [{"task_id": str|null,
"criterion_id": str|null, "problem": str, "adjustment": str}]}`. Recusados como contrato: booleano como
texto/número/nulo, `approved`/`issues` ausentes, aprovação com problemas, reprovação vazia, chave de
referência ausente, referência que não é texto nem nulo, texto vazio, critério sem tarefa, tarefa
inexistente e critério de outra tarefa.

**Frame do WebSocket:** 10 campos; `flow_version: int`. **Sessão:** `flow_version: int|null`,
`messages[].subtype: str|null`. **Falha:** `failure.limit = "planning_attempts"`, `failure.phase = "A3"`.

## 4. Matriz de testes

| # | Critério | Testes |
|---|---|---|
| 1 | Primeiro candidato aprovado | `test_primeiro_candidato_aprovado_confirma_uma_vez_e_segue_para_a4_b_e_c`, `test_o_plano_executado_e_exatamente_o_aprovado_e_a_dependencia_chega_a_fila`, `test_a3_recebe_pedido_criterios_gerais_e_o_candidato_com_dependencias` |
| 2 | Correção semântica | `test_reprovacao_semantica_envia_a_a2_o_ultimo_candidato_e_o_relatorio_e_a3_julga_so_o_novo`, `test_cada_geracao_e_cada_avaliacao_abrem_janela_nova_sem_restaurar_conversa` (templates reais) |
| 3 | Mais de uma revisão | `test_varias_revisoes_cada_a2_recebe_so_a_ultima_versao_e_a_auditoria_guarda_todas` |
| 4 | Fila isolada | `test_candidatos_recusados_nao_consomem_slots_nem_reservam_ids_e_nada_executa_antes`, `test_o_espaco_de_tarefas_continua_valendo_para_cada_candidato` |
| 5 | Cinco tentativas | `test_quinto_candidato_aprovado_conclui`, `test_quinto_candidato_reprovado_encerra_sem_sexta_tentativa_a4_tarefas_ou_sintese`, `test_limite_configurado_menor_encerra_no_proprio_limite` |
| 6 | Configuração e contadores | `test_settings.py` (padrão 5, override, independência), `test_cost_guard_adapter.py` (planejamento × tarefas × C.2), `test_cost_budget.py`, `test_recuperacao_estrutural_nao_e_reprovacao_semantica_e_temperaturas_seguem_a_politica` |
| 7 | Schema de A.3 | `test_structured_response_parser_plan_validation.py` (46 casos), `test_plan_validation_report.py` |
| 8 | Recuperação e temperaturas | `test_recuperacao_estrutural_...` (janela da fase, template uma vez, saída recusada integral, A.2 a 1, A.3 seguinte na temperatura da sessão, vínculo de recuperação, invocações contadas), `test_contrato_invalido_de_a3_esgotado_e_falha_tecnica_sem_promover_o_plano` |
| 9 | A.4 | `test_a4_extrai_uma_vez_depois_da_aprovacao_e_as_notas_chegam_a_b`, testes `test_a4_*` de `test_ralph_thinking_usecase.py` |
| 10 | Orçamento, provedor, cancelamento | `test_limite_de_chamadas_interrompe_sem_promover_plano_recusado` (negação na avaliação, na revisão e depois da confirmação), `test_falha_do_provedor_na_avaliacao_e_registrada_sem_confirmar_o_plano`; cancelamento coberto pelos testes existentes de `BaseThinkingPhase` e `test_ralph_five_fronts_integration.py`, sem alteração de comportamento |
| 11 | Versões | `test_session_document_mapper_flow_version.py`, `test_flow_version_persistence_round_trip.py` (arquivo antigo não reescrito, repositório JSON, pacote completo de benchmark nas duas ordens, ZIP de erros do Ralph), `test_reasoning_event_dto.py`, `test_reasoning_websocket.py` |
| 12 | Frontend | `validatedPlanning.test.ts` (candidatos não inflam tarefas/progresso, trilha v2, arco A.3 → A.2, paridade ao vivo × histórico para sessão revisada e para sessão interrompida antes de A.4, `execute` do plano confirmado, sessão v1), `sessionDocumentFlowVersion.test.ts`, `reasoningFrame.test.ts`, `deriveSubtype.test.ts`, `thinkingPhase.test.ts`, `PhaseTrack.test.tsx`, `LoopArc.test.tsx`; paridade antiga (`parity.test.ts`) mantida |
| 13 | Contratos e avaliação futura | `test_decomposition_validation_contracts.py` + `fixtures/decomposition_validation_v1.json` (condição omitida, resultado antecipado, tarefa redundante; dados numéricos, método com hipótese, dependências e estimativa válidos), `test_planning_instruction_contracts.py` (regras de geração preservadas em A.2) |
| — | C.2 sem A.3 | `test_a3_nao_e_usada_nos_lotes_de_c2` |

Na entrega `6c37126`, as fixtures v2 do frontend (`session-a1-v2-plan-revision.json`,
`session-a1-v2-planning-exhausted.json`) traziam só a sessão gerada pelo backend, e a paridade comparava
o histórico com eventos reconstruídos a partir dessas mesmas mensagens. Desde a seção 10, elas foram
substituídas por capturas reais (`capture-*.json`: frames e sessão da mesma execução). As fixtures antigas
(versão 1) não foram migradas.

## 5. Falhas observadas antes das correções (TDD)

- **Domínio:** coleta falhou com `ModuleNotFoundError` para `plan_validation_issue` e
  `ralph_flow_version_enum` e asserções falharam para `A3_DECOMPOSITION_VALIDATION`/`A4`, novos subtipos,
  `PLANNING_ATTEMPTS` e `max_planning_attempts`.
- **Parser:** os 46 casos de A.3 falharam antes do validador (fase sem validador e A.4 inexistente).
- **Orquestrador:** os 19 testes de integração novos não executavam (fase e parâmetros inexistentes).
- **Cenários existentes:** com o fluxo novo, 234 testes de integração em 17 arquivos falharam, porque os roteiros
  não traziam a saída de A.3 e contavam chamadas/índices do fluxo antigo. Os roteiros de execução nova
  receberam a aprovação de A.3 antes das notas de A.4; contagens, índices, temperaturas e listas de fases
  foram ajustados. Onde um teste de orçamento visava um ponto exato do fluxo, o teto **do cenário** foi
  ajustado para continuar negando o mesmo ponto (por exemplo, 16 → 17 chamadas em
  `test_orcamento_real_esgotado_depois_da_revisao_aplicada_...`); nenhum padrão de produção foi elevado.
- **Templates:** asserções sobre a seção “Final plan review” de A.2 e sobre exemplos de casos específicos
  removidos de A.2 passaram a verificar a regra geral em A.2 e a dimensão correspondente na rubrica de A.3;
  C.2 mantém a revisão de cobertura dentro da geração.
- **Frontend:** falharam os testes de `flow_version` no frame, de subtipo persistido e das trilhas v2; o
  `tsc` acusou os literais de evento/sessão/run sem os campos novos.

## 6. Comandos e resultados

Em `apps/backend` (ambiente `.venv`):

```sh
.venv/bin/python -m flake8 src tests
.venv/bin/python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

- `flake8`: sem saída, código 0.
- `pytest`: **2.656 testes aprovados** (antes: 2.516), cobertura **100,00%** (6.144 statements, 1.144 branches).

Em `apps/frontend`:

```sh
npm run typecheck
npm run lint
npm run test:coverage
npm run build
```

- `typecheck` e `lint`: código 0, sem avisos.
- `test:coverage`: **687 testes em 86 arquivos** (antes: 649 em 81), todos os limiares por camada
  atendidos (`src/domain/services/**` a 100%); total 96,5% de statements.
- `build`: concluído.

`git diff --check`: sem saída. Nenhuma inferência paga ou benchmark real foi executado.

## 7. Falhas preexistentes

- **`npm run test:coverage` falhava antes desta etapa.** Num worktree limpo do `HEAD` (`ea0088c`),
  `src/domain/services/benchmarkDefinition.ts` tinha 92,3% de branches (linha 76, o fallback
  `?? benchmark` de `benchmarkDatasetLabel`), abaixo do limiar de 100% de `src/domain/services/**`. Foi
  acrescentado um teste para um identificador fora da lista; nenhum código de produção mudou.
- **Marcadores em português no frontend (critérios corrigidos na seção 10).** `taskParser.ts` procura
  `**Decisão:**` e `**Critérios de aceite:**`, mas os templates do backend estão em inglês
  (`**Decision:**`, `**Acceptance criteria:**`). Em sessões versão 1, a derivação de `verify_pass`/`verify_fail`
  cai no critério posicional, e o passo `execute` sintetizado no histórico não lista os critérios, enquanto
  o `execute` ao vivo os traz. Nas sessões versão 2 o subtipo persistido elimina a primeira parte; a
  diferença de conteúdo do `execute` sintetizado continua e afeta igualmente as duas versões.

## 8. Garantias e limitações

| Tipo | O que vale |
|---|---|
| Garantia programática (testada) | Entradas e janelas de A.2/A.3/A.4; contrato e coerência do relatório; confirmação só depois da aprovação e uma única vez; candidatos sem efeito sobre fila, slots, IDs e progresso; limite independente de cinco candidatos; temperaturas; recuperação estrutural na janela da fase; contabilização de toda chamada (inclusive saídas inválidas e falhas do provedor); auditoria completa; versão persistida e compatibilidade de backend, consulta, exportação/importação e frontend. |
| Contrato do prompt (verificado como texto) | Regras de geração de A.2; rubrica fixa, limites do julgamento e exemplos gerais de A.3; ajuste sem impor resultado. Instruções presentes não provam obediência. |
| Avaliação semântica (não medida) | Que um modelo real reprove planos com conclusão antecipada, condição omitida ou tarefa redundante sem rejeitar planos válidos. As saídas dos testes são roteirizadas. |

Outros limites: cada sessão faz ao menos uma chamada a mais (A.3) e cada reprovação acrescenta duas;
os tetos de chamadas, tokens e tempo podem encerrar a sessão antes do quinto candidato; um defeito
estrutural persistente em A.3 encerra a sessão como erro técnico, sem promover o plano; o cancelamento
segue o tratamento existente (recuperações pendentes registradas como falha e propagação).

## 9. Prontidão para o segundo prompt

O workspace está integrado e verde nos dois apps. A segunda etapa
([`02_validacao_tecnica_das_tarefas.md`](02_validacao_tecnica_das_tarefas.md)) parte deste estado: B.1/B.2
inalterados, `RALPH_MAX_TASK_ATTEMPTS = 5`, `ValidationContext` e o parser prontos para receber mais um
critério reservado (o padrão do sufixo `-REV` é a referência), e os roteiros de teste já incluem A.3/A.4
(`plano_aprovado()` em `tests/doubles/ralph_scripts.py`). A entrega da frente 1 foi commitada localmente
em `6c37126`, incluindo o renome do template A.3 → A.4.

## 10. Complemento — ajustes da revisão da entrega

A revisão do commit `6c37126` apontou três ajustes. Os dois primeiros tratam de problemas do histórico
que **já existiam antes da fase 1** (a primeira versão do frontend, `29a2f80`, já gravava a resposta como
único passo de C.3 e já procurava os critérios em português); não são regressões do novo planejamento,
cuja lógica não mudou.

1. **Auditoria de C.3 apresentada como resposta.** `deriveStepKind` classificava toda mensagem de C.3 como
   `result/compile` antes de descartar os registros sem evento, então a auditoria de uma saída recusada
   aparecia como resposta. Agora o subtipo persistido e o descarte dos registros sem evento vêm primeiro; uma
   mensagem de C.3 do sistema (sempre auditoria, em qualquer versão) não vira passo, e a mensagem aceita é o
   `thinking/compile`. O terminal `result/compile`, que o backend emite em seguida com o mesmo conteúdo, é
   reconstruído por `sessionToThinkingRun` só quando a sessão tem resposta final. O reducer não conta esse
   terminal como nova chamada nem soma de novo o tempo de C.3 (ao vivo, a chamada era contada duas vezes), e
   um `error` emitido em C.3 deixou de ser tomado como resposta final. A auditoria continua armazenada na
   sessão. Em sessões antigas, a resposta e o status exibidos são os mesmos; o histórico ganha o passo
   `thinking/compile` de C.3 que a execução ao vivo já mostrava.
2. **Critérios perdidos no `execute` e paridade circular.** `taskParser.ts` aceita `**Acceptance
   criteria:**` e `**Critérios de aceite:**`, e o `execute` do histórico passou a usar o bloco da tarefa
   confirmada exatamente como o backend o escreveu (`extractTaskBlock`), com critérios e dependências, em vez
   de re-renderizá-lo em português. A paridade do fluxo atual deixou de reconstruir eventos a partir das
   mensagens: `validatedPlanning.test.ts` usa capturas reais (`src/test/fixtures/capture-*.json`) com os
   frames que o caso de uso emitiu — convertidos pela mesma função do composition root e serializados como
   no router — e a sessão persistida da mesma execução, com modelo roteirizado. As capturas são geradas por
   `apps/backend/tests/doubles/frontend_parity_capture.py` e conferidas por
   `apps/backend/tests/infra/test_frontend_parity_fixtures.py`, que falha se a emissão ou a persistência
   mudarem. Casos: plano revisado com auditoria de A.3 e auditoria de C.3 seguida da resposta aceita;
   planejamento esgotado antes de A.4; C.3 esgotada sem resposta. Os comentários de `parity.test.ts`
   (sessões antigas) passaram a dizer que lá a sequência é uma reconstrução sintética.
3. **Relatório.** Este documento identifica a entrega `6c37126` e deixou de afirmar que ela não foi
   commitada.

**Testes executados** (depois dos ajustes):

- Frontend: `npm run typecheck`, `npm run lint` (sem avisos), `npm run test:coverage` — **699 testes em 86
  arquivos**, limiares atendidos, `src/domain/services/**` a 100% — e `npm run build`, todos com código 0.
  Antes das correções, os testes novos reproduziram os problemas (12 falhas: auditoria de C.3 como
  resultado, critérios em inglês ignorados, `execute` diferente do capturado e consumo de C.3 duplicado).
  O `error` de C.3 tomado como resposta apareceu durante a correção, na comparação com a captura de C.3
  esgotada, e ganhou a correção e o teste próprios.
- Backend (só testes e dublês mudaram): `flake8 src tests` sem saída; `pytest --cov=src
  --cov-fail-under=100` com **2.660 testes aprovados** e cobertura 100,00%.

**Limitações.** A paridade compara o histórico com os frames capturados menos o `error` terminal, que só
vai pelo WebSocket (a falha fica em `failure`); o campo `updated_at` de uma sessão falha usa o relógio real
e é ignorado na conferência das capturas. Sessões antigas continuam sem captura: `parity.test.ts` usa uma
sequência sintética. O marcador de decisão `**Decision:**` em inglês continua não reconhecido em sessões
antigas sem subtipo (a derivação de `verify_pass`/`verify_fail` segue o critério posicional); o fluxo atual
usa o subtipo persistido. Estes ajustes ainda não foram commitados quando este complemento foi escrito.
