# Análise detalhada dos resultados do Ralph Loop adaptado

**Finalidade:** documento de apoio à redação das seções de resultados, discussão e limitações do paper. **Data da análise:** 23/11/2026. **Experimentos identificados nos arquivos:** 08/11/2026, no horário exibido pelos relatórios; os registros UTC também abrangem 09/11/2026.

Este relatório recalcula os resultados a partir dos dois CSVs de `analise` e examina os 106 registros de erro do Ralph presentes nos três ZIPs. As conclusões quantitativas usam o gabarito registrado nos arquivos. As explicações sobre mecanismos de falha distinguem evidência dos logs, interpretação analítica e hipóteses que ainda exigem outro experimento. Nenhum resultado foi reclassificado ou excluído por julgamento posterior do conteúdo.

## 1. Principais resultados e sua interpretação

1. **O Ralph melhora a acurácia entre os pares sem falha, mas perde na avaliação de ponta a ponta.** Sem falhas, acerta 636/711 questões, contra 627/711 da inferência simples: **89,45% contra 88,19%, +1,27 ponto percentual e 9 acertos líquidos**. Com as falhas contabilizadas como erro, acerta 637/743, contra 652/743: **85,73% contra 87,75%, −2,02 pontos percentuais e 15 acertos líquidos a menos**. Nenhuma dessas diferenças globais atinge significância de 5% pelo McNemar exato.
2. **O benefício depende do domínio.** O ganho sem falha se concentra em exatas e tecnologia (+3,76 p.p.; +14 acertos líquidos). Biológicas e saúde melhoram menos (+1,98 p.p.; +2). Humanas e sociais pioram (−3,07 p.p.; −7). A classificação complementar dessas áreas está explicitada na seção 5 e no apêndice C.
3. **O GPQA Diamond é a principal fonte do ganho condicional.** Sem falhas, passa de 72,78% para 79,29% (+6,51 p.p.; +11). Vestibulares passam de 96,15% para 97,69% (+1,54 p.p.; +4). O MMLU cai de 90,07% para 87,94% (−2,13 p.p.; −6). Sem o GPQA, os outros dois conjuntos somam perda líquida de 2 acertos mesmo no recorte sem falhas.
4. **Entre as matérias com mais observações, Biologia do GPQA tem o maior ganho percentual; Química do GPQA tem o maior ganho absoluto.** Sem falhas, Biologia do GPQA melhora 16,67 p.p. em 18 questões (+3 acertos líquidos); Química do GPQA melhora 6,85 p.p. em 73 questões (+5). Física dos vestibulares melhora 6,25 p.p. em 48 questões (+3). Esses recortes são descritivos e têm tamanhos amostrais distintos.
5. **A complexidade parece favorecer o ganho potencial, mas também aumenta o risco operacional.** O ITA melhora 10,26 p.p. sem falhas e 4,76 p.p. com falhas. O GPQA melhora 6,51 p.p. sem falhas, mas cai 3,16 p.p. com falhas. No ENEM, o ganho não aparece: −0,51 p.p. sem falhas e −1,97 p.p. com elas. Não há uma medida independente e uniforme de dificuldade; origem, nível e tokens são indicadores aproximados.
6. **As falhas não podem ser justificadas predominantemente como problemas externos.** Das 31 falhas do Ralph, 16 são esgotamentos de tentativas de tarefa, 8 são falhas de JSON ou contrato de saída, 3 são estouros de tempo, 2 são respostas finais inválidas, 1 é esgotamento de tentativas de planejamento e 1 é bloqueio do provedor por limite de crédito. Os limites de tarefa, planejamento e tempo são parte do comportamento efetivo da arquitetura avaliada.
7. **A validação não elimina erros de conteúdo.** Há 26 regressões sem falha de execução: a inferência simples acertou e o Ralph entregou uma alternativa errada. Em 20 dessas 26, não houve nenhuma reprovação semântica de tarefa registrada. O problema inclui aprovações incorretas e conservação de premissas erradas, além de falhas de execução.
8. **O custo adicional é muito alto para o ganho observado.** Nos pares sem falha, o Ralph usa 98,36 vezes os tokens e 19,13 vezes a soma das durações individuais. São aproximadamente 4,60 milhões de tokens adicionais por acerto líquido ganho. Isso impede concluir eficiência superior a partir da acurácia isolada.

**Conclusão central para a discussão:** nesta implementação e amostra, o Ralph apresenta potencial de aumentar a qualidade das respostas em problemas científicos e quantitativos, mas esse potencial é parcialmente perdido por falhas de orquestração e por limitações da própria validação. O experimento sustenta uma vantagem condicional e localizada, com custo elevado; não demonstra superioridade geral do sistema completo.

## 2. Base de evidências, escopo e método de análise

### 2.1. Arquivos utilizados

| Fonte | Conteúdo e uso |
| --- | --- |
| [analise-benchmark-considera-erros.md](analise-benchmark-considera-erros.md) | Resumo original da comparação com falhas; usado para reconciliação. |
| [analise-benchmark-desconsidera-erros.md](analise-benchmark-desconsidera-erros.md) | Resumo original após excluir pares com alguma falha; usado para reconciliação. |
| [analise-benchmark-questoes_considera-erros.csv](analise-benchmark-questoes_considera-erros.csv) | 743 observações pareadas; base quantitativa principal. |
| [analise-benchmark-questoes_desconsidera-erros.csv](analise-benchmark-questoes_desconsidera-erros.csv) | 711 observações pareadas sem falha em nenhum fluxo. |
| [ZIP GPQA](benchmark-session-bench_c0b581509c944a10adde91d57d80ef7f-ralph-loop-errors.zip) | 56 questões nas quais o Ralph não acertou: 35 alternativas erradas válidas e 21 falhas. |
| [ZIP MMLU](benchmark-session-bench_9be03b85641c4b62bfa7cd81ebe62d03-ralph-loop-errors.zip) | 37 questões nas quais o Ralph não acertou: 34 alternativas erradas válidas e 3 falhas. |
| [ZIP Vestibulares](benchmark-session-bench_b72b883cb604496c917119d00e55d3b3-ralph-loop-errors.zip) | 13 questões nas quais o Ralph não acertou: 6 alternativas erradas válidas e 7 falhas. |

Cada questão exportada no ZIP contém `questao.json`, `resposta-esperada.json` e `execucao-ralph-loop.json`. O último inclui a sessão, as mensagens das fases, invocações, diagnósticos de saída, consumo e eventual falha. São **106 questões e 318 arquivos JSON**. Os ZIPs cobrem exatamente os 106 resultados não corretos do Ralph presentes no CSV completo.

A análise consultou também o código local para esclarecer o significado dos campos e das regras, especialmente [benchmarkAnalysis.ts](../apps/frontend/src/domain/services/benchmarkAnalysis.ts), [benchmark_answer_evaluator.py](../apps/backend/src/domain/services/benchmark_answer_evaluator.py), [cost_guard_adapter.py](../apps/backend/src/infra/adapters/cost_guard_adapter.py) e [base_thinking_phase.py](../apps/backend/src/application/phases/base_thinking_phase.py). O código atual ajuda a interpretar os registros, mas não substitui um snapshot versionado da implementação do experimento. Os documentos históricos de outras avaliações na raiz do repositório não foram usados como evidência destes resultados.

### 2.2. Configuração observável e cobertura

O modelo identificado é `deepseek/deepseek-v4-flash-0731`. Os relatórios descrevem GPQA e MMLU como inferência generativa, 0-shot. Nos 106 logs disponíveis, o provedor é OpenRouter, `flow_version=2`, a temperatura da sessão é 0,0 e `max_tokens=1000000`. Esses valores descrevem os registros disponíveis; os CSVs não fornecem a configuração completa de cada chamada dos casos bem-sucedidos. Há retentativas com temperatura 1,0 nos logs, portanto temperatura de sessão 0,0 não significa temperatura constante em todas as invocações.

O fluxo observado inclui definição de critérios (A.1), planejamento (A.2), validação do plano (A.3), extração de aprendizados (A.4), resolução de tarefa (B.1), verificação (B.2), armazenamento (B.3), registro de aprendizados (B.4), avaliação global (C.1), eventual replanejamento (C.2) e síntese final (C.3). O armazenamento e a memória tornam conclusões aprovadas disponíveis às etapas seguintes. É esse encadeamento que permite verificações adicionais, mas também pode conservar uma conclusão errada.

| Conjunto | ID da execução | Questões declaradas | Pares disponíveis | Pares sem falha | Removidos pelo filtro |
| --- | --- | ---: | ---: | ---: | ---: |
| GPQA Diamond | `bench_c0b581509c944a10adde91d57d80ef7f` | 198 | 190 | 169 | 21 |
| MMLU | `bench_9be03b85641c4b62bfa7cd81ebe62d03` | 285 | 285 | 282 | 3 |
| Vestibulares | `bench_b72b883cb604496c917119d00e55d3b3` | 270 | 268 | 260 | 8 |
| **Total** | — | **753** | **743** | **711** | **32** |

Há uma diferença de **10 questões entre a quantidade declarada e os pares efetivamente analisados**: 8 no GPQA e 2 nos vestibulares. Os arquivos fornecidos não permitem determinar o resultado dos dois fluxos nesses 10 casos. Pelo código de análise, observações sem resultado de um dos fluxos não entram no pareamento. Portanto, o cenário aqui chamado completo ou de ponta a ponta significa **todos os 743 pares exportados**, e não as 753 questões declaradas. Não se atribui acerto ou erro às 10 ausentes.

O MMLU tem 57 matérias com 5 questões por matéria na base completa. Vestibulares têm 7 matérias e o GPQA tem 3, totalizando 67 rótulos de matéria. Não há repetições independentes do mesmo experimento nos arquivos analisados. Conjunto, idioma, tipo de questão e execução estão associados, o que limita atribuições causais isoladas a qualquer um desses fatores.

### 2.3. Definições das métricas

- **Unidade de análise:** uma questão de uma execução, respondida pelos dois fluxos. As comparações são pareadas.
- **Acurácia:** número de respostas corretas dividido pelo número de pares do recorte. No cenário completo, falhas contam como respostas não corretas.
- **Correção:** simples erra e Ralph acerta. **Regressão:** simples acerta e Ralph erra. Uma falha de execução pode produzir uma regressão na base completa.
- **Ganho líquido:** correções menos regressões, equivalente à diferença entre os totais de acertos. **Δ:** acurácia Ralph menos acurácia simples, em pontos percentuais.
- **Taxa de recuperação:** correções divididas pelos erros da simples. **Taxa de regressão:** regressões divididas pelos acertos da simples. Essas taxas têm denominadores diferentes e não devem ser comparadas diretamente como se fossem proporções sobre a mesma base.
- **Falha operacional:** resultado com campo de erro preenchido no benchmark. Inclui interrupções por limites, erro de provedor, saída estruturada inválida e resposta final não extraível. É mais abrangente que o motivo de sessão `technical_error`.
- **Erro de conteúdo ou semântico:** alternativa válida entregue e divergente do gabarito registrado. O termo não presume que todo gabarito tenha sido auditado por especialista.
- **Sem falhas:** exclui o par inteiro quando qualquer um dos fluxos apresenta falha. Não significa excluir todas as respostas erradas. Permanecem 75 erros do Ralph nesse recorte.
- **Multiplicador de tokens:** soma dos tokens Ralph dividida pela soma dos tokens simples no mesmo recorte. Tokens incluem entrada e saída; não representam apenas raciocínio novo ou custo monetário.

