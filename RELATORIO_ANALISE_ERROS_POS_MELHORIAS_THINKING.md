# Análise dos erros após as melhorias do thinking — Vestibulares, MMLU e GPQA

**Data da análise:** 8 de novembro de 2026.  
**Escopo:** 13 questões, 39 JSONs e 144 invocações do modelo nas três exportações fornecidas.  
**Código consultado:** checkout em `da998d7e5b3447bd0d7043a0683206e4d1e1db2a`; os prompts persistidos nas sessões são a evidência do que efetivamente foi enviado.  
**Natureza do trabalho:** diagnóstico e recomendações. Nenhuma alteração no harness, nova inferência ou execução paga de benchmark foi realizada.

## 1. Diagnóstico principal

O problema remanescente mais evidente é **a homologação de raciocínios errados como se estivessem verificados**. As melhorias deram ao sistema meios para preservar informações, investigar contradições, substituir resultados e produzir uma síntese fiel. Nas execuções analisadas, porém, o julgamento semântico não acionou esses meios: **as 12 sessões que chegaram a C.1 foram aprovadas, nenhuma executou C.2 e nenhuma registrou revisão de resultados**.

O recorte contém **12 respostas incorretas em sessões concluídas e uma falha técnica sem resposta final**. Esses desfechos precisam ser separados: no último caso, o Ralph não demonstrou uma conclusão analítica pior; deixou de entregar uma resposta por violação persistente do contrato de A.2.

Há cinco problemas especialmente claros:

1. **O plano continua transformando interpretações e hipóteses em obrigações.** Isso ocorre no descarte dos 80% de tempo em cruzeiro, na equiprobabilidade de séries de comprimentos diferentes, no modelo incompleto do ácido bórico, na prioridade atribuída à utilidade mais genérica do NGS e na explicação meiótica da mortalidade do zigoto.
2. **B.2 frequentemente verifica se a explicação existe e segue a tarefa, sem detectar que a explicação está errada.** Em 26 avaliações locais, houve 25 aprovações e apenas uma reprovação. A única reprovação foi por falta de marcador de apresentação na sociologia; não corrigiu a resposta conceitual.
3. **A política de melhor ajuste ainda pode encobrir erro de modelagem.** Na World Series, o fluxo chama `4/7` de probabilidade exata e escolhe `35/64` por proximidade. Na reação com HBr, admite condições radicalares não fornecidas para sustentar a seleção que favoreceu.
4. **Dados corretos e interpretações erradas coexistem sem gerar investigação.** No qPCR, a tabela é preservada, mas sua direção é descrita ao contrário. No ácido bórico, a conta produz pH acima de 7 para uma solução ácida a 25 °C e isso passa pelas validações.
5. **A recuperação preserva a saída inválida, mas nem sempre consegue corrigir o defeito.** O campo `acceptance_criteria` permanece embutido na descrição, em vez de ser emitido como lista, em três respostas sucessivas de A.2 no caso do elétron.

Isso explica caminhos pelos quais esta implementação pode perder para a inferência simples. Não demonstra inferioridade geral do raciocínio iterativo. Também não demonstra que as melhorias anteriores foram inúteis: seus mecanismos aparecem nas sessões, mas a presença de instruções e infraestrutura não assegura que o modelo reconheça o erro que deveria ativar a correção.

## 2. Material, método e limites

### 2.1. Fontes examinadas

Foram examinados:

- [README geral](README.md), [metodologia e extensões](RALPH_LOOP_ADAPTADO.md) e trechos técnicos correspondentes do backend;
- [relatório anterior dos oito casos de vestibulares](RELATORIO_BENCHMARK_VESTIBULARES_736136f4.md);
- os sete enunciados de implementação em [feature_melhorias_thinking](feature_melhorias_thinking/);
- [validação das etapas 01–03](VALIDACAO_MELHORIAS_THINKING_01_02_03.md), [validação da etapa 04](VALIDACAO_MELHORIAS_THINKING_04.md) e [validação integrada 01–07](RELATORIO_VALIDACAO_MELHORIAS_THINKING.md);
- todos os arquivos `questao.json`, `resposta-esperada.json` e `execucao-ralph-loop.json` das três pastas indicadas;
- respostas, vereditos, diagnósticos, temperaturas e `session.messages[].prompt_input`, além dos templates, montagem de variáveis, memória, exportador e avaliador;
- para as seis questões GPQA, as colunas **`Correct Answer` e `Explanation` do registro original**, lidas do [dataset local protegido](apps/backend/src/infra/benchmark/gpqa/dataset.zip), no CSV `dataset/gpqa_main.csv`. As explicações foram usadas somente nesta análise externa, nunca injetadas no harness.

Para cada caso, a análise procura **a primeira falha relevante observável, sua propagação, a validação que a aceitou e o efeito sobre a resposta final**. Os números de `order` abaixo são índices do campo `session.messages[].order`, iniciados em zero; não são linhas dos arquivos.

As contas de dose, probabilidade, pH e direção da curva de qPCR foram refeitas com Python, sem chamadas ao modelo. A permutação do provider GPQA foi reproduzida a partir do CSV inteiro: os seis conjuntos de alternativas e respectivos gabaritos exportados coincidem com o mapeamento local.

### 2.2. O que não pode ser inferido

O usuário informou que as questões foram selecionadas por **acerto da inferência simples e erro do Ralph**. Essa condição é adotada como informação do experimento, mas os JSONs exportados contêm somente o braço Ralph. Não há neles a resposta, a justificativa ou a configuração efetiva de cada chamada simples.

O [exportador](apps/backend/src/application/usecases/export_benchmark_ralph_errors_usecase.py) continua incluindo todo `run.ralph` incorreto, inclusive falhas técnicas, **sem verificar `run.simple.is_correct`**. Portanto, a propriedade de seleção depende da informação fornecida pelo usuário. A consulta aos arquivos locais de sessões não encontrou esses três `run_id` para recuperar o braço simples.

Também faltam os resultados completos das baterias e os respectivos denominadores. Assim:

- não se calcula a acurácia global dos fluxos nem o saldo entre ganhos e perdas;
- não se interpreta a passagem de oito erros antigos para dois novos de vestibulares como redução medida: não foi estabelecida a equivalência das amostras;
- não se atribui isoladamente a temperatura, a decomposição, o idioma dos templates ou o modelo a diferença entre os braços;
- não se demonstra que todo erro do Ralph começou em uma resposta que a inferência simples teria produzido corretamente naquele mesmo contexto;
- o commit consultado não substitui um identificador de versão persistido pelo benchmark; a execução real é reconstituída pelos prompts auditados.

O gabarito é a referência de correção do benchmark. Nos itens interpretativos do MMLU, especialmente sociologia e virologia, a plausibilidade de mais de uma leitura recomenda distinguir **discordância com o dataset** de **erro demonstrável internamente**. Não foi feita uma auditoria bibliográfica independente de todos os gabaritos MMLU.

### 2.3. Caracterização das sessões

| Exportação | Dataset identificado pelos itens | Casos | Concluídos com resposta errada | Falhas técnicas | Chamadas | Tokens |
|---|---|---:|---:|---:|---:|---:|
| `bench_c2088cf2fac24cc381fdb0b53b7df120` | MMLU | 5 | 5 | 0 | 48 | 135.222 |
| `bench_d71a5a185535463cbfa84e224e69997b` | Vestibulares | 2 | 2 | 0 | 29 | 110.264 |
| `bench_f90ee2fe4e8a46978aea8de3275c15a1` | GPQA Main | 6 | 5 | 1 | 67 | 253.510 |
| **Total do recorte** | | **13** | **12** | **1** | **144** | **498.996** |

| Propriedade | Observado |
|---|---|
| Modelo/provedor registrados | `deepseek/deepseek-v4-flash-0731` / `open_router` em todas as sessões |
| Temperatura | Sessão `0.0`; 138 chamadas a `0.0` e seis retentativas a `1.0` |
| Limite registrado | `max_tokens = 500000`; não comprova o limite efetivo do provedor |
| Consumo | 439.445 tokens de entrada e 59.551 de saída |
| Tarefas aprovadas | 25; cinco sessões concluídas têm somente uma tarefa |
| B.2 | 26 avaliações: 25 aprovações e uma reprovação |
| C.1 | 12 relatórios válidos, todos aprovados; duas outras saídas de C.1 foram recusadas por contrato |
| C.2/revisões | Zero chamadas / `result_revisions = []` em todas as sessões |
| Contratos inválidos | Seis saídas recusadas, distribuídas em três cadeias; duas recuperadas e uma esgotada |
| Sintaxe | 137 saídas `valid`; sete `valid_after_repair` |
| Término do provedor | Todas as 144 chamadas com `finish_reason = stop`; sem corte por comprimento registrado |
| Degradações | Nenhuma registrada |

Os sete reparos locais de sintaxe não são sete revisões semânticas. Uma saída de B.2 com decisão `reproved` também não é falha do parser: é um relatório válido de reprovação.

Os horários de criação estão em 8 de novembro em UTC; em São Paulo, atravessam a noite de 7 para 8 de novembro.

## 3. O que as sete melhorias entregaram e o que este recorte ainda não mostra

O [relatório integrado](RELATORIO_VALIDACAO_MELHORIAS_THINKING.md) é explícito: os 2.442 testes finais e a cobertura de 100% usam respostas e vereditos roteirizados. Comprovam comportamento programático e contratos, sem medir acurácia de um modelo real. Os erros novos são compatíveis com essa limitação documentada.

| Etapa | Responsabilidade implementada | Evidência nas sessões novas e limite observado |
|---|---|---|
| 01 — Recuperação integral | Reenviar saídas recusadas completas, corrigindo conforme o defeito | Nas cinco transições de recuperação com chamada seguinte, a saída recusada chega integralmente. A.2 da World Series conserva as três tarefas. O caso do elétron mostra que conservar não basta para corrigir o campo ausente. |
| 02 — Aprendizados completos | Preservar dados, associações, hipóteses e resultados parciais | Os 80%, as tabelas de Ct, a concentração/Ka e as alternativas estão nas notas pertinentes. Não há evidência de perda de mapeamento como no caso antigo do cálcio. Há propagação de conclusões erradas e memória redundante. |
| 03 — Planejamento e critérios | Não antecipar respostas; manter cobertura e dependências | Há planos que ainda prescrevem a interpretação errada. Só três das 25 tarefas aprovadas declaram `depends_on`, embora existam outras dependências explícitas no texto. |
| 04 — Validação e aproximações | Conferir conteúdo técnico e consistência sem rejeitar estimativas legítimas | A política atual está nos 38 prompts dos relatórios válidos B.2/C.1. Mesmo assim, os erros passam; a presença do texto não garante aplicação. |
| 05 — Revisão auditável | Substituir resultados e retirar aprendizados obsoletos após investigação aprovada | Nenhuma sessão chega a C.2. Este recorte evidencia falha na detecção que ativaria a revisão; não permite avaliar sua eficácia semântica quando acionada. |
| 06 — Síntese fiel | C.3 usar a cópia aprovada na última C.1, sem novo raciocínio | Nas 12 sessões concluídas, a escolha final preserva a escolha incorreta já disponível antes de C.3. Não foi encontrado novo erro de troca de letra criado somente pela síntese. |
| 07 — Integração | Harmonizar contratos, revisões, memória e apresentação | Os prompts atualizados estão presentes, mas persistem tarefas burocráticas, critérios de apresentação internos e recuperação de contrato sem progresso. |

