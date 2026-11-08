# Validação das implementações 01, 02 e 03 do thinking

Data: 7 de novembro de 2026.

## Parecer

**As três implementações estão de acordo com o escopo planejado para as etapas 01–03. Não foram encontrados defeitos bloqueantes na revisão nem nas suítes executadas. A combinação das três passou em 2.107 testes, com 100,00% de cobertura, incluindo branches, e lint sem erros.**

Não foi identificado acoplamento novo que restrinja o harness a múltipla escolha ou introduza resolução programada de questões específicas. As alterações funcionais continuam recebendo pedidos textuais genéricos, sem consulta a gabaritos, injeção de `question.options`, importação de fixtures em produção ou ramificações por ID de questão.

Essa aprovação é de implementação, contratos de prompts e integração programática. Não demonstra que um modelo real sempre produzirá planos completos, extrairá todos os dados ou melhorará sua acurácia. As chamadas de LLM nos testes são simuladas.

## Estado e material revisado

| Etapa | Material examinado | Estado encontrado |
|---|---|---|
| 01 — Recuperação | Worktree `AI-Harness-Beyond-Software-Engineering-thinking-01`, branch `feature/thinking-01-recuperacao-integral`, sobre `945f7fe` | Implementação e dois arquivos novos de testes ainda não commitados |
| 02 — Aprendizados | Commit `b7cf19a`, branch `feature/thinking-02-aprendizados`, worktree `/private/tmp/ai-harness-thinking-02` | Commitado, sem mudanças locais de código |
| 03 — Planejamento | Commits `7a2c718` e `2b5a29f`, branch `feature/thinking-03-planejamento`, worktree `/private/tmp/ai-harness-thinking-03` | Commitado, incluindo correções separadas de formatação preexistente |

A branch principal de trabalho, `feature/realph-loop`, permanecia em `945f7fe` e ainda não continha as três implementações. As worktrees originais foram preservadas; a resolução de conflitos e a combinação aconteceram somente em uma worktree temporária de auditoria.

Foram comparados os diffs em relação à base, o código de produção, todos os novos testes das três frentes, os templates afetados, as fixtures de planejamento e as alterações de documentação. A revisão verificou também os limites de escopo descritos em `feature_melhorias_thinking/01_recuperacao_de_saidas.md`, `02_aprendizados_pontuais.md` e `03_planejamento_e_criterios.md`.

## Conformidade por etapa

### 01 — Recuperação integral de saídas

**Aprovada.**

- `__compact_invalid_message` e o limite local de 1.000 caracteres foram removidos. A próxima chamada recebe integralmente as saídas rejeitadas e os feedbacks da mesma execução de fase.
- As instruções de sintaxe, contrato e interrupção por comprimento continuam distintas, em inglês e Markdown. O resultado aceito é uma nova saída completa, sem concatenação de fragmentos ou preenchimento local de campos.
- A recuperação de A.2/C.2 orienta preservar a cobertura do pedido, inclusive a determinação final. Permite alterar quantidade, conteúdo ou IDs quando o defeito realmente exige isso, em vez de congelar um lote inválido.
- Os testes conferem a conversa efetivamente enviada, material após o caractere 1.000, erros sucessivos, recuperação de outra fase, temperatura, contabilização, persistência, esgotamento de tentativas, orçamento e cancelamento.
- Uma fase seguinte recebe uma janela nova; a preservação da saída rejeitada não restaura conversas de outras fases.

A cobertura semântica do plano é uma instrução ao modelo, sem certificação por parser ou número de tarefas. Isso corresponde à divisão aprovada: a etapa 01 preserva a informação; a 03 reforça a revisão no planejamento; a validação global será alinhada na etapa 04.

### 02 — Aprendizados completos e autossuficientes

**Aprovada.**

