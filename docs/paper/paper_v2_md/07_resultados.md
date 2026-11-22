# VI. Resultados Experimentais

Os resultados reportados nesta seção foram recalculados diretamente a partir dos registros brutos em JSON das três baterias executadas em 8 de novembro de 2026 (`bench_b72b883cb604496c917119d00e55d3b3`, `bench_9be03b85641c4b62bfa7cd81ebe62d03` e `bench_c0b581509c944a10adde91d57d80ef7f`) e das 1.494 sessões individuais correspondentes (100% em `flow_version = 2`, modelo `deepseek/deepseek-v4-flash-0731`, temperatura base `0,0` e teto de sessão de `1.000.000` *tokens*).

---

## A. Integridade das Baterias Experimentais

Antes da interpretação comparativa, registram-se três achados de integridade apurados na auditoria forense dos dados brutos:

- **Vestibulares (`vestibular-v1`):** encerrada com status `interrupted`, totalizando **268/270** questões pareadas concluídas em ambos os braços; duas questões foram interrompidas antes da conclusão do braço *Ralph* (`FISICA_ITA_2025_F1_UNICA_Q023` e `MATEMATICA_ENEM_2024_AZUL_Q143`).
- **MMLU (`generative_0shot`):** encerrada com status `completed` nas **285/285** questões pareadas (57 disciplinas $\times$ 5). Entretanto, a inspeção dos carimbos temporais revelou que a execução inicial atingiu o limite de créditos da chave na API *OpenRouter* (`HTTP 403 Key limit exceeded`) às `00:27:23 UTC` após aproximadamente 115 questões, sendo cerca de 170 questões retomadas via reexecução seletiva (*rerun*) entre `00:30:32` e `00:46:49 UTC`. Uma única questão (`MMLU_college_mathematics_test_0093`, sessão `sess_d9c2da588f594127bfbe1026e58e586a`) permaneceu sem reexecução no braço *Ralph*, preservando o erro `HTTP 403` como 1 das 3 falhas operacionais contabilizadas no MMLU.
- **GPQA Diamond (`generative_0shot`):** encerrada com status `interrupted`, totalizando **190/198** questões pareadas; oito questões de Química foram interrompidas antes de concluir o pareamento (seis com execução apenas no braço Simples e duas sem nenhum braço).

---

## B. Desempenho Global: Ponta-a-Ponta versus Execuções Válidas

A [TABELA III: Acurácia pareada ponta-a-ponta (todas executadas) versus execuções válidas (sem falhas operacionais)] consolida a acurácia pareada nos três *benchmarks* e no agregado total ($N = 743$ ponta-a-ponta; $N = 711$ execuções válidas), enquanto a [FIGURA 4: Fluxo de transições de desfecho pareado (Sankey/Alluvial) entre Inferência Simples e Ralph Loop nas 743 questões pareadas e nas 711 execuções válidas] detalha o fluxo de concordâncias, resgates e regressões entre os dois métodos.

[TABELA III: Acurácia pareada ponta-a-ponta (todas executadas) versus execuções válidas (sem falhas operacionais)]

