# IV. Implementação e Arquitetura do Sistema

Para viabilizar a execução controlada, auditável e reproduzível do *Ralph Wiggum Loop* adaptado (`flow_version = 2`), desenvolveu-se uma plataforma completa estruturada sob princípios de arquitetura limpa, separando rigorosamente as regras de negócio do domínio (`domain/`), a coordenação de casos de uso e fases (`application/`) e os adaptadores de infraestrutura, provedores de inferência e transporte (`infra/`). A [FIGURA 3: Arquitetura de execução do harness, isolamento de contexto por fase, máquina de estados do ResultsLedger, LearningsMemory e cadeia de recuperação JSON] sintetiza os componentes de execução em tempo real e o ciclo de vida dos estados mantidos pelo *harness*.

[FIGURA 3: Arquitetura de execução do harness, isolamento de contexto por fase, máquina de estados do ResultsLedger, LearningsMemory e cadeia de recuperação JSON — nova figura especificada na Seção 2.1 de `00_auditoria_figuras.md`]

---

## A. Contrato JSON Estrito, *Templates* em Inglês e Isolamento de Contexto

Todos os dez *templates* internos do *harness* (`a1_general_criteria.md` a `c3_final_answer.md`), bem como as mensagens de recusa do *parser*, os *prompts* de correção estrutural e os delimitadores injetados pelo orquestrador (`<previous_attempts>`, `<approved_result>`, `<task_history>`), são mantidos em **inglês** com marcação Markdown. Essa decisão técnica busca maximizar a aderência instrucional e a consistência de raciocínio intermediário dos modelos de linguagem~\cite{shi2023multilingualcot, liu2025contentformat}, preservando o idioma original do usuário na resposta final por meio do critério de idioma capturado em `A.1` e aplicado por `C.3`. Como contrapartida operacional, a riqueza instrucional dos dez *templates* resultou em *prompts* extensos — variando de $671$ palavras em `A.4` e $693$ palavras em `A.1` até $2.284$ palavras em `B.1` e $3.048$ palavras em `B.2` —, fator que impacta diretamente o consumo basal de *tokens* de entrada analisado na Seção~VI.

O isolamento de contexto (*Fresh Context*) é imposto programaticamente pelo método `BaseThinkingPhase.__ensure_fresh_window` em conjunto com o orquestrador `RalphThinkingUseCase`: toda mudança de fase (`A.1` $\rightarrow$ `A.2` $\rightarrow$ `A.3` $\rightarrow$ `A.4` $\rightarrow$ `B.1` $\rightarrow$ `B.2` $\rightarrow$ `B.4` $\rightarrow$ `C.1` $\rightarrow$ `C.2`/`C.3`), toda nova tarefa e toda retentativa de `B.1` após reprovação de `B.2` instanciam uma nova janela de conversação limpa. O único caso em que uma janela é reutilizada ocorre durante o ciclo de recuperação de saída estruturalmente inválida dentro da mesma invocação de fase, no qual o *template* inicial é mantido uma única vez e as respostas recusadas e instruções corretivas são preservadas integralmente em sequência.

---

## B. *Parser*, Reparo Estrutural Conservador e Recuperação Diferenciada

Todas as fases exigem saída estritamente em formato JSON, validada pelo componente `StructuredResponseParserAdapter`. Para equilibrar robustez operacional e fidelidade analítica, o *parser* opera em três níveis:

