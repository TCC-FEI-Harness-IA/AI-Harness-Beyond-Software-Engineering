## Contexto Geral

- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O `README.md` contém uma explicação geral de todo o repositório.
- O `RALPH_LOOP_ADAPTADO.md` contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper. Sua transcrição literal da metodologia original deve ser preservada; novas regras entram como extensões identificadas.
- Você é um agente de desenvolvimento sem acesso à conversa que originou esta solicitação. Este prompt contém as decisões necessárias para implementar a **frente 1 — planejamento**. Leia o código do workspace e execute a implementação, testes e documentação, não apenas um plano de trabalho.
- Este é o primeiro de dois prompts, executados **sequencialmente**. Conclua e integre esta etapa no checkout usado pelo segundo agente antes de executar `02_validacao_tecnica_das_tarefas.md`. Não há uma terceira etapa prevista para corrigir integração pendente.
- O segundo prompt implementará a ampliação de B.2 e o critério técnico obrigatório `<task_id>-TECH`. **Não implemente essa ampliação nesta etapa.** Preserve o comportamento atual de B.1/B.2 enquanto acrescenta o novo planejamento.
- A especificação complementar está em `feature/nova-fase-validacao/README.md`. Os relatórios `RELATORIO_ANALISE_ERROS_POS_MELHORIAS_THINKING.md` e `RELATORIO_VALIDACAO_MELHORIAS_THINKING.md` explicam a motivação e os limites das evidências anteriores. As regras completas para esta etapa estão neste prompt; não dependa de uma exportação de benchmark, de arquivos ignorados ou de conversas externas para implementá-las.
- O harness deve continuar generalista, atendendo perguntas abertas e questões com alternativas. Não usar gabaritos, IDs de questão, `question.options`, fixtures ou fórmulas específicas de benchmark para decidir o comportamento do núcleo.

## O problema

### Estado atual da aplicação

O planejamento executa A.1, A.2 e A.3. A.1 define critérios gerais; A.2 produz tarefas; a atual A.3 extrai aprendizados do enunciado.

Em `RalphThinkingUseCase.__run_planning`, o lote de A.2 é validado estruturalmente, convertido em tarefas, colocado na fila e contabilizado antes da extração de aprendizados. Não existe uma verificação semântica separada da qualidade do plano antes da execução.

A.2 já contém orientações para separar dados, métodos, hipóteses e resultados, manter conclusões em aberto, evitar tarefas redundantes e revisar o próprio plano. Mesmo assim, execuções reais produziram critérios que exigem confirmar uma interpretação ou aplicar um método cuja validade ainda deveria ser investigada. As tarefas seguintes podem cumprir essa especificação errada e receber aprovação.

O parser confere JSON, campos, referências e limites; ele não sabe se uma tarefa antecipou indevidamente uma conclusão. A avaliação semântica precisa ser feita pelo modelo, com regras próprias, antes de confirmar o plano.

### Mudança autorizada

Introduzir **A.3 — Task Decomposition Validator** e renumerar a extração de aprendizados do enunciado para **A.4 — Key Learnings from the Question**. Simplificar A.2 para concentrá-la na geração, transferindo a auditoria detalhada para a nova A.3.

O limite por tarefa B.1/B.2 já foi elevado de três para **cinco tentativas totais**, incluindo a inicial. Verifique esse estado no workspace e preserve-o. O planejamento precisará de um limite próprio de cinco candidatos, sem reutilizar o contador de tentativas das tarefas.

## Sua tarefa

### 1. Leitura e pontos de intervenção

Leia os READMEs geral, backend e frontend, a metodologia e as extensões vigentes. Inspecione, pelo menos:

