## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem contexto da conversa anterior. Implemente esta etapa, incluindo testes e documentação, usando o estado atual do workspace.
- Esta é a etapa 04 de sete. Execute após as melhorias de recuperação integral, aprendizados e planejamento, documentadas como **Melhorias do thinking — 01 a 03**. Preserve essas alterações e leia seus testes.
- O harness deve continuar generalista. A política desejada **permite aproximações, inferência interpretativa, eliminação e melhor ajuste**, mesmo sem um cálculo direto que coincida com a resposta escolhida. Não acople validação a `question.options`, a vestibulares ou a gabaritos.

## O problema

Os prompts atuais têm duas tendências prejudiciais. Em alguns casos exigem literalidade ou formato fora de hora e rejeitam uma boa solução; em outros aprovam um resultado apenas porque alguma alternativa foi escolhida. A flexibilização foi criada porque respostas aproximadas do baseline acertavam, e essa capacidade deve ser preservada. O objetivo é distinguir uma escolha fundamentada de uma contradição ou análise essencial ausente.

Casos concretos:

- Geografia ENEM Q046: a primeira tentativa escolheu corretamente D e explicou que o rito religioso permitia interpretar chuva e seca. B.2 reprovou por D não explicitar religiosidade. A nova tentativa escolheu A e teve aceitação de conteúdo implícito que fora negada a D.
- Matemática ENEM Q137: com a primeira vitória já condicionada, a execução voltou a multiplicar sua probabilidade por 1/2 e obteve `21/64`, metade do correto `42/64`. B.2 aprovou a conta. Uma tarefa escolheu `35/64` por proximidade, e C.1 aprovou. O problema demonstrável é o condicionamento errado, não simplesmente a distância entre números.
- Colisões ENEM Q105: T1 e T2 concluem corretamente força maior nos pneus e dissipação maior nos blocos; T3 afirma o oposto. C.1 aprova uma contradição real.
- Marte ITA Q005: o pedido é período em meses; existe só uma razão de distâncias. C.1 aprova conteúdo insuficiente em vez de chamar C.2.
- FUVEST Q034: C.1 afirma que o resultado 47 corresponde exatamente à alternativa 44. Isso é uma afirmação falsa de igualdade, distinta de selecionar 44 explicitamente por aproximação.

## Sua tarefa

### Leitura e pontos de intervenção

Leia a documentação metodológica e as extensões já implementadas. Inspecione:

- Todos os nove templates em `apps/backend/src/infra/templates/`, principalmente `b1_task_resolution.md`, `b2_task_verification.md` e `c1_global_verification.md`;
- `apps/backend/src/application/usecases/ralph_thinking_usecase.py` e os tipos `VerificationReport`, `GlobalApproval`, `ValidationContext`;
- `apps/backend/src/infra/adapters/structured_response_parser_adapter.py`;
- `apps/backend/tests/application/usecases/test_ralph_scope_sufficiency_integration.py`;
- `apps/backend/tests/application/phases/`, testes de parser e `tests/doubles/ralph_scenario.py`.

### Política a implementar de forma consistente

1. **Resultado exato:** aceitar quando sustentado pelos dados e pela análise da tarefa.
2. **Resultado aproximado ou melhor ajuste:** aceitar quando a resolução fundamenta a escolha com comparação, eliminação, precisão disponível, hipótese explicitada, ordem de grandeza ou inferência contextual pertinente. Coincidência exata e cálculo direto até o valor da opção não são condições universais de aprovação. Não exija prova extra só porque existe diferença numérica.
3. **Contradição real:** pedir revisão quando há afirmações incompatíveis sobre o mesmo objeto, grandeza e condições; conta que contradiz a própria conclusão; troca de unidade/referência; igualdade falsa; ou hipótese que conflita com os dados disponíveis. Resultados sobre objetos, referenciais ou hipóteses diferentes não são automaticamente contraditórios.
4. **Conteúdo essencial ausente:** pedir complementação quando falta a determinação solicitada ou a análise indispensável, e a escolha não está sustentada nem por aproximação/eliminações já realizadas. Não considerar uma razão adimensional como cálculo de um período, nem delegar cálculo ausente a C.3.
5. Não crie tolerância percentual universal, proibição de aproximação em todo problema inteiro, regra “qualquer divergência reprova” ou regra “se escolheu uma opção, aprova”. A diferença numérica isolada não decide a validade.

### Responsabilidades das fases

- **B.1:** raciocinar dentro do escopo, apresentar fundamento e preservar diferença entre resultado calculado e escolha por melhor ajuste. Não obedecer a número/conclusão antecipada equivocadamente no plano como se fosse verdade demonstrada. A regra de comparar opções não deve mascarar um erro de cálculo já identificável. Selecionar uma opção pode continuar obrigatório quando o usuário assim pede, sem tornar a análise automaticamente correta.
- **B.2:** conferir tecnicamente os critérios locais, incluindo relações entre fórmula, condições, dados e conclusão; presença de uma explicação não equivale à sua correção. Admitir paráfrases e conteúdo implícito de maneira consistente para as opções comparadas. Não exigir que uma tarefa intermediária resolva toda a pergunta, nem transformar formato final em obrigação interna.
- **C.1:** avaliar a união dos resultados quanto a suficiência e consistência. Quando aprovar, indicar evidência produzida, inclusive fundamento da aproximação/seleção quando pertinente. Quando reprovar, identificar a lacuna ou contradição e o que precisa ser investigado, sem executar a análise ausente nem decidir antecipadamente qual tarefa deve ser considerada errada.
- **C.2:** receber a lacuna e criar investigação específica com resultado explicado; não criar somente “escolher a mais próxima” para encobrir defeito conhecido nem uma tarefa que apenas imprima a linha final. Pode investigar resultado previamente aprovado se a validação apontou motivo concreto. A etapa 05 implementará a gestão explícita de resultados corrigidos e aprendizados obsoletos.

