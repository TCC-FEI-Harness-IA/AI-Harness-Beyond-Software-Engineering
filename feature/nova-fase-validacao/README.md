# Nova fase de validação do planejamento e ampliação da validação de tarefas

## Objetivo e estado da proposta

Este documento descreve as mudanças acordadas para duas frentes do Ralph Loop adaptado:

1. **Planejamento:** aprovar a qualidade da decomposição antes de executar o plano, acrescentando a fase A.3 — Task Decomposition Validator e renumerando a extração de aprendizados do enunciado para A.4.
2. **Validação:** ampliar B.2 para avaliar a tarefa como um todo, além dos critérios produzidos pelo planejador, com uma condição técnica obrigatória acrescentada pelo harness.

O objetivo é reduzir a execução de tarefas que já carregam conclusões antecipadas e a aprovação de resoluções tecnicamente erradas que apenas seguem essas tarefas.

**Estado:**

| Frente | Situação |
|---|---|
| 1 — Planejamento ([prompt 01](01_planejamento_com_validacao.md)) | **Implementada.** Nova A.3 (Task Decomposition Validator) com retorno a A.2, renumeração da extração para A.4, confirmação do plano na fila só depois da aprovação, `RALPH_MAX_PLANNING_ATTEMPTS = 5`, auditoria de candidatos e relatórios, `flow_version` (sessões novas = 2, antigas lidas como 1) no backend, nos pacotes de exportação e no frontend. Ver [`RELATORIO_IMPLEMENTACAO_01.md`](RELATORIO_IMPLEMENTACAO_01.md). |
| 2 — Validação técnica das tarefas ([prompt 02](02_validacao_tecnica_das_tarefas.md)) | **Pendente.** A ampliação de B.2 (descrição da tarefa em B.2, critério `<task_id>-TECH` em B.1/B.2) ainda não foi implementada; B.1/B.2 seguem o comportamento anterior. |

O limite de tentativas por tarefa (cinco, incluindo a inicial) já tinha sido elevado antes da frente 1 e foi preservado; é estado de partida da frente 2, não uma implementação dela. A especificação abaixo foi mantida como foi acordada; onde ela fala no futuro sobre a frente 1, o comportamento já está implementado conforme o relatório.

As mudanças continuam generalistas: aplicam-se a cálculos, interpretações, classificações, atribuições a fontes, investigações de causas e decisões abertas. IDs de questões, gabaritos, fórmulas de casos específicos e campos especializados do benchmark não devem orientar a implementação.

## Prompts de implementação

Execute os dois prompts abaixo **em sequência**, com a primeira implementação integrada ao workspace antes de iniciar a segunda. Cada prompt contém contexto, comportamento esperado, limites de escopo, critérios de aceite, TDD, verificações e documentação para um agente sem acesso à conversa original.

1. [01 — Planejamento com validação](01_planejamento_com_validacao.md): nova A.3, renumeração da extração para A.4, confirmação do plano, limite próprio de tentativas, auditoria, versionamento e compatibilidade de backend/frontend.
2. [02 — Validação técnica das tarefas](02_validacao_tecnica_das_tarefas.md): descrição da tarefa em B.2, critério técnico obrigatório em B.1/B.2, tratamento de hipóteses/aproximações e verificação integrada das duas frentes.

Esses dois prompts cobrem toda a implementação acordada. O segundo inclui a integração final; não há uma terceira etapa de desenvolvimento prevista. A criação dos prompts não altera o estado de implementação descrito acima.

## Referências

- [Visão geral do repositório](../../README.md).
- [Metodologia e extensões do Ralph Loop adaptado](../../RALPH_LOOP_ADAPTADO.md).
- [Análise dos erros e proposta revisada, especialmente a seção 11](../../RELATORIO_ANALISE_ERROS_POS_MELHORIAS_THINKING.md).
- [Relatório de validação das melhorias anteriores](../../RELATORIO_VALIDACAO_MELHORIAS_THINKING.md).

## 1. Frente de planejamento

### 1.1. Comportamento atual e mudança pretendida

Atualmente, A.2 produz um lote de tarefas que passa pela validação estrutural do parser e entra diretamente na fila. Depois, a atual A.3 extrai aprendizados do enunciado e a execução começa.

Não existe uma avaliação semântica separada da qualidade do plano antes de executá-lo. A.2 concentra a geração e a autoavaliação da decomposição. Mesmo com instruções para manter conclusões em aberto, foram observados planos que impõem resultados qualitativos e métodos cuja aplicabilidade ainda deveria ser investigada.

