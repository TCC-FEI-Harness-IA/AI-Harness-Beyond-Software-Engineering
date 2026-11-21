# Análise das regressões do Ralph Loop no benchmark de Vestibulares

**Execução:** `bench_736136f41a3d4f09bee4e50eaca509c5`  
**Data da execução e da análise:** 7 de novembro de 2026  
**Material analisado:** oito questões da pasta [benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/).

## 1. Diagnóstico principal

Neste recorte, o Ralph Loop falhou principalmente porque **a validação de critérios gerados pelo próprio modelo não garantiu a correção da resposta original**. O fluxo conseguiu aprovar resoluções que obedeciam a tarefas enviesadas, conservar erros matemáticos como aprendizados, aceitar contradições entre resultados e encerrar a execução com conteúdo insuficiente. Em outro caso, a resolução estava correta, mas a síntese inventou a letra da alternativa depois que o mapeamento original deixou de chegar ao contexto.

Há evidências particularmente fortes de degradação causada pelo processamento adicional:

- **Geografia ENEM Q046:** uma tentativa com a resposta correta, D, foi reprovada; a retentativa mudou para A e foi aprovada.
- **Física ENEM Q105:** as duas análises físicas corretas foram aprovadas, mas uma tarefa posterior recebeu conclusões contrárias já inventadas no planejamento e escolheu C.
- **Química ENEM Q094:** o resultado aprovado identificou corretamente o teste 1, cálcio; a resposta final o apresentou como alternativa B, embora corresponda a A.
- **Física ITA Q005:** a recuperação de um erro de contrato transformou um plano de três tarefas em um plano com apenas a primeira. A validação global aceitou uma razão de distâncias como suficiente para responder um período em meses.

Esses casos sustentam uma conclusão sobre **esta implementação e estas execuções**: acrescentar planejamento, validações e síntese também acrescentou caminhos pelos quais uma solução correta pôde se perder. O recorte não demonstra que raciocínio explícito, em geral, seja pior que inferência direta.

## 2. Escopo, evidências e limites

Foram lidos o [README](README.md), o [fluxo adaptado](RALPH_LOOP_ADAPTADO.md), os 24 JSONs exportados, os prompts efetivamente enviados em `session.messages[].prompt_input` e os pontos pertinentes do backend. A análise acompanha a cadeia **primeira falha observável → propagação → aprovação → resposta final**. As contas quantitativas foram refeitas independentemente, com aritmética racional e enumeração em Python, sem novas chamadas ao modelo.

Nas referências abaixo, **`order` é o campo `session.messages[].order`**, iniciado em zero; identifica a mensagem dentro do JSON, não uma linha do arquivo.

### 2.1. O que pode ser afirmado sobre a inferência simples

O usuário informou que este recorte contém apenas questões acertadas pela inferência simples e erradas pelo Ralph Loop. Essa informação é adotada como condição de seleção. **Os arquivos fornecidos contêm somente as sessões Ralph**: não permitem inspecionar as respostas, configurações e justificativas do baseline nem comparar seu consumo. As sessões locais em `apps/backend/data/sessions/` também não continham registros com este `run_id` na consulta realizada.

Além disso, o [exportador atual](apps/backend/src/application/usecases/export_benchmark_ralph_errors_usecase.py) seleciona os desfechos incorretos do Ralph e **não testa se o baseline acertou**. Portanto, a propriedade “baseline certo, Ralph errado” depende da seleção informada pelo usuário; não é garantida pelo nome da pasta ou pelo código de exportação.

Não se calculam aqui acurácia da bateria completa, saldo entre ganhos e perdas, significância estatística ou superioridade geral de um modo. Também não se pressupõe que “inferência simples” comprove ausência de processamento interno do provedor: isso exigiria a configuração e os registros desse braço experimental.

### 2.2. Caracterização das oito sessões Ralph

| Campo | Observado |
|---|---|
| Modelo registrado | `deepseek/deepseek-v4-flash-0731` |
| Provedor | `open_router` |
| Temperatura da sessão | `0.0` em todas |
| Temperatura nas retentativas | `1.0`: correção de A.2 em ITA Q005 e segunda resolução de T2 em Geografia Q046 |
| `max_tokens` registrado | `500000`; não equivale ao tamanho de cada resposta nem comprova o limite do provedor |
| Estado final | Oito sessões `completed`, sem `failure`, `outcome.error` ou degradações registradas |
| Respostas finais | Oito letras válidas, todas diferentes do gabarito |
| Chamadas ao modelo | 106 |
| Tokens | 345.908: 284.351 de entrada e 61.557 de saída |
| B.2 | 22 avaliações: 21 aprovações e uma reprovação |
| C.1 | Oito aprovações na primeira avaliação; nenhuma execução de C.2 |
| Diagnósticos de saída | 105 conteúdos aceitos e uma recusa por contrato, recuperada em A.2 |
| Reparos estruturais locais | Oito saídas aceitas com `syntax_status = valid_after_repair` |
| Término do provedor | As 106 chamadas terminaram com `finish_reason = stop` |