- `apps/backend/src/application/usecases/ralph_thinking_usecase.py`, especialmente planejamento, extração, criação de contextos, construção de eventos, validação e tratamento de falhas;
- `apps/backend/src/application/phases/`, em especial `base_thinking_phase.py`, `task_decomposition_phase.py` e `planning_learnings_phase.py`;
- `apps/backend/src/infra/templates/a1_general_criteria.md`, `a2_task_decomposition.md` e `a3_planning_learnings.md`;
- `apps/backend/src/infra/providers/file_prompt_template_provider.py`;
- `apps/backend/src/infra/adapters/structured_response_parser_adapter.py` e seus diagnósticos;
- entidades de tarefa, contexto de validação, sessão, evento, orçamento e falha; enums de fase, subtipo de evento e limite;
- interfaces de settings, cost guard e session recorder, respectivas implementações e `ralph_thinking_startup.py`;
- `session_document_mapper.py`, DTOs/rotas de sessão e streaming, codec e casos de uso de exportação/importação de benchmark;
- frontend: enums de fase, tipos de sessão/evento, parsers de sessão/frame, `reasoningRunReducer`, `sessionToThinkingRun`, grafo, timeline e detalhes do planejamento;
- testes existentes de fases, parser, orçamento, orquestrador, persistência, exportação/importação e paridade entre streaming e histórico.

Os nomes acima refletem o ponto de partida. Localize os componentes equivalentes se o workspace evoluiu, sem desfazer mudanças do usuário. Use `tests/doubles/ralph_scenario.py`, doubles de completions e repositórios em memória como base para testes sem rede.

### 2. Fluxo e responsabilidades

Implemente:

```text
A.1 — Critérios gerais
  → A.2 — Plano candidato
  → A.3 — Validação da decomposição
       ├─ reprovado → nova A.2 com o último candidato e o relatório → nova A.3
       └─ aprovado → confirma o plano na fila → A.4 — Aprendizados do enunciado
  → B e C existentes
```

A.1 mantém sua responsabilidade atual. Nenhuma tarefa pode começar e A.4 não deve executar enquanto o plano inicial não for aprovado. A.4 mantém a lógica de extração atual: lê somente o pedido original, sem resolver a pergunta, e registra seus aprendizados antes da primeira tarefa.

Mantenha o pedido textual como entrada genérica e preserve `review`/`depends_on`, fila, livro de resultados, memória vigente, Fresh Context e síntese sobre a última aprovação global. Não use o novo validador nos lotes de C.2 nesta etapa.

### 3. A.2 mais simples, sem remover suas regras essenciais

Reorganize o prompt de A.2 para produzir uma sequência de investigações com objetivos claros, dados suficientes, critérios verificáveis e dependências declaradas. Preserve as regras de geração:

- Dados fornecidos podem ser copiados com unidades, referentes e condições.
- Métodos pertinentes podem ser planejados; sua aplicabilidade não pode ser presumida quando depende de condição ainda não estabelecida.
- Valores, classificações, comparações e conclusões ainda desconhecidos devem permanecer em aberto, inclusive em títulos e critérios.
- As tarefas precisam ter objetivo único, admitindo dependência lógica e a integração analítica final quando necessária.
- Critérios devem ser complementares e exigir resultado fundamentado, sem converter formato final em obrigação interna desnecessária.
- Evitar tarefas apenas de transcrição, impressão de marcador, redação ou repetição de uma determinação já realizada.
- Manter cobertura do pedido, contratos estruturais, limites e dependências.

Transfira a auditoria detalhada para A.3, reduzindo repetição e longas instruções de autoavaliação. Não transforme a simplificação em remoção das regras básicas de geração nem imponha um número fixo de tarefas.

### 4. Entradas e rubrica fixa de A.3

Cada avaliação A.3 recebe explicitamente:

1. Pedido/enunciado original.
2. Critérios gerais de A.1.
3. Somente o plano candidato atual, com todas as descrições, critérios e dependências.
4. Regras fixas do template de avaliação.

