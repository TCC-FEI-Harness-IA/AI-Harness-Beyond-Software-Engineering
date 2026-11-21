# Relatório de implementação — 02: validade técnica obrigatória das tarefas e integração das duas frentes

Implementação da frente 2 de [`README.md`](README.md), conforme o prompt
[`02_validacao_tecnica_das_tarefas.md`](02_validacao_tecnica_das_tarefas.md), sobre a base da frente 1
(commit `6c37126`) e da sua correção (commit `a25950f`). Os pré-requisitos foram conferidos no código antes de
começar: A.3 (Task Decomposition Validator) com retorno a A.2, A.4 de extração, confirmação do plano só depois
da aprovação, `RALPH_MAX_PLANNING_ATTEMPTS = 5` e `flow_version` estavam integrados e verdes. A entrega desta
etapa está no commit local `3fc64f3`; os ajustes posteriores da revisão estão registrados na seção 11.

## 1. Resultado

```text
A.1 → A.2 (candidato) → A.3 (validação) ─ reprovado → A.2 … ─ aprovado → fila → A.4
  → B.1 (conjunto efetivo de critérios)
  → B.2 (tarefa + resultado + conjunto efetivo + proposta de revisão + aprendizados)
       ├─ algum critério não atendido (inclusive só <id>-TECH) → nova B.1, janela nova, temperatura 1 (até 5 tentativas)
       └─ todos atendidos → B.3 → B.4
  → C.1 (critérios gerais) → C.2 … → C.3
```

- Toda tarefa — comum ou revisora, de A.2 ou de C.2 — recebe do harness o critério fixo **`<task_id>-TECH`**.
- O **conjunto efetivo** (planejados + TECH + REV numa revisora) é composto pelo domínio, de forma
  determinística, e é o mesmo em B.1, B.2, `ValidationContext.expected_criteria_ids` e em toda retentativa.
- B.2 recebe a **tarefa** (identificação, título, descrição) numa área própria e verifica a tarefa inteira.
- `<task_id>-TECH` é **reservado**: o domínio recusa a tarefa e o parser recusa o lote de A.2/C.2.
- B.1 e B.2 conferem a **base analítica antes** de aceitar aproximação, estimativa, eliminação ou melhor ajuste.
- Schema de B.2, política compartilhada de evidência, REV, cinco tentativas por tarefa, contratos de
  A.3/C.1/C.2/C.3, versão do fluxo e significados de A.3/A.4: inalterados.

## 2. Arquivos alterados

### Backend — código

| Arquivo | Alteração |
|---|---|
| `src/domain/entities/thinking/harness_criteria.py` (novo) | Definição única dos critérios do harness: sufixos `-TECH`/`-REV`, descrições em inglês, `technical_criterion_id`/`revision_criterion_id`, `technical_criterion`/`revision_criterion`. A descrição de REV foi movida de `task.py` sem mudança de texto. |
| `src/domain/entities/thinking/task.py` | `technical_criterion`, `harness_criteria()`, `verification_criteria()` = planejados + TECH + REV. `__post_init__` recusa `<id>-TECH` **antes** do retorno antecipado de `review is None`; regras de REV e dependências preservadas. `acceptance_criteria` continua só com a autoria do planejador. |
| `src/application/usecases/ralph_thinking_usecase.py` | `__verification_variables` passa `task_description` a B.2; cabeçalho da tarefa renderizado por um único método (`__render_task_header`) em B.1, B.2 e B.4. B.1/B.2/parser já usavam `task.verification_criteria()`, que agora inclui TECH. Plano candidato, confirmação e `execute` continuam com os critérios planejados. |
| `src/infra/adapters/structured_response_parser_adapter.py` | `__validate_task_links` recusa `<id>-TECH` em qualquer tarefa (antes do retorno das tarefas sem `review`) e REV numa revisora, via `__reject_reserved_criterion` (código `invalid_value`, campo `tasks[].acceptance_criteria[].id`, ID afetado). Sufixo duplicado `_REVISION_CRITERION_SUFFIX` removido: usa a definição do domínio. Cobertura/coerência de B.2 continuam genéricas. |

### Backend — templates

