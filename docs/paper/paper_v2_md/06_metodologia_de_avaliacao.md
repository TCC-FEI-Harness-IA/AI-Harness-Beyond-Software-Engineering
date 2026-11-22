# V. Metodologia de Avaliação

A avaliação experimental foi delineada para mensurar objetivamente o impacto do *harness* proposto (`flow_version = 2`) frente à inferência direta em etapa única, abrangendo múltiplos domínios do conhecimento, níveis de dificuldade analítica e idiomas, sem uso de ferramentas externas ou busca em base de dados. O protocolo adota uma comparação **pareada, controlada e reproduzível** sobre três *benchmarks* executados integralmente na mesma infraestrutura de avaliação, reportando conjuntamente acurácia (ponta-a-ponta e condicional em execuções válidas), custo computacional, latência e confiabilidade operacional.

---

## A. Modelo, Provedor e Configuração de Inferência

Todas as baterias experimentais foram executadas com um único modelo base: **`deepseek/deepseek-v4-flash-0731`**, acessado via provedor **`open_router`** (`OpenRouterService`) [CITAR: DeepSeek-V4-Flash / OpenRouter API]. Para isolar o efeito da orquestração externa provida pelo *harness* e evitar sobreposição com cadeias ocultas de raciocínio treinadas nativamente no modelo, a variável `LLM_REASONING_EFFORT` foi configurada como `minimal`, o que instrui `OpenRouterService.payload_extras` a enviar explicitamente `{"reasoning": {"enabled": False}}` em todas as requisições.

Os hiperparâmetros de execução foram fixados de forma idêntica para ambos os braços experimentais:
- **Temperatura base da sessão:** `temperature = 0,0` (aplicada à inferência direta e a todas as chamadas não-retentativas do *Ralph Loop*; retentativas e revisões seguem a política da [TABELA I: Guardrails operacionais, limites de orçamento e política dinâmica de temperatura do harness]);
- **Orçamento de *tokens* por sessão:** `max_tokens = 1.000.000`;
- **Paralelismo da bateria:** `max_parallel = 10` questões simultâneas;
- **Guardrails do *harness*:** parâmetros padrão da [TABELA I: Guardrails operacionais, limites de orçamento e política dinâmica de temperatura do harness] (`max_task_attempts = 5`, `max_planning_attempts = 5`, `max_additional_planning_rounds = 2`, `max_tasks_per_session = 12`, `max_llm_calls_per_session = 60`, `final_answer_token_reserve = 4.000`, `session_timeout_seconds = 600`, `json_parse_max_retries = 2`).

Para cada questão, ambos os braços experimentais recebem exatamente o mesmo enunciado, as mesmas alternativas na mesma ordem e a mesma instrução de resposta do *benchmark*. Os braços são comparados da seguinte forma:
1. **Inferência Simples (*Baseline* 0-shot):** chamada direta e única ao modelo sobre o enunciado e a instrução do *benchmark*. Como a instrução permite explicitar o raciocínio antes do marcador final — e no GPQA solicita expressamente deliberação prévia (`"Reason carefully before answering"`) —, o *baseline* configura uma **inferência direta generativa *0-shot* com *Chain-of-Thought* livre**~\cite{kojima2022large}, e não uma simples emissão de letra sem raciocínio.
2. ***Ralph Loop* Adaptado (`flow_version = 2`):** execução completa do fluxo `A.1`–`A.4`, `B.1`–`B.4` e `C.1`–`C.3` descrito nas Seções~III e~IV, sem acesso a gabaritos, metadados de disciplina ou ferramentas externas. Apenas a resposta final produzida por `C.3` é submetida ao avaliador.

---

## B. *Benchmarks*, Amostragem e Protocolos

Foram conduzidas três baterias complementares em 8 de novembro de 2026, totalizando **1.494 sessões individuais** gravadas e **743 questões pareadas** concluídas em ambos os braços. A [TABELA II: Especificação dos benchmarks avaliados, proveniência, parâmetros de amostragem e integridade das baterias] consolida a procedência, os parâmetros de reprodutibilidade e o estado de integridade de cada bateria.

[TABELA II: Especificação dos benchmarks avaliados, proveniência, parâmetros de amostragem e integridade das baterias]

