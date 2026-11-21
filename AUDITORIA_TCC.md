# Auditoria Técnica e Analítica do TCC — Ralph Wiggum Loop Adaptado

**Data da auditoria:** 21 de novembro de 2026  
**Fontes de verdade auditadas:**
- **Paper (desatualizado):** [`docs/paper/TCC.tex`](docs/paper/TCC.tex)
- **Log de alterações (referência auxiliar):** [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md)
- **Implementação real:** [`apps/backend/src`](apps/backend/src) (e infraestrutura em `apps/frontend`, `apps/auth`)
- **Dados crus dos experimentos:** [`apps/backend/data`](apps/backend/data) — baterias:
  - `bench_b72b883cb604496c917119d00e55d3b3` (Vestibular — `vestibular-v1`)
  - `bench_9be03b85641c4b62bfa7cd81ebe62d03` (MMLU — `generative_0shot`)
  - `bench_c0b581509c944a10adde91d57d80ef7f` (GPQA Diamond — `generative_0shot`)

---

## Etapa 1: Diagnóstico do Estado Atual do Paper

### 1.1 Estrutura Atual e Nível de Maturidade

O documento [`docs/paper/TCC.tex`](docs/paper/TCC.tex) (827 linhas, template INOVA FEI em duas colunas, última atualização em 24/08) ainda se encontra em **estado de proposta/qualificação**, não de artigo final:

| Seção / Elemento no `TCC.tex` | Linhas | Maturidade | Diagnóstico Técnico |
|---|---|---|---|
| **Metadados e Resumo** | L274–L293 | **Desatualizado** | Promete experimentos com a família Llama 3.1 em MMLU e GPQA, sem mencionar resultados obtidos, o modelo real testado nem o dataset de Vestibulares. |
| **I. Introdução** | L298–L311 | **Completa (desatualizada)** | Boa contextualização (LLMs, CoT/ToT/ReAct/Reflexion/Self-Refine, *context rot*, Ralph Loop), mas anuncia o protocolo experimental antigo (Llama 3.1 em MMLU/GPQA) e não antecipa os achados nem contribuições empíricas. |
| **II. Referencial Bibliográfico** | L314–L352 | **Completa (revisões menores)** | Cobre *harness*, sistemas compostos, degradação de contexto e Ralph Loop original (incl. Fig. 1). Contém erros ortográficos (`Referencial Bibliografico` sem acento na L314; `"pode melhor"` na L325). |
| **III. Metodologia** | L355–L783 | **Severamente desatualizada + defeitos redacionais** | Descreve a **versão 0** do fluxo (A.1–A.2, B.1–B.4, C.1–C.3). Além de omitir 11 rodadas de mudanças arquiteturais (fluxo v2), apresenta: frase quebrada/truncada na L537 (`"por meio do Template~B.2, o \textbf{Cenário de reprovação...}"`), typo `"atravez"` na L493, e exemplo autocontraditório em B.4 (L615–L640, que afirma listar "um único aprendizado útil" sem definições óbvias após a Tarefa 1, mas lista 5 fatos incluindo definições óbvias e resultados das Tarefas 2 e 3). O diagrama [`docs/paper/diagrams/ralph_loop_adaptado_png.png`](docs/paper/diagrams/ralph_loop_adaptado_png.png) também reflete apenas a arquitetura antiga. |
| **IV. Metodologia de Avaliação** | L787–L794 | **Rascunho / Obsoleta** | Apenas 3 parágrafos (título com erro: `Métodologia`). Descreve um desenho experimental que **não corresponde** ao executado (modelos, datasets, referências comerciais, ausência de detalhamento de hiperparâmetros, amostragem, protocolo 0-shot, avaliação determinística e tratamento de falhas). |
| **Tabela I (Cronograma)** | L797–L821 | **Artefato de proposta (remover)** | Tabela de cronograma fev–nov típica de pré-projeto; deve ser removida no artigo final. |
| **Implementação / Arquitetura do Sistema** | — | **Ausente** | Não descreve o contrato JSON estrito, parser/reparador, guardião de custos/limites, gestão de contexto/sessões nem a stack técnica. |
| **Resultados e Discussão** | — | **Ausente** | Nenhum dado experimental, tabela, teste estatístico ou análise de erro existe no `.tex`. |
| **Limitações e Ameaças à Validade** | — | **Ausente** | Não há seção discutindo custos, falhas operacionais, viés de modelo único ou validade interna/externa. |
| **Conclusão e Trabalhos Futuros** | — | **Ausente** | Inexistente. |

### 1.2 Arquitetura, Metodologia, Métricas e Premissas Prometidas Atualmente

- **Arquitetura prometida:** 3 fases — **A. Planejamento** com 2 etapas (`A.1` critérios gerais, `A.2` decomposição direta na fila); **B. Execução em Loop** (`B.1` seleção/resolução com *Fresh Context* apenas entre tarefas, `B.2` verificação local compartilhando a mesma janela nas retentativas, `B.3` armazenamento local, `B.4` extração sobre o "contexto completo da tarefa" restrita exclusivamente ao loop B); **C. Criação da Resposta Final** (`C.1` verificação global, `C.2` planejamento adicional no topo da fila, `C.3` síntese final exclusivamente a partir de resultados armazenados, sem aprendizados).
- **Premissas experimentais prometidas:**
  - **Modelos:** Llama 3.1 nas variantes **8B, 70B e 405B** para isolar efeito de orquestração vs. escala (L789).
  - **Referência de mercado:** comparação com resultados publicados de **Claude Sonnet 4.6** e **GPT 5.4** nos mesmos datasets (L793).
  - **Datasets:** **MMLU** e **GPQA** (L290, L791).
  - **Baseline:** chamada direta em uma única etapa de inferência "sem qualquer processamento auxiliar" (L791).
  - **Métrica:** exclusivamente **acurácia** por correspondência estrita entre a alternativa selecionada e o gabarito oficial (L290, L791), sem mencionar custo de tokens, latência, taxa de falhas operacionais ou significância estatística pareada.

---

## Etapa 2: Auditoria de Divergências (Paper vs. Implementação Real)

