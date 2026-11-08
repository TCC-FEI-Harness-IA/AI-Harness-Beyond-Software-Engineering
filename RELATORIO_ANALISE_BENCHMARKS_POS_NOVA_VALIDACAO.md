# Avaliação dos benchmarks após a nova validação de planejamento e de tarefas

**Data:** 8 de novembro de 2026.  
**Material atualizado:** 25 questões, 75 JSONs e 394 invocações do modelo.  
**Comparação:** [análise anterior dos 13 erros](RELATORIO_ANALISE_ERROS_POS_MELHORIAS_THINKING.md), [proposta das duas frentes](feature/nova-fase-validacao/README.md) e relatórios de implementação [01](feature/nova-fase-validacao/RELATORIO_IMPLEMENTACAO_01.md) e [02](feature/nova-fase-validacao/RELATORIO_IMPLEMENTACAO_02.md).  
**Escopo:** análise das execuções existentes. A aplicação não foi alterada e não foram feitas novas inferências.

**Atualização do recorte:** as três pastas passaram a conter todos os erros do Ralph, incluindo os casos em que a inferência simples também errou. Foram preservadas as análises dos 15 casos iniciais e acrescentados dez casos: um de vestibulares, seis MMLU e três GPQA. Os totais e a interpretação comparativa abaixo consideram essa mudança de seleção.

## 1. Parecer

**As mudanças produziram ganhos observáveis de detecção e alguns avanços na resolução, mas os arquivos não demonstram melhora global de acurácia. A qualidade semântica dos validadores continua sendo o principal problema.**

A.3 efetivamente rejeita planos e B.2 efetivamente reprova por TECH, inclusive quando todos os critérios planejados foram atendidos. Isso é diferente do recorte anterior, em que quase todas as verificações locais aprovavam e a única reprovação cobrava apresentação. No entanto:

- Há planos incorretos aprovados por A.3, inclusive com omissão de dados decisivos.
- Há reprovações de A.3 que confundem investigar uma hipótese com antecipar sua conclusão, exigem trabalho excessivo ou admitem no próprio relatório que não existe defeito bloqueante.
- B.2 ainda chama de tecnicamente válidos cálculos que não satisfazem suas próprias equações e conclusões que apenas repetem premissas erradas do plano ou da memória.
- Quatro sessões terminam após cinco tentativas sem aprovação: duas propagam resultados anteriores incorretos; as duas acrescentadas nesta atualização repetem uma interpretação ou um conjunto de candidatos inadequados.
- Em um caso, C.1 identifica a alternativa do gabarito e C.3 emite outra letra.
- Há problemas de referência: além das unidades no item GPQA de neutrinos, um novo item MMLU de física marca como erro uma resposta fisicamente sustentada. Outros itens têm alternativas sobrepostas ou dependem de um recorte causal não explicitado.

O resultado é **uma melhora dos mecanismos de fiscalização, ainda sem conversão demonstrada em respostas finais melhores**. Mais reprovações não significam automaticamente melhor julgamento; uma resposta interrompida também continua contando como erro no benchmark.

A ampliação reforça o diagnóstico de autoconfirmação e acrescenta uma distinção essencial: **estes 25 registros são erros segundo a avaliação do benchmark; nem todos demonstram uma resolução tecnicamente errada, e os dez acrescentados não demonstram, por si, perda em relação à inferência simples.**

## 2. Fontes e limites da comparação

### 2.1. Exportações examinadas

| Exportação | Dataset identificado | Casos | Concluídos, divergentes do gabarito | Sem resposta | Chamadas | Tokens |
|---|---|---:|---:|---:|---:|---:|
| `bench_241f93fa34124e089ec7e2634500cd51` | MMLU | 8 | 8 | 0 | 81 | 251.621 |
| `bench_58a6f3c752ef4f63bccaff5bf210b47e` | Vestibulares | 5 | 4 | 1 | 88 | 405.911 |
| `bench_4abe71870570407face0283de4a524a4` | GPQA Main | 12 | 9 | 3 | 225 | 1.287.625 |
| **Total do recorte ampliado** | | **25** | **21** | **4** | **394** | **1.945.157** |

Os dez casos acrescentados representam 128 chamadas e 545.986 tokens: oito respostas finais divergentes do gabarito e duas interrupções. Os 15 IDs previamente analisados continuam presentes, somando as mesmas 266 chamadas e 1.399.171 tokens; a atualização amplia o material, sem evidência de nova execução desses casos.

Foram examinados enunciados, alternativas, gabaritos, resultados, critérios, relatórios, aprendizados, invocações, diagnósticos e prompts efetivamente enviados. Os índices `order` citados adiante são os de `session.messages`, iniciados em zero.

O checkout consultado está em `3fc64f3`, com alterações locais. Como os arquivos exportados não identificam o commit da execução, a evidência de quais regras foram usadas são os prompts persistidos, não a versão atual dos arquivos do workspace.

Os 12 itens GPQA foram confrontados com `Correct Answer` e `Explanation` do CSV `dataset/gpqa_main.csv`, no [ZIP local](apps/backend/src/infra/benchmark/gpqa/dataset.zip). A permutação de alternativas foi reproduzida na ordem completa do CSV, com `random.Random(0)`: **os 12 conjuntos de alternativas e gabaritos exportados coincidem com o provider**. Os três novos itens MMLU de física, identidade e complexidade também coincidem com o [arquivo local do dataset](apps/backend/src/infra/benchmark/mmlu/test.jsonl). As referências foram usadas somente nesta análise externa; coincidência com o dataset não comprova correção científica de todo gabarito.

### 2.2. As alterações realmente estavam em uso

Todas as sessões registram `flow_version = 2`, A.3 como validação do planejamento e A.4 como extração do enunciado. Os **77 relatórios locais válidos** avaliam TECH. Os prompts desses relatórios também contêm a correção posterior que manda reprovar um critério que imponha um resultado incompatível com os dados, em vez de dispensá-lo.

Modelo/provedor: `deepseek/deepseek-v4-flash-0731` / `open_router` em todas as sessões. Temperatura da sessão: `0.0`; 346 chamadas usam `0.0` e 48 usam `1.0`. O limite registrado é `max_tokens = 500000`, que, isoladamente, não comprova o teto efetivo do provedor. As 394 invocações terminaram com `finish_reason = stop`.

### 2.3. O que falta para avaliar o saldo global

Os arquivos contêm somente o braço Ralph dos casos exportados. Conforme informado pelo usuário, o recorte inicial de 15 casos selecionava “simples acerta e Ralph erra”; o ampliado contém todos os erros do Ralph, incluindo os casos em que ambos erraram. Não há nos JSONs as respostas simples nem seus indicadores de acerto. Portanto, a distinção entre o conjunto inicial e os dez acrescentados vem do histórico desta extração; o desfecho individual da inferência simples não pode ser auditado nestes arquivos. O [exportador atual](apps/backend/src/application/usecases/export_benchmark_ralph_errors_usecase.py) seleciona desfechos incorretos do Ralph sem testar `run.simple.is_correct`.

Também não foram encontrados os seis IDs de bateria, antigos e novos, no armazenamento JSON local consultado. Portanto, não foi possível verificar denominadores, amostras completas, pareamento dos braços, protocolo MMLU ou casos em que o Ralph acertou e a inferência simples errou.

**Não é válido comparar os 13 erros antigos com os 25 atuais como se fossem taxas de erro ou inferir piora pela ampliação de 15 para 25.** A seleção mudou. A ampliação permite estudar falhas compartilhadas pelos dois métodos, mas não revela acertos, denominadores ou ganhos líquidos do Ralph. Também não permite atribuir causalmente todos os erros restantes às duas novas frentes.

## 3. Comparação observável com o relatório anterior