| Bateria (*Dataset*) | $N$ pareado | Simples (Todas) [IC 95%] | *Ralph* (Todas) [IC 95%] | $\Delta$ (Todas) | Falhas (S / R) | $N$ válido | Simples (Vál.) | *Ralph* (Vál.) | $\Delta$ (Vál.) | $+$Resg / $-$Regr (Vál.) | McNemar $p$ (Todas / Vál.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Vestibular** | 268 / 270 | 95,52% [92,3–97,4] | 95,15% [91,9–97,1] | $-0{,}37$ p.p. | 1 / 7 | 260 | 96,15% | **97,69%** | **$+1{,}54$ p.p.** | **$+5$ / $-1$** | 1,000 / 0,219 |
| **MMLU** | 285 / 285 | **89,82%** [85,8–92,8] | 87,02% [82,6–90,4] | $-2{,}81$ p.p. | 0 / 3 | 282 | **90,07%** | 87,94% | $-2{,}13$ p.p. | $+8$ / $-14$ | 0,152 / 0,286 |
| **GPQA Diamond** | 190 / 198 | **73,68%** [67,0–79,4] | 70,53% [63,7–76,6] | $-3{,}16$ p.p. | 1 / 21 | 169 | 72,78% | **79,29%** | **$+6{,}51$ p.p.** | **$+22$ / $-11$** | 0,480 / 0,080 |
| **Agregado Total** | **743** | **87,75%** (652) | 85,73% (637) | $-2{,}02$ p.p. | 2 / 31 | **711** | 88,19% (627) | **89,45%** (636) | $+1{,}27$ p.p. | $+35$ / $-26$ | 0,133 / 0,306 |

[FIGURA 4: Fluxo de transições de desfecho pareado (Sankey/Alluvial) entre Inferência Simples e Ralph Loop nas 743 questões pareadas e nas 711 execuções válidas — nova figura especificada na Seção 2.1 de `00_auditoria_figuras.md`]

Observa-se uma divergência marcante entre as duas visões de avaliação:

1. **Na métrica ponta-a-ponta ($N = 743$)**, o *Ralph Loop* registra acurácia inferior ao *baseline* nos três *benchmarks*, totalizando $85{,}73\%$ (IC 95%: $83{,}0\%$–$88{,}1\%$) frente a $87{,}75\%$ (IC 95%: $85{,}2\%$–$89{,}9\%$) da inferência simples ($\Delta = -2{,}02\text{ p.p.}$; McNemar $p = 0{,}133$, não significativo). O *harness* corrige $36$ de $91$ erros do *baseline* (taxa de recuperação de $39{,}6\%$), mas incorre em $51$ regressões sobre os $652$ acertos da inferência simples ($7{,}8\%$), com $55$ questões erradas por ambos ($42$ na mesma alternativa).
2. **Impacto dominante das falhas operacionais:** das $51$ regressões ponta-a-ponta do *harness*, exatamente **25 ($49{,}0\%$)** decorrem de **falhas operacionais *fail-closed*** ou erros técnicos/formato — sendo $17$ de $28$ regressões no GPQA Diamond, $6$ de $7$ no Vestibular e $2$ de $16$ no MMLU —, enquanto a inferência simples apresentou apenas $2$ falhas técnicas no agregado (contra $31$ do *Ralph Loop*).
3. **Na métrica de execuções válidas concluídas ($N = 711$)**, o sinal do efeito inverte-se no agregado e em dois dos três *benchmarks*. O *harness* alcança $89{,}45\%$ (IC 95%: $87{,}0\%$–$91{,}5\%$) contra $88{,}19\%$ (IC 95%: $85{,}6\%$–$90{,}4\%$) do *baseline* ($\Delta = +1{,}27\text{ p.p.}$, $p = 0{,}306$), com saldo líquido de $+9$ questões ($35$ resgates sobre $84$ erros do *baseline*, ou $41{,}7\%$ de recuperação, frente a $26$ regressões semânticas sobre $627$ acertos, ou $4{,}1\%$, equivalente a uma redução relativa de erro de $10{,}7\%$; ambos erram $49$ itens, $41$ na mesma letra). O ganho concentra-se no **GPQA Diamond** ($+6{,}51\text{ p.p.}$, $22$ resgates contra $11$ regressões, $p = 0{,}080$, recuperação de $47{,}8\%$) e nos **Vestibulares** ($+1{,}54\text{ p.p.}$, $5$ resgates contra apenas $1$ regressão semântica, regressão de $0{,}4\%$), ao passo que o **MMLU** mantém perda líquida mesmo sem falhas técnicas ($-2{,}13\text{ p.p.}$, $8$ resgates contra $14$ regressões).

---

## C. Custo Computacional, Latência e Perfil de Consumo por Fase

A [TABELA IV: Custo de tokens, latência e número de chamadas LLM por bateria] apresenta o custo de *tokens*, a latência por questão e o número de invocações do *harness* nas três baterias, e a [TABELA V: Distribuição agregada de chamadas e consumo de tokens por fase do harness (A.1–C.3)] detalha como os $45.653.918$ *tokens* e $9.836$ chamadas distribuíram-se pelas dez etapas do fluxo.

[TABELA IV: Custo de tokens, latência e número de chamadas LLM por bateria]

| Bateria | Simples *Tokens* Média $\pm$ DP (Mediana; IQR) | *Ralph* *Tokens* Média $\pm$ DP (Mediana; IQR) | Razão R/S (Mediana) | Simples Tempo (s) Média (Mediana) | *Ralph* Tempo (s) Média (Mediana) | Chamadas LLM *Ralph* Média $\pm$ DP (Mediana) |
|---|---:|---:|---:|---:|---:|---:|
| **Vestibular** | $733 \pm 371$ ($620$; $545$–$765$) | $56.313 \pm 24.452$ ($51.139$; $36{,}7\text{k}$–$64{,}7\text{k}$) | **$79{,}2\times$** | $2{,}07$ ($1{,}77$) | $39{,}08$ ($35{,}17$) | $12{,}7 \pm 3{,}4$ ($12$) |
| **MMLU** | $335 \pm 168$ ($287$; $250$–$369$) | $45.872 \pm 15.050$ ($45.421$; $31{,}0\text{k}$–$54{,}2\text{k}$) | **$140{,}7\times$** | $1{,}70$ ($1{,}46$) | $36{,}22$ ($32{,}89$) | $11{,}9 \pm 2{,}6$ ($12$) |
| **GPQA Diamond** | $1.888 \pm 13.758^*$ ($732$; $588$–$991$) | $92.044 \pm 59.454$ ($76.538$; $58{,}3\text{k}$–$113{,}4\text{k}$) | **$97{,}1\times$** | $10{,}71^*$ ($3{,}03$) | $92{,}60$ ($57{,}39$) | $16{,}0 \pm 4{,}8$ ($15$) |
| **Total Acumulado** | **$651.365$ *tokens*** | **$45.653.918$ *tokens*** | **$70{,}1\times$ total** | $3.098\text{ s}$ | $38.388\text{ s}$ ($12{,}4\times$) | **$9.836$ chamadas** |

*\*$^*$Nota: a média da inferência simples no GPQA Diamond sofre influência de um único outlier extremo (`GPQA_diamond_recVvpD8miVjmmyfe`, sessão `sess_f40011e40ff24e9fb90ce0d840682bff`), que entrou em loop degenerado consumindo $193.303$ tokens e $1.306\text{ s}$.*

O sobrecusto computacional do *harness* é severo: a razão mediana de *tokens* varia de **$79{,}2\times$** nos Vestibulares e **$97{,}1\times$** no GPQA Diamond até **$140{,}7\times$** no MMLU (onde o enunciado e a resposta do *baseline* são curtos, com mediana de $287$ *tokens*, mas o *harness* ainda executa em mediana $12$ chamadas). Considerando exclusivamente os $711$ pares válidos, o consumo acumulado foi de $424.991$ *tokens* na inferência simples contra $41.800.522$ *tokens* no *Ralph Loop* ($98{,}4\times$), o que equivale a **$4.597.281$ *tokens* adicionais por acerto líquido conquistado**. Em latência mediana, o tempo por questão elevou-se de $1{,}46$–$3{,}03\text{ s}$ para $32{,}89$–$57{,}39\text{ s}$ (fator de $19\times$ a $24\times$).

[TABELA V: Distribuição agregada de chamadas e consumo de tokens por fase do harness (A.1–C.3)]

| Fase | Chamadas (% total) | *Tokens* Totais (% total) | Média Entrada / Chamada | Média Saída / Chamada | Observação Operacional |
|---|---:|---:|---:|---:|---|
| `A1` | 744 (7,6%) | 1.140.043 (2,5%) | 1.277 | 255 | Critérios gerais (`a1_general_criteria.md`: 693 palavras). |
| `A2` | 928 (9,4%) | 2.985.145 (6,5%) | 2.267 | 950 | Decomposição (`a2_task_decomposition.md`: 1.136 palavras). |
| `A3` | 858 (8,7%) | 2.697.746 (5,9%) | 3.061 | 83 | Validação do plano (`a3_decomposition_validation.md`: 1.248 palavras). |
| `A4` | 747 (7,6%) | 1.090.729 (2,4%) | 1.236 | 224 | Aprendizados do enunciado (`a4_planning_learnings.md`: 671 palavras). |
| **`B1`** | **1.741 (17,7%)** | **10.246.632 (22,4%)** | **4.574** | **1.311** | Resolução (`b1_task_resolution.md`: 2.284 palavras). |
| **`B2`** | **1.773 (18,0%)** | **11.480.601 (25,1%)** | **5.929** | **547** | **Maior consumidor de *tokens* do sistema** (`b2_task_verification.md`: 3.048 palavras). |
| **`B4`** | **1.593 (16,2%)** | **7.508.250 (16,4%)** | **4.427** | **286** | Extração de aprendizados (`b4_learnings_extraction.md`: 1.764 palavras). |
| `C1` | 725 (7,4%) | 4.758.744 (10,4%) | 6.055 | 509 | **Aprovou 99,2% das sessões** (reprovou apenas 6 vezes em 725 chamadas). |
| `C2` | 8 (0,1%) | 66.924 (0,1%) | 7.445 | 921 | Acionada em **5/743 sessões (0,67%)**; `ResultsLedger` aplicou revisões em apenas **3 sessões (0,40%)** (2 Vestibular, 1 MMLU, 0 GPQA). |
| `C3` | 719 (7,3%) | 3.679.104 (8,1%) | 4.951 | 166 | Síntese final (`c3_final_answer.md`: 1.841 palavras). |

[FIGURA 5: Perfil de custo computacional por fase do harness (A.1–C.3), distribuição de tokens (escala log) e relação entre complexidade da questão e ganho de acurácia — nova figura especificada na Seção 2.1 de `00_auditoria_figuras.md`]

A desagregação por fase ([TABELA V: Distribuição agregada de chamadas e consumo de tokens por fase] e [FIGURA 5: Perfil de custo computacional por fase]) evidencia três características estruturais do perfil de custo: (i) a **Fase B concentra $63{,}9\%$ de todos os *tokens*** (`B2` $25{,}1\%$, `B1` $22{,}4\%$ e `B4` $16{,}4\%$), tendo `B2` como principal consumidora individual em razão do *template* de $3.048$ palavras combinado aos critérios efetivos e aos `Key Learnings` (média de $5.929$ *tokens* de entrada por chamada); (ii) o consumo é fortemente dominado por **entrada** (*overhead* de *templates* repetidos em *Fresh Context*), com razão entrada/saída superior a $10:1$ em `B2` ($5.929 / 547$), `B4` ($4.427 / 286$), `C1` ($6.055 / 509$), `C3` ($4.951 / 166$) e superior a $36:1$ em `A3` ($3.061 / 83$); e (iii) a etapa `C1` consumiu **$10{,}4\%$ de todo o orçamento ($4{,}76\text{M}$ *tokens*) aprovando $99{,}2\%$ das chamadas** — apenas $6$ reprovações em $725$ execuções —, acionando `C2` em somente $5$ sessões ($0{,}67\%$) e revisões no `ResultsLedger` em apenas $3$ sessões ($0{,}40\%$, nenhuma delas no GPQA).

---

## D. Análise Condicional: Onde o *Harness* Acerta versus Onde Erra

A análise estratificada revela que o efeito do *harness* não é uniforme: ele varia sistematicamente conforme o regime de complexidade analítica, a área do conhecimento, o esforço de raciocínio exigido da inferência simples e o comportamento dos verificadores internos (`A.3` e `B.2`). Os resultados consolidados constam na [TABELA VI: Desempenho condicional por regime de complexidade, área do conhecimento, banca/domínio, quartil de tokens e variáveis internas (A.3 e B.2)] e na [FIGURA 6: Comparação de acurácia pareada (ponta-a-ponta vs. execuções válidas) com intervalos de confiança de 95% e variação Δ por benchmark, regime de complexidade e área do conhecimento].

[TABELA VI: Desempenho condicional por regime de complexidade, área do conhecimento, banca/domínio, quartil de tokens e variáveis internas (A.3 e B.2)]

| Dimensão / Estrato | $N$ (Todas) | Simples (Todas) | *Ralph* (Todas) | $\Delta$ Todas ($p$) | $N$ (Vál.) | Simples (Vál.) | *Ralph* (Vál.) | $\Delta$ Válidas | $+$Resg / $-$Regr (Vál.) | McNemar $p$ (Vál.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Regime — Alta Complexidade (GPQA + ITA + UNICAMP)** | 248 | 76,61% | 75,40% | $-1{,}21$ p.p. (0,791) | **224** | 76,34% | **83,48%** | **$+7{,}14$ p.p.** | **$+27$ / $-11$** | **0,0139** |
| **Regime — Geral / Teto (MMLU + ENEM + FUVEST)** | 495 | **93,33%** | 90,91% | **$-2{,}42$ p.p. (0,043)** | **487** | **93,63%** | 92,20% | $-1{,}44$ p.p. | $+8$ / $-15$ | 0,2100 |
| **Área — Exatas e Biológicas (STEM)** | 458 | 85,2% | 83,6% | $-1{,}5$ p.p. (0,47) | **428** | 85,5% | **89,3%** | **$+3{,}7$ p.p.** | **$+30$ / $-14$** | **0,0230** |
| **Área — Humanidades** | 125 | **92,0%** | 88,0% | $-4{,}0$ p.p. (0,13) | 125 | **92,0%** | 88,0% | $-4{,}0$ p.p. | $+1$ / $-6$ | 0,1300 |
| **Área — Ciências Sociais** | 90 | **93,3%** | 88,9% | $-4{,}4$ p.p. (0,22) | 88 | **94,3%** | 90,9% | $-3{,}4$ p.p. | $+1$ / $-4$ | 0,3800 |
| **Área — Outras (saúde, negócios, geral)** | 70 | 90,0% | 91,4% | $+1{,}4$ p.p. (1,00) | 70 | 90,0% | 91,4% | $+1{,}4$ p.p. | $+3$ / $-2$ | 1,0000 |
| **Quartil *Tokens* Simples — Q1 (menor)** | 188 | 92,0% | 91,0% | $-1{,}1$ p.p. (0,77) | 181 | 92,8% | 92,3% | $-0{,}6$ p.p. | $+4$ / $-5$ | 1,0000 |
| **Quartil *Tokens* Simples — Q2** | 184 | 92,4% | 89,1% | $-3{,}3$ p.p. (0,26) | 177 | 91,5% | 92,1% | $+0{,}6$ p.p. | $+8$ / $-7$ | 1,0000 |
| **Quartil *Tokens* Simples — Q3** | 186 | 85,5% | 84,4% | $-1{,}1$ p.p. (0,83) | 176 | 85,8% | 87,5% | $+1{,}7$ p.p. | $+10$ / $-7$ | 0,6300 |
| **Quartil *Tokens* Simples — Q4 (maior)** | 185 | 81,1% | 78,4% | $-2{,}7$ p.p. (0,49) | 177 | 82,5% | **85,9%** | **$+3{,}4$ p.p.** | $+13$ / $-7$ | 0,2600 |
| **Controle — `B.2` = 0 reprovações (Agregado)** | 695 | 89,06% | 89,35% | $+0{,}29$ p.p. (—) | 679 | 89,40% | **91,31%** | **$+1{,}91$ p.p.** | $+33$ / $-20$ | 0,0984 |
| **Controle — `B.2` = 0 reprovações (só GPQA)** | 159 | 75,47% | **79,25%** | $+3{,}78$ p.p. (—) | **149** | 75,17% | **84,56%** | **$+9{,}40$ p.p.** | **$+21$ / $-7$** | **0,0130** |
| **Controle — `B.2` = 1 reprovação (Agregado)** | 20 | 55,00% | 55,00% | $0{,}00$ p.p. (1,00) | 20 | 55,00% | 55,00% | $0{,}00$ p.p. | $+2$ / $-2$ | 1,0000 |
| **Controle — `B.2` $\ge$ 2 reprovações (Agregado)** | 28 | **78,57%** | **17,86%** | **$-60{,}71$ p.p.** (16 falhas) | 12 | **75,00%** | **41,67%** | **$-33{,}33$ p.p.** | **$0$ / $-4$** | 0,1250 |
| **Controle — `A.3` $\ge$ 1 reprovação (Vestibular)** | 23 | 91,30% | **100,00%** | $+8{,}70$ p.p. (0,50) | 23 | 91,30% | **100,00%** | $+8{,}70$ p.p. | $+2$ / $-0$ | 0,5000 |
| **Controle — `A.3` $\ge$ 1 reprovação (MMLU)** | 27 | 70,37% | **74,07%** | $+3{,}70$ p.p. (—) | 26 | 73,08% | **76,92%** | $+3{,}85$ p.p. | $+4$ / $-3$ | 1,0000 |
| **Controle — `A.3` $\ge$ 1 reprovação (GPQA)** | 52 | 73,08% | 69,23% | $-3{,}85$ p.p. (—) | 45 | 71,11% | **80,00%** | $+8{,}89$ p.p. | $+8$ / $-4$ | 0,3880 |

[FIGURA 6: Comparação de acurácia pareada (ponta-a-ponta vs. execuções válidas) com intervalos de confiança de 95% e variação Δ por benchmark, regime de complexidade e área do conhecimento — nova figura especificada na Seção 2.1 de `00_auditoria_figuras.md`]

Os principais padrões empíricos emergentes dessa estratificação são quatro:

1. **Superioridade estatisticamente significativa em alta complexidade analítica e STEM:** agregando os estratos de maior exigência analítica (**GPQA Diamond + ITA + UNICAMP**, $N_{\text{vál}} = 224$), o *Ralph Loop* elevou a acurácia de $76{,}34\%$ para **$83{,}48\%$ ($\Delta = +7{,}14\text{ p.p.}$, $27$ resgates contra $11$ regressões, McNemar $p = 0{,}0139$)**. De forma convergente, no recorte global de disciplinas **STEM** ($N_{\text{vál}} = 428$), o ganho atingiu **$+3{,}7\text{ p.p.}$ ($85{,}5\%$ $\rightarrow$ $89{,}3\%$, $+30/-14$, $p = 0{,}023$)**. Dentro dos subgrupos individuais em execuções válidas:
   - **ITA (Vestibular):** salto de $84{,}62\%$ para **$94{,}87\%$ ($+10{,}26\text{ p.p.}$, $+4/-0$, $N_{\text{vál}} = 39$)**, atingindo $100\%$ em `ITA_FISICA` ($81{,}82\%$ $\rightarrow$ $100\%$, $+18{,}18\text{ p.p.}$), $100\%$ em `ITA_MATEMATICA` ($85{,}71\%$ $\rightarrow$ $100\%$, $+14{,}29\text{ p.p.}$) e $90{,}48\%$ em `ITA_QUIMICA` ($+4{,}76\text{ p.p.}$). Mesmo na métrica ponta-a-ponta, o ITA permaneceu positivo em $+4{,}76\text{ p.p.}$ ($83{,}33\%$ $\rightarrow$ $88{,}10\%$).
   - **UNICAMP e Física/Exatas (Vestibular):** UNICAMP atingiu $100{,}00\%$ ($93{,}75\%$ $\rightarrow$ $100{,}00\%$, $+6{,}25\text{ p.p.}$, $N = 16$, $0$ falhas); Física (todas as bancas, $N = 49$, $0$ falhas) subiu $+8{,}16\text{ p.p.}$ ponta-a-ponta ($89{,}80\%$ $\rightarrow$ $97{,}96\%$); e Exatas no Vestibular válidas ($N_{\text{vál}} = 143$) avançaram de $94{,}41\%$ para $97{,}90\%$ ($+3{,}50\text{ p.p.}$, $+5/-0$, $p = 0{,}0625$).
   - **GPQA Diamond — ganho consistente nos três domínios científicos (válidas):** Biologia subiu de $61{,}11\%$ para $77{,}78\%$ ($+16{,}67\text{ p.p.}$, $+4/-1$, $N_{\text{vál}} = 18$; $+15{,}79\text{ p.p.}$ ponta-a-ponta); Química subiu de $61{,}64\%$ para $68{,}49\%$ ($+6{,}85\text{ p.p.}$, $+12/-7$, $N_{\text{vál}} = 73$), mas $12$ falhas operacionais inverteram o saldo ponta-a-ponta para $-4{,}71\text{ p.p.}$; e Física avançou de $85{,}90\%$ para $89{,}74\%$ ($+3{,}85\text{ p.p.}$, $+6/-3$, $N_{\text{vál}} = 78$), igualmente invertido para $-5{,}81\text{ p.p.}$ ponta-a-ponta por $8$ falhas operacionais.
2. **Degradação em conhecimento geral, humanidades e efeito teto:** no estrato **Geral/Teto (MMLU + ENEM + FUVEST)**, o *harness* sofreu perda estatisticamente significativa ponta-a-ponta ($93{,}33\%$ $\rightarrow$ $90{,}91\%$, **$\Delta = -2{,}42\text{ p.p.}$, $p = 0{,}043$**) e manteve desvantagem em execuções válidas ($-1{,}44\text{ p.p.}$, $+8/-15$). No **ENEM** ($N_{\text{vál}} = 198$), o *baseline* já operava em $98{,}48\%$, deixando margem praticamente nula para resgates: o *Ralph* registrou $0$ resgates analíticos válidos, $1$ regressão semântica (`GEOGRAFIA_ENEM_2022_AZUL_Q064`) e $4$ falhas operacionais (fechando em $96{,}06\%$ ponta-a-ponta, $-1{,}97\text{ p.p.}$). No **MMLU**, a queda concentrou-se em **Humanidades** ($87{,}69\%$ $\rightarrow$ $80{,}00\%$, $-7{,}69\text{ p.p.}$, $+1/-6$, $N = 65$, $0$ falhas) e **Ciências Sociais** ($91{,}53\%$ $\rightarrow$ $88{,}14\%$, $-3{,}39\text{ p.p.}$, $+1/-3$), enquanto **STEM** empatou exatamente ($90{,}91\%$, $+3/-3$) e **Outras** cresceu $+1{,}43\text{ p.p.}$ ($+3/-2$).
3. **Relação monotônica entre complexidade implícita da questão e benefício do *harness*:** estratificando os $711$ pares válidos por quartil de *tokens* da resposta da inferência simples ([FIGURA 5: Perfil de custo computacional e relação entre complexidade da questão e ganho de acurácia], painel c), a variação de acurácia do *Ralph Loop* cresce monotonicamente de **$-0{,}6\text{ p.p.}$ no Q1** (questões mais curtas) para **$+0{,}6\text{ p.p.}$ no Q2**, **$+1{,}7\text{ p.p.}$ no Q3** e **$+3{,}4\text{ p.p.}$ no Q4** (questões mais extensas). Nos tercis superiores específicos por *benchmark*, o efeito amplifica-se: no Vestibular ($> 691$ *tokens* no Simples, $N_{\text{vál}} = 86$), o ganho é de $+4{,}65\text{ p.p.}$ ($90{,}70\%$ $\rightarrow$ $95{,}35\%$, $+4/-0$); no GPQA Diamond ($> 840$ *tokens*, $N_{\text{vál}} = 56$), atinge **$+10{,}71\text{ p.p.}$ ($62{,}50\%$ $\rightarrow$ $73{,}21\%$, $+9/-3$)** — embora esse mesmo tercil concentre $12$ das $21$ falhas operacionais do GPQA. Inversamente, em questões curtas do MMLU ($\le 260$ *tokens*, $N = 95$), o *harness* perde $-3{,}16\text{ p.p.}$ ($91{,}58\%$ $\rightarrow$ $88{,}42\%$, $+1/-4$).
4. **Sinal polarizado das variáveis internas de controle (`A.3` vs. `B.2`):** enquanto intervenções de `A.3` ($\ge 1$ reprovação de plano) correlacionam-se positivamente com o desempenho em todos os três *benchmarks* válidos (Vestibular $+8{,}70\text{ p.p.}$, MMLU $+3{,}85\text{ p.p.}$, GPQA $+8{,}89\text{ p.p.}$), o comportamento de `B.2` exibe uma bifurcação drástica: quando `B.2` aprova de primeira ($0$ reprovações), o *Ralph* supera o *baseline* em $+1{,}91\text{ p.p.}$ no agregado válido e em **$+9{,}40\text{ p.p.}$ no GPQA Diamond ($75{,}17\%$ $\rightarrow$ $84{,}56\%$, $+21/-7$, McNemar $p = 0{,}0130$)**; com exatamente $1$ reprovação, o saldo zera ($0{,}00\text{ p.p.}$, $+2/-2$); e com **$\ge 2$ reprovações em `B.2`** ($28$ sessões), o *harness* colapsa para **$17{,}86\%$ ponta-a-ponta** ($16$ falhas operacionais) e **$41{,}67\%$ nas $12$ sessões válidas** (**$-33{,}33\text{ p.p.}$**, $0$ resgates contra $4$ regressões). No quartil superior de *tokens* consumidos pelo próprio *Ralph* (Q4 ponta-a-ponta, $n = 184$), essa dinâmica traduz-se em queda estatisticamente significativa de $-7{,}6\text{ p.p.}$ ($79{,}3\%$ $\rightarrow$ $71{,}7\%$, $p = 0{,}034$).