O enunciado original é a referência principal. Se A.1 inventou uma exigência, isso não autoriza distorcer o plano. A.3 deve identificar o conflito sem reescrever A.1 ou resolver a pergunta. Não crie um ciclo novo de revisão de A.1.

A.3 deve avaliar, por rubrica fixa do harness:

- **Fidelidade:** preservação dos dados, referentes, condições e restrições relevantes do pedido.
- **Neutralidade:** ausência de resultados quantitativos ou qualitativos antecipados como obrigações.
- **Aplicabilidade:** hipóteses necessárias aos métodos são dadas ou serão verificadas durante a execução.
- **Critérios:** verificáveis, complementares, pertinentes ao objetivo e sem impor uma solução não investigada.
- **Coerência:** objetivos delimitados e ordem compatível com as dependências.
- **Cobertura:** determinação completa do que foi pedido, deixando somente apresentação e associações literais sustentadas para C.3.
- **Necessidade:** ausência de trabalho burocrático, redundante ou mais amplo do que o necessário.

Não avaliar o plano apenas pelos próprios critérios gerados por A.2. Não resolver o problema, escolher resposta ou exigir uma conclusão alternativa calculada pelo validador. Não rejeitar automaticamente números, fórmulas, hipóteses explícitas justificáveis, dependências ou aproximações legítimas.

Os exemplos nos templates devem explicar princípios gerais, sem reproduzir respostas ou valores dos casos usados no diagnóstico.

### 5. Contrato estruturado de A.3

Implemente saída com booleano real, separada do contrato `decision` de B.2/C.1:

```json
{
  "approved": false,
  "issues": [
    {
      "task_id": "T2",
      "criterion_id": "T2-AC1",
      "problem": "The criterion requires an unestablished conclusion.",
      "adjustment": "Ask for an investigation that keeps the conclusion open."
    }
  ]
}
```

A aprovação válida é `{"approved": true, "issues": []}`. A reprovação válida tem `approved: false` e ao menos um problema concreto. Em cada problema, `problem` e `adjustment` devem ser textos não vazios. `task_id` e `criterion_id` são obrigatórios no objeto, mas admitem `null` conforme o escopo:

- Ambos nulos: problema do plano inteiro.
- Tarefa preenchida e critério nulo: problema da tarefa.
- Ambos preenchidos: o critério precisa pertencer à tarefa indicada no candidato atual.
- Critério preenchido com tarefa nula, referência inexistente, booleano como string/número, campos ausentes ou combinação aprovação/problemas incoerente: violação de contrato.

Passe ao parser a referência estrutural do candidato atual para conferir os IDs. Adote entidade tipada e contexto mínimo de validação adequados à arquitetura. Não reutilize `VerificationReport` de forma que altere os contratos de B.2/C.1 ou perca a semântica booleana pedida.

Uma reprovação semântica coerente é **saída aceita**, não erro de parsing. Contrato inválido segue a recuperação estrutural existente da própria fase, com diagnóstico e contabilização. O parser não fabrica aprovação, problemas ou ajustes.

### 6. Contextos, revisão e temperaturas

- Cada geração A.2 e cada avaliação A.3 abre uma janela nova.
- A primeira A.2 recebe o pedido, template e limites; não há plano anterior.
- Após reprovação, A.2 recebe explicitamente o pedido, template/limites, **último candidato reprovado e relatório correspondente**. Não restaure a conversa anterior nem acumule todos os candidatos no prompt.
- A.2 pode corrigir quantidade, conteúdo, ordem, IDs e dependências quando o defeito exige, preservando partes não afetadas e cobertura. Sua nova saída completa é o próximo candidato.
- A nova A.3 recebe o pedido, critérios gerais e **somente esse novo candidato**, sem planos antigos, relatórios anteriores, aprendizados ainda não extraídos ou conversa de A.2.
- Feedback deve identificar o defeito e a alteração de investigação necessária, sem antecipar resultado ou produzir um plano corrigido pelo validador.
- Primeiras gerações e avaliações usam a temperatura da sessão. A.2 refeita por reprovação usa temperatura `1`, conforme a política de retentativa existente; a avaliação A.3 seguinte volta à temperatura da sessão.
- Correções de JSON/contrato preservam integralmente a janela da própria execução de fase, com temperatura de retentativa e sem repetir o template, mantendo a recuperação já implementada.