| Template | Alteração |
|---|---|
| `b2_task_verification.md` | Título “Verification of the task”; nova área `## Task` (`{{task_description}}`) antes do resultado; área de critérios explica o conjunto efetivo; aprovação exige todos, inclusive TECH/REV; papel de verificador (não resolve, não completa, não edita critérios); defeito de planejamento registrado na justificativa, sem retorno a A.2; nova seção `Technical validity criterion (<task id>-TECH)`; ordem: TECH → `Technical verification of the local criteria` → `Revision criterion` → `Evidence and consistency policy` → `Selection criteria`; exemplo de saída com `T2-TECH: false`. |
| `b1_task_resolution.md` | Área de critérios explica o conjunto efetivo; nova seção `Technical validity (<task id>-TECH)` antes da política compartilhada e de `Calculated result and chosen option`. Placeholders inalterados. |
| `a2_task_decomposition.md`, `c2_additional_planning.md` | `-TECH` e `-REV` reservados; toda tarefa recebe `<task id>-TECH` automaticamente. |
| `a3_decomposition_validation.md` | Ausência de critério técnico não é defeito do candidato (TECH é acrescentado na execução). |
| `b4_learnings_extraction.md` | A lista do que não registrar cita os critérios do harness (`T1-TECH`, `T1-REV`). Entrada e política inalteradas. |

A seção `Evidence and consistency policy` de B.1/B.2/C.1 continua **idêntica** nos três templates; C.1, C.3 e
A.1 não mudaram.

### Frontend

Nenhuma mudança de código. `validatedPlanning.test.ts` ganhou a captura `capture-v2-tech-retry.json` na
paridade ao vivo × histórico e dois testes; as três capturas existentes foram regravadas (só os relatórios de
B.2 ganharam a linha de TECH, além do `updated_at` de relógio real que a conferência ignora).

### Testes e documentação

Novos: `test_task_technical_criterion.py`, `test_structured_response_parser_technical_criterion.py`,
`test_technical_validation_contracts.py`, `test_ralph_technical_validation_integration.py`,
`test_technical_criterion_history_round_trip.py`, `fixtures/technical_validation_v1.json`. Ajustados: roteiros
de execução nova (seção 5) e `tests/doubles/ralph_scripts.py` (`aprovado`/`reprovado` avaliam AC1 e TECH, cada
um com veredito próprio; novos `tech`, `reprovado_tecnico`), `frontend_parity_capture.py` (caso `v2-tech-retry`).
Documentação: `RALPH_LOOP_ADAPTADO.md`, `NOVAS_REGRAS_RALPH_LOOP.md`, `README.md`, `apps/backend/README.md`,
`apps/backend/tests/fixtures/README.md`, `apps/frontend/README.md` e o estado de [`README.md`](README.md).

## 3. Contratos finais

**Conjunto efetivo de B.1/B.2/parser:** `(*acceptance_criteria, <id>-TECH[, <id>-REV])`, cada um uma vez.

**Relatório de B.2** (inalterado): `criteria_evaluation[{criterion_id, met, justification}]`,
`unmet_criteria_ids`, `decision ∈ {approved, reproved}`. Aceito só com cobertura exata do conjunto efetivo,
`unmet_criteria_ids` igual aos `met=false` e decisão coerente. `TECH: false` coerente = reprovação semântica.

```json
{"criteria_evaluation": [
  {"criterion_id": "T2-AC1", "met": true, "justification": "The requested calculation steps are present."},
  {"criterion_id": "T2-TECH", "met": false, "justification": "The rate is applied outside its stated interval. Investigate the interval used before recomputing the quantity."}],
 "unmet_criteria_ids": ["T2-TECH"], "decision": "reproved"}
```

**Relatório de A.3** (inalterado e distinto): `{"approved": bool, "issues": [...]}`.

**Planejamento:** critério `<id>-TECH` em qualquer tarefa de A.2/C.2, ou `<id>-REV` numa revisora →
`invalid_value` com recuperação estrutural (não conta como candidato de A.3 nem como rodada de C.2).

**Variáveis de B.2:** `task_description`, `preliminary_result`, `task_acceptance_criteria`,
`revision_proposal`, `learnings`.

## 4. Matriz de testes