A mudança introduz uma avaliação específica entre a geração do candidato e sua confirmação na fila.

### 1.2. Novo fluxo

```text
A.1 — Critérios gerais
  ↓
A.2 — Decomposição: gera um plano candidato
  ↓
A.3 — Task Decomposition Validator
  ├─ approved: false → A.2 revisa o plano com o relatório
  │                       ↓
  │                  nova A.3, em contexto novo
  └─ approved: true → confirma o plano na fila
                          ↓
A.4 — Key Learnings from the Question
  ↓
B — Execução e validação das tarefas
  ↓
C — Fluxo atual de verificação global e síntese
```

### 1.3. A.1 — Critérios gerais

A.1 mantém sua responsabilidade de identificar o que a resposta final precisa atender: conteúdo solicitado, idioma, formato e restrições.

Os critérios gerais também serão fornecidos à nova A.3, para verificar se o plano cobre o pedido. O enunciado original permanece como referência principal: uma obrigação inventada em A.1 não deve justificar distorcer o planejamento.

### 1.4. A.2 — Elaboração do plano candidato

A.2 passa a se concentrar na elaboração da decomposição. Seu prompt será simplificado, transferindo a auditoria detalhada da qualidade para A.3.

As regras essenciais de geração continuam presentes:

- Criar tarefas com objetivo claro e critérios verificáveis.
- Preservar os dados e as condições necessários à resolução.
- Manter resultados ainda desconhecidos em aberto.
- Declarar as dependências pertinentes.
- Evitar tarefas redundantes ou destinadas apenas à apresentação final.
- Respeitar os limites e a estrutura exigida pelo sistema.

Simplificar A.2 não significa retirar essas regras. A mudança reduz a concentração de instruções de geração e autoavaliação na mesma chamada.

A saída de A.2 será um **plano candidato**, ainda sem autorização para execução.

### 1.5. A.3 — Entradas e isolamento de contexto

Cada execução da nova A.3 receberá:

- O enunciado original.
- Os critérios gerais produzidos por A.1.
- Somente o plano candidato atual.
- As regras fixas de avaliação do harness.

A.3 não receberá planos anteriores, relatórios de reprovações anteriores ou a conversa usada por A.2. Cada candidato será julgado em contexto novo.

A expressão “somente o novo plano” restringe o histórico de versões, não retira o enunciado ou os critérios gerais. Sem a referência original, o validador não conseguiria conferir adequadamente omissões e interpretações inventadas.

A.3 também não dependerá dos aprendizados do enunciado, pois eles só serão extraídos posteriormente, em A.4.

### 1.6. A.3 — Regras fixas de avaliação

A avaliação seguirá regras do template fixo do validador, independentes dos critérios escritos por A.2. Julgar o plano somente pelos critérios produzidos dentro dele repetiria o problema de autoconfirmação.

| Dimensão | O que A.3 verificará |
|---|---|
| Fidelidade ao pedido | Se o plano preserva dados, condições, referentes e restrições relevantes. |
| Neutralidade | Se as tarefas investigam conclusões, em vez de impor resultados quantitativos ou qualitativos antecipadamente. |
| Aplicabilidade | Se métodos e fórmulas dependem de condições que precisam ser verificadas durante a execução. |
| Qualidade dos critérios | Se são verificáveis, complementares e adequados ao objetivo, sem exigir uma conclusão previamente escolhida. |
| Coerência da decomposição | Se os objetivos estão bem delimitados e a ordem permite utilizar os resultados necessários. |
| Cobertura | Se o conjunto chega à determinação solicitada, deixando para C.3 apenas apresentação e associações literais já sustentadas. |
| Necessidade | Se existem tarefas redundantes, meramente burocráticas ou mais abrangentes do que o pedido exige. |

A.3 não resolverá a pergunta. Poderá identificar que uma tarefa obriga a aceitar uma hipótese ainda não demonstrada, mas não deverá calcular a resposta e exigir que o plano conduza a ela.

Também não deverá rejeitar automaticamente números, fórmulas ou métodos. Dados fornecidos podem ser obrigatórios, e métodos pertinentes podem ser planejados. A distinção será entre **planejar uma investigação** e **antecipar seu resultado**.

Uma tarefa pode depender logicamente de outra e continuar tendo objetivo único. A validação não deve exigir independência absoluta entre todas as tarefas nem impor uma quantidade fixa delas.

### 1.7. A.3 — Contrato do relatório