Os oito reparos estruturais não são oito novas chamadas nem oito reprovações semânticas. A única recusa de contrato ocorreu no plano de Marte. Não há indicação de interrupção por comprimento do provedor ou de esgotamento de orçamento como causa destes resultados. O corte local do texto reenviado na recuperação de Marte, descrito adiante, é outro mecanismo.

## 3. Visão comparativa

| Questão | Gabarito | Ralph | Primeira falha relevante | Como chegou à resposta errada | Chamadas | Tokens |
|---|---|---|---|---|---:|---:|
| Física ENEM 2022 Q105 | A | C | A.2 inventa conclusões para T3 | T3 contraria T1/T2 corretas; C.1 aprova contradição | 14 | 41.288 |
| Física ENEM 2023 Q122 | D | A | A.2 embute interpretação errada nos critérios de T3 | Origem e consumo da energia são confundidos; B.2 exige a conclusão errada | 14 | 37.549 |
| Física ITA 2024 Q005 | B | A | Recuperação de A.2 elimina tarefas necessárias | C.1 aceita resultado intermediário como solução completa | 9 | 22.742 |
| Física ITA 2024 Q007 | E | D | A.2 troca aumento linear por angular na ocular | Fórmula imposta pela tarefa produz 89,3; escolhe-se 75 por proximidade | 17 | 46.924 |
| Geografia ENEM 2022 Q046 | D | A | A.2 estreita a interpretação; B.2 reprova D | Retentativa racionaliza A e recebe aprovação | 13 | 40.427 |
| Matemática ENEM 2022 Q137 | C | A | B.1/T2 confunde probabilidade condicional com conjunta | Obtém metade do valor correto; validação aceita a opção mais próxima | 14 | 43.500 |
| Matemática FUVEST 2024 Q034 | A | E | A.2 enfraquece a definição de moda | Conta casos sem moda e erra a contagem; C.1 afirma que 47 coincide com 44 | 17 | 96.045 |
| Química ENEM 2023 Q094 | A | B | A.3 omite as alternativas | C.3 associa o teste correto à letra errada | 8 | 17.433 |

## 4. Análise por questão

### 4.1. Física ENEM 2022 Q105 — o planejamento antecipa respostas falsas

**Tema:** força média e energia dissipada em colisões com pneus ou blocos deformáveis.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-FISICA_ENEM_2022_AZUL_Q105/execucao-ralph-loop.json).

**Resposta correta.** Para a mesma massa, velocidade inicial e duração da colisão, sejam `v > 0` a velocidade de aproximação e `u > 0` o módulo da velocidade de retorno nos pneus:

- Pneus: `|Δp| = m(v + u)`; blocos: `|Δp| = mv`. Logo, a força média é maior nos pneus.
- Pneus: `E_diss = mv²/2 − mu²/2`; blocos: `E_diss = mv²/2`. Logo, a dissipação é maior nos blocos.

As duas conclusões correspondem exatamente a **A**.

**Rastro observado.**

1. A.2 (`order=2`) planeja T1 para a força e T2 para a energia, mas escreve na descrição de T3 duas supostas conclusões anteriores: força maior nos blocos e energia igual nas colisões. Elas ainda não haviam sido calculadas e ambas são falsas.
2. B.1/T1 (`order=5`) encontra corretamente força maior nos pneus; B.1/T2 (`order=10`) encontra corretamente dissipação maior nos blocos. Ambas são aprovadas, e B.4 registra os resultados corretos.
3. B.1/T3 (`order=15`) obedece às premissas falsas da própria descrição e escolhe C. B.2 (`order=16`) aprova a correspondência entre a resposta e essas premissas.
4. C.1 (`order=19`, AC5) repete as conclusões corretas de T1/T2, mas afirma que elas eliminam todas as opções e que C seria a mais coerente. A opção A corresponde precisamente às duas conclusões.
5. C.3 (`order=20`) conserva C e mistura fundamentos corretos com conclusões incompatíveis. Escreve `v + u` para pneus e `v` para blocos, mas conclui força maior nos blocos. A explicação também diz dissipação maior nos blocos, enquanto o texto da opção C diz dissipação igual.

**Causa sustentada pelo registro:** contaminação antecipada do plano, seguida de validação local contra premissas falsas e falha de consistência global. A memória não perdeu a física correta: ela chegou às etapas seguintes e coexistiu com as afirmações contrárias. O fluxo já possuía informação suficiente para acertar e a degradou ao fazer a seleção.

### 4.2. Física ENEM 2023 Q122 — o critério transforma a conclusão errada em obrigação

**Tema:** energia fornecida pelo vapor à produção de doce de leite.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-FISICA_ENEM_2023_AZUL_Q122/execucao-ralph-loop.json).