O teste utilizado é o **McNemar exato bicaudal**, calculado sobre as discordâncias. Os intervalos individuais de acurácia são de Wilson a 95%. Os intervalos da diferença pareada apresentados adiante são aproximações normais da média das diferenças −1/0/+1 por questão. Esses intervalos aproximados não substituem o teste exato, especialmente em grupos pequenos. Os valores de p dos recortes são exploratórios e, salvo indicação explícita, não têm correção por múltiplas comparações.

## 3. Resultado global: qualidade condicional e desempenho de ponta a ponta

| Cenário | n | Simples | Ralph | Δ | Corrige | Piora | Líquido | p exato |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Todos os pares | 743 | 652 (87,75%) | 637 (85,73%) | -2,02 p.p. | 36 | 51 | -15 | 0,1329 |
| Pares sem falha | 711 | 627 (88,19%) | 636 (89,45%) | +1,27 p.p. | 35 | 26 | +9 | 0,3057 |

### 3.1. Decomposição dos resultados pareados

| Desfecho | Todos os pares | Sem falha | Pares removidos |
| --- | ---: | ---: | ---: |
| Ambos acertam | 601 | 601 | 0 |
| Só Ralph acerta | 36 | 35 | 1 |
| Só simples acerta | 51 | 26 | 25 |
| Ambos erram | 55 | 49 | 6 |

Na base completa, o Ralph recupera **36/91 erros da simples (39,56%)**, mas perde **51/652 acertos da simples (7,82%)**. O saldo negativo ocorre porque há muito mais respostas inicialmente corretas sujeitas a regressão do que respostas erradas disponíveis para recuperação.

Sem falhas, recupera **35/84 erros (41,67%)** e perde **26/627 acertos (4,15%)**. Os erros caem de 84 para 75, uma **redução relativa de 10,71%**. Na base completa, os erros sobem de 91 para 106, aumento relativo de 16,48%. Redução relativa do erro e diferença em pontos percentuais são medidas distintas e devem ser identificadas no paper.

Os 49 casos sem falha nos quais ambos erram incluem **41 com a mesma alternativa errada (83,67%)** e 8 com alternativas erradas diferentes. Isso é compatível com limitações compartilhadas de conhecimento, interpretação ou avaliação. A existência de várias etapas de validação não garantiu evidência independente capaz de alterar esses resultados.

### 3.2. Incerteza estatística

| Cenário | IC95% simples | IC95% Ralph | IC95% aproximado da diferença pareada | p exato |
| --- | ---: | ---: | ---: | ---: |
| Todos os pares | 85,20% a 89,92% | 83,03% a 88,06% | -4,48 a 0,44 p.p. | 0,1329 |
| Sem falha | 85,61% a 90,36% | 86,98% a 91,50% | -0,89 a 3,42 p.p. | 0,3057 |

As duas diferenças globais são compatíveis com zero segundo os procedimentos utilizados. A redação correta é que houve **ganho observado de 1,27 p.p. sem falhas**, acompanhado de incerteza; não que o experimento comprovou superioridade geral. Da mesma forma, o resultado completo desfavorável não prova inferioridade universal. Sobreposição dos intervalos individuais de acurácia não é o teste usado para a comparação pareada.

### 3.3. Por que remover falhas inverte a conclusão

O filtro retira 32 pares: 30 com falha somente no Ralph, 1 com falha em ambos e 1 com falha somente na simples. Nos 32 pares retirados, a simples acertou 25 e o Ralph acertou 1. Assim:

```text
Ganho líquido nos 711 pares sem falha:       +9
Ganho líquido nos 32 pares removidos:      -24
Ganho líquido nos 743 pares completos:    -15
```

Essa é uma decomposição exata de contagens. Não se deve subtrair os deltas percentuais de bases diferentes como se essa subtração medisse isoladamente o efeito das falhas.

O filtro é pareado, mas seleciona questões em função do comportamento dos métodos. Os pares removidos não são uma amostra aleatória: concentram falhas do Ralph, problemas científicos e consumo extremo. A acurácia de 89,45% responde à pergunta **“como os métodos se comparam quando ambos entregam uma saída válida?”**. Não estima, sem hipóteses adicionais, o que o Ralph obteria nas 743 questões caso todas as falhas fossem corrigidas.

## 4. Comparação por benchmark

| Grupo | n total | Simples total | Ralph total | Δ total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | Corrige/piora sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpqa | 190 | 140/190 (73,68%) | 134/190 (70,53%) | -3,16 p.p. | 169 | 72,78% | 79,29% | +6,51 p.p. | 22/11 |
| mmlu | 285 | 256/285 (89,82%) | 248/285 (87,02%) | -2,81 p.p. | 282 | 90,07% | 87,94% | -2,13 p.p. | 8/14 |
| vestibular | 268 | 256/268 (95,52%) | 255/268 (95,15%) | -0,37 p.p. | 260 | 96,15% | 97,69% | +1,54 p.p. | 5/1 |

### 4.1. GPQA Diamond: maior ganho potencial e maior perda por falhas

Nos pares sem falha, o Ralph corrige 22 respostas e introduz 11 regressões, um saldo de +11 e p=0,0801. Recupera **47,83% dos 46 erros da simples**, mas perde **8,94% dos 123 acertos**. Esse é o recorte com maior contribuição absoluta para o ganho global condicional.

Na base completa, há 21 falhas do Ralph em 190 pares (**11,05%**), contra 1 falha da simples (**0,53%**). As 21 observações removidas têm 17 acertos da simples e nenhum do Ralph. O total de acertos Ralph permanece 134 entre os dois recortes, mas o da simples cai de 140 para 123 após o filtro. Isso explica a passagem de −6 para +11 acertos líquidos sem supor que os casos removidos teriam sido acertados pelo Ralph.

**Leitura para o paper:** o GPQA evidencia uma dissociação forte entre capacidade condicional e confiabilidade. A orquestração agrega acertos quando termina validamente, mas falha com frequência justamente no conjunto em que há mais espaço para melhorar.

### 4.2. MMLU: perda que persiste após retirar as falhas

Sem falhas, são 8 correções e 14 regressões: saldo −6 e p=0,2863. O Ralph recupera **28,57% dos 28 erros da simples** e perde **5,51% dos 254 acertos**. A exclusão de somente 3 falhas altera o saldo de −8 para −6; portanto, o resultado desfavorável do MMLU não pode ser explicado principalmente por falhas de execução.

O recorte de humanas e sociais dentro do MMLU tem 139 pares sem falha e saldo −6. Exatas e tecnologia têm 78 e saldo +1; biológicas e saúde têm 55 e saldo −1; geral/interdisciplinar tem 10 e saldo zero. Isso localiza a maior parte da perda, sem autorizar generalização para todo o domínio do MMLU: a amostra contém apenas cinco questões de cada matéria.

**Leitura para o paper:** em muitas questões de classificação conceitual, interpretação e conhecimento factual desta amostra, o raciocínio adicional não compensou a introdução de novas interpretações incorretas. Essa explicação é compatível com os casos examinados, mas não foi isolada experimentalmente.

### 4.3. Vestibulares: benefício concentrado nas provas mais exigentes

Sem falhas, há 5 correções e 1 regressão, saldo +4 e p=0,2188. O Ralph recupera **50% dos 10 erros da simples** e perde **0,40% dos 250 acertos**. A acurácia inicial de 96,15% impõe um teto forte ao ganho absoluto.

As 7 falhas do Ralph correspondem a **2,61% dos 268 pares**, enquanto a simples tem 1 falha (**0,37%**). O filtro remove 8 pares porque inclui também uma questão de Física em que a simples falhou e o Ralph acertou. Por isso, a remoção de falhas reduz o total de acertos Ralph de 255 para 254: o recorte sem falhas pode também retirar sucessos reais do método.

Dos cinco acertos recuperados sem falha, **quatro são do ITA e um da UNICAMP**. A única regressão sem falha é uma questão de Geografia do ENEM. Não há recuperação no ENEM após o filtro.

## 5. Áreas do conhecimento: exatas, biológicas e humanas

### 5.1. Classificação original dos arquivos

Os CSVs juntam exatas e biológicas em STEM e colocam parte da saúde em “Outras”. Isso impede responder diretamente à comparação entre exatas, biológicas e humanas sem uma regra complementar. A classificação original é preservada abaixo para permitir comparação com os relatórios exportados.

| Grupo | n total | Simples total | Ralph total | Δ total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | Corrige/piora sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Exatas e biológicas (STEM) | 458 | 390/458 (85,15%) | 383/458 (83,62%) | -1,53 p.p. | 428 | 85,51% | 89,25% | +3,74 p.p. | 30/14 |
| Humanidades | 125 | 115/125 (92,00%) | 110/125 (88,00%) | -4,00 p.p. | 125 | 92,00% | 88,00% | -4,00 p.p. | 1/6 |
| Ciências sociais | 90 | 84/90 (93,33%) | 80/90 (88,89%) | -4,44 p.p. | 88 | 94,32% | 90,91% | -3,41 p.p. | 1/4 |
| Outras (saúde, negócios, geral) | 70 | 63/70 (90,00%) | 64/70 (91,43%) | +1,43 p.p. | 70 | 90,00% | 91,43% | +1,43 p.p. | 3/2 |

O agrupamento STEM sem falhas tem saldo **+16**, 30 correções e 14 regressões, com **p=0,0226 nominal**. Esse sinal favorável exige cuidado: foi observado entre vários recortes. Se forem consideradas apenas as quatro áreas originais como família de testes e aplicado Holm, o menor p ajustado é aproximadamente **0,0905**. Portanto, o achado não permanece significativo a 5% nem nessa família restrita de comparações; a exploração de matérias e níveis torna a cautela ainda mais necessária.

### 5.2. Reagrupamento complementar para a pergunta do estudo

Foi adotada uma classificação mutuamente exclusiva: **Exatas e tecnologia**, **Biológicas e saúde**, **Humanas e sociais**, além de **Geral/interdisciplinar** para duas matérias que não têm alocação disciplinar clara. Psicologia permanece em humanas e sociais; sexualidade humana e envelhecimento entram em biológicas e saúde; economia, contabilidade e negócios entram em humanas e sociais. A lista completa está no apêndice C. Essa é uma decisão analítica explícita, não uma nova classificação oficial dos benchmarks.

| Grupo | n total | Simples total | Ralph total | Δ total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | Corrige/piora sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Exatas e tecnologia | 399 | 339/399 (84,96%) | 332/399 (83,21%) | -1,75 p.p. | 372 | 85,22% | 88,98% | +3,76 p.p. | 26/12 |
| Biológicas e saúde | 104 | 90/104 (86,54%) | 90/104 (86,54%) | 0,00 p.p. | 101 | 87,13% | 89,11% | +1,98 p.p. | 5/3 |
| Humanas e sociais | 230 | 213/230 (92,61%) | 205/230 (89,13%) | -3,48 p.p. | 228 | 92,98% | 89,91% | -3,07 p.p. | 4/11 |
| Geral/interdisciplinar | 10 | 10/10 (100,00%) | 10/10 (100,00%) | 0,00 p.p. | 10 | 100,00% | 100,00% | 0,00 p.p. | 0/0 |

**Exatas e tecnologia é a área com melhor ganho comparativo observado.** Sem falhas, corrige 26 respostas e perde 12, saldo +14, recuperação de 47,27% dos 55 erros da simples e regressão de 3,79% dos 317 acertos. O p nominal é 0,0336; com Holm sobre as quatro categorias complementares, o menor p ajustado é 0,1342. O ganho aparece no GPQA (+8 acertos), nos vestibulares (+5) e, em menor grau, no MMLU (+1). Na base completa, 26 falhas Ralph em 399 pares (6,52%) fazem o saldo passar a −7.