**Comparação direta possível com o relatório anterior:** a World Series é o único ID repetido entre os dois recortes. Continua selecionando A, mas o mecanismo mudou: antes havia dupla contagem da condição inicial e `21/64`; agora o plano considera equiprováveis trajetórias de comprimentos diferentes e produz `4/7`. A classe de falha persiste, sem que se possa dizer que o cálculo antigo simplesmente foi repetido.

## 4. Visão dos 13 casos

| Caso | Esperado | Ralph | Primeira falha relevante | Desfecho |
|---|---|---|---|---|
| MMLU `moral_disputes_0107` | C | B | B.1 atribui a Singer uma estratégia sem evidência textual verificável | B.2 aceita a atribuição e C.1 a trata como sustentada |
| MMLU `philosophy_0143` | B | D | B.1 constrói uma atribuição categórica a Parfit | Explicação longa é homologada como evidência |
| MMLU `virology_0032` | D | B | A.2 redefine o alvo como utilidade mais ampla e fundamental | Critérios já exigem justificar a superioridade de B |
| MMLU `sociology_0070` | A | D | B.1 agrega posições por associação ampla entre autores | Única reprovação pede marcador; a conclusão errada permanece |
| MMLU `moral_scenarios_0622` | C | D | B.1/T2 inventa transparência da oferta e estreita o padrão moral | Memória e integração propagam “Not wrong” |
| Física ENEM 2023 Q117 | A | B | A.2 manda ignorar a fração de 80% | Cálculo de 10 radiografias é aceito em vez de 8 |
| Matemática ENEM 2022 Q137 | C | A | A.2 impõe equiprobabilidade entre trajetórias de comprimentos distintos | `4/7` é aceito e substituído pela opção mais próxima |
| GPQA `recA1i5ZAh0Uzclxp` | A | D | Modelo de reação incompleto; B.1/T2 descreve a ciclização com o centro nucleofílico errado | Condições não fornecidas são admitidas para sustentar D |
| GPQA `recIgdTGiUZLCejXx` | D | C | A.2 ignora a autoionização da água e prescreve teste insuficiente | pH 7,077 passa como cálculo válido |
| GPQA `recJpyGtGIsxulevT` | C | Sem resposta | A.2 omite a lista estruturada de critérios em três saídas | Falha técnica antes de A.3/B/C |
| GPQA `recZdZxsN0AxDx0pB` | C | A | A.2/T3 já descreve tendência contrária à tabela; T1 perde o sinal na comparação | C.1 recupera o contrato, mas aprova leitura invertida |
| GPQA `reclLfdRGRmiI6CO5` | C | B | B.1/T1 inventa uma estrutura organometálica persistente | Análise de RMN é feita sobre o produto errado |
| GPQA `recsFK6wqE0dBoy4N` | A | C | A.2 exige explicar por que a meiose seria a causa mais direta | Confusão de estágio biológico é homologada |

## 5. Análise dos casos MMLU

### 5.1. Singer — atribuição factual substituída por uma narrativa plausível

**ID:** `MMLU_moral_disputes_test_0107`. **Gabarito:** C, distribuição por loteria. **Ralph:** B, obrigatoriedade universal. [Execução](benchmark-session-bench_c2088cf2fac24cc381fdb0b53b7df120-ralph-loop-errors/questao-MMLU_moral_disputes_test_0107/execucao-ralph-loop.json).

A.2 (`order=2`) pede identificar a posição efetivamente atribuída a Singer e não fixa B nos critérios. A primeira falha relevante está em B.1 (`order=5`): o modelo apresenta B como posição do autor, menciona uma obra e desenvolve justificativas utilitaristas para a obrigação universal. A coerência dessas justificativas não estabelece que o autor tenha defendido a estratégia perguntada.

B.2 (`order=6`) aceita a referência bibliográfica e os exemplos introduzidos como apoio contextual, inclusive no critério que proíbe alegações externas sem suporte. B.4 (`order=8`) transforma a atribuição em fato; C.1 (`order=9`) e C.3 (`order=10`) a mantêm.

**Diagnóstico sustentado:** erro de atribuição em relação ao gabarito, não detectado pelo validador. O registro não contém trecho da obra que permita verificar a afirmação. A melhoria generalista é distinguir uma pergunta sobre **o que uma fonte afirma** de uma pergunta sobre **qual argumento parece defensável**. Não é necessário incorporar Singer ou sua resposta aos prompts.

### 5.2. Parfit — detalhamento e repetição não constituem confirmação

**ID:** `MMLU_philosophy_test_0143`. **Gabarito:** B, comparação apenas aproximada. **Ralph:** D, impossibilidade de comparação. [Execução](benchmark-session-bench_c2088cf2fac24cc381fdb0b53b7df120-ralph-loop-errors/questao-MMLU_philosophy_test_0143/execucao-ralph-loop.json).

A.2 (`order=2`) mantém as possibilidades em aberto, mas introduz um enquadramento bibliográfico e conceitual sobre identidade pessoal. B.1 (`order=5`) constrói uma longa defesa da incomparabilidade, relacionando privacidade da experiência, ausência de um sujeito estável e impossibilidade de agregação. Essas passagens são afirmações do modelo, não excertos fornecidos da obra.

B.2 (`order=6`) chama a fundamentação de coerente e ancorada nas posições conhecidas do autor. B.4 (`order=8`) gera dez notas, várias reformulando a mesma tese. C.1 (`order=9`) aprova porque as demais possibilidades foram eliminadas pela própria narrativa; C.3 (`order=10`) a apresenta fielmente.

**Diagnóstico sustentado:** atribuição divergente do gabarito, aprovada por coerência interna. A memória amplia a repetição do erro, mas o erro já existe antes dela. Não há prova de que a repetição tenha causado a escolha inicial ou de que apenas remover notas faria o modelo acertar.

### 5.3. NGS — o planejador decide o significado de “principalmente”

**ID:** `MMLU_virology_test_0032`. **Gabarito:** D, identificação rápida de novos vírus. **Ralph:** B, identificação de variação genética. [Execução](benchmark-session-bench_c2088cf2fac24cc381fdb0b53b7df120-ralph-loop-errors/questao-MMLU_virology_test_0032/execucao-ralph-loop.json).

A.2 (`order=2`) converte “principalmente útil” em “aplicação mais ampla, fundamental e geral”. A descrição já classifica a descoberta de novos vírus como subconjunto da identificação genética. `T1-AC2` exige explicar por que A, C e D são usos mais específicos ou subordinados à capacidade de identificar variação.

B.1 (`order=5`) executa exatamente esse enquadramento e escolhe B. B.2 (`order=6`) verifica sua conformidade; C.1 (`order=9`) aprova e C.3 (`order=10`) repete B.

**Diagnóstico sustentado:** o plano troca a determinação solicitada por uma hierarquia de generalidade não explicitada no pedido e incorpora a conclusão aos critérios. Identificação de variação é uma aplicação plausível da técnica; isso, por si só, não decide a pergunta do dataset. O relatório não trata a existência dessa aplicação como erro. O erro de processo é fazer sua prioridade virar obrigação antes da investigação.

### 5.4. Sociologia — correção de apresentação consome a retentativa

**ID:** `MMLU_sociology_test_0070`. **Gabarito:** A. **Ralph:** D. [Execução](benchmark-session-bench_c2088cf2fac24cc381fdb0b53b7df120-ralph-loop-errors/questao-MMLU_sociology_test_0070/execucao-ralph-loop.json).

A.2 (`order=2`) pede avaliar três afirmações e verificar se todas caracterizam o movimento. Também cria `T1-AC3`, exigindo o marcador final dentro da tarefa analítica, apesar de a apresentação pertencer a C.3.

B.1 (`order=5`) escolhe D. Relaciona crítica às metanarrativas com equivalência entre quaisquer teorias e aproxima “anything goes” do movimento por associação entre autores. **B.2 (`order=6`) aprova os dois critérios de conteúdo e reprova exclusivamente a ausência de `FINAL_ANSWER: D`.** A retentativa (`order=7`, temperatura 1) conserva D e acrescenta o marcador; B.2 (`order=8`) aprova. C.1/C.3 (`orders=11/12`) mantêm D.

**Diagnóstico sustentado:** a única intervenção corretiva deste recorte prioriza apresentação, enquanto a generalização conceitual permanece. Não houve reversão de uma resposta correta para incorreta: as duas tentativas escolhem D. A ambiguidade conceitual merece revisão externa, mas não elimina a evidência de que uma retentativa analítica foi consumida para produzir um detalhe de formatação.

### 5.5. Cenários morais — ausência de informação convertida em fato favorável

**ID:** `MMLU_moral_scenarios_test_0622`. **Gabarito:** C. **Ralph:** D. [Execução](benchmark-session-bench_c2088cf2fac24cc381fdb0b53b7df120-ralph-loop-errors/questao-MMLU_moral_scenarios_test_0622/execucao-ralph-loop.json).

T1 (`order=5`) classifica o primeiro cenário como não errado, em concordância com o gabarito. Em T2 (`order=10`), o modelo conclui que oferecer à irmã uma bebida após observar a abelha não é claramente errado porque não houve dano, intenção, coerção ou ocultação descritos. Vai além: afirma que **a oferta é transparente**, embora o enunciado não diga que a irmã foi avisada.

B.2 (`order=11`) aceita transparência e ausência de intenção como elementos da justificativa. B.4 (`order=13`) os incorpora ao aprendizado. T3 (`order=15`) combina os dois resultados sem novo exame e escolhe D; C.1/C.3 (`orders=19/20`) mantêm a seleção.

**Diagnóstico sustentado:** o modelo fortalece o limiar de reprovação moral com condições que não foram solicitadas e converte ausência de relato em evidência de ausência. A integração funciona conforme seus insumos, mas um insumo foi homologado com premissa inventada.

## 6. Análise dos casos de vestibulares

### 6.1. Dose de radiação — o plano manda descartar uma condição relevante