A resposta conterá `approved: true` ou `approved: false`, usando booleanos reais.

Quando reprovado, o relatório deverá identificar a tarefa ou o critério afetado, quando houver, o problema concreto encontrado e o ajuste necessário.

Exemplo ilustrativo de estrutura:

```json
{
  "approved": false,
  "issues": [
    {
      "task_id": "T2",
      "criterion_id": "T2-AC1",
      "problem": "The criterion requires confirming a classification that should be investigated.",
      "adjustment": "Ask for the classification and its supporting evidence, keeping the conclusion open."
    }
  ]
}
```

Problemas que atingem o plano inteiro poderão ser registrados com referências nulas. Referências preenchidas deverão apontar para tarefas ou critérios existentes no candidato.

Uma reprovação precisará apresentar pelo menos um problema impeditivo. Uma aprovação não poderá coexistir com problemas impeditivos pendentes; seu relatório terá `issues: []`.

O parser verificará tipos, referências e consistência estrutural. Não decidirá se o julgamento do modelo está correto nem alterará seu booleano automaticamente.

O feedback deverá orientar a correção da decomposição, sem impor uma nova resposta antecipada. “Investigar se a hipótese se aplica” é um ajuste adequado; “reescrever a tarefa para chegar ao resultado Y” repetiria o problema que a fase pretende eliminar.

### 1.8. Retorno de A.3 para A.2

Após uma reprovação, A.2 receberá, em contexto novo:

- O pedido original.
- Suas instruções de planejamento.
- O último plano que produziu.
- O relatório de problemas daquela versão.

A revisão poderá alterar descrições, critérios, ordem, dependências e quantidade de tarefas quando necessário. Partes não afetadas deverão ser preservadas.

O plano revisado voltará para A.3. Essa nova avaliação receberá apenas a versão atual, além do enunciado e dos critérios gerais, sem conhecer o histórico da correção.

A referência de cada revisão será o candidato mais recente. O sistema não deverá reiniciar sempre do primeiro plano nem reenviar indefinidamente toda a cadeia de versões. A cadeia completa permanecerá na auditoria da sessão.

### 1.9. Confirmação do plano na fila

Enquanto A.3 não aprovar, as tarefas serão candidatas. Elas não deverão entrar na fila executável, consumir os slots de tarefas confirmadas da sessão, aparecer como prontas para execução ou deixar versões antigas misturadas ao plano revisado.

Todos os candidatos e relatórios permanecerão na auditoria. Depois da aprovação, somente o plano aprovado será inserido na fila e contabilizado como conjunto de tarefas da sessão.

Essa separação evita que revisões do plano criem duplicatas, esgotem slots antes da execução ou mantenham tarefas reprovadas como pendentes.

### 1.10. A.4 — Extração de aprendizados do enunciado

A atual A.3 será renumerada para **A.4 — Key Learnings from the Question**.

Sua responsabilidade será mantida: extrair dados e associações relevantes do pedido, sem resolvê-lo. A.4 será executada depois da aprovação do plano e antes da primeira tarefa.

A nova A.3 recebe diretamente o enunciado original e não depende dessa extração para validar o planejamento.

### 1.11. Limite de tentativas do planejamento

O planejamento terá limite próprio de **cinco tentativas**, independente das tentativas por tarefa.

Cada tentativa corresponderá à geração de um candidato e à sua avaliação por A.3. Se o primeiro for aprovado, o ciclo termina imediatamente. Caso contrário, haverá até quatro revisões adicionais.

Uma saída com JSON ou contrato inválido continuará sendo tratada pela recuperação estrutural existente. Essa recuperação é diferente da reprovação semântica de um plano.

Ao esgotar as tentativas sem aprovação, a sessão será interrompida, preservando a auditoria. O plano reprovado não será executado.

Os limites existentes de tokens, chamadas e tempo continuarão ativos e poderão interromper a sessão antes desse teto.

### 1.12. Versionamento e compatibilidade

Nas sessões antigas, `A3` significa extração de aprendizados. Nas novas, significará validação da decomposição. Essa diferença será identificada pela versão persistida do fluxo.

Sessões antigas sem esse campo serão interpretadas como pertencentes à versão anterior. Seu histórico não será reescrito.

A mudança deverá alcançar:

- Identificadores e componentes das fases.
- Templates e inicialização do fluxo.
- Contratos de saída e parser.
- Eventos e auditoria de candidatos, aprovações e reprovações.
- Persistência, consulta, exportação e importação das sessões.
- Interpretação das fases no frontend e visualização do histórico.
- Testes e documentação técnica.