Não reintroduza cortes arbitrários de saída recusada nem faça concatenação ou preenchimento local de objetos incompletos.

### 7. Candidatos, fila e auditoria

Somente o plano aprovado pode entrar na fila e consumir os slots/contador de tarefas confirmadas. A validação estrutural de um candidato deve respeitar o espaço disponível, mas o candidato recusado não o consome. IDs de candidatos descartados não devem impedir o uso correto desses IDs pelo candidato seguinte.

Persista todos os candidatos e relatórios com ordem, fase, contexto, `prompt_input`, invocação, consumo e estado distinguível de aprovação/reprovação. Não sobrescreva mensagens antigas com o plano final.

Os eventos que exibem candidatos não podem ser interpretados pelos consumidores existentes como tarefas confirmadas. Acrescente subtipo ou metadado mínimo coerente em backend/frontend, se necessário. Emita/represente a confirmação uma única vez após A.3 aprovar; nenhuma tarefa descartada pode aparecer como executável ou inflar progresso.

Use a cópia do candidato efetivamente julgado. A.3 não devolve um lote substituto que o orquestrador possa aceitar silenciosamente.

### 8. Limites e interrupções

Crie `RALPH_MAX_PLANNING_ATTEMPTS`, default **5**, com configuração, interface, snapshot de orçamento/contagem, injeção e doubles coerentes. São cinco candidatos semânticos totais: inicial mais até quatro revisões. O contador é independente de `RALPH_MAX_TASK_ATTEMPTS`, que permanece em **5**.

Não reutilize o contador das rodadas adicionais C.2 nem conte recuperação estrutural como nova reprovação semântica. Preserve `RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS=2` e `RALPH_JSON_PARSE_MAX_RETRIES=2`, bem como os tetos atuais de tarefas, chamadas, tokens, reserva da síntese e tempo.

Ao esgotar cinco candidatos sem aprovação, encerre a sessão sem executar tarefas, A.4 ou síntese, com falha estruturada que identifique o limite de planejamento, a fase e a quantidade de tentativas. Acrescente o identificador de limite necessário em todos os consumidores pertinentes. Não promova o último plano reprovado.

Todas as chamadas, inclusive saídas inválidas e falhas de provedor, continuam passando pelo guardião e pelo recorder. Orçamento/cancelamento/interrupção não permitem fila parcialmente confirmada ou chamada fora da contabilização. Não aumente outros tetos para facilitar os testes. Não prometa que haverá recursos para cinco tentativas se outro limite encerrar a sessão antes.

### 9. Renumeração e versionamento ponta a ponta

A mudança de A.3 para A.4 não é uma substituição textual global. Nos registros antigos, `phase: "A3"` significa extração, e isso precisa continuar verdadeiro na apresentação do histórico.

Adote uma versão persistida do fluxo, por exemplo `flow_version`: novas sessões Ralph usam versão 2; sessões Ralph antigas sem o campo são interpretadas como versão 1. Preserve a inferência direta e seu histórico, sem forçá-los a adquirir semântica de fases Ralph.

No fluxo novo, `A3` significa validação e `A4` extração. No antigo, `A3` continua sendo extração. A versão deve acompanhar a sessão e chegar ao frontend também no streaming, antes de interpretar os eventos ambíguos. Não inferir a versão apenas da presença de A.4 nem reinterpretar documentos antigos como versão nova por default.

Atualize enums, provider de templates, fases e startup, domínio de sessão/eventos conforme necessário, recorder, mapeadores, DTOs, consulta, exportação/importação e frontend. Evite aliases que façam o mesmo valor `A3` escolher o template errado no fluxo novo. Não execute o parser da nova A.3 sobre texto histórico de extração.