| # | Critério de aceite | Testes |
|---|---|---|
| 1 | Critério fixo | `test_task_technical_criterion.py` (comum, A.2/C.2, revisora com REV, uma vez, determinístico, planejados identificáveis, definição única); `test_c2_que_emite_tech_e_corrigido_e_a_tarefa_adicional_recebe_tech_do_harness`; `test_tech_e_rev_sao_independentes_...` (ordem `T3-AC1, T3-TECH, T3-REV`) |
| 2 | Colisão | domínio: `test_tarefa_comum_recusa_...`, `test_tarefa_revisora_recusa_...`, `test_tarefa_comum_sem_dependencias_nem_revisao_tambem_e_conferida`; parser: `test_planejador_nao_pode_emitir_o_identificador_tecnico_reservado` (6 casos A.2/C.2), `test_recusa_nao_remove_o_criterio_silenciosamente`; fluxo: `test_a2_que_emite_tech_e_corrigido_pela_recuperacao_estrutural_e_nao_por_a3`, `test_c2_que_emite_tech_...` |
| 3 | Entradas reais | `test_b1_b2_e_parser_recebem_o_mesmo_conjunto_efetivo_com_tech_uma_vez`, `test_b2_recebe_tarefa_resultado_criterios_e_aprendizados_em_areas_separadas_em_janela_nova`, `test_technical_validation_contracts.py` (áreas, ordem, placeholders) |
| 4 | Falha técnica isolada | `test_falha_tecnica_isolada_reprova_e_b1_e_retentada_com_o_feedback_integral` (sem B.3/B.4 antes da aprovação; ledger e memória só com o aprovado) |
| 5 | Aprovação completa | `test_aprovacao_completa_armazena_e_extrai_sem_chamada_extra_de_verificacao` |
| 6 | Relatório inconsistente | `test_relatorio_inconsistente_e_recuperado_na_janela_de_b2_sem_mudar_vereditos` (6 casos), `test_b2_que_nunca_avalia_tech_encerra_como_erro_tecnico_...`, `test_relatorio_inconsistente_com_tech_e_recusado_sem_mudar_vereditos` (9 casos no parser) |
| 7 | TECH × REV | `test_tech_e_rev_sao_independentes_e_a_revisao_so_e_aplicada_com_os_dois` (TECH falha / REV falha), `test_revisao_reprovada_em_todas_as_tentativas_por_tech_nao_e_aplicada`, `test_tech_e_rev_sao_avaliados_de_forma_independente` (parser) |
| 8 | Escopo e controles positivos | `test_matriz_tecnica_transporta_cada_caso_pelo_fluxo` (6 positivos: intermediária, estimativa, hipótese, aproximação, inferência contextual, justificativa final não pedida); contratos de escopo em `test_technical_validation_contracts.py`; controles anteriores preservados (`test_validation_policy_contracts.py`, `test_validation_semantics_matrix.py`) |
| 9 | Negativos generalistas | mesma matriz (premissa não fornecida, método fora das condições, direção × tabela, etapa temporal, proximidade sobre cálculo inválido) pelo fluxo e pelo template; `test_nenhum_template_contem_os_exemplos_ou_referencias_da_matriz`. São **transporte/contrato**, não resultado semântico. |
| 10 | Retentativa e temperatura | `test_falha_tecnica_isolada_...` (feedback integral, janela nova, B.1 `[0.3, 1.0]`, B.2 `[0.3, 0.3]`, TECH uma vez por prompt, mesmos IDs no parser), `test_quatro_reprovacoes_...` |
| 11 | Cinco tentativas e falhas | `test_quatro_reprovacoes_tecnicas_e_aprovacao_na_quinta_concluem`, `test_cinco_reprovacoes_tecnicas_encerram_sem_sexta_tentativa_armazenamento_ou_sintese`, `test_orcamento_esgotado_depois_de_reprovacao_tecnica_nao_promove_o_resultado_reprovado`, `test_b2_que_nunca_avalia_tech_...`; cancelamento coberto pelos testes existentes de `BaseThinkingPhase`/cinco frentes, sem mudança de comportamento |
| 12 | Histórico | `test_technical_criterion_history_round_trip.py` (sessão nova com A.3/A.4 e TECH; antiga sem versão e sem TECH, sem reescrita; inferência direta; exportação/importação; parser proibido durante leitura) e `test_flow_version_persistence_round_trip.py` (inalterado) |
| 13 | Integração das frentes | `test_integracao_das_duas_frentes_do_plano_revisado_a_resposta_aprovada` (A.3 reprova, A.2 revisa, A.3 aprova, A.4 uma vez, B.2 reprova só por TECH, B.2 aprova, C.1, C.3 uma vez; janelas isoladas, candidato correto, fila, notas, 13 chamadas) |
| 14 | Independência dos limites | `test_tentativas_do_planejamento_nao_reduzem_as_da_tarefa_e_b2_nao_reabre_o_planejamento` (guardião real: 5 candidatos + 5 tentativas); `test_c2_que_emite_tech_...` (C.2 sem A.3) |
| 15 | Regressões anteriores | suíte completa (2.796 testes), incluindo recuperação integral, resultados/memória vigentes, revisão confirmatória/substitutiva, aproximações legítimas, snapshot da C.1 para C.3, eventos/histórico da frente 1 e paridade do frontend com capturas reais |