1. **Extração e reparo estrutural conservador:** extrai objetos JSON puros, encapsulados em cercas de código Markdown ou recortados de texto auxiliar; escapa barras invertidas inválidas; e, exclusivamente quando o término informado pelo provedor não indica truncamento (`finish_reason != "length"`), aplica reparo conservador de chaves ou colchetes finais ausentes (`__repair_missing_closings`). O *parser* jamais fabrica campos ausentes, completa *strings* interrompidas, converte tipos silenciosamente ou altera vereditos de aprovação/reprovação.
2. **Validação estrita de contrato e coerência:** verifica esquema, tipos obrigatórios, unicidade de identificadores de tarefas e critérios, ausência de reserva indevida de `<id>-TECH` e `<id>-REV` pelo planejador, integridade referencial de `depends_on` e `review` (prevenindo autorreferências e ciclos), presença exata de todos os critérios efetivos no relatório de `B.2` e coerência lógica entre `decision`, os sinalizadores `met` individuais e a lista `unmet_criteria_ids`.
3. **Recuperação diferenciada por classe de defeito e diagnóstico estruturado:** quando uma saída é recusada, o *harness* classifica o defeito em três categorias — `SYNTAX` (ausência de JSON legível), `CONTRACT` (JSON legível que viola esquema, referências ou coerência de decisão) e `TRUNCATED` (`finish_reason == "length"` sem JSON válido) — e dispara até `RALPH_JSON_PARSE_MAX_RETRIES = 2` chamadas de correção na mesma janela, a `temperature = 1,0`, com instruções específicas para cada defeito (sem consumir tentativa da tarefa em `B.1`). Cada invocação grava na sessão um registro `OutputDiagnostic` (`syntax_status` em `{valid, invalid, valid_after_repair}`, `contract_status`, código de problema, `finish_reason` e detecção de `length_interruption`) e um vínculo `OutputRecovery`, separando explicitamente sucesso de transporte (`outcome == "success"`) de aceitação de conteúdo (`content_accepted`).

---

## C. Controle de Estado (`ResultsLedger` e `LearningsMemory`)

Dois serviços de domínio governam a consistência do estado entre janelas isoladas:

- **`ResultsLedger`:** mantém o ciclo de vida auditável das resoluções aprovadas (`CURRENT`, `SUPERSEDED` e `AWAITING_REVALIDATION`). As transições ocorrem exclusivamente de forma atômica na etapa `B.3` após aprovação completa em `B.2` (incluindo `<id>-TECH` e `<id>-REV`). Resultados substituídos permanecem no registro de auditoria (`result_revisions`), mas são excluídos das visões entregues a `C.1`, `C.2` e `C.3`; dependentes declarados via `depends_on` de um resultado substituído são suspensos transitivamente até revalidação.
- **`LearningsMemory`:** armazena cada aprendizado com sua lista de fontes de procedência (`None` para `[Question]` em `A.4` e o `task_id` para `[Task Tx]` em `B.4`). Executa deduplicação exata normalizada apenas por espaços em branco — preservando diferenciação entre maiúsculas e minúsculas para símbolos científicos e unidades — e renderiza a seção `## Key Learnings` exclusivamente a partir de fontes vigentes, retirando (`withdraw()`) ou restaurando (`restore()`) fatos conforme revisões aplicadas pelo `ResultsLedger`. Notas provenientes de `[Question]` nunca são retiradas por revisão.

---

## D. Guardrails de Custo, Escalonamento de Temperatura e Política *Fail-Closed*

Para evitar execuções indefinidas ou consumo descontrolado de recursos, o adaptador `CostGuardAdapter`, parametrizado centralmente em `Settings`, impõe sete limites rígidos de orçamento e execução combinados a uma política estritamente ***fail-closed*** (`RalphThinkingUseCase.__fail`): atingir qualquer teto de tentativas, tarefas, chamadas, *tokens* ou tempo — ou esgotar as correções de *parsing* JSON — encerra imediatamente a sessão com `status = failed` e `final_answer = None`, sem promover candidatos reprovados nem improvisar respostas de contorno. A [TABELA I: Guardrails operacionais, limites de orçamento e política dinâmica de temperatura do harness] resume os parâmetros padrão e a política de temperatura adotada para romper ciclos determinísticos em `T = 0,0`.

[TABELA I: Guardrails operacionais, limites de orçamento e política dinâmica de temperatura do harness]

