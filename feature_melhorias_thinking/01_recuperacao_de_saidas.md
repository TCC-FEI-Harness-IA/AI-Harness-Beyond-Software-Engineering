## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem acesso à conversa que originou esta tarefa. Este prompt contém as decisões necessárias. Implemente esta etapa no workspace, incluindo testes e documentação.
- Esta é a etapa 01 de uma sequência de sete implementações. Não depende das seguintes. O harness deve continuar generalista, para perguntas abertas e de múltipla escolha.

## O problema

Uma saída pode ser JSON legível, mas violar o contrato de sua fase: por exemplo, uma tarefa sem `title`. Hoje, `BaseThinkingPhase.__run_until_accepted` registra a saída completa na auditoria, chama `__compact_invalid_message`, acrescenta uma instrução de correção e repete a chamada na mesma janela. A compactação substitui a saída rejeitada pelos primeiros 1.000 caracteres mais `...`, independentemente de o defeito ser sintaxe, contrato ou interrupção por comprimento.

Isso remove material de que o modelo precisa para corrigir a saída. O registro completo na auditoria não resolve: a auditoria não é a mensagem reenviada ao modelo.

O caso concreto foi Física ITA 2024 Q005, sobre o período de Marte. A primeira A.2 trouxe três tarefas: obter razão de distâncias, obter razão de raios orbitais e aplicar a terceira lei de Kepler. A terceira estava sem título. Ao pedir correção, a aplicação reenviou somente o começo de T1. A resposta corrigida trouxe só T1 e foi aceita pelo parser. O enunciado original permanecia na janela, mas o restante do plano anterior tinha sido cortado. C.1 posteriormente aprovou uma razão de distâncias como suficiente para responder período em meses.

Há dois problemas distintos: perda programática de conteúdo na recuperação e verificação semântica insuficiente de cobertura. Você corrige a primeira e explicita a obrigação de preservar cobertura na recuperação; a revisão de planejamento e C.1 será reforçada em etapas posteriores. Não confunda JSON estruturalmente válido com plano semanticamente completo.

## Sua tarefa

### Leitura e pontos de intervenção

Leia `apps/backend/README.md`, `RALPH_LOOP_ADAPTADO.md` e as seções pertinentes de `NOVAS_REGRAS_RALPH_LOOP.md`. Inspecione:

- `apps/backend/src/application/phases/base_thinking_phase.py`;
- `apps/backend/src/infra/adapters/structured_response_parser_adapter.py`;
- `apps/backend/src/domain/entities/thinking/output_diagnostic.py` e `output_recovery.py`;
- `apps/backend/tests/application/phases/test_base_thinking_phase.py` e `test_base_thinking_phase_diagnostics.py`;
- `apps/backend/tests/infra/adapters/test_structured_response_parser_diagnostics.py`;
- `apps/backend/tests/doubles/ralph_scenario.py` e `scripted_llm_completions.py`.

### Comportamento a implementar

1. Pare de usar `__compact_invalid_message` para cortar a saída rejeitada na janela enviada ao modelo. Remova o método e suas constantes se ficarem sem uso. Não substitua por outro corte arbitrário, por resumo livre ou por ponteiro para auditoria que o modelo não consegue ler.
2. Preserve integralmente a saída rejeitada e as mensagens de correção na mesma janela da execução de fase. A mudança de fase/tarefa continua abrindo contexto novo. Não acrescente novamente o template inteiro a cada correção.
3. Mantenha a distinção entre defeitos:
   - Sintaxe: pedir o mesmo conteúdo em JSON válido, sem refazer a resolução.
   - Contrato: pedir correção do defeito indicado e saída completa; preservar conteúdo não afetado, sem remover tarefas ou etapas necessárias apenas para obter aceitação do parser.
   - Interrupção por comprimento: pedir uma nova saída completa e concisa, sem emendar ou continuar a anterior.
