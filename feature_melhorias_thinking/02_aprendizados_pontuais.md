## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem acesso à conversa que originou esta tarefa. Implemente as mudanças descritas, com testes e documentação, a partir do código atual do workspace.
- Esta é a etapa 02 de sete. Pode ser implementada em worktree própria em paralelo a 01 e 03, sem exigir que já estejam integradas. Limite seu escopo a A.3/B.4, memória, transporte das notas e testes relacionados; não altere a recuperação nem a política de planejamento/validação das outras fases. Preserve a recuperação integral de saídas se ela já estiver presente. Os três resultados serão integrados e validados antes da etapa 04.
- O harness é generalista. Foi explicitamente rejeitado alimentar o núcleo com `question.options` ou outro campo especializado do benchmark para contornar a extração de A.3.

## O problema

Cada tarefa roda em Fresh Context. Ela não recebe automaticamente o enunciado original nem as resoluções anteriores. As informações necessárias precisam chegar pela descrição da tarefa e pela memória de aprendizados.

A.3 deve registrar os dados fornecidos pelo enunciado antes da primeira tarefa. B.4 deve registrar os resultados novos obtidos pela execução aprovada, com significado suficiente para uso posterior. Há falhas quando se preserva um valor sem sua referência, se omitem identificadores ou textos de opções, se perdem unidades/condições ou se transforma uma aproximação em igualdade.

Exemplo real: em Química ENEM 2023 Q094, a tabela era `1-Cálcio, 2-Cloreto, 3-Turbidez, 4-Coliformes totais, 5-Sólidos sedimentáveis`, e as alternativas eram `A) 1, B) 2, C) 3, D) 4, E) 5`. A.3 guardou a tabela, mas omitiu as alternativas. B.1 determinou corretamente `1-Cálcio`; C.3, sem receber o mapeamento das letras, escreveu `B (1-Cálcio)`.

Outro exemplo: no microscópio, `130 mm da objetiva` não pode virar `130 mm da ocular`. O número pode permanecer igual e o fato estar errado. A memória também precisa conservar se um resultado é aproximado, sob que hipótese vale e a que objeto se refere.

## Sua tarefa

### Leitura e pontos de intervenção

Leia as regras vigentes em `RALPH_LOOP_ADAPTADO.md` e `NOVAS_REGRAS_RALPH_LOOP.md`. Inspecione:

- `apps/backend/src/infra/templates/a3_planning_learnings.md` e `b4_learnings_extraction.md`;
- `apps/backend/src/application/usecases/ralph_thinking_usecase.py`, especialmente extração, conversão e renderização da memória;
- `apps/backend/src/domain/entities/thinking/learning.py`;
- `apps/backend/src/domain/services/learnings_memory.py` e sua interface;
- `apps/backend/tests/application/usecases/test_ralph_learnings_extraction.py`;
- `apps/backend/tests/domain/services/test_learnings_memory.py`;
- `apps/backend/tests/application/usecases/test_ralph_scope_sufficiency_integration.py` e `tests/doubles/ralph_scenario.py`.

### Comportamento a implementar

1. Reforce A.3 para percorrer o pedido e preservar os dados que alguém anotaria para continuar a resolução: nomenclaturas, nomes de objetos, siglas e suas definições quando fornecidas, símbolos e referentes, valores/unidades, fórmulas, relações, tabelas, listas, identificadores, textos completos de alternativas quando existirem, condições simultâneas e o que exatamente se solicita determinar.
2. Preserve relações, não apenas itens isolados: código e significado, teste e parâmetro, valor e objeto, distância e referência espacial, prazo e evento, unidade e grandeza. Não expandir uma sigla por palpite quando o significado não estiver no enunciado.
3. Dados literais de A.3 não devem ser corrigidos, convertidos, arredondados, classificados como solução nem complementados com conhecimento inferido. Se a redação é ambígua, preservar a ambiguidade relevante; não escolher uma interpretação como se fosse dado fornecido.
4. Reforce a revisão de completude dentro da própria chamada A.3 antes da resposta: conferir grupos de dados, associações e condições que seriam perdidos no próximo contexto. Não adicione uma fase de LLM só para revisar A.3.
5. Reforce B.4 para preservar todos os novos resultados úteis aprovados: fato compacto, motivo breve, referência explícita, unidade, sinal/referencial, condições, hipóteses e caráter exato/aproximado. Preserve distinção entre valor calculado e escolha por melhor ajuste. Não escrever `47 = 44` nem converter `aproximadamente` em `exatamente`.
6. Mantenha as responsabilidades: A.3 copia dados fornecidos; B.4 registra conclusões derivadas. Não transforme a memória em cópia do raciocínio completo, dos critérios, das instruções ou dos vereditos. Tentativa rejeitada não fornece conclusão vigente se ela foi refutada.
7. Confirme que a memória efetivamente chega, em área separada, a B.1, B.2, B.4, C.1, C.2 e C.3, incluindo tarefas adicionais. As notas não se tornam critérios nem substituem evidência ausente nos resultados aprovados.
8. Preserve deduplicação por espaços, origem `source_task_id`, ordem das informações e auditoria. Não faça deduplicação que descarte `A` versus `a`, unidades diferentes ou afirmações com condições diferentes. Mudanças de schema só se necessárias e justificadas; revisão de resultados já aprovados será tratada em etapa posterior.
9. Não introduza parser especializado em provas, injeção de alternativas, gabaritos ou valores do benchmark. O núcleo continua recebendo o pedido textual genérico.