**Biológicas e saúde tem vantagem menor e heterogênea.** Sem falhas, são 5 correções e 3 regressões, saldo +2 em 101 questões e p=0,7266. O ganho vem principalmente da Biologia do GPQA; não há ganho em Biologia dos vestibulares. A saúde no MMLU inclui tanto uma correção em `clinical_knowledge` quanto uma regressão em `medical_genetics`. Não há suporte para afirmar superioridade ampla em toda a área biológica.

**Humanas e sociais é o agrupamento menos favorável.** Sem falhas, são 4 correções e 11 regressões, saldo −7 em 228 questões e p=0,1185. O resultado desfavorável persiste porque a maior parte das perdas não decorre de interrupções operacionais. A base completa tem apenas 2 falhas Ralph nesse agrupamento, mas 12 regressões no total.

Comparar apenas a acurácia final pode levar a uma conclusão diferente da comparação do ganho: no recorte sem falhas, humanas e sociais chega a 89,91%, biológicas e saúde a 89,11% e exatas e tecnologia a 88,98%. Apesar disso, exatas é onde o Ralph mais melhora em relação à simples. Os grupos diferem em dificuldade inicial; **“melhor área para o Ralph” deve significar maior ganho comparativo, não simplesmente maior percentual final de acertos**.

### 5.3. Famílias de matérias harmonizadas entre os conjuntos

A tabela seguinte combina rótulos equivalentes de Física, Química, Biologia e Matemática/Estatística. Trata-se de uma leitura descritiva: ela mistura provas e níveis, e não deve substituir a análise por benchmark. A composição exata é registrada no script de reprodução e no apêndice C.

| Família | n total | Δ total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | Corrige/piora |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Química | 145 | -2,07 p.p. | 131 | 74,81% | 80,15% | +5,34 p.p. | 14/7 |
| Física | 150 | -1,33 p.p. | 141 | 88,65% | 92,20% | +3,55 p.p. | 9/4 |
| Biologia estrita | 59 | 0,00 p.p. | 56 | 87,50% | 91,07% | +3,57 p.p. | 4/2 |
| Matemática e estatística | 74 | -2,70 p.p. | 70 | 97,14% | 100,00% | +2,86 p.p. | 2/0 |

Nessa harmonização, **Química tem o maior ganho absoluto (+7) e percentual (+5,34 p.p.) sem falhas**, mas acumula 14 falhas na base completa. Matemática e estatística chega a 100% sem falhas, porém havia somente dois erros da simples disponíveis para corrigir. Esses resultados distinguem aumento de capacidade, margem inicial de melhora e confiabilidade operacional.

## 6. Matérias: onde o Ralph melhora e onde piora

### 6.1. Matérias com maior volume de questões

| Grupo | n total | Simples total | Ralph total | Δ total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | Corrige/piora sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| biology | 19 | 11/19 (57,89%) | 14/19 (73,68%) | +15,79 p.p. | 18 | 61,11% | 77,78% | +16,67 p.p. | 4/1 |
| chemistry | 85 | 54/85 (63,53%) | 50/85 (58,82%) | -4,71 p.p. | 73 | 61,64% | 68,49% | +6,85 p.p. | 12/7 |
| physics | 86 | 75/86 (87,21%) | 70/86 (81,40%) | -5,81 p.p. | 78 | 85,90% | 89,74% | +3,85 p.p. | 6/3 |
| FISICA | 49 | 44/49 (89,80%) | 48/49 (97,96%) | +8,16 p.p. | 48 | 91,67% | 97,92% | +6,25 p.p. | 3/0 |
| MATEMATICA | 49 | 48/49 (97,96%) | 47/49 (95,92%) | -2,04 p.p. | 47 | 97,87% | 100,00% | +2,13 p.p. | 1/0 |
| QUIMICA | 50 | 46/50 (92,00%) | 46/50 (92,00%) | 0,00 p.p. | 48 | 93,75% | 95,83% | +2,08 p.p. | 1/0 |
| BIOLOGIA | 30 | 30/30 (100,00%) | 28/30 (93,33%) | -6,67 p.p. | 28 | 100,00% | 100,00% | 0,00 p.p. | 0/0 |
| GEOGRAFIA | 30 | 30/30 (100,00%) | 28/30 (93,33%) | -6,67 p.p. | 29 | 100,00% | 96,55% | -3,45 p.p. | 0/1 |
| HISTORIA | 30 | 28/30 (93,33%) | 28/30 (93,33%) | 0,00 p.p. | 30 | 93,33% | 93,33% | 0,00 p.p. | 0/0 |
| FILOSOFIA_SOCIOLOGIA | 30 | 30/30 (100,00%) | 30/30 (100,00%) | 0,00 p.p. | 30 | 100,00% | 100,00% | 0,00 p.p. | 0/0 |

As letras maiúsculas identificam as matérias dos vestibulares; `biology`, `chemistry` e `physics` identificam GPQA. Os rótulos não devem ser fundidos silenciosamente.

- **Biologia do GPQA:** maior ganho percentual entre as matérias com mais de cinco observações, tanto com falhas (+15,79 p.p.) quanto sem elas (+16,67 p.p.). São 4 correções e 1 regressão sem falhas; a base de 18 questões exige cautela. O p exato é 0,3750.
- **Química do GPQA:** maior contribuição líquida positiva por matéria sem falhas: 12 correções e 7 regressões, saldo +5. É também a matéria com mais falhas Ralph: 12/85 (14,12%), o que inverte o ganho sem falha de +6,85 p.p. para uma perda de −4,71 p.p. na base completa.
- **Física dos vestibulares:** melhora nos dois cenários, com 4 correções e nenhuma regressão na base completa. Uma dessas correções é uma falha da simples, retirada no filtro; restam 3 correções e nenhuma regressão sem falhas. É uma evidência favorável operacionalmente mais estável nesta amostra: não há falha Ralph nessa matéria.
- **Física do GPQA:** sem falhas, 6 correções e 3 regressões, saldo +3; com 8 falhas em 86 pares (9,30%), o saldo passa a −5. A melhora condicional de 3,85 p.p. é menor que a de Química do GPQA.
- **Matemática dos vestibulares:** passa de −2,04 p.p. com falhas para +2,13 p.p. sem elas. Há uma correção de conteúdo, nenhuma regressão de conteúdo e duas falhas Ralph. A acurácia condicional de 100% representa uma melhora sobre uma base simples que já tinha 97,87%.
- **Química dos vestibulares:** empate no total de acertos com falhas; +1 acerto líquido sem falhas. O baixo saldo total combina uma correção com duas falhas, sendo que uma dessas falhas também ocorre numa questão que a simples errou.
- **Biologia dos vestibulares:** o Ralph não corrige nenhum erro da simples, que já acerta todas as questões. As duas perdas na base completa são falhas de JSON; após o filtro, há empate em 100%.
- **Geografia dos vestibulares:** piora nos dois cenários. Uma falha de tentativas explica uma perda, mas outra é uma alternativa errada efetivamente entregue. Sem falhas, cai de 100% para 96,55%.
- **História e Filosofia/Sociologia dos vestibulares:** empate em acurácia. História conserva os mesmos dois erros em ambos os métodos; Filosofia/Sociologia está em 100% para os dois. O custo adicional não produz ganho de acurácia observado.

### 6.2. MMLU: ganhos pontuais e regressões distribuídas

Entre as matérias do MMLU, **um único item representa 20 pontos percentuais** na base completa. Assim, os ganhos de +20 p.p. não podem ser tratados como evidência mais forte que os ganhos menores em grupos maiores.

Há ganho líquido de uma questão em `clinical_knowledge`, `college_chemistry`, `high_school_computer_science`, `high_school_statistics`, `professional_accounting` e `security_studies`. Cada uma tem 5 questões. Algumas alcançam 100% de acurácia Ralph, mas esse resultado cobre somente cinco itens e não demonstra domínio geral da matéria.

Há perda líquida de uma questão em `computer_security`, `high_school_biology`, `high_school_geography`, `high_school_macroeconomics`, `high_school_physics`, `high_school_us_history`, `high_school_world_history`, `jurisprudence`, `medical_genetics`, `moral_scenarios`, `prehistory` e `public_relations`. Essas perdas persistem no recorte sem falhas. `college_mathematics` perde duas questões na base completa exclusivamente por falhas de execução; nos três pares restantes, empata em 100%.

`business_ethics` e `world_religions` merecem cuidado: ambas empatam em acurácia, mas cada uma contém uma correção e uma regressão. Empate agregado não equivale a comportamento idêntico. `virology` permanece em 20% para os dois métodos, exemplo de baixa acurácia que o loop não resolveu.

No conjunto das 67 matérias, o cenário completo tem **8 com ganho, 18 com perda e 41 empatadas**. Sem falhas, são **12 com ganho, 13 com perda e 42 empatadas**. As contagens dão o mesmo peso a uma matéria de cinco questões e a outra de dezenas de questões; por isso, complementam as contagens de acertos, mas não as substituem. A simples já atinge 100% em 42 matérias no recorte sem falhas, criando um teto importante para a melhora.

O apêndice A apresenta todas as matérias, inclusive as empatadas, para evitar seleção apenas de resultados favoráveis.

## 7. Complexidade: nível, origem e esforço de inferência

### 7.1. Origem e nível das questões

| Grupo | n total | Simples total | Ralph total | Δ total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | Corrige/piora sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Vestibular · ENEM | 203 | 199/203 (98,03%) | 195/203 (96,06%) | -1,97 p.p. | 198 | 98,48% | 97,98% | -0,51 p.p. | 0/1 |
| Vestibular · UNICAMP | 16 | 15/16 (93,75%) | 16/16 (100,00%) | +6,25 p.p. | 16 | 93,75% | 100,00% | +6,25 p.p. | 1/0 |
| Vestibular · FUVEST | 7 | 7/7 (100,00%) | 7/7 (100,00%) | 0,00 p.p. | 7 | 100,00% | 100,00% | 0,00 p.p. | 0/0 |
| Vestibular · ITA | 42 | 35/42 (83,33%) | 37/42 (88,10%) | +4,76 p.p. | 39 | 84,62% | 94,87% | +10,26 p.p. | 4/0 |
| MMLU · Ensino fundamental | 5 | 5/5 (100,00%) | 5/5 (100,00%) | 0,00 p.p. | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 |
| MMLU · Ensino médio | 70 | 66/70 (94,29%) | 62/70 (88,57%) | -5,71 p.p. | 69 | 95,65% | 89,86% | -5,80 p.p. | 2/6 |
| MMLU · Graduação | 30 | 28/30 (93,33%) | 27/30 (90,00%) | -3,33 p.p. | 28 | 92,86% | 96,43% | +3,57 p.p. | 1/0 |
| MMLU · Profissional | 20 | 17/20 (85,00%) | 18/20 (90,00%) | +5,00 p.p. | 20 | 85,00% | 90,00% | +5,00 p.p. | 1/0 |
| MMLU · geral/especializado | 160 | 140/160 (87,50%) | 136/160 (85,00%) | -2,50 p.p. | 160 | 87,50% | 85,00% | -2,50 p.p. | 4/8 |
| GPQA · Diamond | 190 | 140/190 (73,68%) | 134/190 (70,53%) | -3,16 p.p. | 169 | 72,78% | 79,29% | +6,51 p.p. | 22/11 |