**ID:** `FISICA_ENEM_2023_AZUL_Q117`. **Gabarito:** A, oito radiografias. **Ralph:** B, dez. [Execução](benchmark-session-bench_d71a5a185535463cbfa84e224e69997b-ralph-loop-errors/questao-FISICA_ENEM_2023_AZUL_Q117/execucao-ralph-loop.json).

No modelo pretendido pela questão, o tempo anual de cruzeiro é `0,8 × 1000 = 800 h`. A dose correspondente é `2 × 800 = 1600 μSv = 1,6 mSv`, equivalente a `1,6/0,2 = 8` radiografias. Essa conferência usa os dados do enunciado, não uma atualização de normas médicas ou de aviação.

A.2 (`order=2`) já exige usar `2 μSv/h × 1000 h` e justificar por que os 80% não alteram a conta. T1 (`order=5`) acrescenta que o tempo total de trabalho é essencialmente tempo de cruzeiro. A.3 (`order=3`) havia preservado corretamente o percentual e a referência da taxa.

T2 (`order=10`) segue a fórmula imposta, encontra 2 mSv e repete a justificativa. B.2 (`order=11`) a chama de coerente com os dados e com os aprendizados — que já contêm a interpretação errada de T1. T3 (`order=15`) calcula dez radiografias; C.1 (`order=19`) aprova inclusive o critério geral que menciona os 80%; C.3 (`order=20`) mantém B.

**Diagnóstico sustentado:** antecipação qualitativa do plano e erro de domínio de aplicação da taxa. Não há perda da informação de 80%, erro de conversão de unidade ou necessidade de aproximação. A coerência dimensional da multiplicação não valida a escolha das horas às quais a taxa se aplica.

### 6.2. World Series — outra modelagem errada para o mesmo ID

**ID:** `MATEMATICA_ENEM_2022_AZUL_Q137`. **Gabarito:** C, `42/64`. **Ralph:** A, `35/64`. [Execução](benchmark-session-bench_d71a5a185535463cbfa84e224e69997b-ralph-loop-errors/questao-MATEMATICA_ENEM_2022_AZUL_Q137/execucao-ralph-loop.json).

Condicionada a primeira vitória, a probabilidade correta é:

```text
1/8 + 3/16 + 6/32 + 10/64 = 42/64.
```

As contagens de trajetórias favoráveis por duração são `1, 3, 6, 10`, mas os respectivos pesos são `2^−3, 2^−4, 2^−5, 2^−6`. Não se pode dividir a soma dessas contagens pelo número de trajetórias terminais de comprimentos diferentes supondo equiprobabilidade.

A primeira saída de A.2 (`order=2`, auditoria de recusa) emite critérios como strings em vez de objetos. A recuperação (`order=3`) conserva o plano completo e corrige a estrutura. **A hipótese falsa de equiprobabilidade já estava na saída inicial e permanece na corrigida**: não foi criada pelo reparo.

T1 (`order=6`) registra corretamente a equivalência entre a pergunta e a probabilidade condicional, mas mistura igualdade de probabilidades com equivalência de eventos. T2 (`order=11`) chega às contagens corretas, embora apresente justificativas e um exemplo incompatíveis com as posições fixadas. B.2 (`order=12`) aprova pelos valores finais e pelo argumento anunciado.

T3 (`order=16`) obedece ao plano, calcula `20/35 = 4/7` e compara as opções. Chega a mencionar B como a mais próxima antes de a própria tabela indicar A; encerra com A. B.2 (`order=17`) e C.1 (`order=20`) aceitam o melhor ajuste, enfatizando que não foi escrita uma igualdade falsa. C.3 (`order=21`) conserva `4/7` como “probabilidade exata” e apresenta A como aproximação.

**Diagnóstico sustentado:** modelagem probabilística errada prescrita em A.2 e não detectada em B.2/C.1. A melhoria de síntese está visível: não transforma `4/7` em igualdade com `35/64`. Isso preserva fielmente uma conclusão errada, sem corrigir sua origem. A ausência de igualdade falsa não basta para validar o melhor ajuste.

## 7. Análise dos casos GPQA Main

As explicações técnicas de referência desta seção vêm do campo **`Explanation` dos registros originais** no dataset local; as letras usadas abaixo são as da permutação exportada. Isso permite separar o erro do modelo de um possível erro de remapeamento, que não foi encontrado nos seis itens.

### 7.1. Reação com HBr — hipótese conveniente e tratamento assimétrico

**ID:** `GPQA_main_recA1i5ZAh0Uzclxp`. **Gabarito:** A. **Ralph:** D. [Execução](benchmark-session-bench_f90ee2fe4e8a46978aea8de3275c15a1-ralph-loop-errors/questao-GPQA_main_recA1i5ZAh0Uzclxp/execucao-ralph-loop.json).

A explicação original descreve protonação do alceno, formação de carbocátion, uma rota de ciclização com o anel aromático e outra com rearranjo por migração de metila antes da ciclização. As duas rotas produzem os heterociclos da alternativa A. O centro que participa da formação da nova ligação com o carbocátion é o **anel aromático**, não um ataque do oxigênio como descrito pelo Ralph.

A.2 (`order=2`) organiza a primeira tarefa em torno de adição e clivagem do éter. T1 (`order=5`) considera carbocátion e rearranjo, mas não desenvolve a rota de ciclização relevante. T2 (`order=10`) avalia A usando o mecanismo de ataque pelo oxigênio e a descarta por baixa nucleofilicidade em meio ácido.

Na mesma T2, o modelo reconhece que o produto anti-Markovnikov de D exigiria condições radicalares não indicadas. Rejeita B com essa objeção, mas flexibiliza a mesma condição para aceitar D: peróxidos em traços seriam possíveis porque não foram explicitamente excluídos. B.2 (`order=11`) aprova o argumento com ressalvas. T3 (`order=15`) repete a seleção; C.1/C.3 (`orders=19/20`) a conservam.

**Diagnóstico sustentado:** conhecimento/mecanismo incorreto, cobertura incompleta da investigação e uso assimétrico de uma hipótese não fornecida. Não basta proibir aproximação numérica: o mesmo problema ocorre com condições qualitativas inventadas para sustentar uma preferência. O gabarito não precisa entrar na implementação; é suficiente verificar se as condições usadas para aceitar e rejeitar hipóteses são as mesmas.

### 7.2. Ácido bórico — teste de uma aproximação não valida o modelo inteiro

**ID:** `GPQA_main_recIgdTGiUZLCejXx`. **Gabarito:** D, 6,89. **Ralph:** C, 7,08. [Execução](benchmark-session-bench_f90ee2fe4e8a46978aea8de3275c15a1-ralph-loop-errors/questao-GPQA_main_recIgdTGiUZLCejXx/execucao-ralph-loop.json).

A.2 (`order=2`) restringe o método ao modelo `Ka = x²/(C−x)`, com `x = [H+] = [A−]`, e só pede verificar se `x << C`. T1 (`order=5`) calcula `x ≈ 8,37×10^−8 M` e aprova a aproximação porque `x/C ≈ 0,84%`. Esse teste verifica a pequena depleção do ácido, mas **não verifica se a contribuição da água pode ser desprezada**.

T2 (`order=10`) obtém pH 7,077 e o arredonda a 7,1, conforme uma precisão imposta pelo plano. T3 (`order=15`) escolhe 7,08 por proximidade. B.2 aprova as três tarefas; C.1 (`order=19`) cita o teste de 0,84% como fundamento suficiente; C.3 (`order=20`) mantém C.

A explicação original usa eletroneutralidade e autoionização da água. Com depleção pequena do ácido:

```text
[H+]² ≈ Ka·C + Kw
       = 7×10^−15 + 10^−14
[H+] ≈ 1,30×10^−7 M
pH ≈ 6,885 → 6,89.
```

Sem substituir a concentração de ácido não dissociado pela formal, o balanço completo é `H = Ka·C/(H+Ka) + Kw/H`. Sua solução numérica dá pH `6,885254…`, que arredonda para 6,89. A expressão simplificada acima dá `6,884775…`; ambas sustentam D, com diferença inferior a 0,001 unidade de pH.

**Diagnóstico sustentado:** modelo incompleto e teste de aplicabilidade parcial homologado como total. O pH acima da neutralidade para a solução ácida deveria motivar investigação das contribuições desprezadas, dentro da validação existente. O arredondamento prematuro é um problema adicional, mas não causa a escolha errada neste caso: mesmo o valor não arredondado do modelo incompleto aponta para C.

### 7.3. Elétron — falha de contrato, sem evidência de erro analítico final

**ID:** `GPQA_main_recJpyGtGIsxulevT`. **Gabarito:** C. **Ralph:** sem resposta. [Execução](benchmark-session-bench_f90ee2fe4e8a46978aea8de3275c15a1-ralph-loop-errors/questao-GPQA_main_recJpyGtGIsxulevT/execucao-ralph-loop.json).

A.1 (`order=1`) é aceita. As três saídas de A.2 (`orders=2,3,4`) têm JSON legível, mas colocam os critérios em prosa dentro de `description`, sem a propriedade obrigatória `acceptance_criteria`.

A primeira correção preserva integralmente a saída anterior. A segunda saída repete o defeito; a terceira altera títulos e redação, mas continua sem a lista. As duas correções usam temperatura 1. A sessão encerra com `failure.reason = technical_error`, na fase A2, após quatro chamadas e 12.648 tokens.

**Diagnóstico sustentado:** recuperação sem correção estrutural efetiva. Não houve B.1, B.2, C.1 ou C.3. Não se pode dizer que o Ralph escolheu um valor físico errado ou que uma síntese estragou uma solução correta. O reparo integral da etapa 01 funcionou como transporte, mas faltou um feedback de contrato mais específico e eficaz para a geração seguinte.

### 7.4. qPCR — o sinal se perde e a tabela é narrada ao contrário

**ID:** `GPQA_main_recZdZxsN0AxDx0pB`. **Gabarito:** C. **Ralph:** A. [Execução](benchmark-session-bench_f90ee2fe4e8a46978aea8de3275c15a1-ralph-loop-errors/questao-GPQA_main_recZdZxsN0AxDx0pB/execucao-ralph-loop.json).

Os dados preservados por A.3 e por T1 fornecem médias Ct de `34,2; 30,9; 27,6; 24,3; 21,0` quando a concentração cai de `100000` para `10` cópias/μl. Logo, **o Ct observado diminui quando há diluição**. A relação esperada descrita na explicação original é a oposta: menos material exige mais ciclos. Os extremos dão inclinação observada `+3,3` de Ct por `log10(concentração)`, incompatível com a inclinação declarada `−3,3`.

Há três falhas encadeadas:

1. **A.2 (`order=2`) já antecipa em T3 que os Ct observados são menores em concentrações maiores**, contrariando sua própria transcrição dos dados.
2. T1 (`order=5`) informa corretamente que uma diluição deveria aumentar o Ct, mas calcula diferenças no sentido `Ct_alto − Ct_baixo = 3,3` e as compara apenas em módulo. Conclui compatibilidade. B.2 (`order=6`) aprova.
3. T2 (`order=10`) define “desvio” como amplitude `máximo−mínimo`, encontra 0,6 e favorece A. Essa é uma estatística calculável, mas o enunciado não estabelece que “deviation” signifique amplitude. T3 (`order=15`) repete a tabela e afirma que ela mostra Ct menor com maior concentração; usa isso para rejeitar C.

B.2 (`order=16`) aprova a inversão e a explicação de A. Na C.1, duas respostas (`orders=19/20`) omitem campos do relatório: `decision` e também `unmet_criteria_ids`. O parser reporta primeiro `decision`; a terceira saída (`order=21`) corrige o contrato e aprova o mesmo conteúdo. C.3 (`order=22`) mantém A.

**Diagnóstico sustentado:** inversão direcional demonstrável pela própria tabela, mais operacionalização não justificada de uma estatística. A recuperação de C.1 não é revisão semântica. O fato de o enunciado declarar R² e inclinação não autoriza substituir as medidas observadas por uma narrativa coerente com esses indicadores; a discrepância entre ambos é precisamente o objeto a investigar.

### 7.5. Sequência com titanoceno — uma estrutura inventada vira base da tarefa seguinte

**ID:** `GPQA_main_reclLfdRGRmiI6CO5`. **Gabarito:** C, dois dupletos. **Ralph:** B, dois duplos dupletos. [Execução](benchmark-session-bench_f90ee2fe4e8a46978aea8de3275c15a1-ralph-loop-errors/questao-GPQA_main_reclLfdRGRmiI6CO5/execucao-ralph-loop.json).

A.2 (`order=2`) cria T1 para identificar estrutura e enumerar todos os isômeros, e T2 para analisar RMN. A exigência de enumerar todos os isômeros amplia o trabalho além do necessário quando a própria pergunta informa a invariância da resposta, embora algum exame estrutural continue necessário.

B.1/T1 (`order=5`) não estabelece uma estrutura única: apresenta produto 1 como duas possibilidades, produto 2 como reagente/aduto e produto 3 como titanaciclo de cinco ou seis membros. Ainda assim, B.2 (`order=6`) aprova a identificação estrutural e a enumeração. B.4 (`order=8`) armazena essas hipóteses como fatos.

T2 (`order=10`) usa a estrutura recebida e escolhe dois duplos dupletos. A explicação chega a descrever um mesmo carbono como CH e depois como quaternário. B.2 (`order=11`) não pede resolver essas inconsistências; C.1/C.3 (`orders=14/15`) mantêm B.

A explicação original descreve metilenação da cânfora, formação de dicloroceteno e cicloadição para um produto orgânico espiro. Os prótons relevantes pertencem a um CH₂ adjacente ao carbonilo, sem prótons nos dois carbonos vizinhos; o acoplamento mútuo dos dois prótons não equivalentes dá os dois dupletos.

**Diagnóstico sustentado:** erro técnico de identificação estrutural que atravessa a fronteira entre tarefas. O validador aceitou uma descrição de possibilidades como se fosse conectividade estabelecida. A memória transporta o erro, mas não o origina. O caso também mostra o risco de pedir uma enumeração extensa quando basta demonstrar a propriedade relevante.

### 7.6. Zigoto — um mecanismo de outra etapa biológica vira requisito

**ID:** `GPQA_main_recsFK6wqE0dBoy4N`. **Gabarito:** A. **Ralph:** C. [Execução](benchmark-session-bench_f90ee2fe4e8a46978aea8de3275c15a1-ralph-loop-errors/questao-GPQA_main_recsFK6wqE0dBoy4N/execucao-ralph-loop.json).

A.2 (`order=2`) reconhece que a injeção ultrapassa a barreira de ligação do espermatozoide. Entretanto, `T1-AC2` exige explicar como incompatibilidades cromossômicas provocam falha meiótica e morte do zigoto; `T1-AC3` exige explicar por que epistasia é menos direta ou provável. A conclusão favorável a C já está nos critérios.

B.1 (`order=5`) mistura pareamento meiótico, segregação em clivagens iniciais e formação de gametas. Afirma ainda que interações epistáticas tenderiam a se manifestar apenas mais tarde. B.2 (`order=6`) aprova a cadeia; B.4 (`order=8`) a consolida; C.1/C.3 (`orders=9/10`) mantêm C.

A explicação original distingue inviabilidade do zigoto por interações gênicas entre espécies de falha de meiose relacionada à produção de gametas e esterilidade híbrida. O mesmo número de cromossomos não resolve todas as incompatibilidades, mas também não faz da meiose futura uma causa imediata de morte do zigoto.

**Diagnóstico sustentado:** antecipação qualitativa no plano e erro de correspondência entre mecanismo, etapa temporal e desfecho solicitado. É uma falha generalizável: uma causa válida para um evento posterior foi usada para explicar outro evento, sem estabelecer a ponte causal.

## 8. Por que o processamento adicional pode piorar a resposta

### 8.1. O harness cria vários pontos de compromisso com uma hipótese

A inferência simples precisa produzir uma resposta. O Ralph também produz um plano, critérios, conclusões locais, resumos e vereditos. Se uma hipótese incorreta entra no plano como obrigação, as chamadas seguintes podem otimizar a concordância com esse plano, em vez de testar a pergunta original.

Nos casos de radiação, NGS e zigoto, a validação recompensa o cumprimento de uma interpretação antecipada. Na World Series e no ácido bórico, o método prescrito já exclui parte da modelagem correta. A informação necessária não desapareceu necessariamente; sua interpretação foi fixada cedo demais.

Cinco sessões concluídas já têm somente uma tarefa. Portanto, reduzir decomposição pode evitar trabalho redundante em parte do recorte, mas não explica nem resolve todos os casos. Mesmo uma tarefa passa por planejamento, resolução, validação, memória e síntese; uma atribuição factual incorreta pode sobreviver a esse percurso inteiro.

### 8.2. Fresh Context separa conversas, mas não torna os julgamentos independentes

O modelo e o provedor registrados são os mesmos entre fases. Mesmo com janelas novas, B.2 recebe a solução que vai julgar e os critérios produzidos pelo planejador; C.1 recebe resultados já aprovados e notas que os repetem. Isso permite **erros correlacionados e ancoragem**, embora não prove que essas sejam as únicas causas.

O sinal observável é que os vereditos frequentemente recontam a justificativa da solução como evidência de sua correção. A concordância entre chamadas que dependem da mesma premissa não equivale a uma verificação por evidência independente.

### 8.3. A validação tem um ponto cego entre “não resolver” e “verificar tecnicamente”

B.2 já instrui verificar aplicabilidade, dados, unidades e inferências. Ao mesmo tempo, enfatiza escopo local, proíbe reescrever critérios e não recebe a descrição da tarefa: a [montagem de variáveis](apps/backend/src/application/usecases/ralph_thinking_usecase.py) fornece resultado preliminar, critérios, proposta de revisão e aprendizados. Isso reduz o contexto explícito de propósito, condições e limites que acompanha a avaliação.

O [template B.2](apps/backend/src/infra/templates/b2_task_verification.md) permite superar uma antecipação numérica/algebraica errada quando a dedução está correta, mas essa exceção é redigida de forma mais estreita que a proibição geral de antecipação qualitativa em A.2. Persiste uma tensão para critérios como “explique por que esta causa é menos provável”, quando a hierarquia causal é justamente o que deveria ser descoberto.

C.1, por sua vez, não deve produzir a análise ausente. Essa limitação é adequada, mas não deve ser interpretada como dispensa de apontar um conflito já visível, como tabela crescente narrada como decrescente ou condição de aplicação contradita pelos dados. A detecção e o encaminhamento pertencem a C.1; a solução pertence a C.2 → B.

### 8.4. A aproximação correta exige que a base do cálculo seja defensável

A política atual evita rejeições indevidas de estimativas legítimas. Esse objetivo deve ser preservado. O problema é aceitar “comparou e escolheu a mais próxima” como fundamentação suficiente quando a validade do modelo não foi efetivamente examinada.

Na World Series, o erro existe antes de comparar opções. No ácido bórico, a pequena dissociação não valida desprezar a água. Na reação com HBr, explicitar uma hipótese de peróxidos não a torna sustentada pelos dados. Essas limitações também valem para previsões abertas, recomendações de capacidade, decisões operacionais e diagnósticos, sem qualquer alternativa rotulada.

### 8.5. Memória aprovada pode ser confundida com dado fornecido

Há 83 notas produzidas em A.3 e 119 em B.4 neste recorte. O armazenamento tem proveniência, mas [a renderização atual da memória](apps/backend/src/domain/services/learnings_memory.py) emite uma lista plana de conteúdos, sem mostrar sua origem. Assim, observações copiadas do pedido e conclusões inferidas aparecem juntas.

Na radiação, os 80% literais coexistem com a conclusão derivada de que podem ser ignorados. No qPCR, a tabela literal coexistirá com a declaração de que sua tendência é inversa. Na filosofia, dez notas reafirmam uma atribuição sem evidência nova. Isso pode aumentar a força aparente de uma premissa, mas a relação causal entre redundância e erro precisa ser medida; o volume de notas, isoladamente, não prova dano.

### 8.6. Algumas falhas anteriores não reapareceram neste recorte

Não foi encontrada troca de letra criada somente em C.3, perda do restante do plano por corte em mil caracteres ou aprovação global seguida de nova análise silenciosa decisiva na síntese. Também não houve revisão aplicada com resultado obsoleto ressuscitado.

Essas ausências não certificam eliminação dessas classes na bateria inteira. Indicam que **o próximo ajuste deve priorizar a qualidade da detecção e da investigação**, preservando as correções de transporte, isolamento e síntese já implementadas.

## 9. Conferências reproduzíveis

O trecho abaixo reproduz a contagem central e as verificações numéricas. Usa somente a biblioteca padrão; não executa o harness, não lê credenciais e não chama modelos. Deve ser executado na raiz do repositório.

