## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem acesso à conversa anterior. Este prompt autoriza implementar a revisão direcionada descrita abaixo, com testes e documentação.
- Esta é a etapa 05 de sete. Execute após recuperação integral, aprendizados autossuficientes, planejamento sem respostas antecipadas e validação equilibrada, documentados como **Melhorias do thinking — 01 a 04**. Preserve as decisões e testes dessas etapas.
- O harness é generalista. Aproximação fundamentada e inferência contextual continuam válidas; não injete `question.options`, gabaritos ou regras específicas de questões.

## O problema

Detectar uma contradição em C.1 não basta se o fluxo não consegue revisar conclusões aprovadas e deixar claro quais fatos continuam vigentes.

Hoje, os resultados são armazenados por tarefa em B.3, e os aprendizados de B.4 são acrescentados a uma memória. `Learning` já registra `source_task_id`, mas a memória é essencialmente acumulativa e deduplica texto. O prompt original de C.2 proíbe reabrir o que foi aprovado; as etapas anteriores tornaram explícita a exceção para investigação de erro ou contradição. Falta implementar uma política verificável para o resultado dessa investigação.

Exemplo: T1 conclui força maior nos pneus, T2 conclui dissipação maior nos blocos e T3 afirma força maior nos blocos e dissipação igual. C.1 deve solicitar uma investigação, não escolher qual narrativa vence. Uma nova tarefa pode demonstrar que a conclusão de T3 precisa ser corrigida. Se a aplicação simplesmente acrescentar outra conclusão, a memória e os resultados continuam contendo versões opostas, e as fases seguintes podem seguir a antiga.

“A tarefa mais recente sempre vence” também é incorreto: ordem não prova correção, perguntas podem envolver hipóteses distintas e uma revisão pode confirmar o resultado anterior. A mudança precisa ser explícita, limitada, aprovada e auditável.

## Sua tarefa

### Leitura e pontos de intervenção

Inspecione a documentação atualizada e:

- `apps/backend/src/application/usecases/ralph_thinking_usecase.py`, especialmente C.1/C.2, B.3/B.4, renderização dos resultados e `GlobalApproval`;
- entidades `task.py`, `task_result.py`, `learning.py`, `verification_report.py`, `global_approval.py`, `validation_context.py`;
- `apps/backend/src/domain/services/learnings_memory.py`, fila e interfaces;
- templates C.1/C.2/B.1/B.2/B.4 e os schemas do `StructuredResponseParserAdapter`;
- mapeadores, gravador, DTOs de sessão e testes correspondentes, caso metadados novos precisem atravessar persistência/exportação;
- `apps/backend/tests/application/usecases/test_ralph_scope_sufficiency_integration.py`, `test_ralph_learnings_extraction.py`, testes de entidades/memória/parser e `tests/doubles/ralph_scenario.py`.

### Política a implementar

1. C.1 identifica motivo concreto para investigação: contradição, cálculo defeituoso ou lacuna de fundamentação. C.2 pode criar uma tarefa corretiva de objetivo único, com os dados necessários, referências aos resultados envolvidos e critérios de verificação, sem antecipar qual resposta será correta.
2. Defina o menor contrato explícito necessário para distinguir tarefa normal de tarefa que revisa resultados. A descrição livre pode explicar a revisão, mas a alteração programática de estado precisa de referências estruturadas validadas; não infira supersessão por palavras como “correção”, por regex ou apenas por ordem temporal.
3. Diferencie resultados sob investigação de resultados efetivamente substituídos. O planejamento pode apontar candidatos; somente a conclusão da execução corretiva, verificada em B.2, pode fundamentar a substituição. Uma investigação que confirma o resultado anterior não deve eliminá-lo automaticamente.
4. Se incluir campos novos em tarefas, resultados ou relatórios, atualize de forma coerente templates, parser, entidades, montagem de entradas, persistência e fakes. Valide existência dos IDs, unicidade, escopo permitido e ausência de autorreferência/ciclo quando aplicável. Não preencha campos inválidos por suposição nem exija metadados de revisão em toda tarefa normal.
5. Aplique a revisão somente depois da aprovação em B.2, pelo caminho de armazenamento previsto. Uma tentativa rejeitada ou saída de contrato inválida não altera resultados vigentes nem a memória. B.2 precisa receber a proposta explícita de revisão que deve avaliar, não só o texto da nova conclusão.
6. Conserve o histórico integral das respostas, aprovações e revisões na auditoria. Os conteúdos antigos deixam de ser apresentados como fatos vigentes quando substituídos; não devem ser apagados da história nem apresentados como se nunca tivessem sido aprovados. Registre quais resultados foram substituídos, por qual tarefa e por qual motivo aprovado.
7. Atualize a visão de resultados enviada a C.1/C.2/C.3 e a memória transversal para refletir o estado vigente. Aprendizados derivados exclusivamente de resultado substituído não podem continuar como verdades atuais. Preserve os dados de A.3, cuja origem é o enunciado, e os aprendizados de tarefas não afetadas.
8. Trate a origem dos fatos com cuidado: a deduplicação atual pode ocultar que o mesmo fato veio de mais de uma fonte. Não remova um fato ainda sustentado por fonte vigente só porque sua primeira origem foi revisada; mantenha ou reconstrua a proveniência necessária. Não use comparação semântica livre para deletar fatos.
9. Considere resultados dependentes da conclusão substituída. Quando uma dependência relevante estiver explicitamente registrada, a conclusão derivada precisa ser reavaliada antes da síntese; não pode continuar vigente só porque foi aprovada antes. Adote uma representação mínima de dependências/proveniência se necessária e documente como ela é produzida. Não alegue detectar toda dependência oculta em texto livre nem reinicie todas as tarefas indiscriminadamente. C.1 continua responsável por reconhecer contradições residuais.
10. Após executar correções e extração dos fatos vigentes, execute novamente C.1. C.3 só pode usar o conjunto de resultados efetivamente aprovado nessa nova passagem, vinculado a `GlobalApproval`. Não reutilize aprovação anterior a uma revisão.
11. Preserve IDs únicos, limites de tarefas e replanejamentos, orçamento, Fresh Context, temperatura de retentativa e interrupção controlada quando não há recursos. A revisão usa C.2 → B.1/B.2/B.3/B.4 → C.1, sem criar uma fase nova ou reconciliação invisível pelo orquestrador.
12. Para sessões antigas sem metadados novos, mantenha leitura compatível e ausência de revisão presumida. A auditoria nova deve ser consultável pelo mecanismo de sessão/exportação existente, sem exigir redesenho de frontend.