**Os melhores sinais estão no ITA e no GPQA Diamond, mas por motivos e com riscos diferentes.** O ITA tem +4 acertos líquidos sem falhas, sem regressões nesse recorte, enquanto o GPQA tem +11, acompanhado de 11 regressões. Com falhas, o ITA preserva ganho de +2, mas o GPQA perde 6. A UNICAMP tem +1 acerto e nenhuma regressão nos 16 pares; a FUVEST empata em sete pares já totalmente acertados pela simples.

O MMLU não apresenta uma relação monotônica entre nível nominal e ganho: ensino médio piora 5,80 p.p. sem falhas; graduação melhora 3,57 p.p. e profissional melhora 5,00 p.p., porém cada uma dessas últimas melhoras corresponde a apenas uma correção. O nível geral/especializado piora 2,50 p.p. Ensino fundamental tem somente cinco observações e empate em 100%.

Não é possível concluir que aumentar a complexidade sempre beneficia o loop. O que os dados mostram é uma concentração de ganhos em alguns conjuntos exigentes, associada a maior margem para recuperar erros da simples, e uma concentração de falhas no GPQA. Comparações entre ENEM, ITA e GPQA também variam em matéria, idioma, formato e composição da amostra.

### 7.2. Tokens da inferência simples como indicador aproximado de esforço

Os quartis foram calculados **separadamente dentro de cada execução**, pelo método de posição mais próxima, preservando empates. O exportador recalcula os quartis depois do filtro de falhas. Assim, Q1 do MMLU e Q1 do GPQA representam posições relativas em suas respectivas distribuições, não a mesma quantidade absoluta de tokens. Tokens da inferência simples são uma medida observada de esforço, não uma anotação independente de dificuldade.

| Quartil simples | n total | Δ total | Falhas Ralph no total | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | p sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | 188 | -1,06 p.p. | 3 | 181 | 92,82% | 92,27% | -0,55 p.p. | 1,0000 |
| Q2 | 184 | -3,26 p.p. | 5 | 177 | 91,53% | 92,09% | +0,56 p.p. | 1,0000 |
| Q3 | 186 | -1,08 p.p. | 8 | 176 | 85,80% | 87,50% | +1,70 p.p. | 0,6291 |
| Q4 | 185 | -2,70 p.p. | 15 | 177 | 82,49% | 85,88% | +3,39 p.p. | 0,2632 |

Sem falhas, o ganho observado cresce de −0,55 p.p. em Q1 para +0,56, +1,70 e +3,39 p.p. em Q2, Q3 e Q4. Esse padrão é compatível com benefício maior quando a simples precisa de mais esforço e erra mais. Entretanto, não foi feito um teste confirmatório de tendência, os quartis são relativos e o comportamento da simples participa de sua definição.

Na base completa, todos os quartis têm saldo desfavorável. Q4 concentra 15 falhas Ralph em 185 pares (**8,11%**), contra 3/188 (**1,60%**) em Q1. Há, portanto, um compromisso observado: o subconjunto com mais margem para melhoria também apresenta maior risco de interrupção.

Uma verificação adicional manteve os quartis da base completa e só então removeu as falhas. Nesse procedimento, os ganhos sem falha são **0,00; −0,56; +2,25; +3,55 p.p.** em Q1–Q4. A vantagem maior nas faixas superiores permanece descritivamente, mas detalhes das duas primeiras faixas dependem dos cortes.

### 7.3. Tokens do próprio Ralph: consumo elevado não garante melhor resultado

| Quartil Ralph | n total | Δ total | Falhas Ralph | p total | n sem falha | Δ sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | 187 | -1,07 p.p. | 7 | 0,8145 | 179 | +2,79 p.p. |
| Q2 | 185 | +1,08 p.p. | 0 | 0,7539 | 177 | +1,13 p.p. |
| Q3 | 187 | -0,53 p.p. | 3 | 1,0000 | 178 | -0,56 p.p. |
| Q4 | 184 | -7,61 p.p. | 21 | 0,0336 | 177 | +1,69 p.p. |

O quartil de maior consumo Ralph é o pior no cenário completo: **−7,61 p.p., 26 regressões e 12 correções**, com 21 falhas em 184 pares (**11,41%**). O p=0,0336 é nominal e exploratório. Esse quartil reúne **67,74% das 31 falhas Ralph**.

Após o filtro e recálculo dos cortes, Q4 melhora 1,69 p.p.; mantendo os cortes originais e só retirando falhas, Q4 fica em **0,00 p.p.**. Logo, não há suporte robusto para dizer que gastar mais tokens no Ralph causa melhores respostas. Consumo pode ser consequência de dificuldade, replanejamento, tentativas repetidas ou geração excessiva. Usá-lo como medida causal da “dose” do método confundiria esses efeitos.

## 8. Confiabilidade e taxonomia das falhas

### 8.1. Quantidade, cobertura e distinção entre falha e resposta errada

O Ralph tem **31 falhas em 743 pares (4,17%)**, contra **2 na simples (0,27%)**. O quociente descritivo entre as taxas é 15,5, mas o número de falhas da simples é pequeno. Há 29 sessões Ralph com status `failed` e 2 com status `completed` cuja resposta final é rejeitada pelo avaliador do benchmark. Portanto, contar apenas sessões `failed` subestima o total de falhas relevantes para a acurácia.

Entre os 106 resultados não corretos do Ralph, **75 (70,75%) são alternativas erradas válidas** e **31 (29,25%) são falhas operacionais**. Das 51 regressões da base completa, **25 são falhas Ralph e 26 são erros de conteúdo sem falha**. Assim, nem todas as perdas são explicadas pelas interrupções, e o filtro não remove o problema da validação semântica.

| Causa terminal | n | % das falhas | GPQA | MMLU | Vestibulares | Simples acertou | Tokens Ralph conhecidos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cinco tentativas reprovadas de tarefa | 16 | 51,61% | 11 | 0 | 5 | 13 | 2.279.155 |
| JSON ou contrato de saída inválido | 8 | 25,81% | 5 | 1 | 2 | 8 | 349.160 |
| Tempo de sessão excedido | 3 | 9,68% | 3 | 0 | 0 | 1 | 798.601 |
| Resposta final inválida para o avaliador | 2 | 6,45% | 1 | 1 | 0 | 1 | 269.167 |
| Cinco planos candidatos reprovados | 1 | 3,23% | 1 | 0 | 0 | 1 | 83.105 |
| Limite financeiro da chave no provedor | 1 | 3,23% | 0 | 1 | 0 | 1 | 0 |

Os limites de tarefa, tempo e planejamento somam **20/31 falhas (64,52%)**. JSON/contrato e resposta final somam **10/31 (32,26%)**. O bloqueio explicitamente externo de crédito corresponde a **1/31 (3,23%)**. Essa classificação é pelo motivo terminal; uma falha pode ter antecedentes de conteúdo e de orquestração simultaneamente.

### 8.2. Cinco reprovações da mesma tarefa: principal causa terminal

São 16 casos: 11 no GPQA e 5 nos vestibulares, todos encerrados em B.2 após cinco tentativas. Esses casos somam **2.279.155 tokens** e **80 reprovações semânticas de tarefa**. A simples acertou 13 dos 16.

O limite de cinco tentativas é a causa imediata do encerramento. A causa anterior não é única: inclui premissas erradas aprovadas anteriormente, objetivos ou critérios mal formulados, falha em reconsiderar dependências e incapacidade de resolver a questão. Os quatro casos abaixo permitem distinguir essas situações sem atribuir toda reprovação a “rigor excessivo”.

**Caso 1 — uma premissa numérica errada torna a tarefa final insolúvel: `MATEMATICA_ENEM_2023_AZUL_Q138`.**

O enunciado informa que a urna B tem 4 bolinhas pretas e probabilidade inicial de preta igual a 25%. Portanto, ela tem inicialmente **16 bolinhas**, das quais 12 brancas. Se forem adicionadas `n` bolinhas brancas, a condição é `0,20 × 4/(16+n) ≤ 0,01`, que produz `n ≥ 64`, alternativa C, igual ao gabarito. Essa verificação usa apenas os números do enunciado.

Na execução Ralph, T1 adota `4/(8+n)`, sem sustentar o denominador inicial 8. B.2 aprova essa etapa e T2 calcula 72, que também é aprovado e registrado na memória. T3 deve encontrar uma alternativa igual a 72; como não existe, repete cinco vezes a comparação e termina sem resposta. Na última verificação, o critério técnico chega a aprovar a comparação local com 72, enquanto os critérios de seleção continuam reprovados.

**Diagnóstico:** erro de interpretação quantitativa na origem, aprovação incorreta e retentativas restritas a uma tarefa posterior. A validação detecta a impossibilidade da seleção final, mas não resolve a premissa que a produziu. Aumentar apenas o número de retentativas de T3 não tem justificativa empírica nesse caso.

**Caso 2 — o plano exige uma relação diferente da pedida: `MATEMATICA_ITA_2024_F1_UNICA_Q043`.**

O enunciado pergunta em qual intervalo o raio de um cilindro **pode estar**, sabendo que área da base, área lateral e volume formam uma progressão geométrica crescente. Os próprios resultados Ralph chegam a `r > 2`. A opção E, `(2; 5/2)`, é inteiramente compatível com esse resultado e é o gabarito.

A tarefa final, contudo, exige que a alternativa seja exatamente igual ao intervalo derivado ou que o contenha. O validador reprova a escolha E porque `(2; 5/2)` é um subconjunto de `(2; +∞)`. As cinco tentativas mantêm esse conflito e a sessão termina sem resposta, apesar de o candidato final escolher E.

**Diagnóstico:** a decomposição converte uma pergunta de possibilidade em uma exigência de igualdade ou inclusão na direção contrária. O validador aplica o critério planejado de maneira consistente, mas esse critério não preserva a intenção do enunciado. É um exemplo concreto de aprovação de plano inadequado em A.3 e de rigor dirigido ao objetivo errado.

**Caso 3 — um erro de conteúdo fica cristalizado como aprendizado: `QUIMICA_ITA_2025_F1_UNICA_Q035`.**

A pergunta pede o valor errado de NOX e apresenta +3 para o carbono do ácido metanoico. T1 escreve `H–C(=O)–OH`, mas calcula a neutralidade usando um único H: `x + 1 − 2 − 2 = 0`, obtendo +3. A própria fórmula mostrada contém dois H; usando os valores de NOX que a execução adota, a soma correta é `x + 2 − 4 = 0`, isto é, +2. Portanto, a opção E contém o valor errado, como registra o gabarito.

O resultado +3 é aprovado e registrado em B.4. T2 recebe a classificação de todas as alternativas como corretas e não encontra a única errada, acumulando cinco reprovações. O verificador por vezes descreve a análise local como correta porque confere a tabela recebida, sem corrigir a omissão inicial.

**Diagnóstico:** a arquitetura conserva um erro verificável e trata a coerência com a memória como evidência de validade. O problema não é somente a formatação nem a falta de novas tentativas.

**Caso 4 — uma busca incompleta é aceita e a tarefa seguinte não pode repará-la: `GPQA_diamond_recIj8lR4tuDgrHou`.**

T1 enumera configurações de quatro partículas sob o limite de duas por nível, cujas somas calculadas em T2 resultam em `10E`, `15E` e `20E`. Usando a própria regra `E_n=n²E` registrada na execução, a configuração de níveis `(1,2,2,3)` satisfaz o limite de ocupação e soma `1+4+4+9=18E`, inferior a `20E`. A alternativa D e o gabarito trazem `10E, 15E, 18E`.