```python
import json
from collections import Counter
from fractions import Fraction
from math import comb, log10, sqrt
from pathlib import Path

files = sorted(Path('.').glob(
    'benchmark-session-bench*-ralph-loop-errors/questao-*/execucao-ralph-loop.json'
))
sessions = [json.loads(p.read_text())['session'] for p in files]
calls = [i for s in sessions for i in s['invocations']]
messages = [m for s in sessions for m in s['messages']
            if m['source'] == 'llm_agent']
assert len(files) == 13
assert Counter(s['status'] for s in sessions) == {'completed': 12, 'failed': 1}
assert len(calls) == 144
assert sum(s['totals']['total_tokens'] for s in sessions) == 498996
assert sum(not i['content_accepted'] for i in calls) == 6
assert not any(i['phase'] == 'C2' for i in calls)
assert all(not s['result_revisions'] for s in sessions)
b2 = [m for m in messages if m['phase'] == 'B2']
c1 = [m for m in messages if m['phase'] == 'C1']
assert (len(b2), sum('`reproved`' in m['content'] for m in b2)) == (26, 1)
assert (len(c1), sum('`approved`' in m['content'] for m in c1)) == (12, 12)

assert Fraction(2) * Fraction(4, 5) * 1000 / 200 == 8
probability = sum(Fraction(comb(n - 2, 2), 2 ** (n - 1))
                  for n in range(4, 8))
assert probability == Fraction(42, 64)
assert Fraction(1 + 3 + 6 + 10, 1 + 4 + 10 + 20) != probability

ph_without_water = -log10(sqrt(7e-10 * 1e-5))
ph_with_water = -log10(sqrt(7e-10 * 1e-5 + 1e-14))
assert round(ph_without_water, 2) == 7.08
assert abs(ph_with_water - 6.89) < 0.01

# Balanço completo, mantendo a depleção do ácido (Newton).
h = sqrt(7e-10 * 1e-5 + 1e-14)
for _ in range(10):
    residual = h - 7e-10 * 1e-5 / (h + 7e-10) - 1e-14 / h
    derivative = 1 + 7e-10 * 1e-5 / (h + 7e-10)**2 + 1e-14 / h**2
    h -= residual / derivative
assert round(-log10(h), 2) == 6.89

# Ordem: concentrações 100000, 10000, 1000, 100 e 10.
ct = [Fraction(x, 10) for x in (342, 309, 276, 243, 210)]
assert all(ct[i + 1] - ct[i] == Fraction(-33, 10) for i in range(4))
assert (ct[0] - ct[-1]) / (5 - 1) == Fraction(33, 10)
```

A pequena diferença entre o modelo aproximado e o balanço completo não altera a seleção: D é a opção sustentada. O script distingue as duas contas em vez de forçar uma igualdade. A conferência numérica não é uma proposta de incluir essas fórmulas no harness.

## 10. Sugestões de melhorias compatíveis com o Ralph Loop adaptado

**Atualização de escopo:** esta seção preserva as sugestões originais. A decisão posterior do usuário reorganiza 10.1 em uma nova validação de planejamento e reúne 10.2/10.3 no fortalecimento de B.2; 10.4–10.7 ficam adiadas. O desenho atualizado, suas limitações e os complementos recomendados estão na seção 11. A restrição original de não adicionar fases, descrita a seguir, é substituída pela autorização explícita para a nova A.3 nesse desenho.

As propostas abaixo são **ajustes nas responsabilidades e na implementação das fases existentes**, tomando como referência a metodologia e as extensões já documentadas em `RALPH_LOOP_ADAPTADO.md`. Mantêm A.1–A.3, B.1–B.4 e C.1–C.3, Fresh Context, aprovação antes do armazenamento, memória separada e síntese sem análise nova.

Não dependem de múltipla escolha: aplicam-se a cálculos, atribuições a fontes, interpretação de texto, classificação, investigação de causas e decisões abertas. Os casos reais servem à avaliação externa; IDs, fórmulas específicas, gabaritos e respostas esperadas não devem entrar nos prompts genéricos de produção.

Cada melhoria distingue o **estado atual da aplicação**, o **comportamento que pretende mudar**, o **ajuste proposto** e **como ele pretende resolver o problema**. O estado atual considera tanto as regras já implementadas quanto o comportamento observado nas sessões: quando uma regra já existe, a proposta busca melhorar sua aplicação, sem apresentá-la como uma capacidade inteiramente ausente. Os efeitos semânticos descritos são esperados e precisam ser medidos.

### 10.1. Prioridade alta — planejamento neutro e investigação proporcional ao pedido

**Estado atual da aplicação:** A.2/C.2 já orientam separar dados, métodos, hipóteses e resultados, manter conclusões em aberto, evitar tarefas redundantes e revisar o plano na própria geração. O parser confere a estrutura e as referências do plano; não verifica semanticamente se um critério antecipou a resposta. Nas sessões analisadas, o modelo ainda produziu tarefas que obrigavam a descartar os 80% de cruzeiro, assumir equiprobabilidade ou defender uma causa específica antes da investigação.

**Comportamento que a proposta pretende mudar:** A.2 ainda fixa conclusões qualitativas e receitas cuja aplicabilidade deveria ser verificada.

**Ajuste proposto:** simplificar e reorganizar A.2/C.2 para que cada descrição tenha um objetivo a determinar, dados fornecidos e condições do método a verificar. Na revisão final já existente dentro da chamada, conferir também se o critério continuaria válido caso a investigação chegasse à conclusão oposta. Um critério que exige justificar por que uma causa é superior, quando essa superioridade não foi fornecida, deve ser reescrito como investigação comparativa.

Planejar um método continua permitido. O cuidado é evitar que “aplique esta fórmula” esconda uma hipótese ainda não verificada. A descoberta de que o método não se aplica pode ser resultado legítimo da investigação, com explicação, permitindo complementação pelo caminho já existente.

**Mudanças concretas nos templates:** retirar tarefas que apenas organizam dados já disponíveis em A.3, repetem uma seleção já estabelecida ou imprimem apresentação. Exigir enumeração completa só quando necessária à determinação. Não proibir a última integração analítica quando ela realmente falta.

**Exemplos generalistas:** determinar o intervalo de operação de uma taxa antes de integrá-la; verificar as condições de uma regra antes de aplicá-la; investigar a causa na etapa temporal solicitada; estabelecer qual comparação o pedido exige sem substituir “principal” por “mais amplo”.

**Como a proposta pretende resolver:** a revisão do plano passa a testar também a neutralidade de cada critério, além de sua cobertura. Manter a conclusão aberta permite que B.1 rejeite uma hipótese inadequada sem contrariar a tarefa recebida. Retirar atividades de transcrição e apresentação reduz chamadas que apenas repetem conclusões; a concisão busca tornar as obrigações analíticas mais claras para o modelo.

**Arquivos:** `a2_task_decomposition.md`, `c2_additional_planning.md` e, para harmonização, `b1_task_resolution.md`. É reforço de instruções já previstas, não um novo revisor de plano. Como parte delas já existe, a hipótese a testar é a eficácia de uma redação mais curta e menos prescritiva, não a novidade da regra.

### 10.2. Prioridade alta — B.2 verificar a premissa decisiva, com o escopo explícito

**Estado atual da aplicação:** B.2 recebe o resultado preliminar, os critérios locais, a proposta de revisão quando existente e os aprendizados acumulados. A descrição da tarefa não é enviada. O template já exige verificação técnica, mas também determina avaliar todos os critérios sem reescrevê-los; a exceção explícita para antecipações erradas do plano se refere a números ou expressões. Nas execuções, houve aprovações que repetiam a explicação de B.1 sem detectar premissas inventadas ou relações incompatíveis com os dados.

**Comportamento que a proposta pretende mudar:** explicações completas e aderentes aos critérios passam apesar de relações erradas ou premissas não fornecidas.

**Ajustes propostos na mesma chamada B.2:**

- fornecer a descrição da tarefa como contexto de escopo, em área separada dos critérios, usando o objeto `Task` já disponível no orquestrador;
- orientar a justificativa a identificar a **premissa decisiva** e conferir seu apoio nos dados, a aplicabilidade do método e a ligação com a conclusão;
- antes de aprovar, verificar uma relação relevante por outro ângulo quando isso for simples: direção de uma variação, caso limite, conservação, relação temporal, compatibilidade de unidades/referentes ou um exemplo que teste uma generalização;
- não aceitar que o resultado certifique a si próprio, como “não contei” quando o texto contou, ou “a linha está presente” quando não está;
- distinguir ausência de informação, negação explícita e hipótese. “Não foi informado que houve dano” não demonstra “a oferta foi transparente”.

Para tornar a mudança observável, a justificativa pode registrar, no campo textual já existente, o dado ou trecho de apoio, a relação que foi conferida e o resultado dessa conferência. Não basta repetir a conclusão como justificativa. Casos de atribuição factual sem fonte fornecida precisam distinguir conhecimento lembrado de evidência presente; uma explicação plausível não cria uma citação verificável. Isso melhora a disciplina da avaliação, mas não supre automaticamente conhecimento que o modelo não possui.

Isso não exige que B.2 refaça toda a solução ou produza a resposta corrigida. Uma justificativa como “a direção declarada contradiz os pares fornecidos; investigar essa relação” basta para reprovar e devolver a análise a B.1.

**Tensão a resolver:** harmonizar a obrigação de avaliar todos os critérios com a regra de que uma antecipação do planejador não é padrão de verdade. A proteção existente para números/expressões deve abranger classificações e relações qualitativas. Se a resolução demonstrar uma conclusão correta que diverge da hipótese do plano, o validador não deve exigir a hipótese falsa só para obter conformidade. O ajuste precisa ser documentado como interpretação do critério analítico, preservando o schema e a auditoria; o orquestrador não deve reescrever vereditos automaticamente.

**Como a proposta pretende resolver:** a descrição explicita o objetivo e as condições da tarefa, enquanto a justificativa passa a mostrar qual relação foi efetivamente conferida. Isso busca substituir a aprovação por presença de explicação por uma avaliação de seu fundamento. Uma premissa incompatível com os dados deve gerar feedback concreto para a retentativa de B.1, sem exigir que B.2 produza a solução corrigida.

**Arquivos:** `b2_task_verification.md` e `RalphThinkingUseCase.__verification_variables`. A descrição é uma entrada explícita da tarefa, não restauração da conversa anterior nem injeção de resultado de outras tarefas.

### 10.3. Prioridade alta — melhor ajuste condicionado ao modelo e às hipóteses

**Estado atual da aplicação:** B.1/B.2/C.1 compartilham uma política que admite aproximação e melhor ajuste sustentados por comparação, eliminação, precisão, hipótese explícita ou inferência contextual. A mesma política já manda revisar erros identificáveis e contradições. Entretanto, nas sessões, comparar valores foi suficiente para homologar `4/7` na World Series, e a possibilidade de peróxidos não informados foi usada para sustentar a seleção na reação com HBr. A validade da base não foi efetivamente estabelecida antes da escolha.

**Comportamento que a proposta pretende mudar:** comparação ou hipótese explicitada são tratadas como fundamento suficiente sem validar sua relação com os dados.