### TDD e critérios de aceite

Antes de implementar, crie testes de domínio e integração com os seguintes comportamentos observáveis:

- Contradição entre T1/T2/T3 chega a C.2; tarefa corretiva explicitamente revisa a conclusão incorreta, é aprovada e a próxima C.1/C.3 recebe somente os resultados vigentes. A conclusão antiga continua na auditoria.
- O mesmo cenário sem aprovação da correção não substitui resultados nem remove aprendizados.
- Uma investigação que confirma o resultado anterior não gera supersessão indevida. Uma aproximação ou hipótese diferente, sem contradição, não dispara substituição por ser mais recente.
- Notas originais de A.3, resultados não afetados e fatos com outra fonte válida são preservados. Aprendizados obsoletos não aparecem em B.1 posterior nem como notas atuais de C.3.
- Uma tarefa dependente explicitamente de resultado revisado não fornece conteúdo final até ser revalidada/corrigida; uma tarefa independente não é refeita sem motivo.
- Referência inexistente, ID repetido, revisão fora do escopo, autorreferência ou ciclo indevido são recusados com diagnóstico de contrato, sem mutação parcial de estado. Campos opcionais ausentes mantêm o fluxo normal compatível.
- Orçamento/limite insuficiente interrompe com auditoria íntegra e sem síntese sobre conteúdo ainda conflitante. Cada chamada é contabilizada uma vez.
- Sessão antiga continua legível; novos metadados preservam round-trip em mapeamento e exportação quando usados.
- Um novo `GlobalApproval` corresponde exatamente aos resultados vigentes que C.3 recebe.

Escolha uma solução mínima e explícita; não construa um sistema genérico de grafos ou versionamento além do necessário. Os testes com LLM fake devem provar protocolo, transições e gestão de estado, não que um modelo detectará qualquer contradição real.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: primeiro testes de estado/protocolo, confirmação da falha e depois implementação.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown, mantendo os envelopes JSON coerentes com os schemas e o idioma final solicitado pelo usuário.
- Respeite interfaces e camadas. Não altere conclusões automaticamente por preferência do orquestrador e não trate aprovação de um LLM como prova infalível de verdade.
- Preserve melhorias anteriores e atualize testes afetados por contratos novos sem enfraquecer garantias. Não faça migrações destrutivas nem elimine sessões históricas.
- Execute testes focados e, em `apps/backend`, `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`.
- Não faça chamadas pagas a modelos. Relate as limitações semânticas e de dependências não explicitadas.

## Documentação das alterações:
- Esta mudança altera a gestão de conhecimento vigente e deve ser descrita como extensão metodológica explícita, com entradas, decisões, aprovação, atualização da memória, transições e auditoria.
- Acrescente ao `NOVAS_REGRAS_RALPH_LOOP.md` existente na raiz a seção **Melhorias do thinking — 05: revisão auditável de resultados e aprendizados vigentes**. Preserve seções anteriores; crie esse arquivo `.md` apenas se ausente.
- Forneça um exemplo completo de contradição, investigação, confirmação ou substituição, atualização de fatos e nova aprovação global. Documente schema, dependências, compatibilidade com sessões antigas, limites e comportamento em falha.
- Atualize as extensões de `RALPH_LOOP_ADAPTADO.md`, contratos técnicos e README do backend conforme necessário, sem modificar a transcrição literal do paper.
- Entregue descrição da implementação concreta, testes executados e resultados. Explicite que referências estruturadas permitem gerir revisões, enquanto a identificação semântica do erro continua dependendo das fases do modelo.