T2 exige usar as configurações herdadas de T1 e também verificar que não existem estados intermediários. Durante a própria execução de T2, o Ralph encontra a configuração de `18E` e reconhece que ela contradiz o intervalo entre `15E` e `20E`. B.2 reprova exatamente esse requisito de cobertura, mas aprova o critério técnico por considerar correta a aritmética sobre as configurações recebidas. As cinco tentativas continuam reportando os valores herdados, e a sessão termina sem revisar T1 nem chegar à seleção final.

**Diagnóstico:** cobertura insuficiente de possibilidades em T1, seguida de falha de encaminhamento da correção. A inconsistência é identificada dentro do próprio fluxo, mas a retentativa da tarefa atual não substitui o resultado anterior que a provoca. A capacidade de detectar um erro não assegura que a arquitetura consiga repará-lo.

**Outros exemplos:** `GEOGRAFIA_ENEM_2024_AZUL_Q071` fica presa à leitura de agentes explicitamente citados e à rejeição de todas as alternativas; `QUIMICA_ITA_2024_F1_UNICA_Q053` herda somente a afirmação III como verdadeira e não reconsidera IV ao comparar as combinações; várias questões de síntese química do GPQA oscilam entre “nenhuma opção” e escolhas por melhor ajuste reprovadas. Esses últimos casos indicam dificuldade de reconciliação entre premissas e opções, mas não foram reavaliados integralmente por especialista.

### 8.3. JSON e contrato de saída: falha real de integração, com tentativas de recuperação

Há 8 casos, distribuídos em **A.2 (4), B.2 (3) e C.2 (1)**. Todos têm uma tentativa original e duas correções no trecho terminal. Nessas 24 invocações terminais, o diagnóstico informa `finish_reason=stop` e `length_interruption=not_detected`. Portanto, os logs não sustentam atribuir essas oito falhas a truncamento por limite de saída.

- Em `BIOLOGIA_ENEM_2022_AZUL_Q133` e `BIOLOGIA_ENEM_2024_AZUL_Q105`, a saída B.2 contém uma chave `}` excedente no fim da avaliação de critérios. As três saídas de cada sessão repetem o defeito. No primeiro caso, o conteúdo do verificador declara aprovação da alternativa D, que coincide com o gabarito, mas o JSON inválido impede que a execução prossiga. Há evidência de conteúdo aproveitável no estágio intermediário; não há uma resposta final efetivamente entregue que possa ser contabilizada como acerto.
- Em `MMLU_college_mathematics_test_0098`, `GPQA_diamond_recPSTGXK3P39yNYT`, `GPQA_diamond_recINGR1z01Fh1Z3A` e `GPQA_diamond_recPzW1WqRnPs57D6`, os planos omitem o campo estruturado `acceptance_criteria` de tarefa ou incorporam critérios dentro da descrição textual. As correções nem sempre alteram a estrutura necessária e, em alguns casos, introduzem erros de sintaxe.
- Em `GPQA_diamond_rec9W28HgpEUeUN8k`, o replanejamento C.2 não fornece `review.task_ids` como lista. O diagnóstico admite reparo de fechamentos, mas o contrato permanece inválido. Isso distingue JSON sintaticamente recuperável de saída semanticamente compatível com o esquema do harness.
- Em `GPQA_diamond_recGee5m84dg5FZkc`, B.2 também repete uma chave excedente, apesar das correções solicitadas.

Esses casos somam **349.160 tokens** e são oito questões que a simples acertou. Há suporte para apontar fragilidade na geração e recuperação de saídas estruturadas. **Não há suporte para afirmar ausência de mecanismo de recuperação:** ele existe nos registros e falhou nesses casos. A repetição de saídas praticamente idênticas mostra que pedir correção, mesmo com temperatura 1,0 nas retentativas, não garantiu reparo efetivo.

### 8.4. Tempo: limite nominal de dez minutos, observado após chamadas extensas

Os três estouros ocorrem em B.1 no GPQA. O limite registrado é 600.000 ms, mas as durações totais são aproximadamente **1.827,66 s, 1.818,53 s e 650,44 s**. As chamadas B.1 consomem, respectivamente, **256.083, 324.325 e 177.893 tokens de saída**, com `finish_reason=error` e `outcome=success` nos registros de invocação. Essa combinação de campos exige cautela: sucesso de recebimento/contabilização da invocação não é conclusão bem-sucedida da tarefa.

O código local consulta o limite antes de iniciar chamadas e contabiliza o tempo após o retorno. Esse mecanismo é compatível com os excessos observados e não equivale a cancelar a chamada exatamente ao atingir dez minutos. Os logs evidenciam geração muito extensa e retorno com erro; não permitem estabelecer se a origem é repetição interna do modelo, comportamento do provedor ou outro defeito no transporte.

As três sessões somam **798.601 tokens e 4.296,63 s**. São apenas 0,40% dos pares completos, mas consomem **11,19% da soma das durações Ralph**. Esse comportamento afeta a viabilidade e a interpretação das médias.

### 8.5. Planejamento: o controle impede execução, mas não produz solução

`GPQA_diamond_recdya6FuYraBU5Rh` termina após **cinco planos candidatos reprovados em A.3**, consumindo 83.105 tokens. As objeções registradas incluem conclusão antecipada, hipóteses não estabelecidas e critérios que forçam a escolha de uma opção apesar da incompatibilidade com a derivação proposta.

Há evidência de que o controle de planejamento identifica problemas reais de neutralidade e aplicabilidade. Entretanto, as revisões não convergem para um plano executável dentro do orçamento, e a simples acertou a questão. O resultado permite discutir o custo do controle e a dificuldade de revisão; não demonstra que remover o controle melhoraria a resposta.

### 8.6. Resposta final: duas naturezas distintas de saída inválida

Em `MMLU_high_school_macroeconomics_test_0007`, a sessão conclui com uma explicação que escolhe A, mas omite a linha obrigatória `FINAL_ANSWER: A`. O avaliador aceita marcador final válido, letra isolada ou alternativa completa isolada; uma alternativa seguida de explicação, sem marcador, não satisfaz suas regras. **O gabarito é D**, logo recuperar a letra A resolveria a validade de extração, mas não transformaria esse caso em acerto.

Em `GPQA_diamond_rec2fsnzUuvNtUYK8`, a resposta termina com `FINAL_ANSWER: NONE`, após concluir que nenhuma opção satisfaz a classificação de simetria. A linha viola a exigência de selecionar uma das quatro alternativas. **Esse caso não se reduz a um parser excessivamente restritivo:** o modelo explicitamente recusou escolher uma opção disponível.

As duas sessões têm status `completed`, mas erro no desfecho do benchmark, e somam 269.167 tokens. É necessário distinguir validade de formato, adesão à tarefa de múltipla escolha e correção de conteúdo.

### 8.7. Provedor: um caso comprovado de limite de crédito

`MMLU_college_mathematics_test_0093` falha em A.1 com HTTP 403 porque o limite total de **US$ 10** da chave foi alcançado. O consumo conhecido da sessão é zero tokens e há uma chamada registrada. Esse é um fator externo diretamente documentado; a simples havia acertado.

Remover apenas essa observação deixaria **637/742 acertos Ralph e 651/742 simples**, saldo −14. Portanto, ela não explica a inversão global. O consumo zero é o consumo conhecido dessa sessão, não demonstração de que não houve custos anteriores na chave.

## 9. Erros de conteúdo e limites da autovalidação

### 9.1. A maioria dos erros válidos passa sem reprovação de tarefa

Os 75 casos com alternativa errada válida incluem 35 no GPQA, 34 no MMLU e 6 nos vestibulares. **59/75 (78,67%) não registram nenhuma reprovação semântica B.2**. Nas 26 regressões de conteúdo, são **20/26 (76,92%)** sem reprovação B.2. Esses percentuais são condicionados aos erros exportados; não estimam a taxa global de falsos positivos do validador, pois os logs dos acertos não estão disponíveis.

Isso mostra que o controle pode aprovar toda a trajetória e ainda assim terminar numa alternativa divergente do gabarito. Critérios podem estar incompletos, a avaliação pode concordar com uma interpretação equivocada, e resultados herdados podem ser aceitos como premissas confiáveis. O uso do mesmo modelo em diferentes fases cria oportunidades de verificação, mas não garante independência dos erros.

### 9.2. Exemplos de mudança do foco ou da interpretação

**Geografia do ENEM — `GEOGRAFIA_ENEM_2022_AZUL_Q064`:** o enunciado relaciona a interação de forças naturais à ocupação do espaço geográfico. O Ralph escolhe relevos escarpados (C), explicando a interação entre soerguimento e erosão, enquanto o gabarito é solos vulcânicos (A), que a simples escolheu. A execução não registra reprovação de tarefa. A justificativa final enfatiza a formação do relevo e não resolve adequadamente o condicionante “favorece a ocupação”. O caso ilustra como uma explicação internamente coerente pode responder a uma versão mais estreita do problema.

**Biologia no MMLU — `MMLU_high_school_biology_test_0215`:** o Ralph escolhe lisossomos (B), enquanto o gabarito é centríolos em centrossomos (D). Uma verificação intermediária aponta que a análise considera B e D compatíveis e usa exceções de maneira assimétrica para eliminar D. A execução depois aprova B e o entrega. Assim, houve detecção de um problema de discriminação entre alternativas, mas a retentativa não convergiu para o gabarito.

**Relações públicas no MMLU — `MMLU_public_relations_test_0081`:** o Ralph privilegia interrupção operacional (B) como característica de crise; o gabarito privilegia ocorrência súbita (D). Há revisão de plano, mas nenhuma reprovação de tarefa. **Jurisprudência — `MMLU_jurisprudence_test_0091`:** o Ralph escolhe ascensão do fascismo (B), enquanto o gabarito aponta reconhecimento internacional dos direitos humanos após a Segunda Guerra (C), e constrói uma explicação causal para afastar C. Esses exemplos documentam divergência de enquadramento conceitual. Não constituem, sem validação especializada, prova de que o gabarito esteja errado.

### 9.3. Possíveis problemas de gabarito: hipótese separada da avaliação principal

Em `MMLU_high_school_physics_test_0034`, o gabarito exportado é C (“I e II”), incluindo a afirmação de aceleração nula no ponto mais alto de um lançamento vertical. A resposta Ralph escolhe A (“somente I”) e justifica que a velocidade nula não implica ausência de gravidade. O conteúdo sugere necessidade de auditoria do item e de seu rótulo. Os dois métodos erram segundo o gabarito registrado, portanto o item não é uma regressão do Ralph na comparação pareada.

Esse achado não autoriza reclassificar todos os desacordos ou presumir que explicações extensas são corretas. A análise principal conserva todos os gabaritos. Uma auditoria futura deve confrontar enunciado, alternativas e rótulo com a fonte original e registrar as decisões antes de recalcular resultados. Sem isso, o paper deve tratar a possível inconsistência como limitação de validade da avaliação, não como correção demonstrada do benchmark.

## 10. Custo computacional e duração

| Cenário | Tokens simples | Tokens Ralph | Razão tokens | Soma durações simples | Soma durações Ralph | Razão durações |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Todos os pares | 651.365 | 45.653.918 | 70,09× | 3.097,97 s | 38.388,04 s | 12,39× |
| Sem falha | 424.991 | 41.800.522 | 98,36× | 1.649,68 s | 31.565,27 s | 19,13× |