4. Para recuperação de planejamento A.2/C.2, deixe explícito que a saída completa corrigida deve continuar cobrindo a determinação solicitada, incluindo os passos finais necessários. Uma correção de título não autoriza eliminar as outras tarefas. Preserve a possibilidade de alterar o lote quando o próprio defeito exigir isso, como excesso de tarefas ou IDs duplicados.
5. Não fixe a quantidade de tarefas, não bloqueie qualquer alteração de ID/conteúdo como se fosse sempre incorreta e não implemente detecção semântica de cobertura por regex. Nesta etapa, cobertura é orientação da recuperação, com limitação claramente documentada; os testes programáticos provam preservação do conteúdo.
6. Preserve temperatura 1 nas retentativas, retorno à temperatura da sessão depois delas, consumo de orçamento, limites de retentativa, contabilização de todas as chamadas, diagnósticos, vínculo da recuperação, persistência e cancelamento controlado. Orçamento insuficiente deve seguir a interrupção existente, sem restaurar o corte silencioso.
7. Não complete títulos localmente, não force aprovação, não mude vereditos e não aproveite parcialmente objetos rejeitados para construir uma saída supostamente aprovada.

### TDD e critérios de aceite

Antes da implementação, crie testes que falhem no comportamento atual:

- Uma A.2 rejeitada com mais de 1.000 caracteres e dado indispensável no final chega **inteira** à próxima chamada, inclusive T2/T3; o template aparece uma vez e a mensagem de correção aponta o defeito.
- A resposta corrigida completa é a única aceita e encaminhada ao fluxo; nada é concatenado entre respostas.
- A mesma preservação vale para correção de saída de outra fase, evitando solução específica para Marte.
- Erro de contrato, erro de sintaxe e corte do provedor recebem instruções distintas; uma saída cortada localmente não deve ser confundida com `finish_reason=length`.
- Cada chamada tem consumo, temperatura e diagnóstico corretos; a recuperação aponta a invocação apropriada. Cubra esgotamento de tentativas, orçamento e cancelamento afetados pela mudança.
- Uma fase seguinte não herda a conversa rejeitada; a preservação ocorre apenas dentro da execução de fase em recuperação.

Use fakes para a rede e inspecione o `prompt_input` efetivamente enviado, não só o texto da auditoria. Verifique os novos contratos das mensagens sem tornar testes dependentes de um parágrafo inteiro ou da redação exata de exemplos. Não alegue que uma resposta completa roteirizada prova qualidade semântica do modelo.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: escreva primeiro os testes de comportamento, confirme a falha e depois implemente o código que os faz passar.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown. Preserve os envelopes JSON das fases e o idioma final solicitado pelo usuário.
- Respeite a arquitetura por camadas, interfaces e injeção de dependências existentes. Não acople a solução a `question.options`, ao gabarito, ao ID da questão ou a dados de benchmark.
- Execute os testes focados e depois as verificações exigidas em `apps/backend/README.md`: na pasta `apps/backend`, `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`, usando o ambiente Python do projeto. Não reduza a cobertura exigida nem remova testes para obter sucesso.
- Não faça chamadas pagas a modelos nem execute toda uma bateria como substituto dos testes. Relate separadamente qualquer validação semântica que não tenha sido realizada.

## Documentação das alterações:
- Sempre que houver alteração na lógica de execução do Ralph Loop, documente detalhadamente a regra nova, seu motivo, as entradas, as saídas, as transições e exemplos para atualização posterior do paper.
- O arquivo `NOVAS_REGRAS_RALPH_LOOP.md` já existe na raiz. Acrescente uma seção identificada como **Melhorias do thinking — 01: recuperação integral de saídas**. Preserve o conteúdo anterior; não crie um arquivo sem extensão nem uma cópia alternativa. Se estiver ausente, crie-o com esse nome.
- Mostre o exemplo de um plano com três tarefas e título ausente, distinguindo o conteúdo integral auditado do conteúdo integral reenviado. Explique o custo potencial de preservar a resposta e a aplicação dos limites existentes.
- Atualize a seção de extensões de `RALPH_LOOP_ADAPTADO.md` e os trechos técnicos pertinentes do README do backend. Não altere a transcrição literal da metodologia do paper.
- Registre os testes executados e seus resultados reais. Ao entregar, descreva o que ficou garantido por código e o que ainda depende do comportamento do modelo, especialmente a cobertura semântica do plano.