| Componente / Seção do Paper | O que o Paper diz | O que o Código realmente faz | Ação necessária no texto |
|---|---|---|---|
| **Fase A — Estrutura do Planejamento** (Seção III.A, L393–L483) | Planejamento possui **2 etapas** (`A.1` e `A.2`). A lista de `A.2` entra diretamente na fila de execução. | O fluxo atual (`flow_version = 2`, `apps/backend/src/domain/enums/thinking_phase_enum.py`) possui **4 etapas**: `A.1` critérios gerais → ciclo **`A.2` ⇄ `A.3` (Validação da Decomposição)** com rubrica fixa de 7 regras em `apps/backend/src/infra/templates/a3_decomposition_validation.md` (até `RALPH_MAX_PLANNING_ATTEMPTS = 5` candidatos em `RalphThinkingUseCase.__run_planning`, L363–L384); só o plano aprovado entra na fila em `__confirm_plan` (L493–L524) → **`A.4` (Aprendizados do Enunciado)** em `PlanningLearningsPhase` e `apps/backend/src/infra/templates/a4_planning_learnings.md`. | Reescrever Seção III.A para 4 subetapas (`A.1`–`A.4`), incluir as expressões de `A.3` e `A.4` e redesenhar a Figura 2 (`ralph_loop_adaptado_png.png`). |
| **Escopo e Proveniência dos Aprendizados Pontuais** (Seções III.B L493–L501, III.B.4 L603–L643, III.C L651–L772) | Memória inicia vazia na Tarefa 1; aprendizados têm escopo **estritamente restrito à fase B** e **"em nenhuma hipótese"** entram na fase C. | `A.4` pré-popula a memória antes da Tarefa 1 com dados literais do enunciado (`[Question]`). Todos os 6 templates das fases B e C (`B.1`, `B.2`, `B.4`, `C.1`, `C.2`, `C.3`) recebem a seção fixa `## Key Learnings` via `RalphThinkingUseCase.__learnings_variables` (L1348–L1357). `LearningsMemory` (`apps/backend/src/domain/services/learnings_memory.py`) faz deduplicação exata normalizada por espaços, rastreia múltiplas fontes (`[Question]`, `[Task T1]`, `[Tasks T1, T3]`) e suporta `withdraw()`/`restore()` quando resultados são revisados. | Atualizar todas as expressões de `B.2`, `B.4`, `C.1`, `C.2`, `C.3`, remover a afirmação de proibição na fase C e explicar o papel de referência separada dos resultados armazenados + rótulos de procedência. |
| **Isolamento de Contexto (*Fresh Context*) em Retentativas e em B.4** (Seções III.B.2 L527 e III.B.4 L603–L612) | Afirma que o contexto **não** é reinicializado entre tentativas da mesma tarefa e que `B.4` roda sobre o "contexto completo da tarefa" acumulado na janela. | **Toda mudança de fase e toda retentativa de `B.1` abrem uma janela nova** (`__new_context` em `RalphThinkingUseCase.__resolve_task` L651–L675 e `__extract_learnings` L788), garantido por `BaseThinkingPhase.__ensure_fresh_window` (`apps/backend/src/application/phases/base_thinking_phase.py`, L454–L474). Apenas correções de saída inválida reaproveitam a janela da mesma invocação de fase. O histórico anterior chega como entrada delimitada (`<previous_attempts>` em `B.1`, `<task_history>` + `<approved_result>` em `B.4`). | Corrigir a descrição de *Fresh Context* na Seção III.B: explicitar o isolamento total por invocação de fase e a injeção estruturada do histórico. |
| **Critérios Fixos do Harness (`-TECH` e `-REV`)** (Seção III.B.2, L525–L571) | `B.2` avalia apenas os critérios individuais planejados em `A.2` (ou `C.2`) e recebe apenas o resultado preliminar e esses critérios. | `Task.verification_criteria()` (`apps/backend/src/domain/entities/thinking/task.py`, L108–L117) e `harness_criteria.py` (`apps/backend/src/domain/entities/thinking/harness_criteria.py`) injetam deterministicamente **`<task_id>-TECH`** (validade técnica obrigatória: premissas, relação decisiva, consistência) em **toda tarefa**, e **`<task_id>-REV`** em tarefas revisoras. `B.2` também recebe a descrição da tarefa (`task_description`) e `Key Learnings` (`__verification_variables`, L1290–L1312). | Documentar `<id>-TECH` e `<id>-REV` na Seção III.B.2 e atualizar a expressão (4) (`eq:fluxo_b2`). |
| **Livro de Resultados (`ResultsLedger`), Dependências (`depends_on`) e Revisões (`review`)** (Seções III.B.3 L575–L597 e III.C.2 L712–L756) | Armazenamento local passivo indexado por tarefa; tarefas são independentes e `C.2` apenas cria tarefas novas para lacunas faltantes. | `ResultsLedger` (`apps/backend/src/domain/services/results_ledger.py`) mantém máquina de estados (`CURRENT`, `SUPERSEDED`, `AWAITING_REVALIDATION`). Tarefas declaram `depends_on` (em `A.2`/`C.2`) e `review` (em `C.2`), propondo vereditos `confirmed`/`superseded` em `B.1` validados via `<id>-REV` em `B.2` e aplicados atomicamente em `B.3` (`__store_result`, L743–L752) com suspensão transitiva de dependentes e retirada/restauração na memória de aprendizados. `C.2` recebe resumos (`statement` + `conclusion`), `result_revisions` e a pergunta original (`user_question`). | Documentar o ciclo de vida de resultados vigentes/substituídos/suspensos, a separação `result` vs. `conclusion` em `B.1`, e o mecanismo de revisão auditável em `C.1`/`C.2`/`B.3`. |
| **Escalonamento Dinâmico de Temperatura em Retentativas** (Ausente no Paper) | Não menciona temperatura nem variação entre chamadas. | Retentativas de `B.1` após reprovação de `B.2` e correções de saída inválida/vazia usam **`temperature = 1.0`** (`BaseThinkingPhase._RETRY_TEMPERATURE`, L90 e L430–L452). Revisões semânticas de `A.2` após reprovação de `A.3` usam escala progressiva: candidato 1 = temperatura da sessão (`0.0` nos benchmarks), candidato 2 = **`0.5`**, candidatos 3–5 = **`1.0`** (`RalphThinkingUseCase.__plan_revision_temperature`, L430–L447). Verificações (`A.3`, `B.2`, `C.1`) retornam à temperatura da sessão. | Incluir subseção explicando a política de temperatura em retentativas e sua motivação técnica (quebrar determinismo repetitivo em `T = 0`). |
| **Saída Estruturada em JSON, Parser, Reparos e Recuperação** (Ausente no Paper) | Prompts e saídas são ilustrados como texto livre em português; não trata falhas de formato ou parsing. | **Todos os 10 templates estão em inglês** (`apps/backend/src/infra/templates/*.md`) e exigem JSON estrito. `StructuredResponseParserAdapter` (`apps/backend/src/infra/adapters/structured_response_parser_adapter.py`) extrai JSON puro/em cercas/recortado, repara chaves/colchetes finais ausentes (`__repair_missing_closings`, exceto em `finish_reason == "length"`), escapa backslashes inválidos e valida estritamente esquemas, unicidade de IDs e coerência `decision`/`met`/`unmet_criteria_ids`. Recusas disparam até `RALPH_JSON_PARSE_MAX_RETRIES = 2` prompts de correção diferenciados por defeito (`SYNTAX`, `CONTRACT`, `TRUNCATED`) na mesma janela (`BaseThinkingPhase.__run_until_accepted`, L360–L428), gravando `OutputDiagnostic` e `OutputRecovery`. | Adicionar seção de Implementação cobrindo contrato JSON, idioma inglês dos templates, reparo estrutural conservador e cadeia de recuperação. |
| **Resiliência de Custos, Orçamentos e Política *Fail-Closed*** (Ausente no Paper) | Não define limites operacionais; assume convergência do loop até aprovação. | `CostGuardAdapter` (`apps/backend/src/infra/adapters/cost_guard_adapter.py`) + `Settings` (`apps/backend/src/infra/config/settings.py`, L86–L94) impõem 7 limites rígidos (defaults: `max_task_attempts = 5`, `max_planning_attempts = 5`, `max_additional_planning_rounds = 2`, `max_tasks_per_session = 12`, `max_llm_calls_per_session = 60`, `final_answer_token_reserve = 4000`, `session_timeout_seconds = 600`, além do `max_tokens` da sessão). Semântica estritamente ***fail-closed*** (`RalphThinkingUseCase.__fail`, L970–L1038): atingir qualquer limite ou esgotar parsing encerra a sessão como `failed` com `final_answer = None`. | Documentar os guardrails de custo e a política *fail-closed* — essenciais para interpretar as falhas operacionais na Etapa 3. |
| **Fidelidade de `C.3` e Imutabilidade da Aprovação Global** (Seção III.C.3, L759–L783) | `C.3` apenas formata resultados compilados com critérios gerais. | `C.3` recebe o snapshot imutável de `GlobalApproval` validado por `approval.ensure_current()` (L938–L947), inclui `Key Learnings` para conferência literal de identificadores/alternativas e um checklist interno de 7 pontos (`Fidelity check before answering` em `c3_final_answer.md`, L62–L116). | Atualizar Seção III.C.3 e expressão (8) (`eq:fluxo_c3`). |
| **Modelos e Provedor de Inferência** (Resumo L290, Seção I L311, Seção IV L789–L793) | Promete avaliar **Llama 3.1 (8B, 70B e 405B)** e comparar com resultados publicados de **Claude Sonnet 4.6** e **GPT 5.4**. | As 3 baterias foram executadas com **um único modelo**: **`deepseek/deepseek-v4-flash-0731`** via **`open_router`** (`LLMServiceFactory` em `apps/backend/src/infra/services/llm_service_factory.py` registra apenas `OpenRouterService`; OpenAI e Azure existem no código mas não são registrados), com `temperature = 0.0`, `max_tokens = 1.000.000`, `max_parallel = 10` e `LLM_REASONING_EFFORT = minimal` → `{"reasoning": {"enabled": False}}` (`OpenRouterService.payload_extras`, L99–L116). Não há dados de Llama 3.1 nem baseline externo integrado. | Reescrever a Seção IV para refletir o modelo realmente avaliado (`deepseek/deepseek-v4-flash-0731`), o desligamento de *reasoning* nativo na OpenRouter, e remover promessas não executadas (ou rodar novas baterias antes da versão final). |
| **Datasets, Amostragem e Protocolo de Prompt** (Seção IV, L791) | Menciona apenas "questões amostradas das bases MMLU e GPQA" e baseline "sem qualquer processamento auxiliar". | Existem **3 benchmarks**: (1) **Vestibular** (`vestibular-v1`, corpus próprio de 270 questões de ENEM, FUVEST, ITA e UNICAMP em português — ver `apps/backend/src/infra/benchmark/VALIDATION.md` e `FileBenchmarkQuestionProvider`); (2) **MMLU** (285 questões = 57 disciplinas × 5 via `select_subject_questions`, `sample_seed = 42`, `generative_0shot`); (3) **GPQA Diamond** (198 questões, `choice_seed = 0`, `sample_seed = 42`, `generative_0shot`). Ambos os fluxos recebem a instrução de benchmark (`gpqa.md`, `mmlu.md`, `vestibular.md`), que permite passo a passo — e no GPQA instrui explicitamente `"Reason carefully before answering"` (elicitando **Zero-Shot CoT** no baseline). | Incluir e documentar o corpus de Vestibulares, especificar revisões/hashes/seeds exatas, e esclarecer que o baseline é **inferência direta 0-shot com CoT livre** (explicitamente induzido em GPQA). |
| **Avaliador Determinístico e Contabilização de Falhas** (Seção IV, L791) | Apenas diz "correspondência estrita entre a alternativa selecionada e o gabarito oficial". | `BenchmarkAnswerEvaluator.select_alternative` (`apps/backend/src/domain/services/benchmark_answer_evaluator.py`) exige marcador exato na **última linha** (`RESPOSTA_FINAL: LETRA` ou `FINAL_ANSWER: LETTER`), letra isolada ou alternativa completa isolada. `BenchmarkModeSummary` (`apps/backend/src/domain/entities/benchmark/benchmark_mode_summary.py`) conta falhas técnicas, limites de recurso e formato inválido **como erros em `wrong`** (reduzindo a acurácia global), registrando-os separadamente em `failures`. | Explicitar a regra determinística de extração e reportar ambas as visões: **acurácia ponta-a-ponta (incluindo falhas)** e **acurácia condicional (execuções válidas concluídas)**. |
| **Infraestrutura da Aplicação** (Ausente no Paper) | Não menciona a plataforma construída. | O projeto inclui backend FastAPI + WebSockets, serviço de autenticação multiusuário (`apps/auth`), frontend React/Vite com visualização em Chat e Grafo (`apps/frontend`), executor paralelo (`RunBenchmarkUseCase`) e reexecução seletiva (`RerunBenchmarkQuestionUseCase`). | Mencionar brevemente a plataforma de instrumentação e observabilidade na seção de Implementação. |
| **Inconsistência menor no código/templates** (N/A no Paper) | — | Referência residual a `A.3` onde hoje é `A.4` em `apps/backend/src/infra/templates/b4_learnings_extraction.md` (L90: `"Only supplied data belong to A.3"`) e nas docstrings de `apps/backend/src/domain/services/learnings_memory.py` (L29–L44). | Corrigir nos templates caso haja nova bateria experimental; não replicar no texto do paper. |