| Indicador | Recorte antigo, antes da feature | Primeira análise após a feature | Atualização ampliada | Interpretação |
|---|---:|---:|---:|---|
| Questões exportadas | 13 | 15 | 25 | A última coluna inclui erros compartilhados com a inferência simples. |
| Concluídas com resposta divergente | 12 | 13 | 21 | Divergência do rótulo, inclusive nos itens que exigem auditoria. |
| Sem resposta | 1 | 2 | 4 | Antes: contrato de A.2; depois: `task_attempts` em B.2. |
| Planos candidatos avaliados por A.3 | Não existia | 25 | 38 | No ampliado: 25 aprovações e 13 reprovações em sete sessões. |
| B.2: aprovações / reprovações válidas | 25 / 1 | 41 / 12 | 55 / 22 | No ampliado, as reprovações se concentram em cinco sessões. |
| TECH: atendido / não atendido | Não existia | 43 / 10 | 57 / 20 | Duas reprovações de B.2 têm TECH atendido e critérios planejados pendentes. |
| C.1: aprovações / relatórios válidos | 12 / 12 | 13 / 13 | 21 / 21 | Nenhuma investigação adicional acionada nesses casos. |
| C.2 / revisões de resultados | 0 / 0 | 0 / 0 | 0 / 0 | Sem uso neste material. |
| Chamadas | 144 | 266 | 394 | Populações diferentes; não estima efeito causal da feature. |
| Tokens | 498.996 | 1.399.171 | 1.945.157 | Mesma ressalva. |
| Tokens médios por caso exportado | 38.384 | 93.278 | 77.806 | A redução da média na expansão também é efeito de composição, não ganho de eficiência comprovado. |

Houve 17 saídas recusadas por protocolo: sete em A.2, uma em A.3, três em B.1, quatro em B.2, uma em B.4 e uma em C.1. Elas foram recuperadas; nenhum dos quatro encerramentos sem resposta foi causado por esgotamento de correção estrutural. As quatro interrupções são `resource_limit`, limite `task_attempts`, na fase B.2.

### 3.1. Comparação dos oito IDs repetidos

| Questão | Antes | Agora | Avaliação |
|---|---|---|---|
| `MMLU_moral_scenarios_test_0622` | D; esperado C | D | O problema de hipótese favorável não sustentada permanece. |
| `MMLU_philosophy_test_0143` | D; esperado B | C | A atribuição a Parfit mudou, mas a verificação continua homologando uma posição divergente do gabarito. |
| `MMLU_moral_disputes_test_0107` | B; esperado C | B | Reaparece no recorte ampliado; a atribuição a Singer continua sendo reconstruída por plausibilidade. |
| `MMLU_sociology_test_0070` | D; esperado A | D | Reaparece no recorte ampliado; generalização entre autores continua sustentando a combinação. |
| `MMLU_virology_test_0032` | B; esperado D | B | Reaparece no recorte ampliado; o plano ainda define previamente o sentido de “principal”. |
| `GPQA_main_recIgdTGiUZLCejXx` | pH 7,08; esperado 6,89 | pH 6,97 | O modelo passou a considerar a água, mas a solução numérica continua errada. Ganho parcial claro. |
| `GPQA_main_reclLfdRGRmiI6CO5` | B; esperado C | B, após duas reprovações TECH | Há detecção, mas a retentativa não corrigiu a estrutura química errada. |
| `GPQA_main_recA1i5ZAh0Uzclxp` | D; esperado A | Sem resposta após cinco reprovações de T2 | A.3 retirou antecipação de resposta e B.2 bloqueou escolhas sem suporte; a premissa errada de T1 permaneceu. |

Nenhum desses oito IDs virou um acerto final segundo o gabarito nesta exportação. **Três deles estavam ausentes da primeira seleção de 15, mas continuam errados no conjunto ampliado.** Portanto, sua ausência anterior não demonstrava recuperação. Outros cinco IDs do relatório antigo continuam ausentes; sem confirmar execução e amostragem, isso também não comprova correção.

### 3.2. Inventário dos dez casos acrescentados

“Novo” nesta tabela significa ainda não examinado na primeira versão deste relatório. Singer, sociologia e virologia já eram conhecidos da análise anterior à feature.

| Questão | Gabarito → Ralph | Principal contribuição à análise | Detalhamento |
|---|---|---|---|
| `HISTORIA_ENEM_2022_AZUL_Q066` | C → sem resposta | A.3 censura operações interpretativas legítimas; cinco tentativas repetem E, sem revisar a exclusão de C. | §5.5 |
| `MMLU_high_school_physics_test_0034` | C → A | O gabarito contradiz a dinâmica no ponto mais alto; há resposta tecnicamente sustentada marcada como erro. | §6.3 |
| `MMLU_human_sexuality_test_0066` | B → D | Significado cotidiano de incerteza substitui uma definição de estágio do modelo usado pelo próprio solver. | §6.4 |
| `MMLU_machine_learning_test_0027` | C → D | Plano escolhe escopo e resposta; argumento exclui linearidade do conjunto dos polinômios. Item subespecificado. | §6.5 |
| `MMLU_moral_disputes_test_0107` | C → B | Afinidade com uma filosofia substitui confirmação de uma atribuição específica. | §6.6 |
| `MMLU_sociology_test_0070` | A → D | Associações amplas entre autores são aprovadas como suporte de todas as afirmações. | §6.7 |
| `MMLU_virology_test_0032` | D → B | “Mais geral” vira critério obrigatório sem ter sido solicitado. | §6.8 |
| `GPQA_main_rec1BjNQici8oD53a` | B → sem resposta | Objeção pertinente de B.2 não modifica o espaço de busca; variantes isotópicas são descartadas arbitrariamente. | §7.10 |
| `GPQA_main_recBeOYL2vJeESmQ5` | A → D | A.3 remove a letra antecipada, mas o mesmo enquadramento retorna após cinco tarefas. Há sobreposição factual entre as opções. | §7.11 |
| `GPQA_main_recftca7pyp2TCeAG` | A → D | A.2 fixa uma direção causal; a referência exige outra via, sem o enunciado explicitá-la. | §7.12 |

## 4. Ganhos e limitações por frente

### 4.1. Planejamento: A.3 funciona, mas também intervém incorretamente

Há uma intervenção útil no HBr: o primeiro plano já continha uma resolução extensa favorecendo D. A.3 a identifica como resultado antecipado e pede uma comparação aberta. Isso trata diretamente a classe de falha que motivou a feature.

Entretanto, A.3 também deixa passar omissões concretas, como os pedágios e a margem de lucro, e chega a **resolver ou dirigir a resolução** dentro de seu feedback. No PCR, uma reprovação menciona uma suposta “resposta correta C”; em outra parte do mesmo relatório declara que não existe defeito bloqueante e que nenhum ajuste é necessário. O sistema recebe `approved: false` com problemas textuais preenchidos e volta a A.2, conforme seu contrato estrutural; o problema é o conteúdo do julgamento.

Na sequência orgânica com HCl, A.3 exige investigar expansão de anel, depois reprova a investigação dessa hipótese como se mencioná-la já antecipasse o resultado. Também pede generalizações e possibilidades não necessárias ao pedido. A sequência chega a cinco candidatos antes da aprovação.

**O ganho esperado não era apenas acrescentar um parecer. Era impedir especificações erradas sem transformar a investigação em uma resolução feita pelo validador. Esse segundo requisito ainda falha.**

### 4.2. Validação técnica: TECH altera decisões, mas não assegura conferência real

No NMR, as duas primeiras reprovações mantêm todos os critérios planejados como atendidos e marcam somente TECH como não atendido. Portanto, a nova condição tem efeito independente e programaticamente correto.

Mas a terceira resposta volta a usar o mecanismo químico incorreto e é aprovada após mudanças na explicação. Em outras sessões, TECH aceita uma raiz descrita como “plausível”, uma quantidade de não gaussianidade negativa e inferências que ignoram a própria tabela de dados. A justificativa frequentemente explica por que o texto parece consistente, em vez de demonstrar a relação decisiva.

Duas das quatro sessões encerradas ilustram outro limite: B.2 encontra incompatibilidade na **última tarefa**, depois que resultados anteriores incorretos já foram aprovados. As retentativas reutilizam esses resultados na memória. Como a tarefa atual não consegue satisfazer suas exigências a partir deles, o loop repete a divergência até o limite. Nos dois novos encerramentos, há estagnação mesmo sem essa causa: nos gases, não se amplia a busca; em história, não se revisa a interpretação que descartou a resposta de referência.