## 5. Evidência de TDD

1. **Parser** (antes de qualquer código): 7 falhas em `test_structured_response_parser_technical_criterion.py`
   (colisão de TECH não recusada em A.2/C.2, inclusive sem `review`); os casos de cobertura/coerência de B.2 já
   passavam, porque o parser é genérico sobre os IDs esperados.
2. **Novos arquivos** (após criar só `harness_criteria.py`): **83 falhas, 49 aprovados** — domínio sem TECH em
   `verification_criteria`, sem recusa do ID; templates sem as áreas e regras; fluxo rejeitando `T1-TECH` como
   critério desconhecido.
3. **Suíte existente** depois da implementação: 2 testes de domínio fixavam o conjunto sem TECH
   (`test_result_revision_entities.py`) e 2 fixavam os placeholders/variáveis de B.2; foram atualizados ao novo
   contrato. Em seguida, a suíte completa teve **88 falhas em 11 arquivos**: 84 em cenários de execução nova
   cujos relatórios de B.2 roteirizados não avaliavam TECH (o parser recusava por cobertura), 1 no teste que
   proibia a descrição em B.2 e 3 na conferência das capturas do frontend. Cada roteiro passou a avaliar o conjunto
   efetivo explicitamente: `T<n>-TECH` com veredito próprio — `true` quando a resolução roteirizada é aceita,
   e, nos casos da matriz semântica v1 cuja referência é reprovação técnica, `false` junto com o critério
   planejado. `test_transicao_b1_para_b2_leva_so_o_resultado_preliminar_e_os_criterios` foi substituído por
   `..._leva_a_tarefa_o_resultado_preliminar_e_os_criterios` (a descrição agora chega a B.2, só na área da
   tarefa). As 3 falhas de `test_frontend_parity_fixtures.py` foram resolvidas regravando as capturas.
4. Nenhum teto de produção, limiar de cobertura ou controle positivo foi alterado; não há `TECH: true`
   injetado automaticamente por dublê ou parser.

## 6. Comandos e resultados

Em `apps/backend` (`.venv`):