| Categoria | Parâmetro / Condição Operacional | Valor Padrão / Comportamento Implementado |
|---|---|---|
| **Orçamento (`CostGuardAdapter`)** | `RALPH_MAX_PLANNING_ATTEMPTS` | Máximo de **5** planos candidatos semânticos em `A.2` $\rightleftarrows$ `A.3`. |
| **Orçamento (`CostGuardAdapter`)** | `RALPH_MAX_TASK_ATTEMPTS` | Máximo de **5** tentativas de resolução por tarefa em `B.1` $\rightleftarrows$ `B.2`. |
| **Orçamento (`CostGuardAdapter`)** | `RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS` | Máximo de **2** rodadas de planejamento adicional em `C.2`. |
| **Orçamento (`CostGuardAdapter`)** | `RALPH_MAX_TASKS_PER_SESSION` | Teto de **12** tarefas acumuladas na sessão (incluindo `C.2`). |
| **Orçamento (`CostGuardAdapter`)** | `RALPH_MAX_LLM_CALLS_PER_SESSION` | Teto de **60** invocações ao LLM por sessão. |
| **Orçamento (`CostGuardAdapter`)** | `RALPH_FINAL_ANSWER_TOKEN_RESERVE` | Reserva de **4.000** *tokens* para garantir margem à síntese `C.3` dentro do teto `max_tokens` da sessão. |
| **Orçamento (`CostGuardAdapter`)** | `RALPH_SESSION_TIMEOUT_SECONDS` | Limite de **600 s** por sessão (verificado entre chamadas ao provedor). |
| **Recuperação JSON** | `RALPH_JSON_PARSE_MAX_RETRIES` | Até **2** chamadas de correção na mesma janela por invocação recusada. |
| **Política de Temperatura** | Chamadas regulares e verificadores (`A.1`, `A.3`, `A.4`, `B.1` tent. 1, `B.2`, `B.4`, `C.1`–`C.3`) | Temperatura base da sessão (`0,0` nos experimentos). |
| **Política de Temperatura** | Revisão semântica de `A.2` após reprovação de `A.3` | Escala progressiva: candidato 2 = **`0,5`**; candidatos 3 a 5 = **`1,0`**. |
| **Política de Temperatura** | Retentativa de `B.1` após reprovação de `B.2` e correções de saída inválida/vazia | **`1,0`** (temporária; retorna à temperatura da sessão na chamada seguinte). |
| **Encerramento por Limite** | Política global de falha | ***Fail-closed***: encerra com `status = failed` e `final_answer = None`. |

Um aspecto arquitetural crítico identificado na auditoria de código refere-se ao acoplamento do teto de saída por chamada (`BaseThinkingPhase.__call_max_tokens`): o *harness* envia todo o saldo remanescente do orçamento da sessão (cerca de `990.000` *tokens* nas baterias experimentais) como parâmetro `max_tokens` de uma única chamada HTTP, enquanto o *timeout* de `600 s` do `CostGuardAdapter` é verificado apenas nas transições entre chamadas (não-preemptivo). Como demonstrado na Seção~VII, essa característica permitiu que loops degenerados individuais extrapolassem o limite temporal da sessão antes do cancelamento.

---

## E. Plataforma de Instrumentação, Execução Paralela e Observabilidade

Além do núcleo algorítmico do *harness*, construiu-se uma plataforma completa de instrumentação e experimentação composta por:

- **Backend assíncrono (FastAPI + WebSockets + `httpx`):** expõe endpoints REST e canais WebSocket para execução interativa e baterias de *benchmark*, integrando-se à API de inferência via `LLMServiceFactory` (registrando `OpenRouterService` para roteamento de modelos) e persistindo sessões individuais e baterias em arquivos JSON ou MongoDB com registro integral de mensagens, invocações, temperaturas efetivas, diagnósticos de saída, consumo de *tokens* e latência por chamada.
- **Motor de *benchmark* paralelo e reexecução seletiva:** os casos de uso `RunBenchmarkUseCase` e `RerunBenchmarkQuestionUseCase` executam questões de forma concorrente (limitada por `max_parallel`), submetendo exatamente o mesmo enunciado e instrução tanto ao braço de inferência simples quanto ao braço *Ralph Loop* em sessões independentes, além de suportar exportação/importação completa de baterias em formato ZIP para auditoria *post-hoc*.
- **Interface web de observabilidade e análise (React + Vite + TypeScript):** disponibiliza visualização em tempo real e histórica das sessões em **Modo Chat** (exibindo fases, candidatos reprovados, critérios e aprendizados) e **Modo Grafo** (trilha macro `A.1`–`C.3` com arcos de revisão `A.3` $\rightarrow$ `A.2` e faixas por tarefa), além de uma aba dedicada de análise comparativa (`/analise`) com gráficos interativos em SVG (transições de desfecho, acurácia em halteres, $\Delta$ divergente, tendências por quartil e custo por desfecho).
