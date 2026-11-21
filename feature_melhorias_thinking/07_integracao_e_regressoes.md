## Contexto Geral
- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.
- Você não tem acesso à conversa anterior. Sua tarefa é concluir a integração e corrigir incompatibilidades das melhorias já implementadas, com testes e documentação.
- Esta é a etapa 07, última da sequência. Execute após as implementações documentadas como **Melhorias do thinking — 01 a 06**. Leia o código e as seções atuais; não dependa de resumos de agentes anteriores.
- Ao terminar, devem estar integradas cinco frentes: estrutura/recuperação, aprendizados, planejamento, validação e síntese fiel. A revisão auditável de resultados faz parte da estrutura e da validação.
- O harness é generalista. Não usar `question.options`, gabaritos ou IDs de questões no núcleo. Aproximações fundamentadas, melhor ajuste, eliminação e interpretação contextual continuam permitidos.

## O problema

Alterações separadas podem produzir contratos incoerentes mesmo com testes locais passando. Um template pode permitir revisão, mas o parser rejeitar seus campos; C.2 pode investigar um erro, mas a memória continuar contendo sua conclusão antiga; C.1 pode aceitar aproximação e C.3 exigir igualdade; a recuperação pode preservar o plano, mas a passagem seguinte ainda aceitar conteúdo insuficiente.

Também existe um risco metodológico: um teste com LLM roteirizado que devolve a resposta correta não demonstra que o modelo real passou a raciocinar melhor. Precisamos provar comportamento programático, verificar os contratos dos prompts e preparar exemplos de avaliação semântica sem inventar resultados de acurácia.

## Sua tarefa

### Leitura e escopo

Leia os READMEs, a metodologia e todas as novas seções de `NOVAS_REGRAS_RALPH_LOOP.md`. Inspecione os templates reais, orquestrador, fases, entidades, memória, parser, diagnósticos, mapeadores, budgets e testes afetados pelas seis etapas anteriores.

Use `apps/backend/tests/doubles/ralph_scenario.py`, parser e providers reais nos testes de integração; substitua a porta de rede por fakes. Verifique estado persistido, sequência de chamadas e `prompt_input`, não apenas eventos bonitos ou strings de respostas finais.

O arquivo `RELATORIO_BENCHMARK_VESTIBULARES_736136f4.md` e a exportação `benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/`, quando presentes, são evidência adicional. Não leia arquivos ignorados em testes nem faça a suíte depender deles: converta os casos necessários em fixtures pequenas e versionáveis.

### Matriz mínima de regressões integradas

| Caso | Defeito original e comportamento que precisa ser exercitado |
|---|---|
| Recuperação de Marte | Plano com três tarefas e título ausente, conteúdo depois de 1.000 caracteres preservado na correção; sem corte silencioso |
| Cobertura de Marte | Razão de distâncias sozinha não responde período em meses; C.1 encaminha a C.2, a análise é completada e há nova C.1 antes de C.3 |
| Colisões | T1/T2 corretas e T3 contraditória geram investigação; a correção aprovada atualiza resultados/notas vigentes e mantém histórico auditado |
| Tacho | Planejamento não deve prescrever a conclusão sobre origem da energia; contratos distinguem origem e efeito, sem transformar uma hipótese em obrigação |
| Microscópio | Referências e grandeza pedida são conservadas; aumento linear não é substituído silenciosamente por angular; hipóteses de uma fórmula precisam de fundamento |
| Geografia | Interpretação apoiada no texto não é reprovada por ausência literal de uma palavra nem tratada assimetricamente entre opções |
| Probabilidade | Erro de condicionamento não é justificado por haver opção próxima; revisão percorre as fases previstas e não acontece escondida na síntese |
| Contagem FUVEST | Definição e condições não são enfraquecidas pelo plano; igualdade falsa entre 47 e 44 não é confundida com escolha explícita por aproximação |
| Química | Tabela de testes e alternativas preservadas por A.3; conclusão aprovada e identificação final correspondem aos dados textuais |
| Aproximação legítima | Estimativa numérica e escolha por melhor ajuste aceitas mesmo sem coincidência exata ou cálculo direto até o valor escolhido |
| Pergunta aberta | Siglas, nomes, unidades, condições e resposta final coerentes sem alternativas, marcadores ou campos do benchmark |
| Revisão confirmatória | Investigação que confirma resultado anterior não o substitui por ser mais recente; fontes independentes e dados originais são preservados |

Exemplos quantitativos de referência, somente para fixtures/oráculos externos aos prompts de produção:

- Marte: `(R+r)/(R-r)≈7,7`, então `R/r≈1,2985` e `12*(R/r)^(3/2)≈17,76 meses`, escolha 18.
- Microscópio: `f1=5 mm`, `p1=5,2 mm`, `f2=70 mm`, separação `190 mm`; imagem da objetiva a `130 mm` dela, objeto da ocular a `60 mm`, imagem final a `−420 mm`, módulos dos aumentos `25` e `7`, total `175`.
- World Series: condicionada a primeira vitória, probabilidades por duração `1/8 + 3/16 + 6/32 + 10/64 = 42/64`. Usar `2^(−n)` com a primeira partida já fixada introduz fator `1/2` indevido.
- Listas da FUVEST: ordenadas, cinco inteiros positivos, mediana/média/amplitude/moda 23; oito listas com moda 23. Admitir indevidamente cinco valores distintos acrescenta 36 casos. A contagem 47 inclui outros erros; proximidade não demonstra que essa conta é correta.
- Colisões: mesma duração, velocidade inicial `v`, retorno nos pneus com módulo `u>0`; impulso nos pneus `m(v+u)` versus `mv` nos blocos; dissipação maior nos blocos.
- Tacho: vapor entra a `120 °C` e sai líquido a `100 °C`; a energia fornecida pelo vapor envolve resfriamento e condensação. Evaporação do produto é o destino dessa energia.

