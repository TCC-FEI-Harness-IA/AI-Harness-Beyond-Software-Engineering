## Contexto Geral

A entrega da fase 1, no commit `6c37126`, foi revisada. O novo planejamento A.2/A.3/A.4 está de acordo com a proposta. Restaram três ajustes no histórico, nos testes e no relatório.

Leia `feature/nova-fase-validacao/RELATORIO_IMPLEMENTACAO_01.md` e corrija somente os pontos abaixo. Não implemente a fase 2 nem altere a lógica do planejamento.

## O problema

1. **Auditoria de C.3 aparece como resposta final.** Em `apps/frontend/src/domain/services/deriveSubtype.ts`, a classificação de C.3 como `result/compile` acontece antes de descartar auditorias sem evento na versão 2. Assim, uma saída recusada pelo parser pode aparecer no histórico como resposta válida.
2. **O teste de paridade pode esconder diferenças.** Em `validatedPlanning.test.ts`, `liveEvents` reconstrói os eventos a partir das próprias mensagens persistidas. Os dois caminhos podem repetir a mesma omissão. A revisão confirmou que o `execute` reconstruído perde critérios: o backend escreve `**Acceptance criteria:**`, mas `taskParser.ts` procura `**Critérios de aceite:**`.
3. **Relatório desatualizado.** O final de `RELATORIO_IMPLEMENTACAO_01.md` afirma que a entrega não foi commitada, embora ela esteja no commit `6c37126`.

Os problemas de histórico já existiam antes da fase 1; não os apresente como regressões dessa entrega.

## Sua tarefa

1. Corrija `deriveStepKind` para que auditorias de C.3 sem evento não sejam apresentadas como resultado. Preserve a resposta aceita, os eventos programáticos legítimos e a leitura de sessões antigas. A auditoria deve continuar armazenada.
2. Corrija a perda dos critérios no histórico, aceitando os formatos inglês e português. Ajuste o teste de paridade para comparar eventos realmente capturados do caso de uso backend com a sessão persistida da mesma execução, usando modelo roteirizado, sem chamadas pagas. Não reconstrua os supostos eventos ao vivo com o mesmo parser do histórico. Preserve a distinção entre `thinking/compile` e o evento terminal `result/compile`, sem duplicar resultado ou consumo.
3. Atualize o relatório para identificar a entrega já commitada e registrar brevemente as correções e sua verificação. Não afirme que as novas correções foram commitadas sem conferir.

Arquivos principais: `deriveSubtype.ts`, `taskParser.ts`, `sessionToThinkingRun.ts` e `validatedPlanning.test.ts`, em `apps/frontend/src/domain/services/`. Consulte a emissão real dos eventos em `apps/backend/src/application/usecases/ralph_thinking_usecase.py`.

## Metodo de desenvolvimento:

Use TDD: primeiro reproduza os erros em testes, depois aplique a menor correção necessária. Cubra auditoria C.3 seguida de resposta válida, esgotamento sem resposta, critérios preservados e paridade com eventos reais. Preserve a compatibilidade com sessões antigas.

Execute os testes afetados e os checks do frontend: `npm run typecheck`, `npm run lint`, `npm run test:coverage` e `npm run build`. Se alterar backend, execute também seus testes e lint pertinentes. Não reduza os limiares existentes.

## Documentação das alterações:

Acrescente um complemento curto em `feature/nova-fase-validacao/RELATORIO_IMPLEMENTACAO_01.md`, explicando os três ajustes, os testes executados e eventuais limitações. Corrija comentários que apresentem reconstruções sintéticas como eventos capturados. Não há mudança metodológica do Ralph Loop neste ajuste.