Isso não é motivo para dispensar TECH ou aprovar uma alternativa só porque sua letra coincide com o gabarito. Nos dois casos orgânicos interrompidos houve tentativa que mencionou a letra esperada, mas a própria análise não sustentava o produto escolhido. Nos novos casos, B.2 também encontra objeções pertinentes à resposta apresentada. O ganho que falta é transformar essas objeções em investigação capaz de corrigir a premissa, não apenas repetir a rejeição.

## 5. Casos de vestibulares

### 5.1. Pedágios — uma condição fornecida desaparece do plano

**ID:** `FISICA_ENEM_2023_AZUL_Q124`. Esperado B, 42 minutos; Ralph C, 72. [Execução](benchmark-session-bench_58a6f3c752ef4f63bccaff5bf210b47e-ralph-loop-errors/questao-FISICA_ENEM_2023_AZUL_Q124/execucao-ralph-loop.json).

A.2 (`order=2`) planeja calcular apenas `480/100`, `480/80` e a diferença, embora somente o caminhão tenha cobrança automática. Não inclui os dez pedágios de três minutos do carro. A.3 aprova (`order=3`). Os cálculos locais são feitos corretamente para essa especificação incompleta e todos recebem TECH atendido.

A conta pertinente é `360 − (288 + 10×3) = 42 minutos`. Não falta conhecimento especializado; falta preservar uma condição expressa. A.4 conserva os dados dos pedágios e o fato de que somente o caminhão tem cobrança automática, mas isso não faz o plano ou os validadores retomarem a condição. É uma falha direta de cobertura/fidelidade de A.3, seguida de validação restrita à receita recebida.

### 5.2. Torneio — condições verificadas isoladamente se perdem na junção

**ID:** `MATEMATICA_ENEM_2022_AZUL_Q140`. Esperado B, 25 dias; Ralph A, 22. [Execução](benchmark-session-bench_58a6f3c752ef4f63bccaff5bf210b47e-ralph-loop-errors/questao-MATEMATICA_ENEM_2022_AZUL_Q140/execucao-ralph-loop.json).

O plano aprovado tem seis tarefas. T2 reconhece sete partidas para a finalista e descanso entre quaisquer jogos, inclusive na transição grupos→oitavas; isso permanece nos aprendizados (`order=15`). Mas A.2 já exige que as eliminatórias comecem no dia seguinte ao fim dos grupos, e T5-AC2 fixa essa condição.

T3 obtém grupos nos dias 1, 5 e 9; T4 obtém 13 dias para as eliminatórias. T5 soma `9+13=22` e começa as oitavas no dia 10 (`order=29`). B.2 aprova (`order=30`), apesar do intervalo insuficiente após o jogo do dia 9.

Um cronograma compatível é `1, 5, 9, 13, 17, 21, 25`. O erro não é a contagem interna de cada fase: é a condição da fronteira entre elas. A.3 aprovou um critério que impunha uma junção inválida, e TECH não conferiu a condição disponível na memória.

### 5.3. Casa de shows — contribuição ao lucro confundida com faturamento

**ID:** `MATEMATICA_ENEM_2024_AZUL_Q143`. Esperado D, R$ 52,00; Ralph C, R$ 34,00 por proximidade de R$ 31,20. [Execução](benchmark-session-bench_58a6f3c752ef4f63bccaff5bf210b47e-ralph-loop-errors/questao-MATEMATICA_ENEM_2024_AZUL_Q143/execucao-ralph-loop.json).

A.2 prescreve que `custo + lucro desejado − ingressos` seja a receita de bebidas e petiscos e manda dividi-la por 500. A condição de 60% de lucro nas vendas não entra na receita planejada. A.3 aprova.

Os ingressos rendem R$ 35.750; descontado o custo de produção de R$ 34.350, já há R$ 1.400 de lucro. Faltam R$ 15.600 de **lucro** nas vendas. No modelo de 60% adotado pelo item, `0,60 × 500 × gasto = 15.600`, resultando em R$ 52. O Ralph trata os R$ 15.600 como faturamento e obtém R$ 31,20.

TECH aprova a conta e a opção mais próxima (`order=13`). Isso mostra a persistência do problema anterior: a comparação por proximidade encobre uma condição omitida na modelagem. A distinção necessária é entre grandezas e suas relações, não uma proibição geral de aproximações.

### 5.4. Geografia — o plano estreita o objeto da pergunta

**ID:** `GEOGRAFIA_ENEM_2022_AZUL_Q064`. Esperado A, solos vulcânicos; Ralph C, relevos escarpados. [Execução](benchmark-session-bench_58a6f3c752ef4f63bccaff5bf210b47e-ralph-loop-errors/questao-GEOGRAFIA_ENEM_2022_AZUL_Q064/execucao-ralph-loop.json).

O plano reformula a investigação como formação do relevo, destacando soerguimento + erosão (`order=2`). O solver admite que o intemperismo participa da formação dos solos vulcânicos, mas os rejeita por não serem propriamente uma forma de relevo. Para aceitar escarpas, passa a falar das condições favoráveis dos vales e sopés associados, mudando o referente da alternativa (`order=7`).

B.2 repete a exclusão de solos como processo primariamente interno e aprova TECH (`order=8`). A.3 não antecipou uma letra, mas aprovou uma restrição conceitual que favoreceu a leitura errada. Não foi um problema de formato da resposta.

### 5.5. História da educação feminina — interpretação legítima censurada e retentativa estagnada

**Novo nesta atualização. ID:** `HISTORIA_ENEM_2022_AZUL_Q066`. Esperado C, dominação de corpos e igualdade humana; sem resposta, após cinco reprovações de T2. Foram 22 chamadas e 124.908 tokens. [Execução](benchmark-session-bench_58a6f3c752ef4f63bccaff5bf210b47e-ralph-loop-errors/questao-HISTORIA_ENEM_2022_AZUL_Q066/execucao-ralph-loop.json).

A.3 rejeita dois candidatos. No primeiro parecer (`order=3`), considera antecipação exigir que os termos sejam associados respectivamente ao Texto I e ao Texto II. No segundo (`order=5`), censura pedir que a tarefa formule a oposição conceitual e identifique seus polos: afirma que isso já imporia uma interpretação, embora o critério pedisse produzir a interpretação na execução. O plano aprovado volta a exigir o mapeamento na mesma ordem (`orders=6–7`). Há aplicação instável da regra de neutralidade: **pedir para identificar uma oposição não equivale a determinar previamente qual ela será**.

Na resolução de T2 (`order=17`), B.1 reconhece restrição educacional por suposta incapacidade de um lado e igualdade de acesso do outro. Rejeita C porque “dominação de corpos” não seria controle intelectual e “igualdade humana” seria ampla demais. Escolhe E, apesar de reconhecer que “participação política” não corresponde ao segundo discurso. B.2 reprova por falta de suporte para E (`order=18`), mas marca como atendida a comparação que descartou C. As quatro tentativas seguintes repetem a mesma escolha e a mesma exclusão (`orders=19–26`).

O ponto conceitual perdido é que uma categoria pode descrever a regulação social do acesso das mulheres à educação, sem aparecer literalmente no trecho nem se limitar a coerção física. A resposta de referência contrapõe essa subordinação à igualdade; a justificativa para E substitui igualdade educacional por participação política sem estabelecer o vínculo.

**Leitura da intervenção:** não há uma resposta C fundamentada rejeitada nestas cinco tentativas. B.2 bloqueia E por uma razão pertinente, mas não leva B.1 a reconsiderar sua exclusão inicial de C. O plano aprovado já permitia equivalência conceitual; portanto, o problema não se resolve apenas acrescentando essa permissão ao prompt. Este caso amplia a evidência de literalismo seletivo, falsa objeção de neutralidade e feedback sem mudança efetiva da análise.

## 6. Casos MMLU

### 6.1. Cenários morais — hipóteses convenientes continuam sendo tratadas como suporte

**ID:** `MMLU_moral_scenarios_test_0622`. Esperado C; Ralph D, repetindo o erro anterior. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_moral_scenarios_test_0622/execucao-ralph-loop.json).

A.2 sugere que a abelha pode ter ido embora, que a oferta não obriga a irmã a beber e que ela pode ser inofensiva (`order=2`). B.1 transforma a ausência de relato de mentira ou coerção em justificativa para “Not wrong” (`order=12`). B.2 chama essas hipóteses de consistentes com a descrição e aprova TECH (`order=13`).