A interface deverá distinguir planos candidatos de planos aprovados e interpretar corretamente o significado de A.3 em cada versão do fluxo.

## 2. Frente de validação

### 2.1. Comportamento atual e mudança pretendida

B.2 já contém instruções de verificação técnica, mas recebe o resultado, os critérios, os aprendizados e eventual proposta de revisão, sem a descrição da tarefa.

O veredito estruturado está vinculado ao atendimento dos critérios locais. Nas execuções analisadas, houve aprovações que reconheceram uma explicação completa sem detectar que a relação, o método ou a hipótese estavam errados.

A mudança amplia a avaliação para o resultado da tarefa como um todo, mantendo a verificação individual de todos os critérios.

### 2.2. Entradas de B.2

B.2 receberá explicitamente:

- Identificação, descrição e objetivo da tarefa.
- Critérios de aceite gerados no planejamento.
- Resultado preliminar produzido por B.1.
- Aprendizados disponíveis.
- Proposta de revisão, quando a tarefa possuir essa responsabilidade no fluxo atual.
- Critério técnico fixo acrescentado pelo harness.

Esses elementos permanecerão em áreas separadas. A descrição explicará o escopo; os critérios definirão obrigações verificáveis; o resultado será o objeto avaliado; os aprendizados servirão como referência.

O fornecimento da descrição não restaura uma conversa anterior nem encaminha todo o histórico do planejamento para o validador.

### 2.3. Critério técnico obrigatório

O harness acrescentará um critério com identificador reservado, como `T2-TECH`, a toda tarefa. A.2 não será responsável por criá-lo e não poderá removê-lo.

Seu significado será: **o resultado resolve o objetivo da tarefa com fundamentação compatível com os dados, métodos e condições aplicáveis**.

O critério será apresentado tanto a B.1 quanto a B.2. O executor deverá conhecer a condição pela qual será avaliado.

A aplicação deverá impedir colisões entre esse identificador reservado e os critérios produzidos pelo planejador.

### 2.4. Condição de aprovação

B.2 continuará avaliando todos os critérios individualmente. Para aprovar, todos deverão estar atendidos, incluindo `TECH` e o critério de revisão já existente quando aplicável.

Isso permite um resultado como:

| Critério avaliado | Veredito |
|---|---|
| A resposta utilizou a fórmula exigida | Atendido |
| Apresentou as etapas solicitadas | Atendido |
| A fórmula é aplicável às condições e sustenta a conclusão | Não atendido |

Nesse caso, a tarefa será reprovada por `TECH`, mesmo que tenha seguido fielmente a receita do planejador.

O relatório de B.2 manterá o formato atual de avaliações por critério, identificadores pendentes e decisão `approved` ou `reproved`. Uma reprovação em `TECH` deverá aparecer entre as pendências e determinar a reprovação da tarefa.

O parser verificará se o relatório avaliou os identificadores esperados e se a decisão corresponde aos critérios marcados. Ele continuará sem decidir a verdade factual da resposta.

### 2.5. Verificação do fundamento da resposta

B.2 deverá verificar:

- Se as premissas estão fornecidas ou justificadas.
- Se os dados mantêm seus referentes, unidades e condições.
- Se o método se aplica ao caso.
- Se os passos sustentam a conclusão apresentada.
- Se a explicação contradiz alguma informação disponível.
- Se uma hipótese foi tratada indevidamente como fato.

A presença de uma explicação não será suficiente. A justificativa deverá apontar o dado ou trecho relevante e a relação efetivamente conferida, em vez de apenas repetir a conclusão como evidência de sua correção.

Quando simples e pertinente, a conferência poderá usar direção de variação, casos limites, relações temporais ou compatibilidade entre partes da resposta. B.2 não precisará refazer toda a resolução nem produzir a resposta corrigida.

### 2.6. Aproximações, hipóteses e melhor ajuste

Aproximações, estimativas, eliminação e inferências contextuais continuarão permitidas.

B.2 deverá distinguir:

- Uma determinação sustentada, apresentada com precisão compatível.
- Uma seleção por melhor ajuste apoiada em análise válida.
- Uma comparação que apenas aproxima uma resposta candidata de um cálculo errado.
- Uma hipótese acrescentada por conveniência para sustentar a escolha.

Escolher o valor mais próximo não corrigirá um erro de modelagem. Explicitar uma hipótese também não bastará para justificá-la. A exigência de suporte deverá ser aplicada de maneira consistente às hipóteses comparadas.