**Resposta correta.** A energia fornecida ao produto provém do vapor na parede: resfriamento de 120 °C a 100 °C, com liberação de calor sensível, e condensação, com liberação de calor latente. A origem pedida corresponde a **D**. A evaporação da água do produto é o processo que recebe essa energia.

**Rastro observado.**

1. A.2 (`order=2`) separa a evaporação do produto, T1, da transformação do vapor na parede, T2. Essa separação permite análises locais úteis.
2. Entretanto, `T3-AC1` já determina que a energia é “proveniente do calor latente de vaporização da água do produto”. `T3-AC2` exige eliminar alternativas que omitam a vaporização. O planejamento passa a exigir a interpretação errada, em vez de pedir que ela seja investigada.
3. B.1/T2 (`order=10`) descreve corretamente os dois componentes da energia fornecida e afirma que essa combinação é transferida para o interior do tacho. B.2 a aprova.
4. B.1/T3 (`order=15`) escolhe A e rejeita D justamente por D descrever a energia liberada pelo vapor da parede — que é a origem solicitada. B.2 (`order=16`) aprova por coincidência com o critério gerado.
5. C.1 (`order=19`) considera a escolha sustentada; C.3 (`order=20`) repete A.

**Causa sustentada pelo registro:** confusão entre fonte e destino da energia introduzida como resposta nos critérios de A.2. B.2 validou adequação ao critério contaminado. Como T2 já continha a informação necessária para D, ampliar a resolução não foi suficiente para garantir uma integração correta.

### 4.3. Física ITA 2024 Q005 — correção de contrato perde o plano e C.1 não detecta a lacuna

**Tema:** estimativa do período de Marte a partir da variação da área aparente.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-FISICA_ITA_2024_F1_UNICA_Q005/execucao-ralph-loop.json).

**Resposta correta.** No modelo de órbitas aproximadamente circulares, a razão de distâncias é `√60 ≈ 7,7`. Sendo `R` o raio orbital de Marte e `r` o da Terra:

```text
(R + r)/(R − r) = 7,7
R/r = (7,7 + 1)/(7,7 − 1) ≈ 1,2985
T_Marte = 12 × (R/r)^(3/2) ≈ 17,76 meses
```

Portanto, a melhor estimativa entre as opções é **B, 18 meses**.

**Rastro observado.**

1. A primeira saída de A.2, preservada na auditoria (`order=2`), contém três tarefas: razão das distâncias, razão dos raios orbitais e aplicação da terceira lei de Kepler. Ela é rejeitada por ausência de `tasks.title`; a terceira tarefa não tem título.
2. Na chamada de correção, o `prompt_input` de A.2 (`order=3`) contém a resposta anterior limitada a **1.003 caracteres: os primeiros 1.000 e `...`**. Esse trecho termina dentro de T1 e não contém T2 nem T3. O enunciado original ainda está no primeiro prompt; a informação perdida é o restante do plano já produzido.
3. O código de [recuperação de fase](apps/backend/src/application/phases/base_thinking_phase.py), em `__compact_invalid_message`, confirma esse corte. Ele ocorre depois da recusa do parser, inclusive para violação de contrato, e antes de pedir a saída corrigida. O diagnóstico do provedor continua sendo `stop`: não se trata de corte por limite de geração.
4. A saída corrigida, com temperatura 1, contém apenas T1. O parser a aceita e a recuperação fica registrada como `recovered`. O plano recuperou o contrato, mas perdeu a cobertura do problema.
5. B.1/T1 (`order=6`) calcula corretamente `d_oposição/d_conjunção ≈ 0,13`. B.2 o aprova porque esse é o objetivo local.
6. C.1 (`order=10`, AC2 e AC5) considera a razão de distâncias suficiente para estimar o período e selecionar uma opção. Não solicita as etapas ausentes. C.3 (`order=11`) apenas apresenta a razão e termina com A, 13 meses, sem calcular período algum.

**Causa sustentada pelo registro:** perda de cobertura durante a recuperação, seguida de falso positivo de suficiência em C.1. O corte em 1.000 caracteres é um fator concreto que removeu T2/T3 da saída anterior reenviada; o registro não permite atribuir isoladamente a ele, ou à temperatura, toda a mudança de plano. O enunciado continuava disponível para replanejar corretamente.

Não há base para afirmar que o modelo converteu deliberadamente `0,13` em `13 meses`: a escolha não foi fundamentada. O que está demonstrado é que uma grandeza adimensional foi aceita como base completa para responder uma grandeza temporal.

### 4.4. Física ITA 2024 Q007 — o plano impõe a grandeza e a fórmula erradas

**Tema:** aumento linear de um microscópio de duas lentes.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-FISICA_ITA_2024_F1_UNICA_Q007/execucao-ralph-loop.json).

**Resposta correta.** Aplicando `1/f = 1/p + 1/p'` às duas lentes, com distâncias em milímetros:

```text
Objetiva: f₁ = 5; p₁ = 5,2 → p'₁ = 130; m₁ = −130/5,2 = −25
Objeto para a ocular: p₂ = 190 − 130 = 60
Ocular: f₂ = 70 → p'₂ = 1/(1/70 − 1/60) = −420
m₂ = −p'₂/p₂ = 7
|m₁ × m₂| = 175 → alternativa E
```

**Rastro observado.**

1. A.2 (`order=2`) planeja corretamente a posição da imagem e o aumento da objetiva, mas T3 pede **aumento angular** da ocular com `M = 250 mm/f_ocular`. Introduz um ponto próximo de 250 mm, não fornecido, e a hipótese de imagem final no infinito.
2. A descrição de T3 também situa a imagem a 130 mm da ocular, antecipando e trocando a referência espacial do resultado. Os 130 mm corretos, posteriormente obtidos, são medidos a partir da objetiva; a distância relevante para a ocular é 60 mm.
3. T1 e T2 (`order=5` e `10`) encontram corretamente 130 mm e aumento 25. T3 (`order=15`) executa a fórmula imposta e obtém aproximadamente 3,57. Seu validador aprova a aplicação da fórmula e a hipótese de imagem no infinito sem confrontá-las com a configuração real.
4. T4 (`order=20`) multiplica 25 por 3,57, obtém 89,3 e seleciona D, 75, por proximidade. A própria tabela registra diferença de cerca de 16% em relação ao valor calculado.
5. C.1 (`order=24`) declara a aproximação razoável; C.3 conserva D.

**Causa sustentada pelo registro:** mudança de aumento linear para angular e hipótese óptica indevida impostas pelo plano, seguidas de validação da execução da receita. A distância de 190 mm e o resultado de 130 mm não foram perdidos: o erro foi deixar de usá-los para determinar a configuração da ocular. A seleção por proximidade encobriu o resultado incompatível com as alternativas.

### 4.5. Geografia ENEM 2022 Q046 — a validação reverte uma resposta correta

**Tema:** experiência de Santa Luzia e interpretação das condições ambientais do sertão.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-GEOGRAFIA_ENEM_2022_AZUL_Q046/execucao-ralph-loop.json).

**Resposta correta.** A prática religiosa descrita é um meio de interpretar chuva e seca. A consequência expressa pela alternativa **D** é a intimidade com a Caatinga pela interpretação das condições ambientais. A presença da religiosidade na descrição não exige que a alternativa repita explicitamente os dois aspectos.

**Rastro observado.**

1. A.2 (`order=2`) exige, em `T2-AC2`, explicar como a alternativa captura simultaneamente religiosidade, já associada a “devoção/aceitação de destinos sagrados”, e paisagem. A expressão da opção A passa a orientar a interpretação do critério.
2. A primeira B.1/T2 (`order=10`) compara todas as opções, escolhe **D** e explica que a religiosidade está pressuposta no rito usado para interpretar o ambiente. Registra que nenhuma opção explicita inteiramente os dois aspectos.
3. B.2 (`order=11`) reprova apenas `T2-AC2` porque D não explicita a religiosidade, apesar da explicação contextual. O prompt de B.2 orientava aceitar inferências e evitar literalismo.
4. Na retentativa, com temperatura 1 e feedback explícito, B.1/T2 (`order=12`) passa a escolher **A**. Argumenta que a paisagem está implícita em A e elimina D por omitir a religiosidade: a possibilidade de conteúdo implícito é aplicada de maneira assimétrica.
5. B.2 (`order=13`) aprova A; B.4 a transforma em aprendizado; C.1 e C.3 (`order=16` e `17`) a mantêm.

**Causa sustentada pelo registro:** critério enviesado no planejamento e aplicação inadequada pelo validador, que rejeita uma resposta correta e recompensa sua substituição por uma justificativa ajustada ao feedback. Este é o caso mais direto de degradação dentro de uma retentativa. O papel isolado da temperatura não é identificável: ela mudou junto com o feedback e o contexto explícito da tentativa.

### 4.6. Matemática ENEM 2022 Q137 — erro condicional passa como cálculo verificado

**Tema:** probabilidade de o vencedor do primeiro jogo ganhar uma melhor de sete.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-MATEMATICA_ENEM_2022_AZUL_Q137/execucao-ralph-loop.json).

**Resposta correta.** Fixando A como vencedor da primeira partida, essa vitória já está condicionada: só as partidas seguintes contribuem fatores `1/2`. Para terminar em `n` jogos com A campeão, há `C(n−2, 2)` sequências, cada uma com probabilidade condicional `2^(−(n−1))`.

```text
n = 4:  1/8   =  8/64
n = 5:  3/16  = 12/64
n = 6:  6/32  = 12/64
n = 7: 10/64  = 10/64
Total:            42/64 → C
```