A nova regra sobre hipóteses está presente, mas o validador não distingue possibilidade concebível de suporte suficiente para a interpretação preferida. A integração das duas classificações funciona corretamente; a discordância com o gabarito nasce antes dela. Trata-se de julgamento interpretativo: não foi feita uma validação empírica independente dos padrões morais do dataset.

### 6.2. Parfit — aparência de fonte continua substituindo confirmação

**ID:** `MMLU_philosophy_test_0143`. Esperado B; antes D, agora C. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_philosophy_test_0143/execucao-ralph-loop.json).

O plano é aberto e pede evidência da posição de Parfit. B.1 escolhe a comparação somente intrapessoal e apresenta trechos atribuídos a livros e páginas, rotulados como paráfrases (`order=7`). Não houve consulta a essas fontes no fluxo. B.2 descreve o material como citações diretas e considera a atribuição sustentada, inclusive em TECH (`order=8`).

A resposta mudou, mas o mecanismo de autoconfirmação é o mesmo do relatório anterior. O diagnóstico demonstrável é a aceitação de referências produzidas pelo próprio solver como se fossem confirmação independente. A autenticidade de cada passagem não foi auditada bibliograficamente nesta análise.

### 6.3. Física — resposta sustentada marcada como erro pelo gabarito

**Novo nesta atualização. ID:** `MMLU_high_school_physics_test_0034`. Esperado C, I e II; Ralph A, somente I. Foram 12 chamadas e 40.636 tokens. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_high_school_physics_test_0034/execucao-ralph-loop.json).

O item pergunta sobre uma bola lançada verticalmente, com resistência do ar: I, velocidade nula no ponto mais alto; II, aceleração nula nesse ponto; III, subida mais demorada que descida. B.1 identifica I como verdadeira e II/III como falsas; T2 associa isso a A. B.2 aprova ambas as tarefas (`orders=7–8/12–13`), e C.3 preserva A.

No modelo usual de ar parado e arrasto dependente da velocidade, no ponto mais alto `v=0`, logo o arrasto se anula e a gravidade continua atuando: `a=-g`, não zero. Na subida, o arrasto soma-se ao peso; na descida, opõe-se a ele. Assim, a afirmação III também é falsa. A relação entre arrasto e velocidade usada nesta conferência está descrita no [OpenStax, seção 6.4](https://openstax.org/books/university-physics-volume-1/pages/6-4-drag-force-and-terminal-speed); a conclusão para este item é a aplicação dessas forças ao enunciado.

O [registro MMLU local](apps/backend/src/infra/benchmark/mmlu/test.jsonl) traz `answer: 2`, isto é, C. Portanto, a divergência não nasce de uma troca de letras na exportação: **há inconsistência do rótulo com a física do item, e a resposta A do Ralph está sustentada**. O plano ainda prescreve que II seja falsa antes da execução, o que merece avaliação de neutralidade de A.3; essa irregularidade do planejamento não transforma a resolução correta em erro científico.

Este caso não deve orientar o harness a imitar C. Na avaliação, deve ser sinalizado separadamente, mantendo também o resultado bruto do benchmark.

### 6.4. Modelo de identidade — incerteza cotidiana substitui definição técnica

**Novo nesta atualização. ID:** `MMLU_human_sexuality_test_0066`. Esperado B, tolerance stage; Ralph D, confusion stage. Foram nove chamadas e 26.775 tokens. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_human_sexuality_test_0066/execucao-ralph-loop.json).

A pergunta usa a expressão “thinks that she probably is a lesbian”. A.2 já a enquadra como suspeita inicial. B.1 identifica as opções como estágios do modelo de Cass e define tolerance como reconhecer que se é provavelmente homossexual. Mesmo assim, elimina esse estágio por exigir algo além de “probably” e escolhe confusion, apelando à incerteza cotidiana da palavra (`order=7`). B.2 aprova TECH (`order=8`).

O gabarito B é compatível com a definição de tolerance fornecida pelo próprio solver; a eliminação não demonstra a diferença que alega. Trata-se de uma classificação dentro de um modelo teórico específico, não de uma dedução a partir do significado comum de “confusão”. A [publicação original de Cass](https://pubmed.ncbi.nlm.nih.gov/264126/) apresenta o modelo de seis estágios; isso não autoriza tratar seus estágios como descrição universal de trajetórias individuais.

**Falha generalizável:** o fluxo nomeia uma taxonomia, mas valida o resultado por intuição linguística, sem conferir se a característica observada satisfaz a definição que ele próprio adotou. A.3 não remove o enquadramento inicial; TECH não percebe a inconsistência entre definição e exclusão.

### 6.5. Gradiente descendente — escopo inventado e categorias sobrepostas

**Novo nesta atualização. ID:** `MMLU_machine_learning_test_0027`. Esperado C, polynomial in D; Ralph D, dependência do número de iterações. Foram nove chamadas e 25.773 tokens. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_machine_learning_test_0027/execucao-ralph-loop.json).

O enunciado limita-se a “Computational complexity of Gradient descent is”, sem definir N, D, função objetivo, variante do método ou se pergunta por iteração ou pelo custo total. A.2 introduz full-batch, N amostras e D dimensões, fixa `O(ND)` por passo e `O(TND)` no total e já favorece D. A.3 aprova (`orders=2–3`).

B.1 segue esse modelo e descarta C alegando que a dependência em D é linear, “não polinomial de grau maior” (`order=7`). Isso acrescenta a C uma condição ausente: **uma função linear é polinomial de grau um**. Além disso, D também omite N e D, embora a omissão de fatores seja usada para descartar as demais opções. B.2 aprova a comparação e TECH (`order=8`).

Há dois problemas distintos. O fluxo não justificou o escopo que introduziu e usa uma eliminação matematicamente inválida. Ao mesmo tempo, o item é subespecificado e as descrições se sobrepõem; o gabarito C, isoladamente, não demonstra que D seja falsa sob toda interpretação. O diagnóstico sólido é o fundamento inválido da exclusão e a conclusão antecipada no plano, não uma regra de que toda pergunta de complexidade deva receber “polinomial”.

### 6.6. Singer — reconstrução plausível continua substituindo atribuição

**Acrescentado nesta atualização, já conhecido antes da feature. ID:** `MMLU_moral_disputes_test_0107`. Esperado C, loteria; Ralph B, obrigatoriedade para todos os recém-nascidos, repetindo a resposta antiga. Foram nove chamadas e 26.198 tokens. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_moral_disputes_test_0107/execucao-ralph-loop.json).

B.1 deduz que Singer preferiria universalizar os benefícios para evitar desigualdade e transforma essa ideia em obrigação de engenharia genética para todos. Descarta a loteria porque ela ainda deixaria alguns sem acesso (`order=7`). B.2 considera essa reconstrução suficiente para TECH (`order=8`); não há confirmação de uma passagem que estabeleça o que o autor propôs.

O pedido é de atribuição, e não de escolher uma política que pareça coerente com o utilitarismo. A passagem de “disponibilizar a todos” para “exigir para todos” também acrescenta uma obrigação que não decorre automaticamente da primeira afirmação. Não foi feita auditoria bibliográfica integral de Singer nesta análise; a evidência é que o fluxo **não verifica a atribuição decisiva** e mantém a divergência já mapeada. A nova validação não modificou esse mecanismo neste caso.

### 6.7. Sociologia — amplitude de associações vira evidência para uma combinação

**Acrescentado nesta atualização, já conhecido antes da feature. ID:** `MMLU_sociology_test_0070`. Esperado A, imagens superficiais e fragmentadas; Ralph D, todas as anteriores, repetindo o resultado antigo. Foram nove chamadas e 27.424 tokens. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_sociology_test_0070/execucao-ralph-loop.json).

A.2 sugere associações a Baudrillard e Lyotard. B.1 aceita, além da afirmação A, que nenhuma teoria seria melhor que outra e que a mudança social exigiria novas teorias. Reconhece que a afirmação “anything goes” exige nuance, mas a vincula a Feyerabend e considera a afinidade com o pós-modernismo suficiente para a combinação (`order=7`). B.2 aprova TECH e todas as afirmações (`order=8`).