**Ajuste proposto:** reorganizar a política comum de B.1/B.2/C.1 em uma ordem clara: primeiro verificar a base da determinação; depois julgar se aproximação, eliminação ou inferência sustentam a decisão. Uma hipótese deve ser compatível com o pedido e ter justificativa para ser adotada. Sua simples possibilidade não permite acrescentá-la apenas ao candidato favorecido.

Manter aproximações legítimas, estimativas, eliminação e inferência contextual. Não adotar tolerância percentual universal, proibição de aproximação em todo problema discreto ou exigência de cálculo direto até toda resposta. Em contrapartida, **ordenar distâncias entre respostas candidatas não estima o erro do cálculo**, e comparação de alternativas não sana uma inconsistência da modelagem.

Para perguntas abertas, a regra é a mesma: uma estimativa de demanda não pode ser considerada sustentada apenas porque ficou perto de uma capacidade comercial; a hipótese de operação usada precisa corresponder ao cenário.

**Como a proposta pretende resolver:** separar a avaliação da base analítica da avaliação do ajuste evita que proximidade ou uma hipótese conveniente encerrem a investigação de um erro anterior. A proposta preserva estimativas legítimas, mas exige que a aproximação se apoie em dados, modelo e condições defensáveis. O defeito a corrigir passa a ser nomeado antes de decidir entre respostas candidatas.

**Arquivos:** política compartilhada de `b1_task_resolution.md`, `b2_task_verification.md`, `c1_global_verification.md`, com harmonização de A.1/A.2/C.2/C.3. Reduzir redundância e retirar exemplos cuja mensagem possa ser lida como aprovação automática após comparação.

### 10.4. Prioridade alta — C.1 conferir os vínculos entre dados, conclusões e condições

**Estado atual da aplicação:** C.1 recebe os resultados vigentes, os critérios gerais, os aprendizados e o registro de revisões. Já deve conferir suficiência e consistência, apontar erros concretos e encaminhar pendências a C.2. O fluxo de investigação e substituição auditável também está implementado. No recorte, porém, as 12 verificações globais válidas aprovaram o material, inclusive com contradições entre dados e conclusões; nenhuma chamou C.2.

**Comportamento que a proposta pretende mudar:** todas as aprovações locais se acumulam, mas nenhuma das contradições demonstráveis chega a C.2.

**Ajuste proposto:** dentro da chamada C.1 existente, dar prioridade a três perguntas de consistência antes da decisão global:

1. As conclusões respeitam os dados e referências copiados do pedido?
2. As tarefas usaram as mesmas condições, objetos e etapas temporais ao compor o resultado?
3. Há uma hipótese, condição descartada ou relação direcional cuja justificativa não foi estabelecida?

A aprovação de B.2 e a repetição de uma tese em B.4 não devem contar como evidência adicional de verdade. C.1 identifica o vínculo defeituoso e o resultado envolvido; C.2 planeja a investigação sem antecipar o desfecho; B executa e valida; uma nova C.1 decide antes da síntese. O mecanismo de `review` já implementado deve ser reutilizado quando houver resultado a confirmar ou substituir.

Não calcular o resultado ausente em C.1. Não encaminhar todo valor aproximado a C.2. O acionamento deve ter um defeito concreto, como direção incompatível com pares observados ou condição de aplicação não demonstrada. Isso preserva a função de suficiência e consistência do paper.

**Como a proposta pretende resolver:** priorizar a conferência dos vínculos entre dados, condições e conclusões busca fazer C.1 detectar conflitos que a validação local deixou passar. A mudança ativa o caminho corretivo já disponível, com investigação em B e nova aprovação global antes de C.3. A infraestrutura de revisão passa a ser usada quando há um motivo concreto, em vez de o erro seguir diretamente para a apresentação final.

**Arquivos:** `c1_global_verification.md`, `c2_additional_planning.md`; manter `ResultsLedger` e `GlobalApproval` como infraestrutura, sem nova fase de revisão.

### 10.5. Prioridade alta — recuperação de contrato com feedback de campo e tipo

**Estado atual da aplicação:** o parser identifica defeitos e registra informações como código, campo e IDs afetados. A recuperação preserva a saída anterior integralmente e envia uma mensagem de correção conforme a categoria do defeito, com o motivo textual do erro e orientações gerais da fase. Ela não monta, a partir do diagnóstico, uma instrução específica com caminho do campo, tipo esperado e exemplo mínimo. No caso do elétron, o modelo repetiu o campo ausente nas três saídas e esgotou as tentativas.

**Comportamento que a proposta pretende mudar:** A.2 repete critérios em prosa; C.1 omite campos em duas respostas sucessivas.

**Ajuste proposto:** aproveitar os diagnósticos estruturados já disponíveis para que a mensagem de correção inclua caminho do campo, tipo esperado e um exemplo mínimo de estrutura da fase. Para `tasks[].acceptance_criteria`, explicar que os itens precisam estar em uma propriedade irmã de `description`, como lista de objetos com `id` e `description`; texto dentro da descrição não preenche o campo. Para um relatório, lembrar que avaliações, IDs pendentes e decisão devem ser emitidos pelo modelo de forma consistente.

Se o mesmo defeito se repetir, tornar a instrução específica sobre esse defeito, dentro da janela de recuperação já existente e dos mesmos limites. Preservar a saída integral, a contabilização e a temperatura vigente de retentativa. Não completar campos, extrair critérios da prosa automaticamente ou deduzir `approved` no parser.

**Como a proposta pretende resolver:** o feedback mostra onde a estrutura está errada e como o campo deve ser emitido, reduzindo a ambiguidade de mensagens como “deve ser uma lista”. Ao repetir o defeito, a correção reforça a diferença entre escrever critérios na descrição e criar a propriedade exigida. O próprio modelo continua responsável pela saída completa e pelos vereditos; o parser mantém a validação estrita.

**Arquivos:** `base_thinking_phase.py`, tipos de diagnóstico e testes de recuperação. É a melhoria com evidência mais diretamente verificável por testes determinísticos, embora o sucesso do modelo em corrigir o formato ainda exija avaliação real.

### 10.6. Prioridade média — tornar a origem dos aprendizados visível

**Estado atual da aplicação:** a memória já guarda as fontes dos fatos, controla sua vigência e retira aprendizados sem fonte válida após revisões. Contudo, `LearningsMemory.render()` envia somente os conteúdos em uma lista plana, sem identificar visualmente o que veio de A.3 ou de cada tarefa. A deduplicação normaliza espaços, mas não une paráfrases. Assim, dados originais e conclusões derivadas aparecem juntos, e reformulações da mesma tese podem ocupar várias notas.

**Comportamento que a proposta pretende mudar:** dados literais e interpretações aprovadas chegam numa lista plana e podem ser confundidos.

**Ajuste proposto:** manter a área de Aprendizados Pontuais, mas renderizar a proveniência já armazenada: notas do pedido separadas das conclusões de tarefas identificadas. Na validação, dado fornecido e conclusão derivada devem conservar papéis distintos. Quando houver várias fontes válidas do mesmo fato, preservar sua associação; fonte adicional só vale quando a tarefa o reestabeleceu independentemente.

Em B.4, priorizar fatos úteis com referente, condição e motivo breve; evitar dez paráfrases de uma conclusão, relatos de processo e fragmentos de instrução. Não retirar uma conclusão necessária por ser simples, não fazer cortes arbitrários nem deduplicação semântica destrutiva.

Isso melhora a rastreabilidade e torna mais fácil detectar “dado original × interpretação derivada”. Não transforma a origem em garantia de verdade e não substitui os resultados aprovados como base de cobertura em C.1/C.3.

**Como a proposta pretende resolver:** tornar a proveniência visível permite confrontar uma interpretação com o dado que a originou e reconhecer que várias repetições podem depender da mesma conclusão. O ajuste de B.4 busca reduzir redundância sem perder resultados úteis. A gestão de fontes e vigência já existente permanece responsável por retirar ou restaurar os fatos após uma revisão.

**Arquivos:** `learnings_memory.py`, `b4_learnings_extraction.md` e descrições da área de notas nos templates B/C. A mudança de renderização deve preservar a política de revisão da etapa 05.

### 10.7. Prioridade média — dependências e apresentação sem trabalho analítico redundante

**Estado atual da aplicação:** A.2/C.2 já podem declarar `depends_on`, e o livro de resultados suspende conclusões com dependências declaradas quando sua base deixa de ser vigente. Esse controle não reconhece dependências que aparecem apenas em prosa; só três das 25 tarefas aprovadas do recorte declararam o campo. Os templates também já procuram reservar apresentação para C.3, mas A.2 ainda gerou critérios internos de marcador final. Em sociologia, B.2 reprovou a tarefa apenas pela falta desse marcador e exigiu nova resolução.

**Comportamentos que a proposta pretende mudar:** dependências textuais sem metadados e critérios finais indevidamente cobrados em B.2.

**Ajustes propostos:** A.2/C.2 devem declarar `depends_on` sempre que uma tarefa usar conclusão anterior, como já especificado. A revisão final do plano deve conferir a coerência entre referências textuais e metadados, sem adivinhar dependências por regex. Se futuramente forem adicionadas referências estruturadas às fontes usadas por B.1, a mudança deve ser mínima, geral e validada de ponta a ponta; não é requisito para começar as correções prioritárias.

Reduzir em A.2/C.2 a importação do formato final para critérios internos. B.2 pode verificar um contrato interno realmente necessário, mas uma tarefa analítica não deve ser repetida apenas para imprimir a linha que C.3 já foi criada para apresentar. Não resolver isso mandando B.2 ignorar arbitrariamente qualquer critério recebido.

São riscos distintos: a omissão de dependências **não causou uma síntese com estado obsoleto neste recorte**, pois não houve revisões. Ela pode prejudicar a propagação correta assim que C.2 passar a corrigir os erros. A reprovação por marcador, por outro lado, já ocorreu e consumiu duas chamadas adicionais.

**Como a proposta pretende resolver:** alinhar dependências usadas e declaradas permite que o mecanismo existente de revalidação alcance as conclusões afetadas por uma correção. Manter exigências de apresentação fora dos critérios analíticos evita consumir retentativas para tarefas que C.3 já realiza. As duas mudanças buscam reservar chamadas para trabalho necessário e impedir que uma conclusão dependente permaneça vigente sem sua base.

### 10.8. Avaliar as mudanças sem acoplar o harness ao benchmark

**Estado atual da aplicação:** o benchmark executa os dois fluxos e registra acertos, falhas, consumo e sessões. A validação das sete melhorias utilizou respostas roteirizadas; os novos relatórios trazem evidência de modelo real, mas apenas do recorte de erros. A exportação específica desses erros continua selecionando Ralph incorreto sem conferir o acerto do simples e inclui somente a sessão Ralph. Na revisão atual do código, há também uma [exportação completa da bateria](apps/backend/src/application/usecases/export_benchmark_session_usecase.py), que reúne os dois braços quando suas sessões estão disponíveis; ela pode apoiar as próximas comparações, mas não acrescenta dados retroativamente aos arquivos examinados aqui.