Por simetria, esse também é o resultado sem nomear previamente o vencedor da primeira partida. Como conferência independente, completando conceitualmente seis jogos futuros, a probabilidade é `Σ C(6,k)/64`, para `k=3,...,6`, igualmente `42/64`.

**Rastro observado.**

1. O plano de A.2 (`order=2`) pede considerar A vencedor da primeira partida. Não fixa o resultado errado.
2. B.1/T2 (`order=10`) anuncia uma probabilidade condicional, mas usa `2^(−n)` para cada sequência completa, incluindo novamente a partida já fixada. Obtém `21/64`, metade do correto.
3. B.2 (`order=11`) aprova explicitamente a fórmula “número de sequências × `(1/2)^N`”, mesmo reconhecendo que a primeira partida já foi vencida por A.
4. B.4 (`order=13`) registra os valores incorretos como fatos condicionais. T3 (`order=15`) recebe `21/64` da memória e seleciona A, `35/64`, por ser a mais próxima, com diferença de `14/64`.
5. B.2 e C.1 (`order=16` e `19`) aprovam a aproximação. C.3 repete o cálculo errado e a seleção.

**Causa sustentada pelo registro:** erro de probabilidade condicional na resolução, falso positivo na conferência matemática e propagação pela memória. A regra permissiva de aproximação transforma a ausência de correspondência em justificativa para escolher uma opção, em vez de provocar revisão. Aqui a primeira falha de cálculo ocorre em B.1, não no planejamento.

### 4.7. Matemática FUVEST 2024 Q034 — definição relaxada, enumeração errada e igualdade inventada

**Tema:** listas de cinco inteiros positivos com moda, mediana, média e amplitude iguais a 23.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-MATEMATICA_FUVEST_2024_F1_V_Q034/execucao-ralph-loop.json).

**Resposta correta.** Considerando listas em ordem não decrescente, como na modelagem do próprio fluxo, sejam `a ≤ b ≤ 23 ≤ d ≤ e`. A média impõe soma 115 e a amplitude impõe `e = a + 23`. É necessário que 23 seja a moda; uma lista com cinco valores distintos não identifica 23 como moda.

As soluções válidas têm exatamente dois valores 23:

- Forma `(a,23,23,d,e)`: `d=46−2a`, `e=a+23`, com `a=8,9,10,11`: quatro listas.
- Forma `(a,b,23,23,e)`: `b=46−2a`, `e=a+23`, com `a=12,13,14,15`: quatro listas.

Três valores 23 centrais exigiriam `2a=23`, sem solução inteira; os demais padrões com três ou mais valores 23 são incompatíveis com a soma, amplitude ou positividade. O total é **8, alternativa A**.

**Rastro observado.**

1. A.2 (`order=2`, T1/T2) enfraquece “moda = 23” para “23 aparece pelo menos tantas vezes quanto qualquer outro valor”. Isso permite indevidamente cinco valores distintos, com 23 aparecendo uma vez.
2. T1 e B.4 (`order=5` e `8`) consolidam essa interpretação. T2 (`order=10`) admite o caso `k=1`, além de listar padrões impossíveis numa lista ordenada, como `a=b=c=e=23` e `d>23`. B.2 aprova.
3. T3 (`order=15`) contém sucessivas autocorreções e restrições contraditórias. B.4 preserva sistemas e classificações imprecisas, que chegam a T4.
4. T4 (`order=20`) conta 39 listas para `k=1` e oito para `k=2`, chegando a 47. Além do erro de definição, a enumeração falha: para `a=9,10,11`, aceita respectivamente `d=e=32,33,34` depois de afirmar que esses valores precisariam ser distintos. A contagem correta de listas com todos os valores distintos nesse sistema é 36, não 39.
5. B.2 (`order=21`) aprova a contagem. C.1 (`order=24`, AC2/AC5) afirma que 47 corresponde à opção E e que a coincidência é exata, embora a opção E seja 44.
6. C.3 (`order=25`) reconhece que 47 não aparece nas alternativas, mas escolhe 44 por proximidade.

**Conferência independente.** A enumeração de todas as listas ordenadas com soma, mediana e amplitude fixadas encontrou oito listas com moda única 23. Se se admitir indevidamente o caso em que todos os elementos são distintos, o total passa a 44: oito válidas e 36 sem moda definida. Portanto, **44 também é compatível com um distrator ligado à definição relaxada**; essa interpretação do distrator é uma inferência da análise, não informação da banca.

**Causa sustentada pelo registro:** definição incorreta imposta no plano, erros de ordenação e contagem aceitos localmente, memória que os conserva e validação global que inventa uma igualdade. Foi o caso de maior consumo, 96.045 tokens, sem que o volume adicional produzisse uma verificação matemática confiável.

### 4.8. Química ENEM 2023 Q094 — a resposta conceitual está certa, o vínculo com a letra se perde

**Tema:** teste da água para controlar incrustações por sulfatos e carbonatos.  
**Fonte:** [execução completa](benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/questao-QUIMICA_ENEM_2023_AZUL_Q094/execucao-ralph-loop.json).