O salto observável é de afinidade ou associação entre ideias para atribuição integral da proposição ao grupo indicado. Uma ressalva sobre nuance não valida automaticamente uma afirmação absoluta. O relatório não presume que todas essas posições filosóficas tenham interpretação única; identifica que o fluxo não estabelece o suporte mais preciso necessário para sua conclusão combinada. O erro segundo o gabarito continua sendo homologado sem investigação adicional.

### 6.8. Virologia — “principal” é redefinido pelo planejador

**Acrescentado nesta atualização, já conhecido antes da feature. ID:** `MMLU_virology_test_0032`. Esperado D, identificar rapidamente novos vírus; Ralph B, identificar variação genética, repetindo o resultado antigo. Foram nove chamadas e 25.701 tokens. [Execução](benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors/questao-MMLU_virology_test_0032/execucao-ralph-loop.json).

A.2 exige interpretar o uso principal do sequenciamento como sua função direta e mais geral e orienta a justificativa para variação genética (`order=2`). A.3 aprova. B.1 reconhece que identificar novos vírus é uma aplicação possível, mas a descarta por ser especializada e requerer bioinformática; prefere B por ser mais geral (`order=7`). B.2 aprova esse critério e TECH (`order=8`).

O problema não é provar que sequenciamento não detecta variação genética. É que **“principal” virou “mais geral e menos dependente de etapas adicionais” sem essa definição ter sido fornecida**. Essa escolha determina a resposta antes de a execução comparar a finalidade no contexto do pedido. Como as opções descrevem aplicações reais ou plausíveis em níveis diferentes, a unicidade do gabarito também pede contexto; não foi auditada uma fonte didática específica do item.

O caso confirma a persistência da falha original de planejamento: retirar uma letra antecipada não basta quando o critério que favorece aquela resposta continua imposto.

## 7. Casos GPQA

### 7.1. Ácido bórico — modelo melhor, conta ainda errada

**ID:** `GPQA_main_recIgdTGiUZLCejXx`. Esperado D, 6,89; antes C, 7,08; agora B, 6,97. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recIgdTGiUZLCejXx/execucao-ralph-loop.json).

O plano agora inclui equilíbrio ácido, água e eletroneutralidade. Isso corrige a omissão central anterior. B.1 chega à equação correta, mas afirma que a raiz é `h = 1,07×10⁻⁷ M` (`order=8`). B.2 a aceita como raiz “plausível” (`order=9`).

Conferir a própria equação já revela o erro: com esse `h`, `Kw/h + Ka·C/(Ka+h) ≈ 1,58453×10⁻⁷ M`, diferente de `h`. A raiz positiva é aproximadamente `1,30240×10⁻⁷ M`, com pH `6,88525`, compatível com D.

**Ganho parcial:** melhor modelagem. **Pendência:** verificar a solução alegada por substituição, em vez de aceitar a afirmação de que um método numérico foi usado.

### 7.2. HBr — o alerta melhora, mas uma premissa aprovada bloqueia a conclusão

**ID:** `GPQA_main_recA1i5ZAh0Uzclxp`. Esperado A; antes D; agora sem resposta, após cinco reprovações de T2. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recA1i5ZAh0Uzclxp/execucao-ralph-loop.json).

A.3 remove do plano uma resolução que favorecia D (`order=3`). Porém, T1 volta a produzir uma enumeração mecanística errada e a guarda como aprendizado (`orders=9–12`), rejeitando a rota que produziria um dos componentes de A.

Na primeira tentativa de T2, o solver escolhe A por melhor ajuste, mas diz que nenhum par tem dois produtos sustentados. B.2 reprova essa inconsistência (`order=15`). Nas seguintes, o solver passa a escolher D ou a reiterar que nenhum par é sustentado; a base de T1 não é corrigida. A sessão encerra com 19 chamadas e 138.752 tokens.

As cinco reprovações TECH efetivamente bloqueiam seleção sem suporte na análise apresentada. Isso é um ganho de fiscalização, mas não resolve a química. A referência local explica as duas rotas por participação aromática e rearranjo; é essa premissa anterior que permanece incorreta.

### 7.3. Sequência com HCl — A.3 amplia a investigação e B.2 encontra o problema tarde

**ID:** `GPQA_main_recQSmIQF2OGPfbL8`. Esperado C; sem resposta. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recQSmIQF2OGPfbL8/execucao-ralph-loop.json).

São cinco candidatos, quatro reprovações semânticas e recuperações estruturais. A.3 primeiro exige investigar expansão de anel e depois censura a presença dessa investigação. Uma reprovação chega a interpretar “sem pressupor expansão” como uma antecipação de expansão (`order=10`). Outra declara ambígua a conexão indicada pelo nome, que T1 posteriormente resolve como inequívoca (`orders=12/21`).

Após aprovação, T2 exclui o rearranjo da primeira reação; T3 acrescenta uma análise incorreta dos hidrogênios β; T4/T5 propagam um conjunto de produtos diferente do da referência. Só em T6 a incompatibilidade com todas as opções fica explícita.

Há tentativas que mencionam C, mas afirmam que sua estrutura não corresponde ao produto derivado. B.2 as reprova; em duas avaliações, TECH é atendido, mas um critério planejado continua pendente. A distinção entre validade técnica local e aprovação completa está funcionando. Contudo, T6 repete a mesma incompatibilidade, sem corrigir T2–T5.

A sessão consome **41 chamadas e 307.594 tokens**, encerrando por `task_attempts`, não por falta de tokens. O problema é a qualidade da cadeia anterior e a investigação desproporcional, não um teto de três tentativas que ainda precisasse ser elevado.

### 7.4. NMR/titanoceno — duas reprovações não produzem correção do mecanismo

**ID:** `GPQA_main_reclLfdRGRmiI6CO5`. Esperado C; antes e agora B. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_reclLfdRGRmiI6CO5/execucao-ralph-loop.json).

B.2 reprova primeiro uma inconsistência na justificativa dos acoplamentos (`order=8`) e depois uma sequência mecanística sem suporte (`order=10`), mantendo os critérios planejados atendidos e TECH não atendido.

Na terceira tentativa, a resolução muda a redação, mas conserva a formação de um ciclopropano e os duplos dupletos; B.2 aprova (`orders=11/12`). A referência local descreve uma ciclobutanona e dois hidrogênios que se acoplam entre si, produzindo dois dupletos.

Há ganho na capacidade de interromper, mas o feedback não assegurou que o defeito apontado fosse removido. A aprovação posterior não demonstra que a segunda objeção foi resolvida.

### 7.5. Gato de Schrödinger — plano aprovado inverte uma definição fornecida

**ID:** `GPQA_main_rec9W28HgpEUeUN8k`. Esperado B, 1,38; Ralph C, 0, por proximidade de uma quantidade negativa. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_rec9W28HgpEUeUN8k/execucao-ralph-loop.json).

A.3 pede verificar a referência gaussiana. O plano revisado, porém, prescreve `δ = S(ρ) − S(τ)` (`order=4`), invertendo o sinal da definição fornecida. A.3 o aprova. T1 diagonaliza uma representação em base não ortogonal como se fosse ortonormal e depois usa autovalores cuja soma não é 1. T2 propaga momentos incorretos. T3 calcula `δ ≈ −0,1854`; TECH e C.1 aprovam (`orders=20/23`).

Para a definição de entropia relativa, a relação é `δ = S(τ) − S(ρ) ≥ 0`. O estado dado é puro; a conferência externa obtém aproximadamente `1,38633`, compatível com B. A relação e a não negatividade estão nas equações 33–35 de [Genoni e Paris](https://arxiv.org/html/1008.4243#S4.SS2).

O alerta necessário é a violação de uma definição e de condições básicas dos objetos calculados, antes de qualquer escolha por proximidade. A explicação textual do dataset também troca os termos ao dizer qual deles seria zero; por isso a conferência usou a fonte primária e o cálculo, além do gabarito.

### 7.6. PCR — A.3 confunde uma conclusão a investigar com uma resposta antecipada

**ID:** `GPQA_main_reciHTTRFPWrbhWXA`. Esperado B; Ralph C. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_reciHTTRFPWrbhWXA/execucao-ralph-loop.json).