**Comportamento que a proposta pretende mudar:** avaliar melhorias apenas por testes estruturais ou por casos selecionados de erro não permite medir seu benefício líquido, rejeições indevidas e custo. A seleção “simples certo, Ralph errado” também precisa ser verificável nos artefatos usados para essa análise.

**Ajuste proposto:** implementar em incrementos separados e medir cada um contra o estado atual, usando a exportação completa já disponível para recuperar os dois braços e tornando explícito o filtro na exportação específica de regressões. A ordem sugerida é: **recuperação específica de contrato; neutralidade e concisão do planejamento; validação técnica e hipóteses; detecção global; proveniência e dependências**. As instruções interdependentes precisam ser harmonizadas em cada incremento para não recriar conflitos entre fases.

Separar três tipos de evidência:

| Evidência | Verificação necessária | O que pode ser afirmado |
|---|---|---|
| Programática | Templates reais, parser, recuperação, memória, livro, snapshots e auditoria com completions roteirizadas | As entradas, referências e transições são preservadas corretamente |
| Semântica por fase | Modelo real recebe entradas arquivadas, incluindo tentativas corretas e erradas; avaliador externo mede o veredito | A fase passou a detectar melhor determinada classe de erro, naquela avaliação |
| Resultado ponta a ponta | Execuções pareadas completas, repetidas, com modelo e protocolo controlados | Efeito medido sobre respostas finais, custo e regressões |

Para evitar ajustar apenas aos 13 itens, criar casos novos e abertos com os mesmos mecanismos: taxa válida só em parte do tempo; trajetórias com pesos diferentes; contribuição pequena que se torna dominante em certo regime; tabela cuja direção contradiz um resumo; causa atribuída à etapa errada; afirmação sobre uma fonte sem trecho de apoio; hipótese adicional usada de forma assimétrica; estrutura intermediária não determinada. Nenhuma resposta de referência deve entrar no prompt de resolução.

Manter controles positivos: aproximação fundamentada, explicação correta com redação diferente, hipóteses distintas compatíveis, resultado intermediário suficiente ao seu escopo, resposta curta com justificativa final opcional e investigação que confirma um resultado anterior. **Aumentar a taxa de reprovação não é, por si só, melhorar a validação.** É necessário reduzir aprovações erradas sem produzir rejeições indevidas e ciclos desnecessários.

Nas baterias completas, registrar os quatro pares de desfechos simples/Ralph, separando falha técnica de erro semântico; conservar resultados em que o Ralph melhora a resposta. Medir precisão das aprovações/reprovações, correção efetiva após retentativa, acionamento e utilidade de C.2, revisões confirmadas/substituídas, fidelidade de C.3, chamadas, tokens e latência. Persistir commit, hashes dos templates, configuração e protocolo, e incluir o braço simples na exportação de regressões para verificar a seleção informada.

**Como a proposta pretende resolver:** os testes programáticos verificam a implementação, a avaliação por fase mede se o modelo detecta melhor os defeitos e a comparação completa mede se isso melhora as respostas finais. Incluir acertos, erros e os dois braços permite identificar ganhos que custam novas regressões, além de separar melhora de formato de melhora de conteúdo. As versões persistidas tornam a comparação rastreável, sem fornecer gabaritos ao harness.

Essas mudanças na avaliação pertencem ao benchmark e à auditoria; o núcleo continua recebendo somente o pedido textual e os artefatos previstos pelo método. Não se recomenda substituir o fluxo por uma resposta simples de reserva, comitê de modelos, votação ou revisor posterior a C.3. O ganho a buscar é fazer **as verificações existentes reconhecerem os defeitos concretos e encaminhá-los à investigação já prevista**, mantendo estimativas legítimas e a generalidade do Ralph Loop adaptado.

## 11. Avaliação da proposta revisada — duas frentes

**Decisão do usuário:** tratar planejamento com uma nova fase A.3, renomeando a extração de aprendizados do enunciado para A.4; ampliar B.2 para validar a tarefa como um todo; elevar o máximo de tentativas de três para cinco. As melhorias 10.4, 10.5, 10.6 e 10.7 permanecem adiadas.

**Parecer:** as duas frentes formam um próximo incremento bem direcionado às causas principais observadas. A primeira procura impedir que uma interpretação falsa se torne obrigação de execução; a segunda procura impedir que uma resposta tecnicamente errada seja aprovada por obedecer à tarefa. São suficientes para delimitar uma implementação coerente e avaliável, mas **não permitem prometer a correção de todos os 13 casos nem ganho de acurácia sem nova medição**. Um validador do mesmo modelo também pode aceitar uma premissa falsa ou rejeitar um raciocínio correto.

**Estado de implementação deste ajuste:** o limite existente de tentativas por tarefa foi elevado para cinco no default, no exemplo de ambiente e no `.env` local, com atualização da documentação e do teste correspondente. A nova A.3, a renumeração para A.4 e as mudanças de B.2 estão descritas abaixo como proposta; ainda não foram implementadas.

### 11.1. Frente 1 — A.3 valida a decomposição antes da execução

**Estado atual:** A.2 produz um lote estruturalmente válido, que é convertido em tarefas e inserido na fila imediatamente. Depois, a atual A.3 extrai aprendizados e a execução começa. Não há julgamento semântico separado da qualidade do plano antes de executá-lo.

**Fluxo proposto:**

```text
A.1 — Critérios gerais
  ↓
A.2 — Decomposição: gera um plano candidato
  ↓
A.3 — Task Decomposition Validator
  ├─ approved: false → A.2 revisa o plano com o relatório
  │                       ↓
  │                  nova A.3, em contexto novo
  └─ approved: true → confirma o plano na fila
                          ↓
A.4 — Key Learnings from the Question
  ↓
B — Execução e validação das tarefas
  ↓
C — Fluxo atual de verificação global e síntese
```

**Entrada indispensável de A.3:** enunciado original, critérios gerais de A.1 e somente o plano candidato da rodada atual, além das regras fixas de avaliação. A expressão “somente o novo plano” deve restringir o histórico de versões, não retirar o enunciado: sem a referência original, A.3 pode considerar coerente um plano que omitiu ou reinterpretou uma condição importante. As restrições efetivamente fornecidas pelo usuário prevalecem se A.1 também tiver inventado alguma obrigação.

A.3 não recebe planos antigos, motivos de reprovações anteriores, conversa de A.2 ou aprendizados ainda não extraídos. Cada validação abre uma janela nova. Assim, julga a versão atual sem saber que determinada formulação foi objeto de uma correção anterior.

**O que validar:**

| Dimensão | Verificação do plano |
|---|---|
| Fidelidade | Dados, referentes e condições do pedido estão preservados, inclusive quando parecem contraditórios e são objeto de investigação? |
| Neutralidade | Títulos, descrições e critérios deixam conclusões desconhecidas em aberto, em vez de exigir “o resultado é X” ou uma classificação qualitativa determinada? |
| Aplicabilidade | Um método proposto depende de condições ainda não demonstradas? O plano permite verificá-las, sem tratá-las como dados fornecidos? |
| Critérios | São verificáveis, complementares e relacionados ao objetivo, sem exigir uma hipótese conveniente ou importar apresentação final desnecessária? |
| Decomposição | Cada tarefa tem um objetivo claro, dados suficientes e ordem compatível com suas dependências? A divisão evita mera transcrição e repetição? |
| Cobertura | O conjunto chega à determinação pedida e deixa para C.3 somente apresentação e associações literais já sustentadas? |

Essas dimensões precisam pertencer ao **template fixo do validador**, não ser geradas por A.2. Avaliar o plano somente pelos critérios escritos dentro dele repetiria o problema de autoconfirmação encontrado no benchmark.

**Limites do julgamento:** A.3 não resolve o problema nem escolhe uma resposta. Também não deve rejeitar qualquer número, fórmula ou método: um dado literal pode ser obrigatório, um método pode ser pertinente e uma hipótese pode ser justificável. O defeito é transformar uma conclusão desconhecida ou condição não estabelecida em obrigação. Uma investigação que pode concluir “esse método não se aplica” continua válida.

**Contrato de resposta proposto:** booleano real em `approved`, acompanhado de problemas e ajustes quando reprovado. Exemplo ilustrativo de estrutura, sem solução de domínio:

```json
{
  "approved": false,
  "issues": [
    {
      "task_id": "T2",
      "criterion_id": "T2-AC1",
      "problem": "O critério obriga a confirmar uma classificação que deveria ser investigada.",
      "adjustment": "Solicitar a determinação da classificação e sua fundamentação, mantendo o resultado em aberto."
    }
  ]
}
```

Problemas do plano inteiro podem usar referências nulas; referências preenchidas devem apontar para tarefas/critérios existentes no candidato. `approved: false` exige pelo menos um problema concreto; `approved: true` exige ausência de problemas impeditivos. O parser valida essa consistência e os tipos, sem decidir a verdade do parecer ou mudar o booleano. Os exemplos de texto acima explicam o contrato; os templates internos devem seguir a convenção do projeto de redação em inglês.

**Como A.2 revisa:** receber, em contexto novo, seu template, o pedido original, o último plano reprovado e o relatório correspondente. Preservar partes não afetadas, mas permitir mudar quantidade, ordem, descrições, critérios e IDs quando a correção exigir, respeitando as regras estruturais. A cada rodada, o plano de referência é o candidato mais recente; não se deve reiniciar sempre do primeiro plano nem reenviar indefinidamente toda a cadeia de versões.

O feedback identifica a imposição ou lacuna e a alteração necessária, sem antecipar qual resultado deve substituir o errado. Um relatório que manda trocar a conclusão X pela conclusão Y, sem execução, apenas transferiria a antecipação de A.2 para A.3.

**Como a proposta pretende resolver:** o plano deixa de ser executável só por passar no parser e passa por uma avaliação específica antes de comprometer as tarefas posteriores. A.2 pode concentrar-se em produzir descrições claras, critérios e dependências; A.3 concentra a auditoria de qualidade. A simplificação de A.2 deve retirar repetição e instruções extensas de autoauditoria, preservando regras essenciais de geração e o contrato de saída.

### 11.2. Frente 2 — B.2 valida a tarefa e o fundamento da resposta

**Estado atual:** B.2 já contém instruções de verificação técnica, mas recebe o resultado, critérios, notas e eventual proposta de revisão, sem a descrição da tarefa. O veredito estruturado está vinculado ao atendimento dos critérios locais. Na prática, houve aprovações que reconheceram uma explicação completa sem detectar que a relação ou hipótese estava errada.

