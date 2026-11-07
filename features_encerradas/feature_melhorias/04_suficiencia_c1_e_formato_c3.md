## Contexto Geral

- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.

## Cenario Atual

C.1 recebe resultados aprovados e critérios gerais para avaliar se o conteúdo permite construir a resposta. C.3 apresenta esse conteúdo no formato solicitado. O template atual de C.1 já distingue essas responsabilidades, mas o benchmark mostra reprovações porque os resultados intermediários tinham explicações ou não continham a linha final formatada.

Também houve critérios locais artificiais: em Química ENEM 2024 Q097, mencionar “colheres” fez um cálculo ser reprovado; em Q135, surgiram exigências de duas linhas e de justificativa obrigatória que não correspondiam ao pedido. Esses critérios confundem limite de escopo com proibição de palavras e formato de apresentação.

## Sua tarefa

Reforce os templates existentes para respeitar a separação de responsabilidades, sem criar novas fases:

- A.1 deve registrar as restrições reais do pedido, sem transformar uma orientação genérica de objetividade em limites arbitrários de linhas ou palavras.
- A.2/C.2 devem criar restrições sobre ações fora do escopo, preservando a exigência de resultado acompanhado da explicação. Exemplo: “não calcular a massa por colher” restringe a resolução; “não mencionar colheres” proíbe uma referência contextual desnecessariamente.
- B.2 continua verificando todos os critérios recebidos. Não lhe dê autorização para ignorar ou reescrever um critério; melhore a geração dos critérios e a interpretação do que significa violar o escopo.
- C.1 deve julgar se os resultados permitem satisfazer os critérios gerais na resposta a ser construída. Se o conteúdo identifica inequivocamente C, a ausência de `RESPOSTA_FINAL: C` nos resultados intermediários não é lacuna de conteúdo. Explicações nesses resultados também não violam um pedido de resposta final apenas com a letra.
- C.1 deve continuar reprovando lacunas reais de conteúdo, conforme os critérios gerais. Uma exigência explícita de análise conjunta não pode ser considerada coberta apenas porque a formatação é possível.
- C.2 deve suprir lacunas de conteúdo apontadas por C.1, sem converter exigências de apresentação em tarefas que proíbam a justificativa necessária à verificação.
- C.3 deve aplicar idioma, formato e restrições finais usando exclusivamente os resultados aprovados, sem novo raciocínio analítico.

Acrescente exemplos positivos e negativos aos prompts. Diferencie referência contextual de antecipação da solução, formato realizável de conteúdo ausente e justificativa opcional de obrigatória. Não implemente a proposta separada de reconciliação de conclusões, revisão de critérios ou verificação posterior à síntese. Não altere a quantidade de tarefas como objetivo desta correção.

Preserve fresh context entre tarefas e reinicialização ao mudar de fase. Entradas próprias de cada fase devem ser montadas explicitamente; os aprendizados permanecem como memória transversal separada dos resultados aprovados.

Em TDD, verifique os templates renderizados e as transições do fluxo com cenários de conteúdo suficiente sem linha final, resultados explicados para resposta enxuta e lacuna real que exige C.2. Use casos de menção contextual permitida e resolução fora de escopo. Não substitua testes de integração por mera busca de frases no template; respostas simuladas não comprovam, sozinhas, melhora semântica do LLM.

## Metodo de desenvolvimento:

- O desenvolvimento deve ser feito obrigatoriamente em uma **Git worktree exclusiva**, com uma **branch própria para esta correção**, pois outros agentes estão desenvolvendo simultaneamente no mesmo repositório. Crie a worktree antes de alterar código, testes ou documentação e execute nela todas as alterações e verificações.
- Preserve as alterações dos outros agentes: não reutilize suas worktrees ou branches, não reverta nem sobrescreva trabalho alheio e não faça operações destrutivas no repositório compartilhado. Na integração, resolva eventuais conflitos preservando as mudanças compatíveis, especialmente nos arquivos de documentação comuns.
- A aplicação deve ser desenvolvida usando TDD, ou seja, devem ser construídos TESTES que garantam o comportamento corrigido da aplicação, e depois disso deve ser feito o código que respeita esse comportamento.

## Documentação das alterações:

- Por se tratar de uma alteração na regra de funcionamento do Ralph Loop adaptado, atualize o arquivo `RALPH_LOOP_ADAPTADO.md`, que possui uma explicação detalhada do funcionamento do Ralph Loop adaptado.
- Também documente com detalhes como funciona a nova lógica, fornecendo exemplos e atualizando o arquivo existente `NOVAS_REGRAS_RALPH_LOOP.md`. Se ele não existir, crie-o com esse nome. Esse relatório será usado posteriormente para atualizar o paper oficial, contendo os novos ajustes.
- Preserve a transcrição literal do paper. Documente os reforços de prompt e exemplos nas seções apropriadas, deixando clara a diferença entre suficiência em C.1 e apresentação em C.3.
