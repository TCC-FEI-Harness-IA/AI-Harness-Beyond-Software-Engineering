## Contexto Geral

- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.

## Cenario Atual

B.4 extrai aprendizados após a aprovação da tarefa. Esses aprendizados são a memória compacta usada pelas próximas tarefas, que executam com fresh context. Os resultados completos aprovados são armazenados separadamente em B.3 para a fase de criação da resposta final.

O template `apps/backend/src/infra/templates/b4_learnings_extraction.md` já pede conclusões e valores, mas o modelo pode omitir resultados necessários. No benchmark de Matemática ITA 2024 Q037, uma conclusão correta sobre a afirmação I não foi salva nos aprendizados; a próxima tarefa perdeu essa informação. Outros registros incluem anotações sobre critérios e sobre o processo, em vez de fatos úteis do problema.

## Sua tarefa

Reforce B.4 para registrar todo novo resultado parcial da tarefa aprovada, com significado suficiente para ser utilizado sem o histórico anterior:

- Para valores: preservar grandeza, valor, unidade e condições relevantes.
- Para classificações: identificar a afirmação, sua classificação e um motivo breve.
- Para relações: preservar a fórmula ou relação e as hipóteses necessárias.
- Incluir uma explicação curta, sem copiar a resolução completa. Exemplo: “A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade.”
- Priorizar a conclusão finalmente aprovada. Não transformar valores refutados ou substituídos durante as tentativas em aprendizados vigentes.
- Não registrar instruções da tarefa, critérios, vereditos ou relatos do processo. Não duplicar fatos já presentes na memória.
- Permitir `{"learnings": []}` somente quando não houver fato novo ou quando todas as conclusões já estiverem registradas. A simplicidade de uma conclusão nova não justifica omiti-la.

Mantenha o contrato `learnings: list[str]`, a separação entre aprendizados e resultados de B.3 e o fluxo autônomo. A.3 continua extraindo dados do enunciado sem resolver o problema. Não transmita respostas completas entre tarefas.

Respeite o isolamento de contexto entre fases: os dados necessários à extração devem ser entradas explícitas de B.4, sem reutilizar a janela de conversa de outra fase. Preserve o acesso ao histórico da tarefa exigido pelo paper como dado para a extração, separado da memória transversal de aprendizados.

Verifique por testes o prompt efetivamente enviado a B.4, a persistência dos aprendizados e sua presença na próxima tarefa sem vazamento da conversa anterior. Cubra conclusões numéricas, classificações, duplicatas e ausência legítima de fatos novos. Testes com respostas simuladas verificam a implementação; não comprovam, sozinhos, que o LLM nunca omitirá uma conclusão.

## Metodo de desenvolvimento:

- O desenvolvimento deve ser feito obrigatoriamente em uma **Git worktree exclusiva**, com uma **branch própria para esta correção**, pois outros agentes estão desenvolvendo simultaneamente no mesmo repositório. Crie a worktree antes de alterar código, testes ou documentação e execute nela todas as alterações e verificações.
- Preserve as alterações dos outros agentes: não reutilize suas worktrees ou branches, não reverta nem sobrescreva trabalho alheio e não faça operações destrutivas no repositório compartilhado. Na integração, resolva eventuais conflitos preservando as mudanças compatíveis, especialmente nos arquivos de documentação comuns.
- A aplicação deve ser desenvolvida usando TDD, ou seja, devem ser construídos TESTES que garantam o comportamento corrigido da aplicação, e depois disso deve ser feito o código que respeita esse comportamento.

## Documentação das alterações:

- Por se tratar de uma alteração na regra de funcionamento do Ralph Loop adaptado, atualize o arquivo `RALPH_LOOP_ADAPTADO.md`, que possui uma explicação detalhada do funcionamento do Ralph Loop adaptado.
- Também documente com detalhes como funciona a nova lógica, fornecendo exemplos e atualizando o arquivo existente `NOVAS_REGRAS_RALPH_LOOP.md`. Se ele não existir, crie-o com esse nome. Esse relatório será usado posteriormente para atualizar o paper oficial, contendo os novos ajustes.
- Preserve a transcrição literal da metodologia original e registre a mudança na seção de extensões, distinguindo o fato compacto da breve explicação agora exigida.