### 10.1. Distribuições: por que as médias isoladas enganam

| Cenário | Fluxo | Média tokens | Mediana tokens | Média duração | Mediana duração | P95 duração | Máximo duração |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Todos | Simples | 876,67 | 544,00 | 4,17 s | 1,78 s | 5,74 s | 1.306,08 s |
| Todos | Ralph | 61.445,38 | 51.834,00 | 51,67 s | 37,65 s | 101,78 s | 1.827,66 s |
| Sem falha | Simples | 597,74 | 529,00 | 2,32 s | 1,75 s | 5,22 s | 37,32 s |
| Sem falha | Ralph | 58.791,17 | 50.964,00 | 44,40 s | 37,24 s | 88,38 s | 414,95 s |

Na base completa, uma única falha da simples no GPQA, `GPQA_diamond_recVvpD8miVjmmyfe`, usa **193.303 tokens**, cerca de **29,68% de todos os tokens da simples**. O mesmo item também falha no Ralph por tempo. Os arquivos não incluem o log da simples para determinar a causa exata da falha desse fluxo.

Essa observação aumenta muito o denominador da razão de custos completa e ajuda a explicar por que a razão de tokens sobe de 70,09× para 98,36× depois da exclusão de falhas. A razão maior após o filtro não significa aumento do consumo por intervenção; mudou a composição dos dados. Os 32 pares removidos concentram **34,75% dos tokens da simples**, contra **8,44% dos tokens Ralph**.

As 31 falhas Ralph consomem **3.779.188 tokens**, equivalentes a **8,28% do consumo Ralph total**, e **6.781,57 s**, equivalentes a **17,67% da soma de suas durações**. Já os 32 pares excluídos têm 3.853.396 tokens Ralph, pois incluem também a questão em que só a simples falha. Não se devem confundir esses dois totais.

As somas de duração representam a soma dos tempos por questão. Se houve paralelismo, elas não equivalem ao tempo de calendário da bateria. O P95 foi calculado com interpolação linear na posição `(n−1)×0,95`, documentada no script.

### 10.2. Custo por benchmark e por acerto adicional

| Conjunto sem falha | Razão tokens | Razão durações | Ganho líquido | Tokens extras/acerto líquido |
| --- | ---: | ---: | ---: | ---: |
| gpqa | 99,06× | 17,10× | +11 | 1.295.015 |
| mmlu | 140,80× | 21,92× | -6 | Sem ganho líquido |
| vestibular | 76,91× | 19,20× | +4 | 3.556.506 |

No total sem falhas, os tokens adicionais são **41.375.531**, divididos por 9 acertos líquidos: **4.597.281 tokens extras por acerto líquido**. Na base completa, o custo adicional é 45.002.553 tokens e o saldo de acertos é negativo; nesse cenário, a métrica de custo por acerto adicional positivo não se aplica.

O MMLU combina o maior multiplicador de tokens sem falhas, **140,80×**, com perda de acurácia. O GPQA tem ganho maior por token adicional nesta comparação, mas continua muito mais caro que a simples. Não há preços, custo monetário completo por chamada, detalhamento de cache para todas as questões ou consumo energético que permita concluir viabilidade financeira ou energética.

O experimento compara a arquitetura completa com uma inferência simples. Sem uma condição de controle com orçamento de tokens semelhante — por exemplo, múltiplas amostras da simples ou outra estratégia de raciocínio —, não é possível atribuir todo ganho especificamente ao desenho Ralph, separando-o do efeito de usar muito mais computação.

## 11. Análises de sensibilidade e cenários úteis para discussão

### 11.1. Quanto as falhas precisam melhorar para mudar o resultado completo

O Ralph tem 637 acertos contra 652 da simples no conjunto completo. Mantendo todas as outras respostas constantes, seria necessário converter **15 falhas em acertos para empatar** e **16 para superar a simples**. Isso corresponde a acertar 48,39% ou 51,61% das 31 questões com falha. Trata-se de uma conta contrafactual, não de uma previsão de sucesso após correções.

Se todas as 31 falhas se tornassem corretas e os demais resultados permanecessem iguais, o limite superior hipotético seria **668/743 (89,91%)**, +2,15 p.p. sobre a simples. Corrigir a integração pode recuperar desempenho, mas não eliminaria os 75 erros de conteúdo já entregues nem garante preservação dos acertos atuais.

Corrigir os oito erros de JSON/contrato, mesmo com acerto em todos esses casos, aumentaria o total de 637 para 645 e ainda deixaria uma perda líquida de 7 acertos. Portanto, resolver apenas o parser não basta para demonstrar superioridade de ponta a ponta nesta amostra.

### 11.2. Fallback para inferência simples em caso de falha Ralph

Um cenário estritamente retrospectivo é aproveitar a resposta da simples quando o Ralph falha. Nos 31 casos de falha Ralph, a simples acertou 25. A política hipotética alcançaria **662/743 (89,10%)**, 10 acertos a mais que a simples e 25 a mais que o Ralph avaliado. Isso pressupõe disponibilidade da resposta simples e detecção da falha pelo campo de erro; não escolhe com base no gabarito. O mesmo mecanismo não recupera as 26 regressões sem falha.

Esse número não deve ser apresentado como resultado da implementação existente. É uma simulação derivada dos resultados registrados, com custo e latência próprios e necessidade de confirmação em novo conjunto. Uma política de encaminhamento apenas por matéria ou dificuldade também exigiria validação fora desta amostra, pois os grupos promissores foram identificados após observar os resultados.

### 11.3. Robustez ao agrupamento e à composição

Os resultados mais favoráveis a exatas aparecem tanto na classificação original STEM quanto no reagrupamento que separa biológicas. Entretanto, os valores nominais de significância não resistem à correção simples dentro das famílias de áreas. O ganho condicional global depende fortemente do GPQA; a remoção desse conjunto deixa saldo −2. A comparação por famílias harmonizadas preserva o ganho condicional de Física, Química e Matemática, mas muda o peso de cada benchmark.

Essas verificações reforçam uma conclusão localizada: há um padrão favorável em parte dos problemas quantitativos e científicos. Elas não produzem uma estimativa independente de generalização, porque reutilizam as mesmas questões.

## 12. O que os resultados permitem afirmar — e o que exigiria novo experimento

| Afirmação | Avaliação da evidência |
| --- | --- |
| O Ralph ganha acertos entre pares que terminam sem falha. | Sustentada descritivamente: +9 em 711 pares; diferença global não conclusiva a 5%. |
| O Ralph melhora o desempenho completo nesta avaliação. | Não sustentada: perde 15 acertos nos 743 pares disponíveis. |
| Problemas quantitativos/científicos são o principal recorte promissor. | Sustentada como padrão exploratório, com heterogeneidade e forte contribuição do GPQA. |
| A área biológica como um todo é a melhor para o loop. | Não sustentada: Biologia GPQA destaca-se, mas biológicas e saúde agregadas têm ganho menor que exatas. |
| Quanto mais difícil, maior o ganho. | Parcialmente compatível com ITA, GPQA e quartis simples; não há medida independente de dificuldade nem relação universal. |
| As perdas são apenas infraestrutura externa. | Contrariada: só um caso tem bloqueio externo de crédito documentado; 20 falhas envolvem limites do fluxo e há 26 regressões válidas. |
| JSON inválido é uma causa relevante e corrigível. | Relevância observada em oito falhas; benefício após correção precisa ser medido, não presumido. |
| Mais retentativas resolveriam as falhas. | Não demonstrada; vários casos repetem premissas e critérios que impedem progresso. |
| Fresh context ou memória compacta causaram os ganhos. | Não identificável sem ablação; o mesmo desenho também pode conservar erros nas dependências. |
| A validação técnica assegura correção. | Contrariada pelos erros aprovados e pelas regressões sem reprovação de tarefa. |
| Ralph é mais eficiente por questão. | Não sustentada pelo consumo: dezenas a centenas de vezes mais tokens, com ganho pequeno e incerto no agregado. |
| Há erros de gabarito no benchmark suficientes para mudar a conclusão. | Não estabelecida; há item que merece auditoria, sem reclassificação nesta análise. |

## 13. Limitações que precisam acompanhar a seção de resultados

1. **Seleção por conclusão válida:** o recorte sem falhas condiciona a análise a um resultado dos próprios métodos. Deve ser apresentado junto da avaliação completa, com contagem e causas das exclusões.
2. **Cobertura incompleta das questões declaradas:** dez questões não têm pares nos arquivos. O número de pares analisados precisa aparecer em tabelas e texto, evitando afirmar avaliação efetiva de 753 pares.
3. **Uma execução por conjunto e um modelo:** não há repetição suficiente para estimar variação entre sementes, sessões ou provedores. Temperatura de sessão zero não elimina toda variabilidade, e há retentativas com temperatura maior.
4. **Matérias pequenas e múltiplos recortes:** 57 matérias têm somente cinco questões na base completa; vários ganhos de 20 p.p. correspondem a um item. As análises de áreas, matérias e níveis são exploratórias, e os menores valores de p por área não resistem à correção indicada.
5. **Dependência de composição e de observações:** o resultado global é uma média ponderada pelas questões desta amostra. GPQA, MMLU e vestibulares têm pesos e margens iniciais de erro diferentes. Testes e intervalos tratam os pares de questões como unidades independentes; sem análise adicional de dependência por matéria ou origem, não se garante calibração da incerteza caso haja correlação entre itens. A diferença de efeitos entre áreas não foi demonstrada por teste confirmatório de interação.
6. **Confundimento entre domínio, idioma, benchmark e execução:** os resultados não isolam efeito do idioma, matéria ou formato. Não é adequado atribuir a diferença MMLU–Vestibulares apenas a humanas versus exatas ou português versus inglês.
7. **Dificuldade medida indiretamente:** instituição, prefixo de nível e consumo de tokens não são uma escala uniforme de complexidade. O consumo Ralph é posterior à atuação do método e pode refletir falha.
8. **Logs selecionados por erro:** os ZIPs incluem todos os erros Ralph, mas não seus acertos. É possível caracterizar mecanismos de falha; não estimar com esses logs a frequência global de recuperação, o número médio de tarefas de todos os casos ou a precisão total do verificador.
9. **Campos de trajetória vazios nos CSVs:** `ralph_tarefas`, `ralph_verificacoes_reprovadas` e `ralph_planos_reprovados` estão vazios em todas as 743 linhas. Vazio não significa zero. Contagens de trajetória apresentadas aqui foram extraídas somente dos logs disponíveis.
10. **Gabaritos não auditados integralmente:** a métrica usa os rótulos fornecidos. Suspeitas de inconsistência não foram usadas para selecionar ou reclassificar exemplos favoráveis.
11. **Custo sem controle equivalente:** não há comparação com outra estratégia de mesmo orçamento. Tokens totais misturam entrada, saída e possível reapresentação de conteúdo. Não se mediu custo monetário completo, energia ou tempo de calendário sob paralelismo.
12. **Implementação histórica sem snapshot completo na pasta:** os logs registram versão do fluxo e configuração parcial, mas não fornecem todos os prompts e parâmetros dos acertos em um artefato experimental único. Atribuir efeitos isolados a uma extensão específica do Ralph requer ablação e rastreabilidade de versão.
13. **Mecanismos observados não são efeitos causais estimados:** os estudos de caso demonstram trajetórias específicas; não quantificam quanto cada correção de projeto elevaria a acurácia em novas questões.

## 14. Melhorias motivadas pelos dados e experimentos para verificá-las