Assegure round-trip da versão, fases e conteúdos nos pacotes completos de benchmark e nos mecanismos de exportação existentes. Dados antigos permanecem legíveis; a leitura não deve reescrever seus arquivos ou apagar auditoria.

O frontend deve distinguir candidato/reprovação/confirmação no fluxo novo, representar o retorno A.3 → A.2 e exibir A.4. Preserve a paridade entre eventos ao vivo e reconstrução por sessão persistida, além do grafo antigo. Faça as mudanças necessárias de compatibilidade, sem redesenho de produto não relacionado.

### 10. Escopo que não deve ser implementado

Não acrescentar nesta etapa:

- O critério `<task_id>-TECH` ou a ampliação funcional de B.2, que pertencem ao segundo prompt.
- Novas verificações de C.1, revisão posterior a C.3 ou fallback para a inferência simples.
- A chamada de A.3 para lotes de C.2, retorno automático B.2 → A.2 ou revisão automática de A.1.
- Recuperação de contrato mais específica que a atual; somente a integração do novo schema à recuperação existente é necessária.
- Nova apresentação da proveniência da memória, deduplicação semântica, mudanças funcionais de dependências ou revisão do livro de resultados.
- Ferramentas de resolução por domínio, votação, novos modelos ou uso de gabarito no harness.

## Metodo de desenvolvimento:

- A aplicação deve ser desenvolvida usando **TDD**: construa primeiro testes do comportamento corrigido, confirme a falha pertinente e só depois implemente o código que os faz passar.
- Respeite camadas, interfaces e injeção de dependências. Não deixe validação de verdade factual por regex, regras por domínio ou acesso ao dataset no núcleo.
- Todos os prompts internos e mensagens de correção/revisão ao modelo devem ser em **inglês e Markdown**, com envelopes JSON. Dados do pedido e resposta final preservam o idioma solicitado.
- Use componentes reais de templates, parser, contexto, fila, memória, custo, recorder e persistência nos testes de integração, substituindo a rede por completions roteirizadas. Confira estado e mensagens realmente enviados, não só strings de evento.
- Preserve testes de sessões antigas como antigas. Atualize cenários de execução nova para incluir a avaliação A.3 e A.4; não migre todas as fixtures antigas para esconder incompatibilidade.
- Não execute inferências pagas ou benchmarks reais. Saídas roteirizadas verificam o protocolo, não demonstram que um modelo passou a identificar todos os planos ruins.

### Matriz mínima de testes e critérios de aceite