- A.3 passou a exigir relações completas: nomes, siglas definidas, símbolos e referentes, unidades, referências espaciais/temporais, tabelas, condições e determinação solicitada. Alternativas são preservadas quando existem no texto; não são exigidas em todo pedido.
- B.4 conserva referentes, hipóteses, condições, caráter exato/aproximado e a diferença entre valor calculado e escolha por melhor ajuste. Não deve inventar uma justificativa ausente nem guardar conclusão refutada como vigente.
- O código de armazenamento não ganhou extrator de domínio, interpretação de unidade, parser de alternativas ou schema específico de provas. As mudanças Python desta etapa são documentação das responsabilidades existentes; as mudanças comportamentais de extração são nos prompts.
- Os testes usam o caso de uso, templates, parser, memória e persistência reais para conferir transporte a B.1/B.2/B.4/C.1/C.2/C.3, inclusive tarefa adicional, origem, ordem, deduplicação e isolamento.
- Há casos abertos com siglas, bombas de nomes próximos, vazões, prazo, gases e hipóteses distintas. O caso do cálcio é fixture de teste, não uma tabela de respostas na aplicação.

O fato de os testes roteirizarem uma extração completa não prova que um LLM nunca omitirá dados. A documentação da etapa reconhece esse limite corretamente.

### 03 — Planejamento e critérios

**Aprovada.**

- A.1 distingue conteúdo solicitado, formato e justificativa opcional, sem impor marcador de resposta ou tolerância inventada.
- A.2/C.2 distinguem dado literal, método, hipótese e resultado a obter. A proibição de antecipação cobre conclusões qualitativas e hipóteses convenientes, além de valores numéricos.
- Uma tarefa pode depender de aprendizados anteriores e ainda ter objetivo único. A tarefa responsável pela determinação final pode executar a última análise, integração ou comparação; B.1 foi harmonizado com essa responsabilidade.
- A revisão de cobertura acontece dentro da geração do plano. Não foi criada fase adicional, classificador por palavras-chave ou exigência de quantidade fixa de tarefas.
- C.2 passou a receber `global_verification_feedback`, com o relatório válido de C.1 e suas justificativas, separado de resultados e aprendizados. Essa é uma adição geral de informação diagnóstica, sem dependência de prova ou gabarito.
- C.2 admite investigação direcionada de contradição ou erro concreto sem decidir antecipadamente qual conclusão está errada.
- Os novos testes exercitam contratos, transporte de conclusões pela memória e feedback de C.1 para C.2. A matriz versionada contém também pedidos abertos e declara explicitamente que aceitação estrutural não comprova correção semântica.

Não foi implementado nesta etapa o mecanismo completo de substituição de resultados já aprovados. Essa responsabilidade pertence à etapa 05; a permissão de investigar em C.2 não deve ser confundida com sua conclusão.

## Verificação do caráter generalista

| Verificação | Resultado |
|---|---|
| Entradas do núcleo | Continuam textuais; nenhuma entrada especializada de múltipla escolha foi acrescentada |
| Gabaritos, IDs e campos especializados nas linhas novas de produção | Nenhuma referência nova encontrada no núcleo do thinking |
| Alterações funcionais no orquestrador | Inclusão do feedback geral de C.1 em C.2; sem decisão por domínio |
| Fixtures de planejamento | Permanecem em `tests/fixtures`; não são importadas ou injetadas pelos componentes de produção |
| Fórmulas e resultados das questões do benchmark | Não foram introduzidos como atalhos executáveis ou respostas fixadas nos templates modificados |
| Perguntas sem alternativas | Exercitadas nos testes de recuperação, aprendizados e planejamento; não exigem letras A–E ou marcador de prova |
| Aproximações | Preservadas como possibilidade fundamentada, sem tolerância universal e sem conversão de aproximação em igualdade |

Foram examinadas todas as linhas novas de produção em busca de referências a `question.options`, gabaritos, IDs de questão, identificador da bateria e importação de fixtures. A busca foi complementada pela leitura dos diffs e dos fluxos de dados; ausência de palavras em uma busca, isoladamente, não certifica generalidade.

Os exemplos de colisão, energia, óptica e período orbital nos prompts são orientações sobre como preservar escopo e não assumir resultados. Não contêm uma solução fixa das questões nem acionam comportamento especial por enunciado. Continuam exemplos de princípios aplicáveis a outros pedidos, embora seu efeito sobre um modelo real só possa ser medido empiricamente.