```sh
.venv/bin/python -m flake8 src tests
.venv/bin/python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

- `flake8`: sem saída, código 0.
- `pytest`: **2.796 aprovados** (antes desta etapa: 2.660), cobertura **100,00%** (6.166 statements, 1.146 branches).

Em `apps/frontend`:

```sh
npm run typecheck && npm run lint && npm run test:coverage && npm run build
```

- `typecheck` e `lint`: código 0, sem avisos.
- `test:coverage`: **704 testes em 86 arquivos** (antes: 699), limiares atendidos; total 96,51% de statements.
- `build`: concluído.

`git diff --check`: sem saída; arquivos novos sem espaços finais. Nenhuma inferência paga ou benchmark real.

## 7. Compatibilidade

- **Sessões antigas** (sem `flow_version`, A3 = extração, B.2 sem TECH): lidas sem reescrita; leitura,
  consulta, exportação e importação não passam pelo parser (teste com o parser proibido).
- **Sessões novas**: `flow_version = 2`, A.3/A.4 da frente 1, relatórios de B.2 com a linha `<id>-TECH`.
- **Inferência direta**: sem versão, inalterada.
- **Frontend**: trata `T<n>-TECH` como qualquer ID; o subtipo persistido decide a tentativa; o `execute`
  continua com os critérios planejados, igual ao vivo e no histórico.
- **Custos**: sem chamada nova numa aprovação de primeira; cada reprovação por TECH custa B.1 + B.2 dentro dos
  mesmos tetos. A frente 1 continua acrescentando ao menos uma chamada (A.3) por sessão.

## 8. Pontos preexistentes (não regressões desta etapa)

- O parser preenche `unmet_criteria_ids` a partir dos `met` quando o campo está ausente (comportamento
  anterior); não altera nenhum veredito e não fabrica avaliações. Mantido.
- `parseCriterionEvaluations` do frontend procura os rótulos em português (`atendido`), mas só é usado em
  teste; a apresentação usa o conteúdo e o subtipo persistido. Não afeta TECH.

## 9. Garantia programática × contrato de prompt × qualidade semântica

| Tipo | O que vale |
|---|---|
| **Garantia programática** (testada) | Composição única e determinística do conjunto efetivo; TECH uma vez em toda tarefa, ao lado de REV; recusa do ID reservado no domínio e no parser, com recuperação estrutural; mesmo conjunto em B.1, B.2, parser e retentativas; área da tarefa e janela nova em B.2; aprovação só com todos os critérios; reprovação por TECH isolada, retentada a `1` com feedback integral; revisão aplicada só com TECH e REV; cinco tentativas independentes das cinco do planejamento; nada armazenado, extraído ou sintetizado a partir de conteúdo reprovado; C.1 sem TECH; histórico, exportação/importação e frontend compatíveis. |
| **Contrato de prompt** (verificado como texto) | Definição de TECH; fundamento antes de aproximação; distinções sobre premissa, fonte, proximidade e hipótese; conferência por outro ângulo opcional; limites de escopo; justificativa que aponta dado, premissa e relação; reservas nos planejadores; A.3 sem exigir TECH. Instrução presente não prova obediência. |
| **Qualidade semântica** (não medida) | Que um modelo real reprove premissas inventadas, métodos inaplicáveis, direções e estágios temporais trocados e escolhas por proximidade sobre cálculo errado, **sem** rejeitar tarefas intermediárias, estimativas, hipóteses justificadas, aproximações e inferências legítimas. Nenhuma correção dos casos analisados nem ganho de acurácia é declarado a partir de completions roteirizadas. A matriz `technical_validation_v1.json` está pronta para essa avaliação. |

## 10. Limitações e itens fora do escopo

- TECH não garante verdade factual: o verificador é o mesmo tipo de modelo e não tem fontes externas.
- Um verificador que reprove demais consome as cinco tentativas e encerra a sessão por `task_attempts`; isso só
  aparece em avaliação real.
- Um critério planejado inviável que A.3 deixou passar é apenas registrado na justificativa de B.2; não há
  retorno automático de B.2 a A.2.
- Não implementados, conforme o prompt: novas verificações de C.1, recuperação de contrato por campo,
  apresentação da proveniência dos aprendizados, mudanças funcionais de dependências, validação de lotes de C.2
  por A.3, fallback simples, votação, revisor depois de C.3 e resolução especializada por domínio.

## 11. Complemento — ajustes da revisão da entrega

A revisão do commit `3fc64f3` apontou uma ambiguidade no template de B.2 e a informação desatualizada sobre
o estado da entrega neste relatório. Foram feitos os dois ajustes:

1. **Critério planejado inviável.** Foi removida a autorização antiga de considerar atendido um critério
   com resultado pré-calculado incorreto apenas porque a resolução demonstrou o cálculo correto. Se o
   critério impõe um número, expressão ou outra conclusão incompatível com os dados e aprendizados, B.2
   marca esse critério com `met: false` e registra o defeito de planejamento. TECH é avaliado separadamente:
   pode ser atendido pela resolução correta, mas a tarefa continua `reproved` enquanto houver um critério
   planejado não atendido. B.2 não substitui a conclusão exigida nem pede um cálculo incorreto para
   satisfazê-la. A regra distingue esse defeito de um critério que pede aproximação ou melhor ajuste
   fundamentado, que continua sujeito à política de evidência, sem coincidência exata universal. O parser,
   os ciclos, as entradas e os limites permanecem os mesmos. `RALPH_LOOP_ADAPTADO.md` e
   `NOVAS_REGRAS_RALPH_LOOP.md` registram a distinção, preservando a transcrição literal do paper.
2. **Identificação da entrega.** A abertura deste relatório identifica o commit local `3fc64f3`, em vez
   de afirmar que a implementação está somente no workspace.

**TDD e alcance.** Dois testes novos em `test_technical_validation_contracts.py` falharam antes da correção:
um detectou a autorização antiga de aprovação e o outro a ausência da distinção para aproximações. Depois
do ajuste, os 120 testes focados dos contratos técnicos, da política de validação e dos limites generalistas
passaram. Esses testes verificam as instruções efetivamente entregues ao modelo; não medem sua obediência
semântica nem ganho de acurácia.

**Validação final:** 138 testes focados, incluindo a integração das cinco frentes, e **2.798 testes na suíte
completa**, com cobertura de **100,00%**; `flake8 src tests` e `git diff --check` aprovados. A suíte completa
rodou em cópia temporária com as alterações atuais. Como o MongoDB local estava indisponível, uma fixture
temporária usou `AsyncMongoMockClient` nos testes de rota para evitar os timeouts das consultas ao catálogo
de modelos; essa fixture ficou fora do workspace. Os cenários continuam com completions roteirizadas,
sem inferências pagas ou medição de acurácia.