1. **Primeiro candidato aprovado:** A.1 → A.2 → A.3 → confirmação → A.4 → B/C; plano executado é exatamente o aprovado, sem duplicidade de fila/slots.
2. **Correção semântica:** primeiro plano reprovado, segundo aprovado; A.2 recebe candidato e relatório certos; a segunda A.3 não recebe a versão recusada nem o relatório anterior.
3. **Mais de uma revisão:** cada A.2 recebe somente a última versão e seu relatório; auditoria contém todas; não há acúmulo oculto nas janelas.
4. **Fila isolada:** candidatos podem mudar quantidade/IDs; recusas não consomem slots nem contaminam dependências do lote final. Nenhuma execução começa antes da aprovação.
5. **Cinco tentativas:** quinto candidato aprovado conclui; quinto reprovado encerra sem sexta A.2/A.3, A.4 ou B/C. Primeiro aprovado termina sem executar tentativas extras.
6. **Configuração e contadores:** default e override do novo limite, independência do limite B.1/B.2, de C.2 e da recuperação estrutural; nenhum teto global removido.
7. **Schema A.3:** booleanos estritos, referências corretas e incorretas, critério de outra tarefa, referências nulas válidas, strings vazias, aprovação com problemas, reprovação vazia e campos ausentes. Contrato inválido é recuperável; `approved: false` coerente é aceito como relatório.
8. **Recuperação e temperaturas:** saídas recusadas integrais, janela da própria fase, correção sem consumo de tentativa semântica adicional, A.2 retentada a 1 e A.3 seguinte na temperatura da sessão; custo de toda invocação registrado.
9. **A.4:** mesma extração anterior, em janela nova, uma única execução após aprovação; notas alcançam B/C nos canais atuais.
10. **Orçamento, provedor e cancelamento:** interrupções antes/depois de avaliação não promovem plano recusado ou tarefas parciais; auditoria e contabilização preservadas; sem síntese sobre estado não aprovado.
11. **Versões:** sessão antiga sem versão com A.3 de extração, nova com A.3/A.4, e inferência direta; consultas e exportação/importação preservam conteúdo e versão. O frontend não confunde os significados de A.3.
12. **Frontend:** fluxo com reprovação/revisão não infla tarefas ou progresso; candidatos e confirmados distinguíveis; streaming e histórico reproduzem fases e loops equivalentes, incluindo sessão nova interrompida antes de A.4.
13. **Contratos e avaliação futura:** exemplos sintéticos abertos com condição omitida, resultado antecipado e tarefa redundante, além de planos válidos com dados numéricos, método pertinente, dependências e aproximação. Verifique informação disponível e regras do template, sem afirmar acurácia a partir de fakes.

Execute testes focados durante o TDD e, ao final, os checks do projeto. Na pasta `apps/backend`, com o ambiente virtual disponível:

```sh
python -m flake8 src tests
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

Na pasta `apps/frontend`:

```sh
npm run typecheck
npm run lint
npm run test:coverage
npm run build
```

Use o Python da `.venv` se necessário. Preserve os limiares configurados, não exclua arquivos da medição nem enfraqueça regressões para ficar verde. Confira também `git diff --check`. Investigue e complete correções relacionadas; documente falhas preexistentes separadamente, com evidência.

## Documentação das alterações:

- Atualize `RALPH_LOOP_ADAPTADO.md` com o fluxo novo, responsabilidades A.2/A.3/A.4, contratos, contextos, limites, confirmação na fila e compatibilidade. **Preserve a transcrição literal da metodologia original**; registre a mudança como extensão autorizada e ajuste as orientações operacionais atuais.
- O arquivo de novas regras é **`NOVAS_REGRAS_RALPH_LOOP.md`**, já existente na raiz. Não o sobrescreva nem crie uma cópia sem extensão. Acrescente uma seção identificada como **Nova fase de validação — 01: planejamento aprovado antes da execução**, preservando o histórico anterior e explicitando o que foi substituído.
- Documente exemplos de primeiro plano aprovado, plano reprovado por conclusão antecipada e depois corrigido, cinco reprovações, método/hipótese legítimos aceitos e sessão histórica cujo A.3 continua sendo extração. Explique a diferença entre recusa estrutural e reprovação semântica.
- Atualize READMEs técnicos, `.env.example`, contratos de versão/eventos e documentos do frontend afetados. Não apresente o critério TECH da etapa seguinte como já implementado.
- Atualize o estado de `feature/nova-fase-validacao/README.md` sem apagar a especificação ou os prompts. Registre o que esta etapa concluiu e o que permanece para a segunda.
- Crie `feature/nova-fase-validacao/RELATORIO_IMPLEMENTACAO_01.md` com arquivos/contratos alterados, matriz de testes, falhas observadas antes das correções, comandos/resultados reais, cobertura e limitações. Diferencie garantia programática, contrato do prompt e avaliação semântica ainda não medida.
- Na entrega, informe como executar os checks e confirme a prontidão do workspace para o segundo prompt. Não finalize com incompatibilidades resolvíveis de versão, frontend, testes ou exportação deixadas para um terceiro agente.