| *Benchmark* (ID da Bateria) | Fonte / Revisão | Protocolo e Idioma | Composição e Amostragem | Status e Pareamento |
|---|---|---|---|---|
| **Vestibulares** (`bench_b72b883cb604496c917119d00e55d3b3`) | Corpus próprio `vestibular-v1` (24 PDFs oficiais auditados via SHA-256: 12 provas + 12 gabaritos) [CITAR: provas oficiais INEP/ENEM, FUVEST, ITA e COMVEST/UNICAMP] | Múltipla escolha (4 ou 5 opções), Português, marcador `RESPOSTA_FINAL: LETRA` (`vestibular.md`) | **270 questões** em 7 disciplinas: Física (50), Matemática (50), Química (50), Biologia (30), História (30), Geografia (30), Filosofia e Sociologia (30). Bancas: ENEM 2020–2025 (204), ITA 2024–2025 (43), UNICAMP 2025 (16), FUVEST 2024 (7). | `interrupted`: **268 / 270** pareadas (2 interrompidas antes do Ralph). |
| **MMLU** (`bench_9be03b85641c4b62bfa7cd81ebe62d03`) | `cais/mmlu`~\cite{hendrycks2021measuring}, rev. `c30699e8356da336a370243923dbaf21066bb9fe` (MIT) | `generative_0shot` (4 opções A–D), Inglês, marcador `FINAL_ANSWER: LETTER` (`mmlu.md`) | Amostra balanceada de **285 / 14.042** questões de `test` ($57\text{ disciplinas} \times 5$ via `select_subject_questions`, `sample_seed = 42`, sem reposição). | `completed`: **285 / 285** pareadas (com retomada parcial via *rerun* após `HTTP 403`; ver Seção~VI.A). |
| **GPQA Diamond** (`bench_c0b581509c944a10adde91d57d80ef7f`) | `Idavidrein/gpqa`~\cite{rein2023gpqa}, rev. `56686c06f5e19865c153de0fdb11be3890014df7` (CC BY 4.0) | `generative_0shot` (4 opções A–D), Inglês, instrução explícita `"Reason carefully before answering"`, marcador `FINAL_ANSWER: LETTER` (`gpqa.md`) | **198 questões** de pós-graduação: Química (93), Física (86) e Biologia (19). Permutação determinística de opções com `choice_seed = 0` (`random.Random(0)`), `sample_seed = 42`. | `interrupted`: **190 / 198** pareadas (8 questões de Química interrompidas: 6 só com Simples, 2 sem nenhum fluxo). |

A inclusão do corpus próprio de **Vestibulares brasileiros (`vestibular-v1`)** atende a dois objetivos experimentais: avaliar o *harness* em enunciados em Português do Brasil (testando a tradução implícita entre *prompts* internos em inglês e resposta final em português) e cobrir um espectro amplo de exigência cognitiva, desde questões predominantemente contextuais e interpretativas (ENEM) até problemas técnico-matemáticos de alta densidade (ITA e UNICAMP). Todas as 270 questões foram transcritas de provas oficiais sem itens anulados e auditadas automaticamente contra os 24 PDFs originais arquivados (`verify_benchmark_sources.py` e 51 testes de integridade). Quanto ao **MMLU**~\cite{hendrycks2021measuring} e ao **GPQA Diamond**~\cite{rein2023gpqa}, ressalta-se que o protocolo generativo *0-shot* adotado difere de avaliações por probabilidade de *log-tokens* ou *5-shot* frequentes em rankings públicos; portanto, os resultados destinam-se à comparação interna controlada entre os dois braços sob o mesmo protocolo, e não à equiparação direta com tabelas externas.

---

## C. Avaliação Determinística, Métricas e Análise Estatística

A extração da alternativa selecionada é realizada de forma estritamente determinística pelo serviço `BenchmarkAnswerEvaluator.select_alternative`, que verifica na **última linha** da resposta final a presença do marcador exato (`RESPOSTA_FINAL: LETRA` ou `FINAL_ANSWER: LETTER`), aceitando subsidiariamente apenas uma letra isolada ou o texto integral isolado de uma alternativa válida. Respostas ambíguas, alternativas inexistentes (como `"NONE"`), falhas de API, violações de *parsing* e encerramentos por limite de recursos (`CostGuardAdapter`) são registradas em diagnóstico próprio (`failures`) e **contabilizadas como erro** na acurácia ponta-a-ponta (`BenchmarkModeSummary`).

Para separar rigorosamente o potencial analítico da arquitetura de sua confiabilidade operacional sob política *fail-closed*, todos os resultados são reportados sob duas visões complementares:

1. **Acurácia ponta-a-ponta (todas as questões pareadas, $N = 743$):** considera toda questão executada nos dois braços, penalizando integralmente as falhas operacionais como respostas incorretas. Representa o desempenho efetivo entregue ao usuário final.
2. **Acurácia condicional em execuções válidas ($N = 711$):** restringe a comparação pareada aos pares em que **ambos** os fluxos concluíram sem falha técnica, limite de orçamento ou erro de formatação de marcador. Isola o impacto analítico da orquestração sobre a qualidade do raciocínio.

Sobre ambas as visões, mensuram-se: (i) **intervalos de confiança de 95%** para proporções (escore de Wilson) [CITAR: método de intervalo de confiança de Wilson (1927) para proporções binomiais]; (ii) **variação em pontos percentuais ($\Delta$)**, taxa de **resgates** (questões em que o *baseline* erra e o *Ralph* acerta) e taxa de **regressões** (em que o *baseline* acerta e o *Ralph* erra); (iii) significância estatística pareada por meio do **teste exato bilateral de McNemar** ($\alpha = 0{,}05$) [CITAR: teste exato de McNemar (1947) para amostras pareadas dicotômicas], adequado à comparação de dois classificadores sobre exatamente as mesmas instâncias; e (iv) métricas de **custo e eficiência** — total, média, desvio-padrão, mediana e intervalo interquartil (IQR) de *tokens* consumidos, razão mediana de *tokens* (*Ralph*/Simples), latência em segundos, número de chamadas ao LLM e distribuição de consumo por fase (`A.1`–`C.3`). Por fim, conduz-se análise estratificada por regime de complexidade, área do conhecimento, banca/disciplina, quartis/tercis de *tokens* da inferência simples (como *proxy* independente de esforço de raciocínio) e variáveis internas de controle do *harness* (reprovações em `A.3` e `B.2`), seguida de inspeção qualitativa de causa raiz nas sessões individuais persistidas.