O primeiro plano pede **determinar se** é preciso repetir o experimento/redesenhar primers. A.3 considera que isso já antecipa essa conclusão (`order=5`), embora o critério deixe o resultado aberto. No relatório seguinte, A.3 rejeita o plano, menciona uma suposta resposta C e declara que os problemas não são bloqueantes e não precisam de ajuste (`order=7`).

O plano final mantém uma investigação enviesada em torno de dois produtos observados a 600/40 bp. B.1 passa a chamar esses tamanhos de esperados e interpreta os picos próximos de 600 como o mesmo produto dividido; B.2 aprova a hipótese como suporte suficiente. A referência distingue os dois produtos próximos de 600 da banda de 40 bp, atribuída a dímeros de primers, e pede otimização.

Este caso evidencia tanto falsa reprovação de planejamento quanto inferência técnica não conferida. A interpretação sobre dímeros pertence à avaliação externa; não deve virar uma regra especializada do harness.

### 7.7. Sinalização celular — hipótese errada do plano prevalece sobre a tabela

**ID:** `GPQA_main_recm7S5Gq7FWCgaHZ`. Esperado C; Ralph D. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recm7S5Gq7FWCgaHZ/execucao-ralph-loop.json).

A.2 prescreve que Rapalink-1 inibe mTORC1 e mTORC2 e cria faixas de classificação dos sinais (`order=2`). A.3 aprova. T2 admite que o sinal usado para mTORC2 está elevado, mas preserva a inibição com base no alvo atribuído à droga; a própria nota posterior diz que o sinal elevado não indica essa inibição (`order=12`). TECH aprova a interpretação (`order=13`).

As classificações erradas são reutilizadas até concluir que mTORC1+mTORC2 explicam o efeito. A referência local distingue inibição parcial/completa de mTORC1 e compara condições pareadas, sustentando AKT+mTORC1.

Não houve perda da tabela: ela foi conservada. O erro foi converter conhecimento presumido do plano em autoridade e explicar os dados contrários em favor dessa presunção. O padrão é semelhante ao qPCR do relatório anterior, embora o ID seja outro.

### 7.8. Butadieno — erro de referente no plano e troca de letra em C.3

**ID:** `GPQA_main_recXlt6DeL8i1eeTO`. Esperado A; Ralph C. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recXlt6DeL8i1eeTO/execucao-ralph-loop.json).

A pergunta menciona o estado π ocupado de menor energia. A.2 troca esse referente pelo HOMO, o ocupado de maior energia (`order=2`), sem que A.3 detecte a mudança. B.1/B.2 incluem justificativas orbitais problemáticas, mas produzem o par textual `s-trans, s-cis`.

**C.1 identifica expressamente A e registra que C.3 pode escrever `FINAL_ANSWER: A`** (`order=11`). C.3 preserva esse par no texto e encerra com `FINAL_ANSWER: C` (`order=12`), que corresponde a outro par nas alternativas originais.

Esse caso não deve ser atribuído somente à decisão técnica de B.2: a apresentação final introduz um erro suficiente para perder o acerto indicado em C.1. Corrigir a letra preservaria o gabarito, mas não validaria retroativamente as justificativas orbitais nem a troca de referente.

### 7.9. Neutrinos — inconsistência do item e erro na estratégia de melhor ajuste

**ID:** `GPQA_main_recxWirvTOyWz2zja`. Gabarito D, 35; Ralph C, 14. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recxWirvTOyWz2zja/execucao-ralph-loop.json).

O enunciado fornece `ρ ≈ 8 g/cm²`, unidade de massa por área. A.3 primeiro exige preservar essa interpretação e depois reprova a prescrição que havia sugerido, pedindo investigar as duas leituras (`orders=3/6`). O plano final deixa essa escolha para a execução. T1 calcula as duas possibilidades e termina adotando a unidade literal.

A conferência externa encontra um problema no próprio item:

| Leitura | Resultado aproximado |
|---|---:|
| `8 g/cm²` literalmente, como massa por área | `3,37×10⁻⁶` interações |
| `8 g/cm³`, assumindo erro na unidade, com `10465 km = 1,0465×10⁹ cm` | `3,53×10³` interações |
| Expressão numérica da referência, usando `10465×10³` com as demais grandezas em centímetros | `35,30` interações |

Ou seja: recuperar 35 também exige misturar metros e centímetros na expressão de referência. **Este não é um caso limpo em que os dados físicos fornecidos sustentem o gabarito.**

Isso não torna correta a seleção de 14 por proximidade de `3,37×10⁻⁶`: ela não é uma aproximação sustentada. É necessário separar o defeito do benchmark, a oscilação do feedback de A.3 e a escolha final sem suporte. Nenhuma dessas observações autoriza alterar unidades ou fórmulas em produção para imitar o gabarito.

### 7.10. Gases — o feedback sugere outra família de candidatos, mas a busca não muda

**Novo nesta atualização. ID:** `GPQA_main_rec1BjNQici8oD53a`. Esperado B, intervalo 260–280; sem resposta, após cinco reprovações de T1. Foram 15 chamadas e 108.974 tokens. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_rec1BjNQici8oD53a/execucao-ralph-loop.json).

A densidade relativa ao argônio exige massas molares próximas de 19,974 g/mol, com tolerância de 2%. B.1 examina muitos gases comuns, encontra NH₃ e CH₄ para as propriedades qualitativas, reconhece desvios de 14,73% e 19,68% na massa e tenta dispensar a tolerância. B.2 reprova a incompatibilidade (`orders=7–8`).

No segundo parecer, B.2 inclusive questiona a exclusão de variantes isotópicas (`order=10`). A tentativa seguinte as exclui explicitamente por não serem “standard compounds” (`order=11`), restrição que não existe no enunciado. As tentativas posteriores voltam a declarar que os dados são inconsistentes e a escolher NH₃/CH₄; todas reprovam. **O feedback chegou ao contexto da retentativa, mas não produziu a revisão da hipótese que bloqueava a solução.**

A referência oficial identifica amônia deuterada ND₃ e metano deuterado CD₄. Deutério é um isótopo do hidrogênio, de modo que continuam sendo três elementos: N, C e H, com C e N em grupos adjacentes. As massas de aproximadamente 20,049 e 20,067 g/mol satisfazem a tolerância. A existência dessas espécies é confirmada pelos registros do NIST para [ND₃](https://webbook.nist.gov/cgi/cbook.cgi?ID=C84796145&Plot=on&Type=JANAFG) e [CD₄](https://cccbdb.nist.gov/exp2x.asp?casno=558203&charge=0).

Com coeficientes inteiros mínimos e massas arredondadas como na explicação do dataset:

```text
4 ND3 + 3 O2 → 2 N2 + 6 D2O     soma dos produtos: 56 + 120 = 176
  CD4 + 2 O2 →   CO2 + 2 D2O    soma dos produtos: 44 +  40 =  84
Total: 260 → intervalo B
```

Aqui a referência oferece uma solução consistente; não cabe classificar o item como impossível só porque os candidatos usuais falharam. A rejeição da resposta que viola 2% é pertinente. A falha restante é de exploração: uma preferência pelo habitual é tratada como limite do problema, e cinco tentativas reformulam a mesma impossibilidade não demonstrada. Não há resultado anterior aprovado responsável por esse bloqueio: ele ocorre já na primeira tarefa.

### 7.11. Plasmídeos — retirar a letra do plano não retira seu enquadramento

**Novo nesta atualização. ID:** `GPQA_main_recBeOYL2vJeESmQ5`. Esperado A, dificuldade de remover pUC18 por seu alto número de cópias; Ralph D, compatibilidade e coexistência dos plasmídeos. Foram 25 chamadas e 114.295 tokens. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recBeOYL2vJeESmQ5/execucao-ralph-loop.json).

A.3 corretamente identifica que o primeiro plano já declara D como resposta (`order=4`). O segundo candidato é aprovado e expande a questão em cinco tarefas: fatos, compatibilidade, perda sem seleção, seleção por tetraciclina e comparação final (`orders=5–6`). A nova versão não prescreve a letra, mas ainda fornece boa parte das conclusões biológicas nas descrições. O esforço adicional não muda a seleção original.

