# Validação da etapa 04 — validação e aproximações

Data: 7 de novembro de 2026.

## Parecer

**A implementação está de acordo com o planejamento da etapa 04, após dois ajustes pontuais realizados nesta revisão.** A suíte final passou em **2.231 testes**, com **100,00% de cobertura de código e branches**, e lint sem erros. Não foi encontrado acoplamento programático novo a múltipla escolha ou resolução fixa de questões específicas.

Foram preservadas as decisões do usuário: perguntas abertas continuam admitidas; aproximação, eliminação e inferência contextual não exigem coincidência exata; escolher uma opção não prova correção; contradições concretas e conteúdo essencial ausente devem gerar investigação pelas fases existentes.

## Escopo examinado

A base é o commit `6835023` da branch `feature/realph-loop`, já contendo as etapas 01–03. A fase 04 foi encontrada como alterações locais ainda não commitadas. Foram revisados:

- o [prompt da etapa 04](feature_melhorias_thinking/04_validacao_e_aproximacoes.md);
- os diffs dos sete templates alterados e a compatibilidade com A.3/B.4;
- a instrução de retentativa em `RalphThinkingUseCase`;
- os três novos módulos de testes, a matriz semântica de 15 casos e seu guia;
- documentação de metodologia, novas regras e README do backend;
- parser, responsabilidades das fases e testes existentes de recuperação, escopo e suficiência.

## Conformidade com o plano

| Requisito | Evidência revisada | Resultado |
|---|---|---|
| Aproximação fundamentada continua permitida | A.1/A.2/B.1/B.2/C.1/C.2/C.3 admitem melhor ajuste, eliminação e inferência; os casos de 17,76 → 18 e 23 → 20 permanecem nas fixtures de regressão | Conforme |
| Sem tolerância universal ou exigência geral de cálculo direto | Política distingue fundamento da escolha de igualdade numérica | Conforme |
| B.2 verifica conteúdo técnico local | Aplicabilidade, dados, unidades, encadeamento e conclusão; não basta existir explicação | Conforme |
| Interpretação sem literalismo assimétrico | Mesma régua de conteúdo implícito para as opções; retentativa pode explicitar vínculo sem abandonar uma conclusão sustentada | Conforme |
| C.1 verifica suficiência e consistência | Distingue contradição real de objetos, referenciais ou hipóteses diferentes; identifica pendência e evidência por critério | Conforme |
| Lacuna segue para C.2 | Testes exercitam C.1 → C.2 → B → C.1 → C.3 e cobertura após recuperação de A.2 | Conforme |
| C.1 não resolve silenciosamente a lacuna | Instruções encaminham a investigação sem produzir a análise ausente ou escolher previamente a tarefa errada | Conforme |
| C.2 investiga o defeito | Não basta escolher a mais próxima de um valor já apontado como incorreto ou imprimir uma linha final | Conforme |
| Apresentação continua em C.3 | Idioma, marcador e concisão são apresentação; aproximação não vira igualdade | Conforme |
| Contratos e recursos preservados | Parser sem alteração, IDs e decisões consistentes, recuperação, temperaturas, contabilização e isolamento cobertos pela suíte | Conforme |
| Nenhuma fase nova | Permanecem A.1–A.3, B.1–B.4 e C.1–C.3 | Conforme |

A única mudança executável no orquestrador, em relação à base, é o texto da instrução enviada após uma reprovação. Não foram introduzidas regras de decisão por disciplina, tipo de prova, valor calculado ou identidade de questão.

## Ajustes feitos durante a revisão

### 1. Preservar os dados literais em B.1

A redação inicial dizia que um número ou conclusão presente na descrição da tarefa era uma hipótese a verificar. A frase era abrangente demais: um número copiado literalmente do pedido também aparece na descrição, mas não é uma antecipação do planejador.

O [template B.1](apps/backend/src/infra/templates/b1_task_resolution.md) agora distingue explicitamente:

- dados fornecidos pelo usuário, preservados com unidade, referência e condição;
- valores derivados, conclusões e hipóteses introduzidos pelo planejamento, que precisam ser verificados.

Isso mantém a proteção contra respostas antecipadas sem desautorizar os próprios dados de entrada. A documentação correspondente também foi corrigida.