---

## Etapa 3: Análise Crítica dos Resultados (Dados Crus)

Métricas recalculadas diretamente dos arquivos JSON das três baterias em `apps/backend/data/benchmark-sessions/owners/usr_c28b144c4601c68b97cc26391381e89c/` e das **1.494 sessões individuais** em `apps/backend/data/sessions/owners/usr_c28b144c4601c68b97cc26391381e89c/` (100% `flow_version = 2`, `deepseek/deepseek-v4-flash-0731`, `temperature = 0.0`, `max_tokens = 1.000.000`).

### 3.1 Visão Geral Quantitativa

**Integridade das três baterias:**
- **Vestibular (`bench_b72b883cb604496c917119d00e55d3b3`):** status `interrupted` — 268/270 questões concluídas nos dois fluxos (2 interrompidas antes do Ralph: `FISICA_ITA_2025_F1_UNICA_Q023` e `MATEMATICA_ENEM_2024_AZUL_Q143`).
- **MMLU (`bench_9be03b85641c4b62bfa7cd81ebe62d03`):** status `completed` — 285/285 questões (57 disciplinas × 5). **Achado forense:** a execução inicial atingiu o limite de créditos da chave OpenRouter (`HTTP 403 Key limit exceeded`) às `00:27:23 UTC` após ~115 questões (`finished_at = 00:27:27`), e ~170 questões foram retomadas via *rerun* entre `00:30:32` e `00:46:49` (`updated_at`). Uma questão (`MMLU_college_mathematics_test_0093`, `sess_d9c2da588f594127bfbe1026e58e586a`) ficou sem reexecução do Ralph, preservando o `HTTP 403` como 1 das 3 falhas do MMLU.
- **GPQA Diamond (`bench_c0b581509c944a10adde91d57d80ef7f`):** status `interrupted` — 190/198 questões concluídas nos dois fluxos (8 questões de química interrompidas: 6 só com Simple, 2 sem nenhum fluxo).