Reescreva as passagens conflitantes de todos os templates afetados. Em especial, remova de B.2 a autorização irrestrita de aprovar só porque a opção mais próxima foi selecionada e de C.1 a aprovação automática de aproximação independente do resto da análise. Harmonize A.1/A.2/C.2/C.3 sem desfazer a separação entre análise, suficiência e apresentação estabelecida na etapa 03.

O parser continua validando estrutura e coerência formal de relatórios: IDs exatos, uma avaliação por critério, `unmet_criteria_ids` correto e decisão consistente. Não invente um validador semântico por regex, não converta reprovação em aprovação automaticamente e não relaxe tipos para acomodar saídas inválidas.

Cobertura depois da recuperação: crie um cenário no qual A.2 recuperada ainda traz só uma tarefa intermediária. C.1 deve poder declarar o conteúdo insuficiente, C.2 completar as tarefas e uma nova C.1 anteceder C.3. Não adicione fase extra de validação de plano nem teste cobertura por quantidade de tarefas.

### TDD e critérios de aceite

Use testes de contrato dos templates reais e cenários com LLM roteirizado para exercitar:

1. `17,76 meses` com escolha de `18 meses` aprovada, sem C.2 desnecessária.
2. Resultado calculado `23`, opções sem 23 e escolha de `20` fundamentada pela comparação disponível: aprovação permitida; falta de igualdade sozinha não causa reprovação. Inclua uma escolha por inferência/eliminações sem cálculo direto que produza o valor da opção.
3. Pergunta aberta com estimativa, unidades e hipótese explicitada aceita e apresentada como estimativa.
4. Erro de condicionamento como o de Q137 identificado no feedback; C.1 envia pendência a C.2 quando o erro aprovado antes impede resposta sustentada. Não testar isso com regra de distância entre alternativas.
5. Resultados de colisão contraditórios geram pendência específica; uma diferença explicada por hipóteses distintas não provoca falsa contradição.
6. Razão de distâncias sem período produz passagem C.1 → C.2 → B → C.1 → C.3. A falta apenas de marcador final ou tradução não provoca essa passagem.
7. Geografia: o contrato admite religiosidade implícita na interpretação ambiental e não exige palavras literais. O feedback não força mudar uma resposta correta apenas por ausência do termo.
8. Relatório com `met=false` e decisão `approved` continua sendo erro de contrato recuperável, enquanto reprovação coerente é saída aceita semanticamente. Preserve diagnósticos, limites e contabilização.

Os vereditos roteirizados demonstram a fiação, não que o modelo reconhece os erros. Documente uma matriz de avaliação semântica com exemplos positivos e negativos, sem alegar melhora de acurácia medida se não houve avaliação real. Não enfraqueça testes existentes de aproximação apenas para torná-los compatíveis com maior rigidez.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: escreva os testes primeiro, confirme a falha e implemente em seguida o comportamento exigido.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown. Preserve envelopes JSON, idioma final do usuário e formatação solicitada.
- Preserve arquitetura, Fresh Context, histórico explícito de retentativas, memória separada dos resultados e temperatura 1 em retentativas. C.1 identifica problemas; a investigação é executada nas tarefas de C.2/B.
- Não adicione consulta a gabarito, campo especializado de benchmark, fase nova de LLM, aproximação universal ou pós-validação de C.3.
- Execute testes focados e, em `apps/backend`, `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`. Não reduza os requisitos do projeto.
- Não faça chamadas pagas a modelos e não declare garantias semânticas com base só em fakes.

## Documentação das alterações:
- Documente cada mudança na lógica e a política de flexibilidade com exemplos de aceitação e reprovação, incluindo casos sem coincidência exata que continuam válidos.
- Acrescente ao `NOVAS_REGRAS_RALPH_LOOP.md` existente na raiz a seção **Melhorias do thinking — 04: validação, consistência e aproximações fundamentadas**. Preserve seções anteriores; crie esse arquivo `.md` somente se ausente.
- Explique a distinção entre contrato, verificação técnica local, suficiência global, contradição e aproximação. Registre limites dos testes e o uso de C.2 para investigar, sem diagnóstico automático de verdade pelo parser.
- Atualize as extensões de `RALPH_LOOP_ADAPTADO.md` e a documentação técnica pertinente, preservando a transcrição literal do paper.
- Na entrega, liste mudanças, testes executados, resultados e casos que ainda dependem de avaliação semântica com modelo real.