**Resposta correta.** O parâmetro relevante é cálcio, **teste 1**, que corresponde à alternativa **A**. A alternativa B é o teste 2, cloreto.

**Rastro observado.**

1. A.2 (`order=2`) cria uma tarefa suficiente para identificar número e parâmetro, proibindo escolher a letra. Essa divisão é compatível com deixar o pareamento à síntese, desde que as alternativas sejam preservadas.
2. A.3 (`order=3`) registra a tabela dos testes e o contexto químico, mas **omite A) 1, B) 2, C) 3, D) 4, E) 5**. O template mandava copiar todas as opções com seus identificadores.
3. B.1/T1 (`order=5`) encontra corretamente **1-Cálcio**. B.2 aprova e B.4 preserva a conclusão correta.
4. C.1 (`order=9`) declara que C.3 poderá aplicar a letra correta. Contudo, nem os resultados nem a memória contêm o mapeamento das alternativas.
5. O `prompt_input` de C.3 confirma a ausência desse mapeamento. Como C.3 recebe somente resultados, critérios e aprendizados, não vê o enunciado original. A síntese (`order=10`) escreve **“B (1-Cálcio)”** e termina com `RESPOSTA_FINAL: B`.

**Causa sustentada pelo registro:** extração incompleta em A.3, dependência exclusiva dessa memória para metadados da questão e geração sem suporte da letra em C.3. O conhecimento químico permaneceu correto. O [avaliador do benchmark](apps/backend/src/domain/services/benchmark_answer_evaluator.py) comparou corretamente a letra final B com o gabarito A; não é um falso erro de extração da resposta.

## 5. Mecanismos recorrentes

### 5.1. Aprovação formal não equivale a correção factual

Há três verificações diferentes no sistema:

| Camada | O que de fato verifica | Limitação exposta |
|---|---|---|
| Parser e contrato | JSON, tipos, campos e coerência entre avaliações e decisão | Aceita relatórios formalmente coerentes que justificam fatos falsos |
| B.2 | Atendimento aos critérios da tarefa | Pode premiar uma conclusão errada já embutida no critério |
| C.1 | Suficiência dos resultados em relação aos critérios gerais | Pode aprovar contradições e resultados intermediários ou inventar correspondência com opções |

Das 22 avaliações de B.2, a única reprovação eliminou uma tentativa com o gabarito correto, em Geografia. Todas as oito avaliações de C.1 aprovaram o material na primeira passagem. Em cinco casos a letra errada já estava explícita nos resultados das tarefas; na FUVEST, havia uma contagem errada sem correspondência com as opções. Em Marte e Química, C.1 aprovou material insuficiente para determinar a resposta solicitada com o pareamento correto.

Esse resultado não estima a qualidade de B.2/C.1 em toda a bateria, porque o recorte contém apenas erros. Demonstra, porém, que a presença de múltiplas aprovações não certifica correção nesses casos.

### 5.2. Planejamento pode produzir uma resposta antecipada disfarçada de requisito

O [template A.2](apps/backend/src/infra/templates/a2_task_decomposition.md) proíbe antecipar resultados, mas isso ocorreu em conclusões de colisão, interpretação térmica, modelo óptico e definição operacional de moda. Os critérios passaram a testar a concordância com essas escolhas.

O [template B.2](apps/backend/src/infra/templates/b2_task_verification.md) também contém uma tensão: manda não ignorar nem reescrever critérios, mas depois permite considerar atendido um critério com expressão pré-calculada incorreta quando a dedução estiver correta. Essa exceção não funcionou como proteção nos casos analisados. Seu alcance também não resolve automaticamente premissas qualitativas falsas, como a origem da energia no tacho.

As falhas são, portanto, uma combinação de **desobediência a regras já existentes** e **regras permissivas presentes nos próprios prompts**. Acrescentar apenas mais uma instrução para “ter cuidado” não enfrenta todos os mecanismos observados.

### 5.3. Proximidade numérica virou substituto de correção

As instruções efetivamente enviadas em A.1, A.2, B.2, C.1 e C.3 permitem selecionar a opção mais próxima sem exigir correspondência exata. Em particular, B.2 afirma que a falta de coincidência não justifica rejeição e que a seleção falha quando nenhuma opção é escolhida ou outra é evidentemente mais próxima.

Isso aparece diretamente nos casos:

| Questão | Resultado do fluxo | Opção aceita | Problema mascarado |
|---|---:|---:|---|
| ENEM Q137 | `21/64` | `35/64` | Erro de fator 2 na probabilidade, diferença de `14/64` |
| ITA Q007 | `89,3` | `75` | Grandeza/fórmula inadequadas, diferença de cerca de 16% do calculado |
| FUVEST Q034 | `47` | `44` | Definição e contagem incorretas; C.1 chega a declarar igualdade |