As propostas abaixo são derivadas dos erros observados. Não foram implementadas ou avaliadas nesta análise.

| Evidência observada | Mudança a investigar | Como avaliar |
| --- | --- | --- |
| Cinco tentativas repetem conflito com resultado herdado. | Detectar estagnação e abrir revisão da premissa ou da tarefa anterior, com rastreio das dependências. | Comparar taxa de falha por tentativas, acurácia completa e tokens; separar revisão útil de propagação de novos erros. |
| Plano transforma “pode estar” em igualdade exata. | Verificar fidelidade semântica de objetivos e critérios ao pedido original, especialmente quantificadores, negações e direção de inclusão. | Reavaliar o caso ITA e um conjunto novo com estruturas linguísticas semelhantes, sem testar só o item que motivou a mudança. |
| Erro numérico aprovado vira aprendizado. | Acrescentar verificações objetivas de conservação, contagem, substituição e consistência com dados literais quando aplicáveis. | Medir recuperação de erros iniciais e regressões introduzidas; evitar critérios que apenas repetem a justificativa do executor. |
| Oito falhas de JSON/contrato após correções. | Melhorar geração segundo esquema e diagnóstico específico de campo; investigar reparos determinísticos restritos a sintaxe sem alterar decisões. | Medir validade por fase, tentativas de recuperação e acurácia final; registrar qualquer alteração feita ao conteúdo. |
| Marcador ausente ou `NONE` na síntese. | Validar o contrato final antes de encerrar a sessão e distinguir ausência de marcador de recusa de escolha. | Medir formato válido e correção separadamente; o caso macroeconômico exige correção de conteúdo além do formato. |
| Chamadas excedem o tempo nominal de sessão. | Investigar cancelamento por prazo efetivo e limites apropriados por chamada, acompanhando o motivo de término do provedor. | Medir cumprimento do prazo, perda de respostas potencialmente corretas, latência de cauda e consumo conhecido. |
| MMLU perde qualidade com grande custo. | Avaliar encaminhamento seletivo e controles com orçamento equivalente. | Definir a regra de encaminhamento antes do teste e avaliá-la em novas questões; incluir inferência simples e outras estratégias com orçamento comparável. |
| Um bloqueio de crédito. | Registrar orçamento operacional e disponibilidade da chave para a execução da bateria. | Reportar falhas de disponibilidade separadas e manter também a métrica de ponta a ponta. |

Um próximo experimento deve preservar os dois cenários de avaliação, repetir execuções, congelar versões de código/prompts, registrar a trajetória também dos acertos, auditar itens suspeitos e planejar previamente as comparações principais. Para separar o efeito da arquitetura do efeito de computação adicional, convém incluir pelo menos um controle com orçamento de tokens aproximado ao Ralph. Para estimar benefício de cada componente, é necessário comparar variantes com e sem a alteração correspondente.

## 15. Texto-base para a redação do paper

Os parágrafos abaixo podem ser adaptados à seção de resultados. As ressalvas metodológicas das seções anteriores precisam ser preservadas no manuscrito.

**Resultado global.** “A avaliação compreendeu 743 pares de respostas, distribuídos entre GPQA Diamond, MMLU e vestibulares. Considerando falhas de execução como resultados não corretos, a inferência simples atingiu 87,75% de acurácia, enquanto o Ralph Loop adaptado atingiu 85,73%, diferença de −2,02 pontos percentuais (McNemar exato bicaudal, p=0,1329). Após a exclusão pareada de 32 questões com falha em ao menos um fluxo, a acurácia foi de 88,19% para a inferência simples e de 89,45% para o Ralph, diferença de +1,27 ponto percentual (p=0,3057). Nesse recorte, o Ralph corrigiu 35 erros e introduziu 26 regressões, com redução relativa do erro de 10,71%. O ganho condicional observado não foi estatisticamente conclusivo no agregado.”

**Domínio e complexidade.** “O comportamento foi heterogêneo entre conjuntos e áreas. Nos pares sem falha, o GPQA Diamond apresentou ganho de 6,51 pontos percentuais e os vestibulares de 1,54 ponto, enquanto o MMLU apresentou perda de 2,13 pontos. Em um reagrupamento complementar por área, exatas e tecnologia apresentou ganho de 3,76 pontos, biológicas e saúde de 1,98 ponto e humanas e sociais perda de 3,07 pontos. O ITA apresentou ganho de 10,26 pontos sem falhas e de 4,76 pontos na avaliação completa. Esses resultados exploratórios indicam benefício mais promissor em parte dos problemas científicos e quantitativos, sem estabelecer uma relação universal entre complexidade e ganho.”

**Confiabilidade.** “Foram registradas 31 falhas no Ralph e duas na inferência simples. As falhas do Ralph incluíram 16 esgotamentos de tentativas de tarefa, oito falhas de JSON ou contrato de saída, três estouros de tempo, duas respostas finais inválidas, um esgotamento de tentativas de planejamento e um bloqueio por limite financeiro do provedor. A inspeção das trajetórias identificou casos em que premissas incorretas foram aprovadas e reutilizadas, mantendo as retentativas posteriores presas a resultados incompatíveis com as opções. Além das interrupções, houve 26 regressões com resposta válida, das quais 20 ocorreram sem reprovação de tarefa registrada. Assim, a perda de desempenho completo não pode ser atribuída exclusivamente a fatores externos.”

**Custo e alcance da conclusão.** “Entre os pares sem falha, o Ralph consumiu 98,36 vezes os tokens e 19,13 vezes a soma das durações individuais da inferência simples. O acréscimo de consumo foi de aproximadamente 4,60 milhões de tokens por acerto líquido adicional. Os resultados evidenciam um compromisso entre ganho condicional de acurácia, confiabilidade e custo. Como não houve controle com orçamento computacional equivalente, ablações ou repetições independentes, não é possível separar o efeito de cada componente da arquitetura nem concluir superioridade geral do método.”

## Apêndice A. Todas as matérias

Δ é sempre Ralph menos simples. “C/P” significa correções/regressões entre os pares sem falha. A taxa final sem falha está acompanhada do tamanho do recorte; a coluna de falhas conta somente falhas do Ralph na base completa. Os nomes originais do CSV foram preservados para rastreabilidade.

| Matéria | n total | Simples total | Ralph total | Δ total | Falhas Ralph | n sem falha | Simples sem falha | Ralph sem falha | Δ sem falha | C/P sem falha | p sem falha |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `abstract_algebra` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `anatomy` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `astronomy` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `BIOLOGIA` | 30 | 100,00% | 93,33% | -6,67 p.p. | 2 | 28 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `biology` | 19 | 57,89% | 73,68% | +15,79 p.p. | 1 | 18 | 61,11% | 77,78% | +16,67 p.p. | 4/1 | 0,3750 |
| `business_ethics` | 5 | 80,00% | 80,00% | 0,00 p.p. | 0 | 5 | 80,00% | 80,00% | 0,00 p.p. | 1/1 | 1,0000 |
| `chemistry` | 85 | 63,53% | 58,82% | -4,71 p.p. | 12 | 73 | 61,64% | 68,49% | +6,85 p.p. | 12/7 | 0,3593 |
| `clinical_knowledge` | 5 | 80,00% | 100,00% | +20,00 p.p. | 0 | 5 | 80,00% | 100,00% | +20,00 p.p. | 1/0 | 1,0000 |
| `college_biology` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `college_chemistry` | 5 | 60,00% | 80,00% | +20,00 p.p. | 0 | 5 | 60,00% | 80,00% | +20,00 p.p. | 1/0 | 1,0000 |
| `college_computer_science` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `college_mathematics` | 5 | 100,00% | 60,00% | -40,00 p.p. | 2 | 3 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `college_medicine` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `college_physics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `computer_security` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `conceptual_physics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `econometrics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `electrical_engineering` | 5 | 60,00% | 60,00% | 0,00 p.p. | 0 | 5 | 60,00% | 60,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `elementary_mathematics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `FILOSOFIA_SOCIOLOGIA` | 30 | 100,00% | 100,00% | 0,00 p.p. | 0 | 30 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `FISICA` | 49 | 89,80% | 97,96% | +8,16 p.p. | 0 | 48 | 91,67% | 97,92% | +6,25 p.p. | 3/0 | 0,2500 |
| `formal_logic` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `GEOGRAFIA` | 30 | 100,00% | 93,33% | -6,67 p.p. | 1 | 29 | 100,00% | 96,55% | -3,45 p.p. | 0/1 | 1,0000 |
| `global_facts` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_biology` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `high_school_chemistry` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_computer_science` | 5 | 80,00% | 100,00% | +20,00 p.p. | 0 | 5 | 80,00% | 100,00% | +20,00 p.p. | 1/0 | 1,0000 |
| `high_school_european_history` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_geography` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `high_school_government_and_politics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_macroeconomics` | 5 | 80,00% | 60,00% | -20,00 p.p. | 1 | 4 | 100,00% | 75,00% | -25,00 p.p. | 0/1 | 1,0000 |
| `high_school_mathematics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_microeconomics` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_physics` | 5 | 80,00% | 60,00% | -20,00 p.p. | 0 | 5 | 80,00% | 60,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `high_school_psychology` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `high_school_statistics` | 5 | 80,00% | 100,00% | +20,00 p.p. | 0 | 5 | 80,00% | 100,00% | +20,00 p.p. | 1/0 | 1,0000 |
| `high_school_us_history` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `high_school_world_history` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `HISTORIA` | 30 | 93,33% | 93,33% | 0,00 p.p. | 0 | 30 | 93,33% | 93,33% | 0,00 p.p. | 0/0 | 1,0000 |
| `human_aging` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `human_sexuality` | 5 | 80,00% | 80,00% | 0,00 p.p. | 0 | 5 | 80,00% | 80,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `international_law` | 5 | 80,00% | 80,00% | 0,00 p.p. | 0 | 5 | 80,00% | 80,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `jurisprudence` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `logical_fallacies` | 5 | 80,00% | 80,00% | 0,00 p.p. | 0 | 5 | 80,00% | 80,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `machine_learning` | 5 | 80,00% | 80,00% | 0,00 p.p. | 0 | 5 | 80,00% | 80,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `management` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `marketing` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `MATEMATICA` | 49 | 97,96% | 95,92% | -2,04 p.p. | 2 | 47 | 97,87% | 100,00% | +2,13 p.p. | 1/0 | 1,0000 |
| `medical_genetics` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `miscellaneous` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `moral_disputes` | 5 | 60,00% | 60,00% | 0,00 p.p. | 0 | 5 | 60,00% | 60,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `moral_scenarios` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `nutrition` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `philosophy` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `physics` | 86 | 87,21% | 81,40% | -5,81 p.p. | 8 | 78 | 85,90% | 89,74% | +3,85 p.p. | 6/3 | 0,5078 |
| `prehistory` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `professional_accounting` | 5 | 80,00% | 100,00% | +20,00 p.p. | 0 | 5 | 80,00% | 100,00% | +20,00 p.p. | 1/0 | 1,0000 |
| `professional_law` | 5 | 60,00% | 60,00% | 0,00 p.p. | 0 | 5 | 60,00% | 60,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `professional_medicine` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `professional_psychology` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `public_relations` | 5 | 100,00% | 80,00% | -20,00 p.p. | 0 | 5 | 100,00% | 80,00% | -20,00 p.p. | 0/1 | 1,0000 |
| `QUIMICA` | 50 | 92,00% | 92,00% | 0,00 p.p. | 2 | 48 | 93,75% | 95,83% | +2,08 p.p. | 1/0 | 1,0000 |
| `security_studies` | 5 | 40,00% | 60,00% | +20,00 p.p. | 0 | 5 | 40,00% | 60,00% | +20,00 p.p. | 1/0 | 1,0000 |
| `sociology` | 5 | 80,00% | 80,00% | 0,00 p.p. | 0 | 5 | 80,00% | 80,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `us_foreign_policy` | 5 | 100,00% | 100,00% | 0,00 p.p. | 0 | 5 | 100,00% | 100,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `virology` | 5 | 20,00% | 20,00% | 0,00 p.p. | 0 | 5 | 20,00% | 20,00% | 0,00 p.p. | 0/0 | 1,0000 |
| `world_religions` | 5 | 60,00% | 60,00% | 0,00 p.p. | 0 | 5 | 60,00% | 60,00% | 0,00 p.p. | 1/1 | 1,0000 |

