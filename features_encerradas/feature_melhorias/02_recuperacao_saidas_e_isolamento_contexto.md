## Contexto Geral

- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.

## Cenario Atual

`BaseThinkingPhase` acrescenta a resposta à janela antes de validar o JSON. Em caso de falha, registra a saída inválida e pede uma correção genérica. Retentativas podem repetir instruções já presentes e reprocessar respostas muito longas. O parser já extrai JSON de cercas e tenta completar fechamentos finais em casos restritos.

O orquestrador também reaproveita a janela de B.1 em B.4. Esse comportamento precisa ser ajustado à regra solicitada: reaproveitamento somente nas retentativas da mesma tarefa e fase; toda mudança de fase exige contexto novo.

## Sua tarefa

Aplique os três pontos de recuperação aprovados, respeitando o isolamento de contexto:

1. Na retentativa da mesma tarefa e da mesma fase, preserve respostas e feedbacks, mas evite acrescentar novamente o template completo quando as instruções e os aprendizados não mudaram.
2. Use instruções específicas para erro de sintaxe, violação de contrato e interrupção por comprimento. Para defeito apenas de serialização, peça o mesmo conteúdo em JSON válido, sem nova resolução. Para contrato incoerente, peça ao próprio modelo que confira e corrija seu relatório. Para saída truncada, peça uma nova saída completa e concisa, sem concatenar uma continuação presumida.
3. Preserve reparos locais conservadores quando não alterarem conteúdo: extração de cercas e fechamento estrutural inequívoco. Não fabrique campos, complete strings interrompidas, invente explicações ou transforme automaticamente uma reprovação em aprovação.

A regra de contexto deve ser explícita:

- Uma correção de saída na mesma fase e tarefa pode reutilizar sua janela.
- Uma tarefa diferente sempre recebe janela nova, mesmo executando a mesma fase.
- Toda mudança de fase cria uma janela nova, inclusive B.1 → B.2, B.2 → B.1, B.1 → B.4 e C.1 → C.2/C.3. Não restaure implicitamente a conversa anterior ao retornar a uma fase.
- Somente os aprendizados acumulados constituem memória transversal. Não encaminhe conversas anteriores como histórico de mensagens da fase seguinte.
- Reiniciar contexto não elimina as entradas próprias previstas no paper: B.2 recebe o resultado preliminar e critérios; B.4 recebe explicitamente o histórico da tarefa para extração; C.1/C.3 recebem os resultados aprovados e critérios gerais; C.2 recebe os insumos de planejamento adicional. Feedback necessário ao retorno para B.1 deve ser uma entrada explícita. Esses dados não autorizam reaproveitar a janela da fase anterior.
- Mantenha a auditoria completa persistida, separada das janelas enviadas ao modelo. Em B.4, o histórico exigido pelo método deve entrar como material delimitado para extração, sem herdar a conversa ativa de B.1.

Preserve temperatura 1 nas retentativas, limites existentes, schema estrito e contabilização de todas as chamadas. Uma correção de formato continua distinta de uma nova tentativa de resolução após reprovação. Não altere a política de orçamento ou a reserva da síntese.

Teste identidade e conteúdo das janelas em cada transição, ausência de instruções duplicadas nas retentativas, preservação da auditoria e os três tipos de recuperação. Inclua um teste de B.4 em janela nova recebendo o material explícito necessário. Não considere suficiente testar apenas que o `context_id` mudou: verifique as mensagens enviadas.

## Metodo de desenvolvimento:

- O desenvolvimento deve ser feito obrigatoriamente em uma **Git worktree exclusiva**, com uma **branch própria para esta correção**, pois outros agentes estão desenvolvendo simultaneamente no mesmo repositório. Crie a worktree antes de alterar código, testes ou documentação e execute nela todas as alterações e verificações.
- Preserve as alterações dos outros agentes: não reutilize suas worktrees ou branches, não reverta nem sobrescreva trabalho alheio e não faça operações destrutivas no repositório compartilhado. Na integração, resolva eventuais conflitos preservando as mudanças compatíveis, especialmente nos arquivos de documentação comuns.
- A aplicação deve ser desenvolvida usando TDD, ou seja, devem ser construídos TESTES que garantam o comportamento corrigido da aplicação, e depois disso deve ser feito o código que respeita esse comportamento.

## Documentação das alterações:

- Por se tratar de uma alteração na regra de funcionamento do Ralph Loop adaptado, atualize o arquivo `RALPH_LOOP_ADAPTADO.md`, que possui uma explicação detalhada do funcionamento do Ralph Loop adaptado.
- Também documente com detalhes como funciona a nova lógica, fornecendo exemplos e atualizando o arquivo existente `NOVAS_REGRAS_RALPH_LOOP.md`. Se ele não existir, crie-o com esse nome. Esse relatório será usado posteriormente para atualizar o paper oficial, contendo os novos ajustes.
- Preserve a transcrição literal do paper. Registre como extensão a regra de reinicialização entre fases, diferenciando memória de aprendizados, entradas explícitas, histórico auditado e janela ativa. Atualize as explicações que ainda indiquem reaproveitamento de janela entre fases.