Aproximações podem ser legítimas, como a estimativa orbital de Marte. O problema é autorizá-las **sem derivar uma margem dos dados e do método**, inclusive em contagens inteiras e probabilidades exatas. Obrigar uma letra na saída não obriga a aprovar internamente qualquer cálculo.

### 5.4. Fresh Context depende da qualidade das entradas que atravessam as fases

O isolamento impede que cada fase consulte espontaneamente o enunciado ou a resolução anterior. Isso pode funcionar quando as entradas necessárias são preservadas. No recorte:

- Em Química, perdeu-se o mapeamento das opções; C.3 não tinha como recuperá-lo de suas entradas.
- Em Marte, perdeu-se parte do plano na recuperação; C.1 não exigiu os resultados ausentes.
- Em Colisões e Microscópio, os dados corretos estavam disponíveis, mas premissas da tarefa prevaleceram ou não foram confrontadas com eles.

Assim, não há uma causa única “o contexto foi reiniciado”. Há perdas reais em certos pontos e uso incorreto de informação presente em outros.

### 5.5. A memória transforma o resultado aprovado em premissa das etapas seguintes

B.4 preservou tanto resultados corretos quanto erros aprovados: `21/64`, aumento angular inadequado, 47 listas e a escolha A em Geografia. Não há, nesses casos, uma fonte independente que torne os aprendizados verdadeiros; eles herdam a confiabilidade da aprovação anterior.

Em Colisões, a memória chega a conter simultaneamente comparações físicas corretas e a afirmação de que C é correta, apoiada nas comparações opostas. A deduplicação textual não resolve contradições semânticas. O diagnóstico mais preciso é **propagação e consolidação de erro aprovado**, não necessariamente uma falha da extração B.4 em todos os casos.

### 5.6. A síntese pode introduzir erro depois da aprovação global

Segundo a [metodologia adaptada](RALPH_LOOP_ADAPTADO.md), C.3 só apresenta resultados aprovados. Mesmo assim, gerou a letra errada em Química e uma escolha sem cálculo do período em Marte. O [orquestrador](apps/backend/src/application/usecases/ralph_thinking_usecase.py), em `__run_final_answer`, encerra a sessão depois de aceitar o objeto de C.3; não há nova validação semântica do texto final.

Essa ausência está de acordo com a descrição do fluxo atual. Adicionar uma etapa posterior seria uma extensão metodológica, enquanto preservar opções e impedir que C.3 invente conteúdo reforça responsabilidades já previstas.

## 6. Melhorias recomendadas e como avaliá-las

As propostas abaixo não foram implementadas nem testadas em novas inferências. Elas decorrem dos mecanismos observados e precisam de avaliação separada para evitar ajustes excessivos a estas oito questões.

### 6.1. Prioridades

| Prioridade | Mudança proposta | Casos motivadores | Relação com o método |
|---|---|---|---|
| 1 | Preservar identificadores e textos das alternativas diretamente de `question.options` no benchmark, sem depender da extração livre de A.3 | Química | Reforça a conservação dos dados originais; para perguntas livres, manter extração validada |
| 1 | Corrigir recuperação de contrato sem descartar a parte necessária da saída anterior; verificar cobertura do plano após recuperação | Marte | Reforça a intenção de recuperação; checagem adicional deve ser documentada |
| 1 | Exigir consistência entre resultados e impedir que C.1 aprove uma conclusão final contradita por outros resultados aprovados | Colisões, Tacho | Reforço da coerência global; reconciliação com novas tarefas deve usar C.2 ou ser explicitada como extensão |
| 1 | Restringir aproximações às justificadas por hipóteses, arredondamentos ou precisão dos dados; incompatibilidade deve provocar revisão analítica | World Series, Microscópio, FUVEST | Altera a política permissiva atual dos prompts |
| 2 | Separar dados do enunciado, hipóteses e resultados derivados no plano; impedir resposta antecipada nos critérios | Colisões, Tacho, Microscópio, FUVEST | Reforça a regra já existente em A.2 |
| 2 | Em C.1, exigir evidência do resultado final pedido, com grandeza/unidade e vínculo com a opção quando aplicável | Marte, Microscópio, FUVEST | Reforça suficiência de conteúdo, sem transformar formatação em tarefa |
| 2 | Tornar verificável em B.2 a correção técnica, além da presença de explicação; usar verificadores determinísticos quando disponíveis | World Series, FUVEST | Acrescenta evidência externa ao julgamento do modelo; ferramentas devem ser descritas no protocolo |
| 2 | Rever critérios interpretativos que copiam linguagem de um distrator e reprovações por ausência literal de palavras | Geografia | Reforça a orientação existente contra literalismo |
| 3 | Conferir a resposta produzida por C.3 contra resultado selecionado e alternativas originais | Química, Colisões | Checagens estruturadas podem ser determinísticas; revisão semântica posterior acrescenta uma etapa |
| 3 | Avaliar menor decomposição para questões curtas e comparação com inferência direta ou raciocínio em uma chamada | Todos | Experimento alternativo; não deve ser apresentado como o mesmo Ralph Loop sem documentar a alteração |