Os arquivos de seleção e DTO do benchmark também foram alterados em 01/03, para corrigir lint preexistente. A comparação de AST, descontando docstrings, confirmou conteúdo executável idêntico à base nesses arquivos e nos respectivos testes de formatação. Não houve alteração de regra de seleção do benchmark nem de sua relação com o harness.

## Verificações executadas nesta auditoria

Em cada diretório `apps/backend`, utilizando o Python do ambiente virtual já instalado no checkout original:

```bash
python -m flake8 src tests
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

| Estado testado | Testes | Cobertura | Lint |
|---|---:|---:|---|
| Worktree 01 | 2.056 passaram, em 92,18 s | 100,00% | Passou |
| Worktree 02 | 2.053 passaram, em 92,15 s | 100,00% | Cinco avisos de formatação preexistente |
| Worktree 03 | 2.066 passaram, em 92,34 s | 100,00% | Passou |
| Combinação 01 + 02 + 03 | **2.107 passaram, em 78,72 s** | **100,00%** | **Passou** |

Na combinação foram cobertos 5.158 statements e 856 branches, sem lacunas. As durações individuais refletem execução concorrente das três suítes, não um benchmark de performance da aplicação.

O lint da 02 aponta E501 em `benchmark_question_selector.py`, `benchmark_run_input_dto.py` e dois trechos de `test_benchmark_question_selector.py`, além de W391 em `test_benchmark_router.py`. Esses trechos permanecem iguais à base na branch 02. As correções de formatação de 01/03 eliminam os avisos no resultado integrado; não são regressões funcionais da 02.

Também foram verificados:

- `git diff --check` no resultado combinado, sem erros;
- preservação integral do prefixo original de `NOVAS_REGRAS_RALPH_LOOP.md`, com uma seção de cada etapa;
- preservação byte a byte da transcrição literal em `RALPH_LOOP_ADAPTADO.md`;
- manutenção dos contratos de fase, parser, custos, recuperação e Fresh Context pela suíte completa.

Não foram executadas novas inferências com modelo real. O histórico de commits e os testes finais não permitem certificar retrospectivamente toda a ordem temporal do ciclo TDD; a documentação dos agentes descreve esse ciclo, e esta auditoria reproduziu a validação final.

## Integração e pontos operacionais

Não há bloqueio funcional encontrado, mas as seguintes ações continuam necessárias antes de iniciar a etapa 04 sobre a branch de trabalho:

1. Incluir as mudanças não commitadas da etapa 01, especialmente os dois arquivos novos de testes. Fazer merge apenas do HEAD dessa branch não traz sua implementação, pois ele ainda aponta para `945f7fe`.
2. Integrar 02 e 03 preservando todas as seções de documentação e o campo `global_verification_feedback`.
3. Resolver os conflitos de documentação e a diferença de formatação no DTO. A auditoria encontrou conflitos em `NOVAS_REGRAS_RALPH_LOOP.md`, `apps/backend/README.md` e `benchmark_run_input_dto.py`. Não houve conflito funcional no orquestrador.
4. Usar o conteúdo integrado testado como base da etapa 04. B.2/C.1 ainda contêm a política anterior de validação, cuja harmonização é o objetivo daquela etapa; isso não foi apresentado aqui como já corrigido.

A worktree de auditoria com a combinação validada está em:

```text
/private/tmp/ralph-audit-k_2tmhho/combined
```

Um patch completo da combinação, incluindo os novos arquivos de testes e as resoluções de conflito, foi preservado em:

```text
/private/tmp/ralph-audit-k_2tmhho/integracao_validada_01_02_03.patch
```

Base do patch: `945f7fe`. SHA-256: `b775ebca0c32073147c4d0275637830c427e086465944c82ed042ba5a6a4a88d`.

Esses caminhos são temporários. A auditoria não fez merge ou commit na branch principal e não alterou o código das três worktrees originais. Os arquivos de cobertura gerados durante os testes são artefatos locais ignorados.