#### Tabela 1 — Acurácia Pareada: Ponta-a-Ponta (todas executadas) vs. Execuções Válidas (sem falhas operacionais)

| Bateria (Dataset) | N pareado | Simple (Todas) [IC 95%] | Ralph (Todas) [IC 95%] | Δ (Todas) | Falhas (S / R) | N válido | Simple (Vál.) | Ralph (Vál.) | Δ (Vál.) | +Resg / −Regr (Vál.) | McNemar p (Todas / Vál.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Vestibular** (`bench_b72b...`) | 268 / 270 | 95,52% [92,3–97,4] | 95,15% [91,9–97,1] | −0,37 pp | 1 / 7 | 260 | 96,15% | **97,69%** | **+1,54 pp** | **+5 / −1** | 1,000 / 0,219 |
| **MMLU** (`bench_9be0...`) | 285 / 285 | **89,82%** [85,8–92,8] | 87,02% [82,6–90,4] | −2,81 pp | 0 / 3 | 282 | **90,07%** | 87,94% | −2,13 pp | +8 / −14 | 0,152 / 0,286 |
| **GPQA Diamond** (`bench_c0b5...`) | 190 / 198 | **73,68%** [67,0–79,4] | 70,53% [63,7–76,6] | −3,16 pp | 1 / 21 | 169 | 72,78% | **79,29%** | **+6,51 pp** | **+22 / −11** | 0,480 / 0,080 |
| **Agregado Total** | **743** | **87,75%** (652) | 85,73% (637) | −2,02 pp | 2 / 31 | **711** | 88,19% (627) | **89,45%** (636) | +1,27 pp | +35 / −26 | 0,133 / 0,306 |

**Síntese quantitativa:** Na métrica ponta-a-ponta, o harness fica atrás do baseline nos 3 benchmarks (−0,37 a −3,16 pp). Porém, **25 das 51 regressões totais (49%) são falhas operacionais** (17/28 no GPQA, 6/7 no Vestibular, 2/16 no MMLU). Entre execuções válidas concluídas, o Ralph supera o baseline no **GPQA Diamond (+6,51 pp, 22 resgates vs. 11 regressões)** e no **Vestibular (+1,54 pp, 5 resgates vs. 1 regressão)**, enquanto piora no **MMLU (−2,13 pp, 8 vs. 14)**.

#### Tabela 2 — Custo de Tokens, Latência e Dispersão

| Bateria | Simple Tokens Média ± DP (Mediana; IQR) | Ralph Tokens Média ± DP (Mediana; IQR) | Razão R/S (Mediana) | Simple Tempo (s) Média (Mediana) | Ralph Tempo (s) Média (Mediana) | Chamadas LLM Ralph Média ± DP (Mediana) |
|---|---:|---:|---:|---:|---:|---:|
| **Vestibular** | 733 ± 371 (620; 545–765) | 56.313 ± 24.452 (51.139; 36,7k–64,7k) | **79,2×** | 2,07 (1,77) | 39,08 (35,17) | 12,7 ± 3,4 (12) |
| **MMLU** | 335 ± 168 (287; 250–369) | 45.872 ± 15.050 (45.421; 31,0k–54,2k) | **140,7×** | 1,70 (1,46) | 36,22 (32,89) | 11,9 ± 2,6 (12) |
| **GPQA Diamond** | 1.888 ± 13.758* (732; 588–991) | 92.044 ± 59.454 (76.538; 58,3k–113,4k) | **97,1×** | 10,71* (3,03) | 92,60 (57,39) | 16,0 ± 4,8 (15) |
| **Total Acumulado** | **651.365 tokens** | **45.653.918 tokens** | **70,1× total** | 3.098 s | 38.388 s (12,4×) | **9.836 chamadas** |

*\*Outlier no Simple do GPQA: `GPQA_diamond_recVvpD8miVjmmyfe` (`sess_f40011e40ff24e9fb90ce0d840682bff`) entrou em loop degenerado com 193.303 tokens e 1.306 s.*

#### Consumo por Fase do Harness (Agregado — 45.653.918 tokens, 9.836 invocações)

| Fase | Chamadas (% total) | Tokens Totais (% total) | Média Entrada / Chamada | Média Saída / Chamada | Observação Operacional |
|---|---:|---:|---:|---:|---|
| `A1` | 744 (7,6%) | 1.140.043 (2,5%) | 1.277 | 255 | Critérios gerais (`a1_general_criteria.md`: 693 palavras). |
| `A2` | 928 (9,4%) | 2.985.145 (6,5%) | 2.267 | 950 | Decomposição (`a2_task_decomposition.md`: 1.136 palavras). |
| `A3` | 858 (8,7%) | 2.697.746 (5,9%) | 3.061 | 83 | Validação de plano (`a3_decomposition_validation.md`: 1.248 palavras). |
| `A4` | 747 (7,6%) | 1.090.729 (2,4%) | 1.236 | 224 | Aprendizados do enunciado (`a4_planning_learnings.md`: 671 palavras). |
| **`B1`** | **1.741 (17,7%)** | **10.246.632 (22,4%)** | **4.574** | **1.311** | Resolução (`b1_task_resolution.md`: 2.284 palavras). |
| **`B2`** | **1.773 (18,0%)** | **11.480.601 (25,1%)** | **5.929** | **547** | **Maior consumidor de tokens do sistema** (`b2_task_verification.md`: 3.048 palavras). |
| **`B4`** | **1.593 (16,2%)** | **7.508.250 (16,4%)** | **4.427** | **286** | Extração de aprendizados (`b4_learnings_extraction.md`: 1.764 palavras). |
| `C1` | 725 (7,4%) | 4.758.744 (10,4%) | 6.055 | 509 | **Aprovou 99,2% das sessões** (reprovou apenas 6 vezes em 725 chamadas). |
| `C2` | 8 (0,1%) | 66.924 (0,1%) | 7.445 | 921 | Acionada em **5/743 sessões (0,67%)**; `ResultsLedger` aplicou revisões em apenas **3 sessões (0,40%)** (2 Vestibular, 1 MMLU, 0 GPQA). |
| `C3` | 719 (7,3%) | 3.679.104 (8,1%) | 4.951 | 166 | Síntese final (`c3_final_answer.md`: 1.841 palavras). |

---

### 3.2 Análise Condicional (Onde Acerta vs. Onde Erra)

#### A. Regime de Alta Complexidade Analítica vs. Conhecimento Geral / Teto Saturado

| Regime / Estrato | N (Todas) | Simple (Todas) | Ralph (Todas) | Δ Todas (p) | N (Vál.) | Simple (Vál.) | Ralph (Vál.) | Δ Válidas | +Resg / −Regr (Vál.) | McNemar p (Vál.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Alta Complexidade (GPQA + ITA + UNICAMP)** | 248 | 76,61% | 75,40% | −1,21 pp (0,791) | **224** | 76,34% | **83,48%** | **+7,14 pp** | **+27 / −11** | **0,0139** |
| **Geral / Teto (MMLU + ENEM + FUVEST)** | 495 | **93,33%** | 90,91% | **−2,42 pp (0,043)** | **487** | **93,63%** | 92,20% | −1,44 pp | +8 / −15 | 0,2100 |

- **Cenários em que o Ralph supera o baseline (em execuções válidas):**
  - **ITA (Vestibular):** Simple `84,62%` → Ralph **`94,87%`** (**+10,26 pp**, +4 resgates / 0 regressões, N_val = 39; `ITA_FISICA`: `81,82%` → **`100%`** [+18,18 pp]; `ITA_MATEMATICA`: `85,71%` → **`100%`** [+14,29 pp]; `ITA_QUIMICA`: `85,71%` → `90,48%` [+4,76 pp]). Mesmo ponta-a-ponta, o ITA fecha em **+4,76 pp** (`83,33%` → `88,10%`).
  - **UNICAMP (Vestibular):** `93,75%` → **`100,00%`** (+6,25 pp, +1/−0, N = 16, 0 falhas).
  - **Física no Vestibular (todas as bancas):** `89,80%` → **`97,96%`** (**+8,16 pp** ponta-a-ponta, N = 49, 0 falhas).
  - **Exatas no Vestibular (Física + Matemática + Química):** válidas `94,41%` → **`97,90%`** (**+3,50 pp**, +5/−0, p = 0,0625, N_val = 143).
  - **GPQA Diamond — ganho nos 3 domínios científicos (válidas):**
    - **Biologia:** `61,11%` → **`77,78%`** (**+16,67 pp**, +4/−1, N_val = 18; ponta-a-ponta +15,79 pp).
    - **Química:** `61,64%` → **`68,49%`** (**+6,85 pp**, +12/−7, N_val = 73), porém 12 falhas operacionais derrubam o ponta-a-ponta para −4,71 pp.
    - **Física:** `85,90%` → **`89,74%`** (**+3,85 pp**, +6/−3, N_val = 78), porém 8 falhas operacionais derrubam o ponta-a-ponta para −5,81 pp.
  - **Proxy de complexidade (tercil superior de tokens da resposta do Simple):**
    - Vestibular (`> 691 tok`, N_val = 86): `90,70%` → **`95,35%`** (**+4,65 pp**, +4/−0, p = 0,125).
    - GPQA (`> 840 tok`, N_val = 56): `62,50%` → **`73,21%`** (**+10,71 pp**, +9/−3, p = 0,146) — mesmo tercil que concentrou 12 das 21 falhas operacionais do GPQA.

- **Cenários em que o Ralph empata ou piora:**
  - **ENEM (efeito teto):** baseline já acerta `98,48%` (N_val = 198). O Ralph registra **0 resgates**, 1 regressão semântica (`GEOGRAFIA_ENEM_2022_AZUL_Q064`) e **4 falhas operacionais**, fechando em `96,06%` (−1,97 pp) ao custo de ~79× mais tokens.
  - **MMLU Humanidades (N = 65, 0 falhas):** Simple **`87,69%`** vs. Ralph `80,00%` (**−7,69 pp**, +1 resgate vs. **−6 regressões**, p = 0,125).
  - **MMLU Ciências Sociais (N_val = 59):** `91,53%` → `88,14%` (**−3,39 pp**, +1/−3). **MMLU STEM (N_val = 88):** empate exato (`90,91%` vs. `90,91%`, +3/−3). **MMLU Outros (N_val = 70):** `90,00%` → `91,43%` (+1,43 pp, +3/−2).
  - **MMLU questões curtas (`≤ 260 tok` no Simple, N = 95):** `91,58%` → `88,42%` (**−3,16 pp**, +1/−4).

#### B. Segmentação por Variáveis Internas de Controle do Harness

| Variável Interna do Harness | N (Todas) | Simple (Todas) | Ralph (Todas) | Falhas Ralph | N (Vál.) | Simple (Vál.) | Ralph (Vál.) | Δ Válidas | +Resg / −Regr | McNemar p (Vál.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`B.2` = 0 reprovações (Agregado)** | 695 | 89,06% | 89,35% | 15 | 679 | 89,40% | **91,31%** | **+1,91 pp** | +33 / −20 | 0,0984 |
| — *idem, somente GPQA Diamond* | 159 | 75,47% | **79,25%** | 10 | 149 | 75,17% | **84,56%** | **+9,40 pp** | **+21 / −7** | **0,0130** |
| **`B.2` = 1 reprovação (Agregado)** | 20 | 55,00% | 55,00% | 0 | 20 | 55,00% | 55,00% | +0,00 pp | +2 / −2 | 1,0000 |
| **`B.2` ≥ 2 reprovações (Agregado)** | 28 | **78,57%** | **17,86%** | **16** | 12 | **75,00%** | **41,67%** | **−33,33 pp** | **0 / −4** | 0,1250 |
| **`A.3` ≥ 1 reprovação — Vestibular** | 23 | 91,30% | **100,00%** | 0 | 23 | 91,30% | **100,00%** | **+8,70 pp** | +2 / −0 | 0,5000 |
| **`A.3` ≥ 1 reprovação — MMLU** | 27 | 70,37% | **74,07%** | 1 | 26 | 73,08% | **76,92%** | **+3,85 pp** | +4 / −3 | 1,0000 |
| **`A.3` ≥ 1 reprovação — GPQA** | 52 | 73,08% | 69,23% | 7 | 45 | 71,11% | **80,00%** | **+8,89 pp** | +8 / −4 | 0,3880 |

---

### 3.3 Análise de Causa Raiz (O "Porquê")

#### A. Padrões de Falha e Regressão (Por que falhou nos piores cenários)

1. **Deadlock Arquitetural de `B.2` sem *Backtracking* para Erros *Upstream* (16 de 31 falhas operacionais — 51,6% das falhas):**
   - **Mecanismo:** Revisões de resultados (`ResultsLedger` + `review`) só podem ser planejadas em **`C.2`**, que só é atingida depois que todas as tarefas passam por `B.2`. Quando `T1`/`T2` é aprovada com erro, a tarefa final (`T2`–`T5`) confronta um resultado errado contra as alternativas A–D/E; como nenhuma casa, `B.1` recusa escolher ou força um *best fit* incoerente, e `B.2` reprova 5 vezes até `CostGuardAdapter` encerrar em `failed` (`task_attempts`).
   - **Amostras por erro *upstream* (12 de 16 deadlocks):**
     - `MATEMATICA_ENEM_2023_AZUL_Q138` (`sess_8431b537ec9a4b43b20f13e65085e16a`): `T1` assumiu 8 bolinhas na urna B em vez de 16; `B.2` aprovou `T1` e `T2` (`n = 72`). Como 72 não está em `{20, 60, 64, 68, 80}`, `T3` declarou "nenhuma alternativa corresponde" nas 5 tentativas (100.712 tokens; Simple acertou `C) 64`).
     - `QUIMICA_ITA_2025_F1_UNICA_Q035` (`sess_5bfc65d3d0664fcabe24e8aaaa43f0b7`): `T1` calculou NOX de `HCOOH` errado (+3 em vez de +2) e foi aprovada; `T2` não encontrou nenhuma alternativa errada e travou 5× (105.048 tokens; Simple acertou `E`).
     - `GPQA_diamond_recXsYa3i2UhGF5fe` (`sess_f893681e00d54df1bb70931686d8776a`): `T1` derivou estrutura com IHD = 4 (aprovada); `T2` não encontrou opção igual a 4 e travou 5× (121.604 tokens; Simple acertou `A`).
     - Outros casos do mesmo padrão: `QUIMICA_ITA_2024_F1_UNICA_Q053` (`sess_3c1ba3ec8953487ca912874563d80b18`), `GPQA_diamond_recO3hvCWRGiG0odN` (`sess_59d048ff9e7e488faba2dacb9c8177c5`), `GPQA_diamond_recYCMJWH7IpcdqwE` (`sess_61867cd85f3549e7ac886e7d3881eb40`), `GPQA_diamond_recBGxVySx1pkrO1i` (`sess_8ebb6ef94f87450187bb15fe714d2926`), `GPQA_diamond_recJZ3QEfRKjYw9a7` (`sess_88f964d1919d47f2ad151bb4d8c37e7e`), `GPQA_diamond_recUOePh79cp4T2Bg` (`sess_140ee98027d44c68b3a65c6fd3ac0a7f`), `GPQA_diamond_recZt4x514UQNnsgy` (`sess_98001c6544d04ae696864279dcdecbe9`), `GPQA_diamond_recIj8lR4tuDgrHou` (`sess_e33dff894a574c6ba1f39384680e142b`) e `GPQA_diamond_recqGD3fxPCI59vPQ` (`sess_ba5cceb5b61648dd9520c2abec39dc76`).
   - **Amostras por hiper-literalismo de critério planejado (3 de 16 deadlocks):**
     - `MATEMATICA_ITA_2024_F1_UNICA_Q043` (`sess_b94fbae537734de2b0eb00796e1d7145`): `B.1` acertou **`E) (2, 5/2)` nas 5 tentativas**, mas `T4-AC2` exigia igualdade exata com o domínio `(2, +∞)` e `B.2` reprovou a resposta correta 5 vezes até matar a sessão (116.762 tokens).
     - `GEOGRAFIA_ENEM_2024_AZUL_Q071` (`sess_42c2ba7c35094ffe9795fe5426cab716`): `B.1` acertou `D` na Tentativa 1, foi reprovada por literalismo de `T2-AC2`/`T2-TECH` e passou a responder "nenhuma alternativa correta" nas tentativas 2–5.
     - `GPQA_diamond_recgM7o1tcc7tP778` (`sess_00485314ae0d4707a8051ee92c6045ae`): `B.1` acertou `D` na Tentativa 1, mas `T2-AC3` exigia satisfazer Pauli e violar J/P simultaneamente, reprovando 5×.
   - **Falha local de convergência em `T1` (1 de 16):** `GPQA_diamond_recZ13cwgDQf9jRd9` (`sess_b7f61ce7cfca4183b960ab82afd31796`, 5 reprovações em `T1` por atribuição de RMN).

2. **Reversão Destrutiva em `B.2` (Falso Negativo do Validador + Retentativa a `T = 1.0`):**
   - Por usar o mesmo modelo como resolvedor e validador, `B.2` rejeita respostas corretas e empurra `B.1` para respostas erradas.
   - `GPQA_diamond_recEmTBhx2hgw6tPQ` (`sess_4a633387db5048399ae0436e3e2505fd`): Tentativa 1 de `T1` derivou o estereoisômero correto **`C`** (`(3aR,4R,7S,7aS)`), mas `B.2` reprovou `T1-TECH`; na Tentativa 2 (`T = 1.0`), `B.1` trocou para **`A`** (`(3aR,4S,7R,7aS)`, errado) e `B.2` aprovou.
   - Racionalizações forçadas após múltiplas reprovações de `B.2` também geraram regressões válidas em `GPQA_diamond_recrHBEJJoDTV05JR` (`sess_1f4a91bdcb1e429c8fb33d18c9395ba0`, 3 reprovações → `D`), `GPQA_diamond_reczzzihL7btBH7RO` (`sess_95b3c6b47e044976b41b0b01c82ba23c`, 2 reprovações → `A`) e `GPQA_diamond_recyl3usDqb7ruXJx` (`sess_5f1c07a064464b93b746bf8833846ee7`, 2 reprovações → `C`).

3. **Fragilidade de Serialização JSON e Recuperação Cega (8 de 31 falhas + 627 reparos + 162 recusas):**
   - Em 9.836 invocações, `valid_after_repair` atuou em **627 chamadas (6,37%)** (chaves/colchetes finais omitidos pelo modelo) e o parser recusou **162 saídas (1,65%)**, resultando em **8 falhas fatais** (2 no Vestibular, 1 no MMLU, 5 no GPQA).
   - `GPQA_diamond_recGee5m84dg5FZkc` (`sess_5966dbd3439f40c8ab25228929a57f44`): em `B.2` da última tarefa (`T3`), o modelo emitiu um único `}` extra (`"...sound."}}],"unmet_criteria_ids":[]...`). Como `_CORRECTION_BY_DEFECT[SYNTAX]` (`base_thinking_phase.py`, L39–L45) informa apenas `"No valid JSON object was found in the output"` sem a linha/coluna/trecho do `JSONDecodeError`, o modelo repetiu o exato `}}]` 3× seguidas e abortou 80.369 tokens.
   - `BIOLOGIA_ENEM_2022_AZUL_Q133` (`sess_78910ad218ab42588fb8c5945afb3402`) e `BIOLOGIA_ENEM_2024_AZUL_Q105` (`sess_14af9d7a84a546508cb5096185e99f00`): mesmo padrão de `json_syntax` repetido 3× em `B.2`.
   - `GPQA_diamond_rec9W28HgpEUeUN8k` (`sess_9ab0695a76e44028a4667f710ee5736e`): em `C.2`, o modelo gerou `"review": {}` (dicionário vazio em vez de omitir o campo) e repetiu o mesmo JSON de 3.860 caracteres 3× idênticas até abortar 138.237 tokens.
   - Outras falhas fatais de parsing em `A.2`: `MMLU_college_mathematics_test_0098` (`sess_098b1b7d1e5e4969a45d94dd230ba1d0`), `GPQA_diamond_recPSTGXK3P39yNYT` (`sess_16aae04b8c624b298754a13bdd4ff4c3`), `GPQA_diamond_recINGR1z01Fh1Z3A` (`sess_97c2a68ef6e64900a8554a4482a9f055`), `GPQA_diamond_recPzW1WqRnPs57D6` (`sess_8e0db0772f3f49bdafe1a777e91f083c`).

4. **Teto de Saída por Chamada Desacoplado (`1.000.000` tokens) e Timeout Não-Preemptivo (3 de 31 falhas no GPQA):**
   - `BaseThinkingPhase.__call_max_tokens()` (L720–L731) envia todo o saldo da sessão (~990k tokens) como `max_tokens` de uma única chamada, e `CostGuardAdapter` só verifica `session_timeout_seconds = 600` entre chamadas.
   - Em `GPQA_diamond_recVvpD8miVjmmyfe` (`sess_b0b999a970bc45e4b3dd020121131819`: 256.083 tok saída em `B.1`, **1.801 s**), `GPQA_diamond_rectlyG9pCAAuWhoB` (`sess_f50b9d86270a4c97a0fde9f81f8dcd9b`: 324.325 tok saída, **1.801 s**) e `GPQA_diamond_recLAgwx9vbgB5EHk` (`sess_bcc1adacfb5440178d217caa49d93831`: 177.893 tok saída, **621 s**), o modelo entrou em loop degenerado a `T = 0.0` por 10–30 minutos até a OpenRouter encerrar com `finish_reason = "error"`.

5. **Superdecomposição e *Overthinking* em Questões Factuais/Interpretativas (principal causa das 14 regressões do MMLU e da única regressão do Vestibular):**
   - Fragmentar perguntas curtas de conhecimento/humanidades em 2–3 tarefas sob templates de 1.700–3.000 palavras levou à perda da resposta canônica em favor de racionalizações secundárias ou tecnicismos literais:
     - `MMLU_high_school_biology_test_0215` (`sess_bd0e91ebf2dd49feaa52bd5610301656`): `T1` anotou que centríolos (`D`, gabarito) faltam na `"maioria"` das células vegetais; `T2` eliminou `D` pela qualificação `"most"` e escolheu lisossomos (`B`).
     - `MMLU_business_ethics_test_0075` (`sess_f0499c9479d3478fad185607ea9979b2`): após 3 tarefas, `T3` inverteu a polaridade de `"prohibition on ___ and ___ transactions"`, escolhendo `D) Certain, Assured` apesar de o próprio texto de `C.3` citar a proibição de *uncertain* (`gharar`) e *speculative* (`maysir`) (gabarito `C`).
     - Outras regressões interpretativas em Humanidades/Geografia: `MMLU_jurisprudence_test_0091` (`sess_985e1e59bf3f4558a6039bd49e120549`), `MMLU_world_religions_test_0058` (`sess_6f71a1b5aa9243ea8f4c1051a05cb221`), `MMLU_high_school_world_history_test_0137` (`sess_aea9fb6eee3545d680fc584e7a14028c`), `MMLU_high_school_us_history_test_0000` (`sess_c0b9ad8edbb24b2692400cf1c22dafe5`), `MMLU_moral_scenarios_test_0622` (`sess_45a1b5f786dd43b2805c3eb4bd763338`), `GEOGRAFIA_ENEM_2022_AZUL_Q064` (`sess_2b3f0742622d45079bbb59bca35517c1`).

6. **Falhas Residuais de Formatação em `C.3` e Infraestrutura (4 de 31 falhas):**
   - `C.3` omitiu `FINAL_ANSWER:` em `MMLU_high_school_macroeconomics_test_0007` (`sess_2f65f67e2b394394921916adbda155f8`) e emitiu `FINAL_ANSWER: NONE` (aprovado por `C.1`!) em `GPQA_diamond_rec2fsnzUuvNtUYK8` (`sess_149021655418471986db7791e1fc35e1`). Adicionalmente: 1 `planning_attempts` em `A.3` (`GPQA_diamond_recdya6FuYraBU5Rh`, `sess_37125e2288134d9ea2664d277f050861`) e 1 `HTTP 403` residual (`MMLU_college_mathematics_test_0093`, `sess_d9c2da588f594127bfbe1026e58e586a`). *(Nota positiva: `C.3` manteve alta fidelidade analítica — não trocou nenhuma letra corretamente determinada pela última `B.1` nas 26 regressões analisadas.)*

#### B. Padrões de Sucesso (Por que acertou nos 36 Resgates: 6 Vestibular, 8 MMLU, 22 GPQA)

1. **Decomposição em subtarefas isoladas evitando atalhos algébricos e erros de unidade/passo:**
   - `GPQA_diamond_recZbxrocrxh9YENH` (`sess_c2248b33712f4d688ed6d0ccdc999eb4`): Simple calculou `1900 kJ/mol` e marcou `D) 1900 kJ/g` presumindo erro de digitação da unidade; o Ralph isolou a divisão pela massa molar (`166 g/mol → 11,44 kJ/g`) e acertou `C`.
   - `MATEMATICA_ITA_2024_F1_UNICA_Q038` (`sess_01d8e070d03c45e49579857c093ab907`): decomposição em 5 tarefas construiu explicitamente o contraexemplo `A = I, D = 0`, refutando o item III que induziu o Simple ao erro (`C` → `E`).
   - `GPQA_diamond_recRhwQwHijW0gCLo` (`sess_b10388cc10c44faea3c033eddae8c886`, 5 tarefas verificando propriedades unitárias/hermitianas), `GPQA_diamond_recwW1A85nfyQpReG` (`sess_575125c1571e44559eb2e4921f56b13e`, fator jacobiano correto `r⁻²` vs. `r²`), `GPQA_diamond_recuyeuT5rQ6qDt8F` (`sess_c297accd7d024a46a672b8b2f736c91d`, estequiometria de `BrF₂` em vez dos 5.620 tokens erráticos do Simple).

2. **Auditoria de Neutralidade do Plano em `A.3` corrigindo vieses antes da execução (14 de 36 resgates — 38,9%):**
   - `FISICA_ITA_2024_F1_UNICA_Q004` (`sess_90d7f53e3fa1488dabc430ce0801936e`), `FISICA_ITA_2024_F1_UNICA_Q007` (`sess_a92d0d646f26424f984d8ce5255bb3eb`), `GPQA_diamond_recb2M22zaD3tL6Qc` (`sess_80377a9fcb5c4b78b61b7bc3e0f648f4`), `GPQA_diamond_reckl6PkaEMWM50yZ` (`sess_33b17349fd744b78b6f35ccd22052f0d`), `GPQA_diamond_recvZlMbpPz0yLDle` (`sess_d259e2e83f8c4f76aaa8c6e07036b52c`) e `MMLU_college_chemistry_test_0021` (`sess_5d86cddbdb96459d8894e7db4380d8f4`): em todos, `A.3` detectou premissas ou conclusões antecipadas no plano de `A.2` e forçou investigação neutra.

3. **Auto-correção pontual em `B.2`/`C.2` e conformidade de formato em `C.3`:**
   - `GPQA_diamond_recINSFEYLCyyd08m` (`sess_acaaf35fb0044068947f997fb2c4089f`, `B.2` corrigiu ambiguidade de numeração IUPAC → `A`), `MMLU_security_studies_test_0048` (`sess_05d2f25b30c14996b72f9b30961ad4d6`, `B.2` impediu escolha prematura → `D`), `MMLU_business_ethics_test_0040` (`sess_f7db16a960204bee924846da0763f4df`, único resgate via `C.2`), e `FISICA_ENEM_2020_AZUL_Q114` (`sess_fdbbe1da90494382a907f3c075e8cf6f`, resgate de formatação onde o Simple acertou `141 Hz` mas escreveu `**Resposta final: C**` em vez de `RESPOSTA_FINAL: C`).

---

## Etapa 4: Limitações e Hipóteses de Melhoria (Trabalhos Futuros)

### 4.1 Limitações do Projeto (Metodológicas, Técnicas e Experimentais)

1. **Validade Externa — Modelo Único e *Reasoning* Nativo Desabilitado:** Todos os resultados derivam de um único modelo (`deepseek/deepseek-v4-flash-0731`) com `reasoning: {enabled: false}`. Não é possível generalizar o comportamento para outras famílias ou escalas (ex.: 8B vs. 70B vs. 405B) nem contrastar com modelos de raciocínio nativo.
2. **Validade Interna — Baterias Incompletas, Retomada Parcial e Execução Única:** Vestibular (268/270) e GPQA (190/198) encerraram com status `interrupted`; o MMLU sofreu corte de crédito (`HTTP 403`) no meio da bateria e retomada parcial via *rerun* (deixando 1 erro `403` não reexecutado). Além disso, cada questão foi rodada uma única vez, impedindo mensurar variância estocástica (especialmente quando retentativas sobem para `T = 0,5` / `1,0`).
3. **Validade de Construto — Assimetria de Prompts e Ausência de Controle por Orçamento Computacional:** O prompt do GPQA induz explicitamente CoT no baseline (`"Reason carefully before answering"`), diferentemente de MMLU/Vestibular. Ademais, não há um baseline com **orçamento equivalente de *test-time compute*** (ex.: *Self-Consistency* com 12–16 amostras) nem uma ablação **com vs. sem *Fresh Context***, impedindo atribuir causalmente o ganho em GPQA/ITA à mitigação de *context rot* isolada da decomposição e do volume de tokens.
4. **Poder Estatístico e Efeito Teto:** A amostra do MMLU (285/14.042 questões) e a saturação do ENEM (`98,5%` no baseline) limitam o poder estatístico por subgrupo; apenas a agregação de Alta Complexidade válida (p = 0,0139) e o recorte Geral/Teto ponta-a-ponta (p = 0,0428) atingem significância a α = 0,05.
5. **Viabilidade de Custo e Latência:** O consumo mediano de **79× a 141× mais tokens** e **19× a 24× mais latência** (36–93 s/questão) — agravado por templates extensos (11k–20k caracteres cada) repetidos em toda chamada — torna a arquitetura impraticável para perguntas simples sem roteamento prévio.
6. **Escopo Restrito a Múltipla Escolha:** Embora proposto como harness generalista para linguagem natural, toda a validação empírica utilizou múltipla escolha com gabarito fechado, deixando respostas discursivas abertas sem validação quantitativa.

### 4.2 Hipóteses de Melhoria (Vinculadas aos Padrões de Erro da Etapa 3)

| # | Padrão de Erro Identificado na Etapa 3 | Hipótese Técnica de Melhoria |
|---|---|---|
| **H1** | **Deadlock de `B.2` por erro *upstream* aprovado sem *backtracking*** (12/16 falhas de `task_attempts`, ex.: `MATEMATICA_ENEM_2023_AZUL_Q138`, `QUIMICA_ITA_2025_F1_UNICA_Q035`, `GPQA_diamond_recXsYa3i2UhGF5fe`). | **Escalonamento antecipado de revisão (`B.2 → C.2`) em vez de aborto *fail-closed*:** após 2 reprovações consecutivas em `B.2` com sinalização de incompatibilidade com premissas herdadas (ex.: "nenhuma alternativa coincide"), interromper o loop local da tarefa e acionar `C.2` para criar uma tarefa revisora (`review`) sobre os resultados anteriores já no `ResultsLedger`, evitando insistir 5× localmente até abortar. |
| **H2** | **Colapso em `B.2 ≥ 2` reprovações e reversões destrutivas por validação simétrica** (`−33,33 pp` em válidas com `B.2 ≥ 2`; ex.: `GPQA_diamond_recEmTBhx2hgw6tPQ`, `MATEMATICA_ITA_2024_F1_UNICA_Q043`). | **Validação calibrada + fallback *best-effort* controlado:** (i) reduzir retentativas locais de `B.1`/`B.2` para 2–3 e proibir critérios de igualdade estrita de domínio em `A.3`; (ii) ao esgotar tentativas, degradar de forma controlada (ou desempatar por votação de k = 3 amostras independentes de `B.1`) em vez de descartar toda a sessão; (iii) investigar modelo juiz assimétrico ou rubrica mais enxuta em `B.2`. |
| **H3** | **Superdecomposição, *overthinking* e desperdício de 79×–141× tokens em questões simples/factuais** (ENEM `98,5%`, MMLU Humanidades `−7,69 pp`, `C.1` aprovando `99,2%` consumindo `10,4%` dos tokens). | **Roteamento adaptativo de complexidade (*gating*) + poda de fases redundantes:** adicionar um roteador leve (`A.0`) que direciona perguntas factuais/curtas à inferência direta e aciona o Ralph Loop apenas em problemas multi-etapas/STEM de alta densidade; tornar `C.1` condicional (acionar apenas quando houver ≥ 3 tarefas, revisões ou conflito sinalizado) e compactar os templates atuais (1.700–3.000 palavras) em ~60–70%. |
| **H4** | **Falhas fatais de serialização JSON e recuperação cega** (8 sessões abortadas, 627 reparos, 162 recusas; ex.: `GPQA_diamond_recGee5m84dg5FZkc` repetindo `}}]` 3×, `GPQA_diamond_rec9W28HgpEUeUN8k` repetindo `"review": {}`). | **Structured Outputs nativos (`response_format: json_schema`) + feedback diagnóstico preciso:** migrar da instrução textual de JSON para decodificação restrita por esquema nos provedores suportados; como fallback, incluir no prompt de correção a mensagem exata do `JSONDecodeError` (linha/coluna/trecho ao redor do erro) e normalizar campos opcionais vazios (`"review": {}` → `None`). |
| **H5** | **Loops degenerados de geração e timeout não-preemptivo** (3 falhas `session_timeout` de 620–1.828 s e 178k–324k tokens em uma única chamada de `B.1`, ex.: `GPQA_diamond_recVvpD8miVjmmyfe`). | **Teto explícito por chamada (`max_output_tokens_per_call`) + cancelamento preemptivo:** desacoplar o orçamento da sessão (`1.000.000` tokens) do teto de uma chamada individual (ex.: `8.192`–`16.384` tokens em `BaseThinkingPhase.__call_max_tokens()`) e envolver `send_conversation` em `asyncio.wait_for` limitado ao tempo restante no `CostGuardAdapter`. |
| **H6** | **Falta de evidência causal sobre mitigação de *context rot* vs. custo computacional** (limitação metodológica geral). | **Estudo de ablação controlada na próxima rodada experimental:** comparar, sob orçamento pareado de tokens e em múltiplas escalas de modelo: (i) Direct 0-shot, (ii) Self-Consistency (k amostras pareado em tokens), (iii) Ralph Loop *com* histórico acumulado (sem *Fresh Context*) e (iv) Ralph Loop *com Fresh Context*, isolando a contribuição de `A.3`, `A.4`, `B.2` e `C.1`. |