**Proposta:** fornecer descrição e objetivo da tarefa, critérios, resultado preliminar e aprendizados em áreas separadas. B.2 deve avaliar o atendimento dos critérios e a sustentação técnica do resultado dentro daquele escopo. Essa sustentação inclui compatibilidade com dados, aplicabilidade do método, condições assumidas, ligação entre evidência e conclusão e justificativa de aproximações ou decisões por melhor ajuste.

**Complemento recomendado para tornar a mudança efetiva:** acrescentar programaticamente um **critério técnico fixo**, por exemplo `T2-TECH`, a toda avaliação B.2. Seu conteúdo vem do harness, não do planejador: a resposta deve resolver o objetivo da tarefa com fundamento compatível com seus dados e condições. É semelhante ao critério de revisão já acrescentado nas tarefas revisoras, mas aplica-se a toda tarefa.

Isso evita uma lacuna de contrato: se B.2 continuar obrigado a aprovar quando todos os critérios gerados por A.2 forem atendidos, acrescentar apenas instruções de “validar a tarefa inteira” pode não oferecer um lugar consistente para reprovar um erro técnico que esses critérios não capturam. Com o critério fixo, os critérios do plano podem estar formalmente atendidos e `T2-TECH` reprovado; a decisão será `reproved`, com esse identificador nas pendências, usando o formato atual de relatório.

O critério fixo não exige responder o problema inteiro em tarefas intermediárias, reproduzir o formato final ou demonstrar exatidão quando a tarefa admite estimativa. Também não autoriza B.2 a dispensar arbitrariamente critérios recebidos. Ele acrescenta uma condição estável de validade ao julgamento da tarefa, sem nova fase ou um segundo modelo.

**Justificativa real:** apontar o dado ou trecho que sustenta a premissa decisiva e a relação conferida. Onde for simples, verificar uma consequência por outro ângulo — direção de variação, limite, referência, estágio temporal ou compatibilidade entre partes da explicação. Isso não exige refazer toda a solução. Para reprovar, basta identificar o defeito e o que precisa ser investigado; a correção pertence a B.1.

**Aplicação de 10.3:** uma comparação entre respostas candidatas não valida o valor de origem. Da mesma forma, explicitar uma hipótese não a torna sustentada. B.2 deve conferir a base da determinação antes de aceitar o melhor ajuste, preservar aproximações legítimas e aplicar a mesma exigência de suporte a todas as hipóteses comparadas. A instrução de retentativa de B.1 precisa ser harmonizada com essa avaliação, mantendo conclusões não refutadas e tratando o defeito concreto.

**Como a proposta pretende resolver:** A.3 filtra a especificação antes de executá-la; B.2 examina a resolução produzida. Mesmo um plano aprovado pode ser resolvido incorretamente, e esse erro passa a ter uma causa explícita de reprovação, com feedback para a próxima tentativa. Essa divisão atende às duas frentes sem incorporar as mudanças adiadas de C.1, recuperação de contrato ou memória.

### 11.3. Limites de tentativa: cinco, com contadores distintos

**Estado atual do código antes deste ajuste:** `RALPH_MAX_TASK_ATTEMPTS=3` limitava cada ciclo B.1/B.2 a três tentativas, incluindo a inicial. Havia também dois outros limites: duas rodadas de planejamento adicional C.2 e duas retentativas de saída inválida, estas somadas à chamada inicial. São mecanismos diferentes, não um único contador geral de loops.

**Alteração implementada:** `RALPH_MAX_TASK_ATTEMPTS=5`, isto é, **uma tentativa inicial e até quatro retentativas por tarefa**. O default, `.env.example`, `.env` local e a tabela de configuração foram atualizados. Novas instâncias de configuração usam esse valor; um backend já em execução precisa recarregar sua configuração. Variáveis de ambiente externas ainda podem sobrescrevê-lo.

**Para o novo planejamento, recomenda-se um limite próprio**, por exemplo `RALPH_MAX_PLANNING_ATTEMPTS=5`, ainda a implementar. Cada tentativa corresponde a um candidato de A.2 seguido de seu julgamento A.3. Há no máximo cinco candidatos por episódio de planejamento; aprovar o primeiro encerra esse ciclo imediatamente.

Uma correção de JSON/contrato continua usando a recuperação existente e não é uma reprovação semântica de A.3 ou B.2. Os limites de C.2 e de saída inválida não foram elevados: alterar a recuperação de contrato corresponde ao item 10.5, adiado pelo usuário.

Todos os limites de chamadas, tokens e tempo permanecem ativos. Cinco tentativas são um teto, não a promessa de que haverá recursos para usar todas elas. Não se recomenda elevar automaticamente os demais tetos. Se A.3 ou B.2 nunca identificar o defeito, aumentar tentativas não muda o resultado: é necessário primeiro melhorar a detecção.

### 11.4. Complementos que mais contribuem dentro dessas frentes

Além das entradas de referência de A.3 e do critério técnico fixo em B.2, há três cuidados de implementação e uma extensão de escopo a considerar:

1. **Confirmar o plano somente após aprovação.** A fila e o contador de tarefas da sessão recebem apenas a versão aprovada em A.3. Candidatos recusados ficam na auditoria, sem consumir slots de tarefas executáveis ou aparecer como tarefas pendentes. Isso impede que uma correção crie duplicatas ou deixe tarefas antigas na execução.
2. **Versionar a mudança A.3 → A.4.** Nas sessões antigas, `phase = A3` significa extração de aprendizados; nas novas, significará validação de plano. Uma versão do fluxo persistida e transportada na consulta/exportação permite que backend e frontend interpretem corretamente os registros antigos, sem reescrever seu histórico. A renumeração precisa alcançar enums, templates, startup, eventos, parser, memória, UI e testes.
3. **Medir aprovações e reprovações corretas.** Os testes devem incluir planos ruins, planos válidos, hipóteses legítimas e resoluções corretas por aproximação. Um validador que rejeita tudo gera mais loops e não representa melhora. Testes roteirizados comprovam o protocolo; casos novos com modelo real medem a qualidade dos julgamentos. Uma execução sem correções ganha ao menos uma chamada A.3; esse custo precisa ser comparado com a utilidade das revisões.
4. **Recomendação adicional, ainda não adotada: reutilizar o validador de decomposição nos lotes de C.2.** C.2 também escreve tarefas e pode introduzir as mesmas imposições de A.2. Reaproveitar a avaliação, com o novo lote, o enunciado e o contexto explícito de pendências/resultados vigentes, evita que o controle de qualidade exista apenas no plano inicial. O validador continuaria sem histórico de candidatos e sem decidir respostas. Isso não exige novas verificações em C.1, mas amplia os pontos em que A.3 é chamada e deve ser documentado e medido separadamente.

Os três primeiros são parte da implementação consistente e da avaliação das frentes propostas. O quarto é um complemento com potencial de ganho caso o planejamento adicional seja acionado; não foi tratado como autorização para implementar uma mudança de C.2 nesta análise. Nos 13 casos examinados, não houve chamada de C.2, portanto o benefício direto dessa reutilização não pode ser medido por esse recorte.

### 11.5. Cobertura esperada dos problemas observados

| Casos | Como as duas frentes podem ajudar | Limite da expectativa |
|---|---|---|
| Radiação, NGS e zigoto | A.3 pode rejeitar o descarte de condição, a hierarquia de generalidade inventada e a causa antecipada; B.2 confere a resolução | O validador precisa reconhecer a imposição; uma explicação coerente ainda pode ser aceita por engano |
| World Series e ácido bórico | A.3 verifica condições de aplicação; B.2 examina os pesos, contribuições desprezadas e fundamento da aproximação | Um plano neutro não garante que o modelo saiba construir a modelagem correta |
| qPCR | A.3 pode apontar a direção antecipada contrária ao enunciado; B.2 confronta a interpretação com os pares observados | A melhora depende de efetiva conferência, não da presença de mais uma instrução |
| Reação com HBr e sequência com titanoceno | B.2 pode reprovar mecanismo sem suporte, hipótese aplicada assimetricamente e estrutura não determinada | Há conhecimento técnico ausente ou incorreto que o mesmo modelo pode continuar sem detectar |
| Cenários morais e sociologia | B.2 distingue inferência de fato fornecido e testa generalizações; A.3 verifica critérios e escopo | Interpretação e referência do dataset continuam exigindo avaliação externa; não basta aumentar reprovações |
| Singer e Parfit | B.2 pode evitar tratar narrativa plausível como evidência de atribuição a uma fonte | As duas frentes não acrescentam documentos ou fontes externas e não garantem corrigir conhecimento lembrado errado |
| Elétron | Nenhum efeito direto sobre a causa registrada: A.2 falha antes de produzir um plano estruturalmente válido para A.3 | A recuperação continua com o limite atual; a melhoria específica de contrato foi adiada |

**Risco residual relevante:** como a mudança de C.1 foi adiada, um erro que passe por A.3 e B.2 ainda pode seguir para C.3 pelo caminho atual. Isso é uma limitação do incremento escolhido, não uma razão para retomar agora o item 10.4. Da mesma forma, ficam mantidos os mecanismos atuais de memória, dependência e síntese.

Se B.2 identificar um critério de planejamento inviável que A.3 deixou passar, a simples repetição de B.1 pode não conseguir atender simultaneamente à tarefa e à correção técnica. Nesta versão da proposta não se acrescenta uma transição B.2 → planejamento: o defeito deve ficar explícito na auditoria e a execução pode terminar ao esgotar o limite. Essa ocorrência será uma métrica útil para avaliar se a nova A.3 está cumprindo seu papel.

### 11.6. Encaminhamento recomendado e verificação realizada

O próximo incremento pode se concentrar em **A.2 mais simples, nova A.3 com referência ao pedido e rubrica fixa, A.4 renumerada e B.2 com descrição da tarefa e critério técnico obrigatório**. O fechamento de cada correção deve ser demonstrado por avaliação nova, em contexto novo, e não pela concordância com o histórico de reprovações.

Na documentação metodológica, a nova fase deve aparecer como extensão explicitamente autorizada da proposta; a transcrição literal da metodologia original deve continuar preservada. As alterações de memória e de C.1 anteriormente sugeridas permanecem fora desse incremento. A reutilização do validador em C.2 fica como recomendação adicional delimitada acima.

Para o aumento já implementado de tentativas, foi atualizado o teste de default, confirmada sua falha com o valor anterior e aplicada a correção. Passaram **162 testes** de configuração, guardião de custo, startup e integração de limites; o lint dos dois arquivos Python alterados também passou. Não foi executado benchmark pago, e esses testes não demonstram melhora semântica. Nenhuma das novas fases ou regras de validação foi apresentada como já implementada.