Em uma divergência numérica, a tarefa de revisão deve investigar fórmula, condição e cálculo. Criar somente uma tarefa “escolher a opção mais próxima” repetiria o mecanismo encontrado. Da mesma forma, C.1 deve apontar a lacuna ou contradição e encaminhá-la a C.2, sem executar silenciosamente a análise que faltou.

### 6.2. Experimentos de ablação

Comparar o fluxo atual com variantes que alterem **um mecanismo por vez**:

1. Alternativas originais preservadas deterministicamente.
2. Recuperação de contrato com conteúdo necessário preservado e teste de cobertura do plano.
3. Política de aproximação condicionada à natureza e à precisão do problema.
4. Verificação de contradições e de cobertura da grandeza solicitada.
5. Estratégias de retentativa com feedback idêntico e temperatura controlada.
6. Conferência do resultado apresentado por C.3.

Manter modelo, configuração do provedor, questões e instrução de resposta comparáveis. Registrar a revisão dos templates e repetir as execuções, pois um único par de respostas não isola a contribuição de decomposição, feedback ou temperatura. Usar também questões fora deste recorte, incluindo casos em que o Ralph melhora a resposta, para medir regressões introduzidas pelas correções.

Além da acurácia final, registrar:

- **Regressão:** baseline certo e Ralph errado, sobre a bateria completa.
- **Recuperação:** baseline errado e Ralph certo.
- **Reversão por validação:** tentativa correta reprovada e substituída por tentativa errada.
- **Erro de síntese:** resultado aprovado correto e resposta final incorreta.
- **Cobertura após reparo:** etapas necessárias presentes antes e depois de uma correção de saída.
- **Custo:** chamadas, tokens e latência, com desfechos semânticos separados de falhas técnicas.

O gabarito deve servir à avaliação externa desses eventos, sem ser disponibilizado aos agentes durante a resolução.

## 7. Verificações reproduzíveis

O trecho abaixo reproduz as conferências quantitativas usadas nesta análise com a biblioteca padrão de Python. Ele não executa o harness nem chama modelos.

```python
from collections import Counter
from fractions import Fraction
from math import comb

# ENEM Q137: condicionar à vitória já ocorrida na primeira partida.
termos = [Fraction(comb(n - 2, 2), 2 ** (n - 1)) for n in range(4, 8)]
assert sum(termos) == Fraction(42, 64)
assert Fraction(sum(comb(6, k) for k in range(3, 7)), 64) == sum(termos)

# ITA Q007: distâncias em mm e aumento linear de cada lente.
p1 = Fraction(26, 5)
q1 = 1 / (Fraction(1, 5) - 1 / p1)
p2 = 190 - q1
q2 = 1 / (Fraction(1, 70) - 1 / p2)
assert (q1, p2, q2) == (130, 60, -420)
assert abs((-q1 / p1) * (-q2 / p2)) == 175

# ITA Q005: estimativa com a aproximação fornecida para sqrt(60).
razao_raios = (7.7 + 1) / (7.7 - 1)
periodo_meses = 12 * razao_raios ** 1.5
assert 17.7 < periodo_meses < 17.8

# FUVEST Q034: a <= b <= c=23 <= d <= e, soma 115, e-a=23.
validas, distintas = [], []
for a in range(1, 24):
    e = a + 23
    for b in range(a, 24):
        d = 115 - a - b - 23 - e
        if not 23 <= d <= e:
            continue
        lista = (a, b, 23, d, e)
        freq = Counter(lista)
        if freq[23] > max((v for k, v in freq.items() if k != 23), default=0):
            validas.append(lista)
        if len(freq) == 5:
            distintas.append(lista)
assert len(validas) == 8
assert len(distintas) == 36
print(validas)
```

## 8. Implicação para o paper

Os registros recomendam distinguir **controle do processo**, **correção semântica dos resultados** e **fidelidade da resposta final**. O harness controlou execução e formato, mas a aprovação pelo próprio modelo não assegurou as outras duas propriedades.

Uma formulação compatível com a evidência seria:

> No recorte de oito questões informado como acerto do baseline e erro do harness, a análise dos rastros identificou contaminação do planejamento, falsos positivos e um falso negativo de validação, perda de informação na recuperação e na memória de entrada, e erro de associação na síntese. Em casos específicos, resultados intermediários corretos foram substituídos ou apresentados de maneira incorreta. Esses achados mostram mecanismos pelos quais a orquestração pode degradar a resposta, mas não permitem estimar sua frequência na bateria completa nem concluir inferioridade geral do raciocínio iterativo.

A hipótese a testar é que **o benefício do loop depende da confiabilidade das verificações e da preservação das informações entre etapas**, e não apenas da quantidade de chamadas ou de explicação produzida.