### 2. Reduzir a proximidade dos exemplos de produção com o benchmark

Os templates novos não continham lookup de gabarito ou ramificação por questão, mas alguns exemplos reproduziam valores e situações muito próximos dos casos usados para diagnosticar os erros: período 17,76 → 18 meses, igualdade 47/44, barreiras de colisão e interpretação de um rito para chuva e seca.

Essa proximidade não prova acoplamento funcional nem melhora artificial medida, mas é desnecessária para explicar a política geral e pode dificultar uma avaliação independente. Os exemplos foram substituídos por:

- volume estimado e seleção de capacidade próxima;
- registros de inventário contraditórios;
- deliberação de moradores e interpretação de decisão coletiva;
- diferença entre uma medida de comprimento e uma opção aproximada.

A política normalizada de B.1/B.2/C.1 continua idêntica. Os casos anteriores permanecem na matriz de testes, inclusive os positivos de aproximação; não houve remoção de cobertura para esconder uma regressão.

## Evidência de generalidade

- Não foram acrescentados `question.options`, gabaritos, identificadores de questão/bateria ou imports de fixtures ao núcleo. A leitura dos diffs confirmou que os dados de teste não são usados para decidir respostas em produção.
- A entrada continua sendo o pedido textual genérico. Regras sobre seleção são aplicáveis quando o pedido/tarefa exige uma escolha, sem exigir que todo pedido tenha alternativas.
- A matriz inclui uma pergunta aberta sobre estimativa de consumo de água, com unidade, hipóteses e ordem de grandeza. Há também casos de resultados distintos sob hipóteses explícitas diferentes, sem falsa contradição.
- A.1 impede exigir um valor exato quando o pedido admite estimativa; B.1 conserva a qualificação; C.1 permite aprovar; C.3 apresenta o resultado como estimativa.
- Os testes de perguntas abertas das etapas 01–03 continuam passando na suíte completa.
- Nenhum código passou a calcular Kepler, resolver colisões, reconhecer enunciados do ENEM/ITA/FUVEST ou selecionar letras com base em frases conhecidas.

As novas guardas de contrato estão em [test_validation_generalist_boundaries.py](apps/backend/tests/infra/providers/test_validation_generalist_boundaries.py). Elas examinam o template fixo; os mesmos nomes ou números continuam permitidos quando fizerem parte do pedido textual do usuário.

## Verificações executadas

Os comandos válidos de suíte e lint foram executados em `apps/backend`, com o Python do ambiente virtual do projeto:

```bash
python -m flake8 src tests
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

| Verificação | Resultado |
|---|---|
| Suíte da implementação recebida, antes dos ajustes da revisão | 2.227 passaram em 83,90 s; cobertura 100,00% |
| Quatro novas guardas antes dos ajustes | Quatro falhas confirmadas |
| Testes focados da etapa 04 e das novas guardas, após ajustes | 124 passaram em 0,26 s |
| Suíte completa final | **2.231 passaram em 79,12 s; cobertura 100,00%** |
| Lint final | Passou |
| Código e branches cobertos | 5.158 statements e 856 branches, sem lacunas |
| `git diff --check` | Passou |
| Transcrição literal do paper | Idêntica à base |
| Documentação anterior à etapa 04 | Preservada |

Uma primeira tentativa de execução partiu incorretamente da raiz do repositório e foi desconsiderada. As execuções de referência acima foram refeitas no diretório documentado do backend; os erros daquela tentativa não foram atribuídos à implementação.

## Limites e próxima etapa

Os testes usam providers/templates, parser, fila, memória e persistência reais, com completions e vereditos de LLM roteirizados. Demonstram transporte, transições e contratos. Não demonstram que um modelo real sempre identificará um erro, escolherá a interpretação correta ou aplicará bem a política. Não houve inferência paga nem medição de ganho de acurácia.

A gestão explícita de resultados corrigidos e aprendizados obsoletos continua para a **etapa 05**, conforme planejado. Nesta fase, uma investigação corretiva acrescenta seu resultado e explica o que confirma ou corrige; ela ainda não implementa a substituição auditável do estado vigente.

As mudanças da fase 04 e os ajustes desta revisão permanecem locais, sem commit automático. O parecer vale para o conteúdo final testado, incluindo os quatro testes novos e as correções dos templates.