### TDD e critérios de aceite

Escreva testes antes das mudanças e inclua:

- Pergunta aberta com sigla definida, nomes parecidos, unidade e prazo; a memória mantém todas as associações e a grandeza solicitada.
- Questão com tabela e alternativas como o exemplo do cálcio: com extração roteirizada completa, todas as associações aparecem no prompt de C.3 e nos demais destinos previstos, sem acesso a `question.options`.
- Distância de `130 mm da objetiva` mantida com sua referência, sem troca por ocular; resultado aproximado mantém sua qualificação até as fases seguintes.
- Resultado condicionado, por exemplo `sob pressão constante`, não perde a condição. Dois fatos sobre objetos ou hipóteses diferentes permanecem distintos.
- Novos resultados simples não são omitidos por serem óbvios; lista vazia continua válida quando não há fatos novos. Dados de A.3 e conclusões de B.4 não são misturados aos resultados armazenados.
- Duplicatas, espaços, listas vazias e origem dos aprendizados continuam funcionando; nenhuma conversa de outra fase é restaurada.

Use os templates reais para testar as obrigações de extração e fakes para verificar o transporte. Não hardcode a saída correta em produção. Não apresente fixtures completas como prova de que A.3 sempre extrairá tudo: os testes demonstram contrato e preservação programática, não garantia universal da extração pelo modelo.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: primeiro testes que exponham o comportamento ausente, confirmação da falha e depois implementação.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown, preservando os envelopes JSON. A resposta final segue o idioma solicitado pelo usuário.
- Use as interfaces, providers, fakes e organização de camadas existentes. Não introduza acoplamento ao benchmark, regras para IDs de questões ou consulta ao gabarito.
- Execute os testes pertinentes e, em `apps/backend`, `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`, conforme o README. Preserve os requisitos de cobertura existentes.
- Não faça chamadas reais pagas a modelos. Diferencie testes de renderização/transporte de avaliação semântica de extração.
- Ao trabalhar em paralelo, prefira arquivos próprios para novos testes de integração. Evite mudanças desnecessárias em helpers e contratos compartilhados. Se precisar alterá-los, registre explicitamente a dependência para integração. Documente sua seção na sua branch sem apagar conteúdo de outras frentes.

## Documentação das alterações:
- Documente em detalhes toda alteração de lógica e as regras de anotação, incluindo entradas, saídas, fontes, limites e exemplos.
- Acrescente ao arquivo existente `NOVAS_REGRAS_RALPH_LOOP.md` da raiz a seção **Melhorias do thinking — 02: aprendizados completos e autossuficientes**. Preserve as seções anteriores; crie o arquivo com extensão `.md` somente se não existir.
- Inclua exemplos de pergunta aberta, tabela com alternativas, referência espacial, hipótese e aproximação. Explique por que registrar somente um número ou uma sigla não basta e por que a solução continua generalista.
- Atualize as extensões de `RALPH_LOOP_ADAPTADO.md` e a documentação técnica afetada sem modificar a transcrição literal do paper.
- Informe os testes executados, resultados reais e limites da evidência. Não declare correção semântica garantida por testes com respostas roteirizadas.