## Apêndice B. Inventário dos 32 pares removidos

Esta tabela permite auditar a passagem de 743 para 711 pares. “Simples correta” preserva o resultado original; quando a simples falha, esse valor é “não”. Para cada falha Ralph, o JSON correspondente está em `questao-<question_id>/execucao-ralph-loop.json` dentro do ZIP do benchmark indicado na seção 2.1. O caso de falha exclusiva da simples não aparece nos ZIPs de erros Ralph, pois o Ralph o acertou.

| Questão | Conjunto | Simples falhou | Simples correta | Ralph falhou | Causa Ralph/observação | Fase | Tokens Ralph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `GPQA_diamond_recVvpD8miVjmmyfe` | gpqa | sim | não | sim | Tempo de sessão | B1 | 268.926 |
| `GPQA_diamond_recgM7o1tcc7tP778` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 114.613 |
| `GPQA_diamond_recIj8lR4tuDgrHou` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 90.592 |
| `GPQA_diamond_rectlyG9pCAAuWhoB` | gpqa | não | não | sim | Tempo de sessão | B1 | 338.863 |
| `GPQA_diamond_recPSTGXK3P39yNYT` | gpqa | não | sim | sim | JSON/contrato | A2 | 14.249 |
| `GPQA_diamond_recZ13cwgDQf9jRd9` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 168.172 |
| `GPQA_diamond_recJZ3QEfRKjYw9a7` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 203.419 |
| `GPQA_diamond_recUOePh79cp4T2Bg` | gpqa | não | não | sim | 5 tentativas de tarefa | B2 | 284.899 |
| `GPQA_diamond_recINGR1z01Fh1Z3A` | gpqa | não | sim | sim | JSON/contrato | A2 | 27.507 |
| `GPQA_diamond_recZt4x514UQNnsgy` | gpqa | não | não | sim | 5 tentativas de tarefa | B2 | 157.714 |
| `GPQA_diamond_recPzW1WqRnPs57D6` | gpqa | não | sim | sim | JSON/contrato | A2 | 12.617 |
| `GPQA_diamond_recqGD3fxPCI59vPQ` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 184.288 |
| `GPQA_diamond_recLAgwx9vbgB5EHk` | gpqa | não | sim | sim | Tempo de sessão | B1 | 190.812 |
| `GPQA_diamond_recdya6FuYraBU5Rh` | gpqa | não | sim | sim | 5 planos reprovados | A3 | 83.105 |
| `GPQA_diamond_rec2fsnzUuvNtUYK8` | gpqa | não | sim | sim | Saída final inválida | C3/avaliacao | 203.600 |
| `GPQA_diamond_recO3hvCWRGiG0odN` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 150.187 |
| `GPQA_diamond_recYCMJWH7IpcdqwE` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 138.863 |
| `GPQA_diamond_rec9W28HgpEUeUN8k` | gpqa | não | sim | sim | JSON/contrato | C2 | 138.237 |
| `GPQA_diamond_recBGxVySx1pkrO1i` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 125.330 |
| `GPQA_diamond_recXsYa3i2UhGF5fe` | gpqa | não | sim | sim | 5 tentativas de tarefa | B2 | 121.604 |
| `GPQA_diamond_recGee5m84dg5FZkc` | gpqa | não | sim | sim | JSON/contrato | B2 | 80.369 |
| `MMLU_college_mathematics_test_0098` | mmlu | não | sim | sim | JSON/contrato | A2 | 11.426 |
| `MMLU_high_school_macroeconomics_test_0007` | mmlu | não | não | sim | Saída final inválida | C3/avaliacao | 65.567 |
| `MMLU_college_mathematics_test_0093` | mmlu | não | sim | sim | Crédito do provedor | A1 | 0 |
| `BIOLOGIA_ENEM_2022_AZUL_Q133` | vestibular | não | sim | sim | JSON/contrato | B2 | 33.272 |
| `BIOLOGIA_ENEM_2024_AZUL_Q105` | vestibular | não | sim | sim | JSON/contrato | B2 | 31.483 |
| `FISICA_ENEM_2020_AZUL_Q114` | vestibular | sim | não | não | Falha somente da simples; Ralph correto | — | 74.208 |
| `GEOGRAFIA_ENEM_2024_AZUL_Q071` | vestibular | não | sim | sim | 5 tentativas de tarefa | B2 | 105.014 |
| `MATEMATICA_ENEM_2023_AZUL_Q138` | vestibular | não | sim | sim | 5 tentativas de tarefa | B2 | 100.712 |
| `MATEMATICA_ITA_2024_F1_UNICA_Q043` | vestibular | não | sim | sim | 5 tentativas de tarefa | B2 | 116.762 |
| `QUIMICA_ITA_2024_F1_UNICA_Q053` | vestibular | não | não | sim | 5 tentativas de tarefa | B2 | 111.938 |
| `QUIMICA_ITA_2025_F1_UNICA_Q035` | vestibular | não | sim | sim | 5 tentativas de tarefa | B2 | 105.048 |

## Apêndice C. Regras dos agrupamentos complementares

**Biológicas e saúde:** `BIOLOGIA`, `biology`, `college_biology`, `high_school_biology`, `anatomy`, `clinical_knowledge`, `college_medicine`, `human_aging`, `human_sexuality`, `medical_genetics`, `nutrition`, `professional_medicine`, `virology`.

**Exatas e tecnologia:** todas as matérias originalmente em “Exatas e biológicas (STEM)”, exceto as quatro matérias de Biologia listadas acima. Química permanece nesse agrupamento. A classificação é disciplinar por matéria, sem reclassificação manual de questões individuais.

**Humanas e sociais:** todas as matérias originalmente em “Humanidades” e “Ciências sociais”, exceto `human_sexuality`; acrescentam-se `business_ethics`, `management`, `marketing` e `professional_accounting`.

**Geral/interdisciplinar:** `global_facts` e `miscellaneous`.

Na harmonização por famílias, **Física** reúne `physics`, `FISICA`, `college_physics`, `high_school_physics` e `conceptual_physics`; **Química**, `chemistry`, `QUIMICA`, `college_chemistry` e `high_school_chemistry`; **Biologia estrita**, `BIOLOGIA`, `biology`, `college_biology` e `high_school_biology`; **Matemática e estatística**, `MATEMATICA`, `abstract_algebra`, `college_mathematics`, `elementary_mathematics`, `high_school_mathematics` e `high_school_statistics`. As quatro famílias não cobrem todos os 743 pares e não constituem uma divisão alternativa completa da amostra.

## Apêndice D. Cortes dos quartis e reprodução dos cálculos

A tabela lista os três cortes de tokens que separam Q1–Q4. O valor igual ao corte permanece no quartil inferior. Os cortes se referem a cada benchmark separadamente e são recalculados após o filtro, como no exportador original.

| Cenário | Conjunto | Fluxo | Corte Q1 | Corte Q2 | Corte Q3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Todos os pares | gpqa | simples | 582 | 729 | 986 |
| Todos os pares | gpqa | ralph | 58.188 | 76.415 | 113.500 |
| Todos os pares | mmlu | simples | 250 | 287 | 369 |
| Todos os pares | mmlu | ralph | 31.047 | 45.421 | 54.226 |
| Todos os pares | vestibular | simples | 544 | 619 | 763 |
| Todos os pares | vestibular | ralph | 36.701 | 51.127 | 64.738 |
| Sem falha | gpqa | simples | 562 | 725 | 960 |
| Sem falha | gpqa | ralph | 57.358 | 70.810 | 96.787 |
| Sem falha | mmlu | simples | 249 | 285 | 364 |
| Sem falha | mmlu | ralph | 31.307 | 45.421 | 54.226 |
| Sem falha | vestibular | simples | 544 | 617 | 747 |
| Sem falha | vestibular | ralph | 36.701 | 51.004 | 63.588 |

Os cálculos podem ser reproduzidos com Python 3, sem dependências externas, a partir do script [reproduzir_analise.py](reproduzir_analise.py):

```bash
python3 analise/reproduzir_analise.py --output /tmp/metricas-ralph.json
```

O script verifica unicidade dos pares, consistência entre alternativa e correção, exclusão exata dos pares com falha, igualdade dos demais campos entre os CSVs, correspondência dos 106 logs com os erros Ralph, consumo registrado e reconstrução dos quartis. Recalcula acurácias, diferenças, McNemar exato, intervalos de Wilson, intervalo aproximado da diferença pareada, custos, quantis, agrupamentos e taxonomia das falhas.

Para o intervalo aproximado da diferença, seja `D_i=R_i−S_i`, com valores −1, 0 ou +1; usa-se `média(D) ± 1,959964 × s(D)/√n`, com variância amostral de denominador `n−1`. Para o McNemar exato, com `b` regressões e `c` correções, usa-se `min(1; 2 × Σ[k=0..min(b,c)] C(b+c,k)/2^(b+c))`. Os números das tabelas foram calculados antes do arredondamento para duas casas; pequenas diferenças de apresentação em relação aos resumos originais decorrem do arredondamento.

As inspeções de casos utilizam as mensagens originais, não apenas os diagnósticos finais. Os hashes SHA-256 abaixo identificam as sete entradas da pasta `analise` usadas na análise.

| Arquivo de entrada | SHA-256 |
| --- | ---: |
| analise-benchmark-considera-erros.md | `e777f6a8cb6afd9aa6feae6927e75f402f70b8be7d0533af8cbc22a079a2f4d7` |
| analise-benchmark-desconsidera-erros.md | `811af9f0036f2ae86bc66b90c02421f9dead469e1e71a5ae136cc27184d32fe5` |
| analise-benchmark-questoes_considera-erros.csv | `489eaa79e46be89eb311e2db9fe1f1b8236b35f793bccf914c585b576c4d5944` |
| analise-benchmark-questoes_desconsidera-erros.csv | `d02722d16225d33495e06d23f2acb4d6b89f894d8a7c85d0c87914b85c825058` |
| benchmark-session-bench_9be03b85641c4b62bfa7cd81ebe62d03-ralph-loop-errors.zip | `fd7725a9d1738f1eaecff755a0cbbcd5f6431db93e6fc0accdaabcb92af53f34` |
| benchmark-session-bench_b72b883cb604496c917119d00e55d3b3-ralph-loop-errors.zip | `05f45b766455a239566a4dd17d25b4c7c5d9222b053eba07364d6a7d69acbf53` |
| benchmark-session-bench_c0b581509c944a10adde91d57d80ef7f-ralph-loop-errors.zip | `31d410a1610d45abd64488467731ecb7ed0ba67f3108adc6809d9bfdf6539bc4` |