Não inclua esses valores esperados como respostas antecipadas nos templates genéricos. Nos testes semânticos, o gabarito pertence ao avaliador, não ao agente que resolve.

### Implementação e integração

1. Transforme as lacunas reais da integração em testes que falham e corrija o mínimo necessário nos componentes responsáveis. Não encerre com lista de problemas resolvíveis que ainda deixam as cinco frentes incompletas.
2. Audite todos os nove templates e mensagens de recuperação em conjunto: não pode permanecer “sempre aprovar se escolheu a mais próxima” ao lado de regras de revisão, nem “não reabrir nada aprovado” proibindo investigações justificadas. Evite empilhar novas instruções contraditórias.
3. Verifique schemas e metadados de revisão/dependência ponta a ponta: produção, validação, transporte, domínio, memória, auditoria, consulta/exportação e compatibilidade com sessões antigas.
4. Verifique isolamento: cada fase nova tem janela nova; correção de saída reutiliza a janela completa da própria fase; retentativa de B.1 recebe histórico explicitamente em nova janela. Só material previsto chega às outras fases.
5. Verifique que resultados substituídos ou dependentes ainda pendentes não voltam a C.3 como vigentes, e que dados de A.3 e fatos com fonte válida não são eliminados.
6. Verifique fluxo normal sem revisão, revisão aprovada, revisão rejeitada, recuperação de contrato inválida, esgotamento de budget/retentativas e cancelamento. Nenhuma chamada fica sem contabilização e nenhum limite é removido para facilitar o novo comportamento.
7. Preserve idioma e formato finais, justificativa opcional/obrigatória, perguntas abertas e aproximações válidas. Não acrescente fase nova ou pós-validador de C.3 para maquiar falhas de integração.
8. Mantenha testes rápidos determinísticos sem credenciais. Se criar fixtures para avaliação semântica futura, identifique a finalidade e mantenha o resultado esperado fora do texto enviado ao modelo.

### Evidência de conclusão

Separe explicitamente três níveis de evidência:

- **Garantia programática testada:** mensagens preservadas, transições, contratos, estado vigente, auditoria, budgets e renderização.
- **Contrato de prompt verificado:** instruções coerentes sobre planejamento, memória, aproximação, consistência e apresentação.
- **Desempenho semântico de modelo real:** só pode ser afirmado após avaliação real, controlada e registrada; fakes não produzem essa evidência.

Não reporte “corrigiu 8 de 8 questões” porque um roteiro de teste devolveu oito respostas corretas. Não execute inferências pagas ou benchmarks completos sem autorização específica de custo. É suficiente concluir a integração determinística e registrar honestamente a avaliação semântica pendente.

## Metodo de desenvolvimento:
- A aplicação deve ser desenvolvida usando TDD: escreva os testes das incompatibilidades antes das correções, confirme que falham e implemente em seguida.
- Todos os prompts internos devem ser feitos em inglês e em formato Markdown, preservando os envelopes JSON das fases. Dados do usuário e resposta final mantêm o idioma pertinente.
- Respeite arquitetura e testes anteriores. Não remova cenários de aproximação para obter maior rigidez nem relaxe o parser para esconder contrato inconsistente.
- Na pasta `apps/backend`, execute `flake8 src tests` e `pytest --cov=src --cov-report=term-missing --cov-fail-under=100`, com o ambiente do projeto. Investigue falhas e complete as correções relacionadas; não reduza cobertura exigida ou exclua arquivos da medição para passar.
- Rode verificações adicionais de tipos/contratos apenas quando exigidas pelo projeto ou afetadas pela mudança. Não altere frontend além de compatibilidade estritamente necessária às mudanças de contrato; documente qualquer ajuste assim.

## Documentação das alterações:
- Para toda nova mudança de lógica realizada na integração, registre motivação, funcionamento, transições e exemplos.
- Acrescente ao `NOVAS_REGRAS_RALPH_LOOP.md` já existente na raiz a seção **Melhorias do thinking — 07: integração e evidências das cinco frentes**. Preserve as seis seções anteriores e seu histórico. Se uma orientação atualizada as substituir, explicite a relação sem apagar a procedência.
- Atualize as extensões de `RALPH_LOOP_ADAPTADO.md` e o README técnico para refletir o comportamento final integrado. Não modifique a transcrição literal do paper nem apresente as extensões como texto original dele.
- Crie na raiz `RELATORIO_VALIDACAO_MELHORIAS_THINKING.md`, contendo a matriz de regressões, arquivos/testes que a exercitam, comandos e resultados reais, cobertura, decisões finais de contrato e limitações. Liste separadamente avaliação semântica não executada, sem atribuir acurácia aos fakes.
- Na entrega, descreva o estado final das cinco frentes e a evidência que sustenta cada uma, incluindo preservação do caráter generalista e das aproximações fundamentadas.