Não será introduzida tolerância percentual universal nem exigência geral de coincidência exata. A análise deverá considerar os dados, o método, as condições e a precisão pertinente ao pedido.

### 2.7. Reprovação e retentativa em B.1

Quando houver reprovação, o relatório deverá identificar o defeito concreto e o que precisa ser investigado ou corrigido.

B.1 receberá esse feedback pelo mecanismo existente, em contexto novo. A orientação será corrigir o problema apontado e preservar conclusões que não foram refutadas.

B.2 não editará silenciosamente os critérios, não substituirá o resultado e não armazenará uma correção feita por conta própria. A nova resolução deverá ser produzida por B.1 e avaliada novamente.

Somente uma resolução aprovada poderá seguir para o armazenamento e a extração de aprendizados da tarefa.

### 2.8. Preservação do escopo local

Validar a tarefa inteira não significa exigir que toda tarefa intermediária responda à pergunta completa.

`TECH` avaliará o objetivo daquela tarefa. Não poderá introduzir obrigações de apresentação final, exigir exatidão incompatível com uma estimativa ou cobrar análises pertencentes a outras tarefas.

Se B.2 detectar um defeito no próprio planejamento que A.3 deixou passar, deverá registrá-lo claramente. Não será acrescentado neste incremento um novo retorno automático de B.2 para A.2. Se a tarefa permanecer inviável, poderá encerrar por esgotamento das tentativas.

### 2.9. Limite de tentativas por tarefa

O limite de execução será de **cinco tentativas por tarefa**, incluindo a inicial: até quatro retentativas de B.1/B.2. Esse limite já foi elevado antes da implementação descrita aqui.

Ele será independente das cinco tentativas do planejamento. As recuperações de saída inválida e as rodadas de planejamento adicional C.2 continuarão com seus limites atuais.

Os limites existentes de tokens, chamadas e tempo continuarão podendo interromper a sessão antes desses tetos. Aumentar tentativas não corrige uma aprovação indevida: o ganho depende de os validadores identificarem o defeito e produzirem feedback útil.

## 3. Verificação das duas frentes

Os testes deverão separar comportamento programático de qualidade semântica.

Na implementação, será necessário verificar transporte das entradas, isolamento das janelas, contratos dos relatórios, inclusão obrigatória de `TECH`, confirmação do plano apenas após aprovação, contabilização, esgotamento dos limites, auditoria e compatibilidade com sessões antigas.

A avaliação semântica deverá incluir planos ruins e válidos, respostas erradas e corretas, hipóteses legítimas, aproximações fundamentadas e tarefas intermediárias suficientes ao próprio objetivo. Um validador que rejeita tudo gera mais loops e não representa melhora.

Testes com saídas de modelo roteirizadas comprovam o protocolo. A melhora na identificação dos defeitos e nas respostas finais somente poderá ser afirmada após avaliação com modelo real. A nova A.3 acrescenta ao menos uma chamada ao fluxo que aprova o primeiro plano; esse custo deverá ser considerado na comparação.

As duas frentes não acrescentam fontes externas nem garantem corrigir conhecimento factual errado do mesmo modelo. A recuperação estrutural de A.2 também permanece separada: uma saída que não satisfaz o contrato não chega à avaliação semântica de A.3.

## 4. Limites de escopo e documentação

Permanecem fora deste incremento:

- As mudanças adicionais de C.1 sugeridas no item 10.4 do relatório.
- A recuperação de contrato mais específica sugerida no item 10.5.
- A apresentação da proveniência dos aprendizados sugerida no item 10.6.
- As melhorias adicionais de dependências e apresentação sugeridas no item 10.7, além da compatibilidade necessária com os contratos já existentes.
- A reutilização da nova validação nos lotes de C.2.
- Um novo retorno automático de B.2 para o planejamento.
- Uma nova validação depois de C.3.

Os mecanismos existentes de verificação global, revisão de resultados, memória e síntese serão preservados. As alterações de aproximação descritas nesta proposta serão tratadas na resolução e na validação local, sem acrescentar as verificações globais adiadas.

Os templates internos deverão seguir a convenção do projeto de redação em inglês e formato Markdown, preservando os envelopes JSON. A resposta final continuará seguindo o idioma e o formato solicitados pelo usuário.

A nova fase deverá ser documentada como extensão da metodologia, preservando a transcrição literal do paper original. A documentação técnica deverá distinguir claramente o fluxo novo do comportamento das sessões antigas.