Na tarefa final, B.1 reconhece que A descreve um obstáculo real e que o alto número de cópias dificulta a perda. Prefere D por considerar a compatibilidade o fator “decisivo” e A “incompleta”, em parte por não oferecer um método (`order=30`). Essa exigência é assimétrica: D também não descreve um procedimento para remover o plasmídeo. B.2 aprova os cinco resultados, incluindo TECH da comparação final (`order=32`).

A explicação do dataset enfatiza que, embora a seleção `+Tet/−Amp` permita obter o segundo plasmídeo, a raridade da perda do pUC18 obriga a examinar muitos sobreviventes. O [guia da Addgene sobre origens de replicação](https://blog.addgene.org/plasmid-101-origin-of-replication) confirma tanto o alto número de cópias de pUC quanto os grupos distintos de pUC e pACYC. Logo, há conteúdo factual pertinente nos dois argumentos. Compatibilidade permite coexistência; isso, sozinho, não estabelece uma hierarquia universal entre as explicações A e D.

**Limite da conclusão:** o registro mostra divergência da referência e escolha sustentada por um critério de prioridade não demonstrado. Não demonstra que toda a biologia apresentada em D seja falsa. Este é um caso para auditar sobreposição entre respostas e pertinência da justificativa, além de medir a proporcionalidade do plano: 25 chamadas mantiveram o enquadramento que já aparecia no primeiro candidato.

### 7.12. PKC — direção causal fixada e referência dependente de uma via particular

**Novo nesta atualização. ID:** `GPQA_main_recftca7pyp2TCeAG`. Esperado A, disfunção endotelial → estresse oxidativo; Ralph D, ordem inversa. Foram nove chamadas e 25.302 tokens. [Execução](benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors/questao-GPQA_main_recftca7pyp2TCeAG/execucao-ralph-loop.json).

A.2 já manda usar a sequência hiperglicemia → PKC → estresse oxidativo → disfunção endotelial. A.3 aprova (`orders=2–3`). B.1 repete essa sequência e elimina A por inverter a causalidade (`order=7`). B.2 chama a cadeia de conhecimento estabelecido, fornecido pela tarefa, e aprova TECH (`order=8`). **A conclusão que deveria ser investigada entra no plano como premissa e depois serve para validar a própria resposta.** Esse defeito de neutralidade é demonstrável independentemente do gabarito.

A explicação oficial considera outra via: alteração funcional da eNOS, redução de NO e produção de superóxido pela enzima desacoplada, interpretando disfunção endotelial como anterior ao estresse oxidativo. O fluxo não examina essa via nem explicita por que a cadeia escolhida seria a única admitida pelo pedido.

Entretanto, a inversão do gabarito também não deve ser tratada como lei causal geral. A pesquisa primária de [Guzik e colaboradores, 2002](https://pubmed.ncbi.nlm.nih.gov/11940543/) relaciona desacoplamento da eNOS à produção de superóxido e também descreve a contribuição do superóxido para perda de atividade do NO e disfunção endotelial. Isso sustenta a necessidade de distinguir mecanismos e não demonstra uma única ordem global entre os dois fenômenos.

**Classificação:** planejamento enviesado confirmado; divergência da via escolhida pela referência; unicidade da direção causal não estabelecida pelo enunciado. O ganho generalista seria exigir que a conclusão causal seja condicionada ao mecanismo e ao escopo efetivamente sustentados. Não seria correto instruir o harness a inverter sempre essa sequência para coincidir com A.

## 8. O que os erros dizem sobre a proposta

### 8.1. A.3 precisa avaliar a especificação, sem conduzir a resolução

O relatório anterior recomendava não fixar conclusões em A.2. A nova etapa conseguiu identificar esse defeito no HBr, mas em outros casos ela própria passou a prescrever interpretações, censurar hipóteses apenas por serem mencionadas ou inventar exigências. A responsabilidade mudou de lugar, mas o modelo continua sujeito ao mesmo erro de antecipação.

As falhas de pedágio, margem, intervalo entre fases e referente do orbital são adequadas à rubrica já autorizada: não exigem que A.3 resolva a questão, e sim que confira se todas as condições relevantes foram preservadas e se a tarefa pede a grandeza certa. Os novos casos de complexidade, PKC e virologia acrescentam conclusões ou critérios de prioridade impostos sem suporte. História mostra a falha oposta: pedir que se produza uma interpretação é confundido com já prescrevê-la.

### 8.2. TECH precisa conferir a relação decisiva

O contrato impede aprovar com TECH falso. Não impede o modelo de marcar TECH verdadeiro por razões fracas. Raiz “plausível”, referência bibliográfica produzida pelo solver, hipótese compatível mas não sustentada e resultado herdado da memória não substituem uma conferência da relação relevante.

O ácido bórico é o exemplo mais direto de conferência proporcional: substituir a raiz na equação já montada. O torneio exige conferir a transição, não refazer todo o calendário. A casa de shows exige manter a distinção lucro/receita. São operações locais compatíveis com B.2, sem uma segunda solução completa.

Os novos casos acrescentam relações igualmente locais: uma característica satisfaz a definição de estágio adotada? “Linear” realmente exclui “polinomial”? O critério de “mais geral” foi pedido ou inventado? A obrigação atribuída a um autor decorre da evidência? Nomear uma teoria ou herdar uma afirmação da tarefa não demonstra sua validade.

### 8.3. Retentativas precisam corrigir o defeito, não apenas o texto

No NMR, uma objeção ao mecanismo deixa de bloquear a aprovação após uma explicação reformulada que ainda contém o mecanismo errado. Em duas sessões interrompidas, a tarefa posterior reutiliza resultados aprovados que já eliminavam a solução da referência. Nos gases, o modelo rejeita a própria direção de exploração sugerida pelo feedback; em história, repete E cinco vezes sem rever a exclusão de C. São causas diferentes de estagnação, e não quatro ocorrências da mesma falha de memória.

O limite de cinco funcionou como previsto, mas não supriu a falta de progresso. Elevar novamente o teto não é a intervenção indicada por estes registros. Também não há evidência de que acrescentar mais obrigações gerais aos prompts, indiscriminadamente, resolva a fiscalização semântica.

### 8.4. A avaliação precisa distinguir tipos de desfecho

Há erro de plano, erro de conhecimento, erro aritmético, aplicação inadequada de melhor ajuste, perda de fidelidade na apresentação e inconsistência do dataset. O item da bola acrescenta um exemplo claro de resposta fisicamente sustentada penalizada pelo rótulo. Complexidade tem descrições sobrepostas; plasmídeos e PKC exigem auditoria do recorte ou da unicidade da explicação. Isso não isenta o fluxo de premissas antecipadas ou comparações inválidas nesses mesmos itens.

Bloquear uma seleção internamente contraditória é um avanço de fiscalização, ainda que a pontuação continue zero. Aprovar uma explicação falsa depois de duas recusas não é uma recuperação comprovada. E um erro introduzido por C.3 não deve ser contabilizado como se o validador técnico tivesse escolhido aquela letra.

### 8.5. Falha compartilhada não demonstra deterioração causada pelo loop

Os dez casos acrescentados ampliam o repertório de falhas do Ralph, mas o novo recorte inclui perguntas em que o modelo simples também errou. Esses casos ajudam a avaliar se o harness detecta, corrige ou apenas amplifica uma limitação do modelo; sem a execução simples correspondente, não demonstram que a decomposição causou o erro.

Singer, sociologia e virologia permanecem divergentes do gabarito antes e depois da feature. Gases e história mostram novas reprovações pertinentes sem recuperação. Física mostra que o rótulo pode penalizar uma resposta sustentada. A atualização, portanto, reforça os limites semânticos observados e reduz ainda mais a validade de usar apenas “quantidade de erros exportados” para medir ganhos das duas frentes.

## 9. Próximos ajustes indicados pelos dados

As propostas abaixo se restringem às responsabilidades existentes e à análise experimental. Não pressupõem fórmulas específicas de benchmark nem gabaritos como entrada do harness. As inclusões desta atualização tratam o uso real do feedback, a distinção entre dado e premissa gerada e a necessidade de auditar a avaliação.

| Estado atual observado | Ajuste proposto | Como ajudaria |
|---|---|---|
| A.3 deixa passar condições omitidas, referentes alterados e prioridades inventadas, como “mais geral”. | Orientar a auditoria a confrontar as condições do pedido com a cobertura efetiva do plano e o objeto de cada tarefa. Conferir também se regras de prioridade, taxonomias ou direções causais foram fornecidas ou continuam sendo hipóteses a investigar. | Detectar omissões e mudanças de objeto, além de evitar que a resposta seja imposta por um critério indireto, sem o validador resolver a pergunta. |
| A.3 reprova uma pergunta aberta como se fosse uma conclusão e produz relatórios que dizem não haver defeito. | Tornar central a distinção entre investigar, assumir e concluir. Exigir que cada reprovação identifique uma obrigação que realmente impeça a execução; manter as preferências de resolução fora do parecer. Incluir na avaliação semântica planos válidos que pedem interpretar, classificar ou identificar relações, sem prescrever seu resultado. | Reduzir recusas falsas, como em história, e a oscilação que gera trabalho desnecessário. A qualidade desse julgamento precisa de avaliação semântica, além de teste do schema. |
| TECH aceita plausibilidade e repetição como conferência. | Concentrar a justificativa existente na premissa decisiva e em uma relação efetivamente verificada: substituição, vínculo entre grandezas, condição de aplicação ou compatibilidade com o dado citado, conforme o caso. | Transformar a verificação em evidência do resultado, preservando seu escopo local e a possibilidade de aproximações legítimas. |
| Uma afirmação é tratada como sustentada porque veio da tarefa ou dos aprendizados, mesmo quando foi gerada pelo modelo. | Nos prompts existentes, distinguir dados fornecidos, hipóteses e conclusões herdadas. A pertença ao contexto não deve substituir a justificativa da afirmação decisiva. Usar a procedência já disponível, sem exigir nova etapa ou interface. | Atacar a autoconfirmação de PKC e das atribuições a autores; evitar que uma premissa do planejador se transforme em evidência de si mesma. |
| Retentativas mudam a narrativa sem remover a objeção anterior. | Reforçar, no mecanismo atual de feedback, o dever de mostrar qual afirmação foi corrigida e como deixou de produzir a inconsistência apontada. Se a busca não encontrou solução, revisar restrições assumidas pelo próprio solver antes de declarar impossibilidade ou relaxar dados explícitos. | Nos gases, investigar candidatos antes excluídos; em história, reconsiderar a interpretação descartada; no NMR, corrigir o mecanismo. Permitir medir progresso sem aumentar o limite. |
| Melhor ajuste é defendido por um critério diferente para cada candidato, ou por uma prioridade introduzida pelo próprio solver. | Exigir que a comparação use as mesmas condições relevantes e explicite por que uma diferença é decisiva no escopo pedido. Quando houver sobreposição, separar a justificativa da preferência de uma alegação de falsidade dos demais candidatos. | Reduzir literalismo seletivo, a oposição indevida entre linear e polinomial e comparações como a dos plasmídeos. A regra vale para qualquer decisão entre hipóteses ou ações, sem depender de múltipla escolha. |
| C.3 pode contradizer a determinação que C.1 já identificou. | Reforçar a fidelidade da apresentação à determinação aprovada e ao vínculo entre referências e conteúdo, mantendo C.3 como apresentação. | Evitar a perda de um resultado já identificado. A solução deve valer para referências, rótulos e conclusões em geral, sem uma regra exclusiva para letras de alternativas. |
| O recorte não revela o saldo de acurácia nem separa item inconsistente de erro do fluxo. | Avaliar os mesmos IDs nos dois estados, guardar os quatro pares de desfechos simples/Ralph e registrar separadamente contrato, limite, erro analítico e apresentação. Auditar itens inconsistentes na avaliação externa, publicando a pontuação bruta e a análise dos itens contestados com critérios explícitos. | Medir ganhos líquidos, custo por acerto e precisão das reprovações; impedir que uma resposta física sustentada seja usada para ensinar uma premissa falsa ao harness. |

**Prioridade após a ampliação:** calibrar neutralidade e cobertura em A.3; tornar a conferência decisiva de TECH independente da mera presença de uma afirmação no contexto; e fazer as retentativas responderem ao defeito concreto. Em paralelo, a avaliação deve guardar o resultado simples e auditar referências problemáticas. As novas questões não sustentam aumentar novamente o limite de cinco, nem indicam a necessidade de uma regra exclusiva para alternativas.

Esses ajustes podem reduzir várias falhas observadas, mas não garantem recuperar todo resultado anterior incorreto já aprovado. Criar uma transição direta de B.2 para replanejar ou reabrir tarefas seria outra mudança de fluxo; ela não é pressuposta por estas recomendações nem pela nova A.3. As limitações do fluxo atual devem permanecer explícitas no paper.

Para o paper, os registros sustentam que a nova arquitetura **ativa fiscalização antes ausente**, mas também mostram falsos julgamentos e custos sem recuperação. A afirmação de que ela melhora as respostas exige os resultados completos e uma comparação controlada.

## 10. Conferências reproduzíveis

Os totais principais podem ser reproduzidos a partir das três exportações:

```python
from pathlib import Path
from collections import Counter
import json
import re

exports = [
    'benchmark-session-bench_241f93fa34124e089ec7e2634500cd51-ralph-loop-errors',
    'benchmark-session-bench_58a6f3c752ef4f63bccaff5bf210b47e-ralph-loop-errors',
    'benchmark-session-bench_4abe71870570407face0283de4a524a4-ralph-loop-errors',
]
paths = sorted(p for folder in exports for p in Path(folder).glob(
    'questao-*/execucao-ralph-loop.json'
))
sessions = [json.loads(p.read_text())['session'] for p in paths]
events = Counter(m.get('subtype') for s in sessions for m in s['messages'])

assert len(sessions) == 25
assert all(s['flow_version'] == 2 for s in sessions)
assert sum(len(s['invocations']) for s in sessions) == 394
assert sum(s['totals']['total_tokens'] for s in sessions) == 1945157
assert events['plan_candidate'] == 38
assert events['plan_rejected'] == 13
assert events['plan_approved'] == 25
assert events['verify_pass'] == 55
assert events['verify_fail'] == 22
assert sum(s['status'] == 'completed' for s in sessions) == 21
assert sum(s['status'] == 'failed' for s in sessions) == 4
assert all(s['failure']['limit'] == 'task_attempts' and s['failure']['phase'] == 'B2'
           for s in sessions if s['status'] == 'failed')
assert not any(i['phase'] == 'C2' for s in sessions for i in s['invocations'])
assert not any(s['result_revisions'] for s in sessions)

reports = [m for s in sessions for m in s['messages']
           if m.get('phase') == 'B2'
           and m.get('subtype') in ('verify_pass', 'verify_fail')]
tech = Counter(status for m in reports for status in re.findall(
    r'`[^`]+-TECH` — ((?:not )?met):', m['content']
))
assert len(reports) == 77
assert tech == {'met': 57, 'not met': 20}

new_ids = {
    'HISTORIA_ENEM_2022_AZUL_Q066',
    'MMLU_high_school_physics_test_0034',
    'MMLU_human_sexuality_test_0066',
    'MMLU_machine_learning_test_0027',
    'MMLU_moral_disputes_test_0107',
    'MMLU_sociology_test_0070',
    'MMLU_virology_test_0032',
    'GPQA_main_rec1BjNQici8oD53a',
    'GPQA_main_recBeOYL2vJeESmQ5',
    'GPQA_main_recftca7pyp2TCeAG',
}
new_sessions = [s for p, s in zip(paths, sessions)
                if json.loads(p.with_name('questao.json').read_text())['id'] in new_ids]
assert len(new_sessions) == 10
assert sum(len(s['invocations']) for s in new_sessions) == 128
assert sum(s['totals']['total_tokens'] for s in new_sessions) == 545986
```

O código deve ser executado na raiz do repositório e seleciona explicitamente as três exportações desta análise. Os gabaritos e a permutação dos 12 itens GPQA foram conferidos contra o CSV local; as contas de pedágio, calendário, margem, raiz do equilíbrio, estado quântico, unidades dos neutrinos e gases foram conferidas externamente com Python. Nenhuma dessas contas ou referências foi acrescentada à aplicação.
