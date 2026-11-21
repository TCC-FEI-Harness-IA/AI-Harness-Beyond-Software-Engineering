# Implementação — sete refinamentos do planejamento, da validação e da apresentação

## Contexto Geral

- O backend desta aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do paper do projeto.
- O `README.md` da raiz contém uma explicação geral do repositório.
- O `RALPH_LOOP_ADAPTADO.md` contém a explicação detalhada do funcionamento do Ralph Loop adaptado e de suas extensões.
- O `NOVAS_REGRAS_RALPH_LOOP.md`, também na raiz, é o **documento de mudanças já existente**, usado como base para atualizar o paper. Todas as alterações desta entrega devem ser documentadas nele.
- O harness precisa continuar generalista. Questões de múltipla escolha são instrumentos de avaliação; não podem determinar regras de produção específicas para alternativas, disciplinas, IDs ou gabaritos.

Você implementará as alterações descritas neste prompt. Ele contém o contexto necessário, sem depender de uma conversa anterior. Leia a implementação atual antes de editar: várias instruções já existem, mas nem sempre produziram o comportamento esperado. Refine essas instruções e os mecanismos indicados; não recrie funcionalidades existentes.

## Leitura inicial

Consulte, a partir da raiz:

1. `README.md` e `apps/backend/README.md`, incluindo as regras de desenvolvimento e testes.
2. `RALPH_LOOP_ADAPTADO.md` e as seções pertinentes de `NOVAS_REGRAS_RALPH_LOOP.md`, especialmente as duas frentes de nova validação, a memória com procedência, a recuperação de saídas e a fidelidade de C.3.
3. `RELATORIO_ANALISE_BENCHMARKS_POS_NOVA_VALIDACAO.md`, especialmente os casos e as recomendações da seção 9.
4. `feature/nova-fase-validacao/README.md` e os relatórios `RELATORIO_IMPLEMENTACAO_01.md` e `RELATORIO_IMPLEMENTACAO_02.md` dessa pasta.

As explicações deste prompt prevalecem sobre propostas antigas quando houver diferença de escopo. Os relatórios de benchmark são evidência externa para desenvolvimento e avaliação, nunca entradas do harness em produção.

## Estado atual da aplicação

### Fluxo implementado

```text
A.1 — Critérios gerais
  ↓
A.2 — Gera um plano candidato
  ↓
A.3 — Valida a decomposição
  ├─ Reprovado: nova A.2 recebe o último candidato e o relatório de A.3
  │              → nova A.3 avalia somente o candidato atual
  └─ Aprovado: plano é confirmado na fila
                 ↓
A.4 — Extrai aprendizados do enunciado
  ↓
B.1 — Resolve uma tarefa
  ↓
B.2 — Verifica a tarefa e seus critérios
  ├─ Reprovada: nova B.1 recebe as tentativas anteriores e os pareceres
  └─ Aprovada: B.3 armazena e B.4 extrai aprendizados
  ↓
C.1 — Verificação global
  ├─ Reprovado: C.2 planeja investigações adicionais e retorna à execução
  └─ Aprovado: C.3 apresenta a resposta final
```

Regras que já existem e devem permanecer:

- A.3 recebe o pedido original, os critérios gerais e somente o candidato atual, em contexto novo. Não recebe versões anteriores, pareceres anteriores ou a conversa de A.2.
- Somente o plano aprovado entra na fila. Candidatos recusados permanecem na auditoria e não contam como tarefas confirmadas.
- O limite é de cinco candidatos de planejamento, incluindo o inicial. O limite de resolução é de cinco tentativas por tarefa, incluindo a inicial. São contadores independentes.
- Cada execução de fase usa contexto novo. A recuperação de uma saída inválida reaproveita apenas a janela daquela execução.
- B.2 recebe a descrição da tarefa, o resultado preliminar e os critérios efetivos: planejados, `<task_id>-TECH` e, em tarefas revisoras, `<task_id>-REV`.
- TECH é obrigatório, definido pelo harness e conhecido por B.1. Uma tarefa só é aprovada quando todos os seus critérios são atendidos. B.2 não pode dispensar ou reescrever critérios recebidos.
- Resultados aprovados alimentam a memória por B.4. A memória já registra a origem das notas, inclusive várias fontes para conteúdo deduplicado, e retira fontes de resultados substituídos ou aguardando revalidação.
- C.3 já recebe instruções de fidelidade. Sua responsabilidade é apresentação; ela não resolve lacunas nem altera conclusões aprovadas.
- O fluxo atual é versão 2. Nas sessões antigas, A.3 designa extração de aprendizados; no fluxo atual, designa validação e a extração é A.4. Preserve a compatibilidade histórica.

### Temperatura atual

Hoje, a primeira geração de A.2 usa a temperatura da sessão, e toda revisão após reprovação de A.3 já usa `1.0`. Retentativas de B.1 após reprovação de B.2 e recuperações de saída inválida ou vazia também usam `1.0`.

Nesta entrega, **somente a política das revisões semânticas de A.2 muda**: primeira revisão `0.5`; revisões seguintes `1.0`. A política completa está na mudança 5.

### Arquivos de referência para a implementação

Os caminhos abaixo são relativos à raiz; confirme os detalhes no checkout:

| Responsabilidade | Arquivos principais |
|---|---|
| Orquestração, candidatos, feedback e entradas de fases | `apps/backend/src/application/usecases/ralph_thinking_usecase.py` |
| Execução de fase, temperatura e recuperação | `apps/backend/src/application/phases/base_thinking_phase.py`, `apps/backend/src/domain/interfaces/thinking_phase_interface.py` |
| Planejamento e validação | `apps/backend/src/infra/templates/a2_task_decomposition.md`, `a3_decomposition_validation.md` |
| Resolução e verificação local | `apps/backend/src/infra/templates/b1_task_resolution.md`, `b2_task_verification.md` |
| Extração e apresentação | `apps/backend/src/infra/templates/a4_planning_learnings.md`, `b4_learnings_extraction.md`, `c3_final_answer.md` |
| Descrição central dos critérios do harness | `apps/backend/src/domain/entities/thinking/harness_criteria.py` |
| Aprendizados e procedência | `apps/backend/src/domain/entities/thinking/learning.py`, `apps/backend/src/domain/services/learnings_memory.py` |

## O problema

Após a introdução de A.3 e de TECH, os validadores passaram a detectar defeitos antes ignorados. Entretanto, a avaliação de 25 erros exportados ainda encontrou:

- Planos com condições omitidas, objetos alterados e conclusões disfarçadas de critérios de comparação.
- Reprovações de planos que apenas pediam uma investigação aberta, incluindo pareceres que reprovam e simultaneamente dizem não haver defeito bloqueante.
- Aprovação técnica fundamentada em plausibilidade, repetição ou presença de uma afirmação no contexto, sem conferir a relação decisiva.
- Hipóteses e conclusões geradas pelo modelo tratadas como dados do usuário.
- Retentativas que repetem a mesma premissa ou reformulam o texto sem resolver a objeção.
- Comparações que exigem uma condição de um candidato e a dispensam para o candidato preferido.
- Apresentação final que troca o identificador da conclusão aprovada.

O recorte ampliado inclui erros compartilhados com a inferência simples. Também há itens com gabaritos inconsistentes ou ambíguos. Portanto, não use o gabarito como definição automática de comportamento correto e não declare ganho de acurácia a partir da quantidade de reprovações ou dos testes com respostas roteirizadas.

## Sua tarefa

Implemente as sete mudanças abaixo, de forma integrada. A alteração de temperatura é parte da mudança 5, não uma nova fase. Mantenha a ordem do fluxo e a separação de responsabilidades.

### 1. A.3 — conferir condições, referentes e prioridades impostas

**Estado atual e problema:** A.3 já possui uma rubrica de fidelidade e neutralidade, mas aprovou planos que ignoram pedágios, confundem lucro com receita, trocam o objeto solicitado e definem “principal” como “mais geral” sem essa definição ter sido pedida.

**Comportamento requerido:**

- Confrontar o objetivo e as condições do pedido com a investigação planejada: referentes, unidades, relações temporais, condições simultâneas e restrições relevantes.
- Verificar cobertura também na integração entre tarefas. Condições válidas dentro de duas partes não podem desaparecer na junção.
- Identificar prioridades introduzidas pelo planejador, como “mais geral”, “mais simples”, “mais específico” ou “mais completo”, quando elas determinarem a resposta sem decorrer do pedido ou de uma investigação prevista.
- Distinguir um dado explicitamente fornecido de uma conclusão ainda não obtida. Copiar uma condição do usuário é obrigatório quando pertinente; isso não é antecipação indevida.
- Não exigir repetição integral do enunciado em todas as tarefas. A presença de dados em A.4 também não justifica um plano que prescreve ignorar uma condição relevante.
- O parecer deve apontar a condição ou o referente perdido e qual investigação precisa preservá-lo, sem calcular a resposta nem determinar a conclusão a alcançar.

**Exemplo:** se o pedido compara tempos e informa paradas obrigatórias para apenas um dos veículos, um plano que manda calcular exclusivamente distância/velocidade e subtrair os tempos está incompleto. A.3 deve pedir que as condições de parada entrem na comparação, sem fornecer o resultado numérico.

**Aplicação:** refinar A.3 e manter A.2 coerente com a rubrica. Harmonizar instruções comuns de C.2 somente onde necessário, sem submeter C.2 a uma nova etapa A.3.

### 2. A.3 — distinguir investigação de conclusão e reprovar apenas defeitos bloqueantes

**Estado atual e problema:** a rubrica já proíbe antecipação, mas o modelo às vezes considera que pedir uma classificação, interpretação ou relação já impõe seu resultado. Também produz `approved: false` com justificativas que dizem não haver problema real.

**Comportamento requerido:**

- Aprovar uma investigação adequada que mantenha o resultado em aberto, mesmo que envolva interpretar, comparar, formular uma oposição conceitual ou verificar uma hipótese.
- Reprovar quando título, descrição ou critério impuserem uma conclusão que a execução deveria estabelecer.
- Reprovar apenas com um defeito concreto que torne a especificação errada, incompleta ou inviável. Preferências de estilo, número de tarefas sem prejuízo ou redação alternativa não são defeitos bloqueantes.
- Cada problema deve identificar a exigência problemática, a regra violada e o ajuste necessário. Não emitir reprovação quando a própria avaliação conclui que nenhum ajuste é necessário.
- O feedback não deve resolver o pedido nem introduzir uma “resposta correta” a ser reproduzida por A.2.

**Exemplos contrastivos:**

| Plano | Julgamento esperado |
|---|---|
| “Identificar a divergência entre os discursos e justificar a interpretação.” | A investigação está aberta; não rejeitar por antecipação. |
| “Demonstrar que o primeiro discurso representa a categoria X.”, sem X ter sido fornecida | Há conclusão imposta; pedir investigação sem categoria previamente fixada. |
| “Verificar se há necessidade de corrigir o procedimento.” | Investigar a necessidade é legítimo; não significa exigir correção. |
| “O procedimento deve ser considerado incorreto.”, antes da investigação | Há resultado antecipado. |

Preserve o schema atual de A.3 e suas validações estruturais. Não tente detectar semântica por listas de palavras proibidas, não transforme uma reprovação em aprovação programaticamente e não acrescente outra chamada ao modelo para julgar o parecer.

### 3. TECH — verificar uma relação decisiva em vez de aceitar plausibilidade

**Estado atual e problema:** B.2 já pede evidências e conferências, mas há aprovações que apenas repetem a explicação de B.1 ou chamam um valor de plausível.

**Comportamento requerido:**

- A justificativa de TECH deve identificar o dado relevante, a premissa decisiva e a relação efetivamente conferida que sustenta o veredito.
- Usar uma conferência proporcional à tarefa: substituir uma solução na equação, conferir um vínculo entre grandezas, uma condição de aplicação, a direção de uma comparação ou a correspondência entre característica e definição.
- Uma explicação longa, a menção a um método numérico ou a repetição de uma conclusão não substituem essa conferência.
- Ao reprovar, apontar o passo, dado ou relação que falha e o que B.1 precisa investigar. B.2 não deve entregar a resolução corrigida, completar a análise ausente ou refazer a pergunta inteira.
- Preservar aproximações e inferências fundamentadas. Não impor tolerância universal, igualdade exata ou uma segunda solução completa como requisito de aprovação.

**Exemplo real:** no ácido bórico, B.1 alegou uma raiz `1,07×10⁻⁷`; a substituição na relação de equilíbrio produz aproximadamente `1,58×10⁻⁷` no outro lado. B.2 aprovou dizendo que a raiz era plausível. O comportamento esperado é reprovar a solução numérica por não satisfazer a relação, deixando a correção para B.1.

**Exemplo sintético para testes:** a tarefa pede uma solução de `x² = 9`; o resultado apresenta `x = 2` como solução exata. Não basta dizer que ele descreveu um método: a substituição contradiz a afirmação. Inclua também um caso positivo de aproximação sustentada para impedir que o ajuste vire cobrança indiscriminada de exatidão.

Harmonize B.1, B.2 e a descrição central de TECH quando necessário. Mantenha os identificadores reservados e o mesmo conjunto efetivo de critérios conhecido pelo solver e exigido pelo parser.

### 4. Contexto — tornar a procedência visível e preservar hipóteses

**Estado atual e problema:** `Learning` registra `source_task_id`, e a memória mantém todas as fontes de conteúdos deduplicados. Entretanto, `LearningsMemory.render()` apresenta uma lista de textos sem indicar suas fontes. Além disso, a redação de TECH pode ser interpretada como se toda premissa presente na tarefa ou nos aprendizados já estivesse justificada.

**Comportamento requerido:**

- Renderizar a procedência usando os metadados que já existem: origem no enunciado e origem em uma ou mais tarefas vigentes.
- Exemplos possíveis de representação: `[Enunciado] ...` e `[Tarefa T1] ...`. O formato pode seguir o padrão do projeto, mas deve ser inequívoco e estável.
- Os rótulos indicam origem, não veracidade ou categoria semântica. Uma tarefa pode ter repetido um dado, estabelecido uma conclusão ou usado uma hipótese. Não classifique tudo que vem de tarefa como hipótese nem como verdade demonstrada.
- Quando houver várias fontes, representar as fontes vigentes; não atribuir uma nota à primeira fonte já retirada apenas porque o objeto `Learning` conservou seu identificador inicial. Preservar deduplicação, ordem, retirada e restauração de fontes.
- Manter separação entre conteúdo e metadados. Não incorporar os prefixos ao conteúdo armazenado, à chave de deduplicação ou às notas que B.4 devolve. Oriente B.4 a copiar somente o conteúdo ao registrar novamente um fato estabelecido independentemente.
- Preservar hipóteses, condições, qualificações e motivos compactos na extração de B.4. Não inventar qualificações ausentes para tentar corrigir o resultado aprovado.
- Nos prompts consumidores, esclarecer que uma afirmação não ganha fundamento por estar na descrição da tarefa ou na memória. Premissas geradas no planejamento precisam de justificativa pertinente; resultados herdados conservam seu escopo e suas condições.
- Não exigir refazer todas as tarefas anteriores. Uma contradição concreta disponível no contexto merece ser apontada; a simples origem em outra tarefa não invalida o aprendizado.
- Não tornar obrigatória consulta externa ou citação bibliográfica em toda tarefa.

**Antes e depois, em exemplo sintético:**

```text
Antes: a memória traz “Duração de 8 dias” e uma tarefa posterior a transforma em garantia.

Depois:
[Enunciado] Prazo máximo: 10 dias.
[Tarefa T1] Duração estimada de 8 dias, supondo disponibilidade integral da equipe.
```

Se o pedido admite estimativa condicionada, ela pode ser usada dessa forma. Se a conclusão promete entrega garantida, a condição da equipe precisa estar sustentada; a presença de “8 dias” na memória não basta.

Essa mudança não cria nova etapa, tela, campo obrigatório de resposta do modelo ou classificação automática da verdade. Use rótulos de origem que não confundam A.3 histórica com A.3 atual; “Enunciado” evita depender dessa renumeração. Não migre sessões antigas apenas para exibir esses rótulos.

### 5. Retentativas — corrigir a objeção e graduar a temperatura na revisão do plano

#### 5.1. Uso efetivo do feedback

**Estado atual e problema:** A.2 já recebe candidato e parecer anterior; B.1 já recebe as tentativas da tarefa e os pareceres de B.2. Mesmo assim, há respostas reformuladas que repetem o defeito, e buscas que declaram impossibilidade após excluir candidatos por uma restrição inventada.

**Comportamento requerido:**

- Em A.2, orientar a revisão para o defeito concreto do parecer, mantendo o pedido original como referência. Não tratar como dado do usuário uma conclusão ou exigência indevida presente no feedback de A.3.
- Em B.1, a nova resolução deve enfrentar a objeção: corrigir a premissa, relação, cálculo ou interpretação afetada, ou demonstrar por que ela não invalida a conclusão anterior. Trocar palavras ou escolher outro candidato sem fundamento não basta.
- A fundamentação deve permitir identificar o que mudou e por que o defeito deixou de ocorrer. Não acrescentar campo JSON obrigatório, changelog obrigatório ou nova chamada de diagnóstico.
- Antes de declarar impossibilidade, revisar limites de busca assumidos pelo próprio solver. Não exigir busca exaustiva ilimitada nem dispensar dados explícitos para salvar os candidatos preferidos.
- B.2 deve avaliar o resultado atual e apontar defeitos concretos. Não precisa receber seus pareceres anteriores nem passar a julgar o histórico inteiro.
- Preservar os canais atuais de feedback e as janelas novas. Não criar um detector programático de estagnação, aprovação forçada, nova tentativa fora do limite ou retorno direto de B.2 para A.2.
- B.4 extrai os achados válidos da resposta aprovada, sem converter o histórico das correções em fatos do problema. C.3 não deve mostrar esse processo interno ao usuário.

**Exemplo real:** na questão dos gases, B.2 apontou a possibilidade de variantes isotópicas, mas B.1 as excluiu por não serem compostos “usuais”, restrição ausente no pedido, e repetiu que os dados eram inconsistentes. O ajuste deve favorecer revisar a restrição assumida em vez de relaxar a tolerância fornecida. Não acrescente uma regra química sobre isótopos ao harness: use esse caso como evidência de uma falha geral de exploração.

#### 5.2. Nova política de temperatura das revisões de A.2

A revisão mencionada aqui é **a nova geração de A.2 após um relatório estruturalmente válido de A.3 com `approved: false`**. Não é a correção de JSON inválido dentro de uma mesma execução.

| Geração de A.2 | Situação | Temperatura da primeira chamada dessa geração |
|---|---|---:|
| Candidato 1 | Geração inicial | Temperatura configurada pelo usuário na sessão |
| Candidato 2 | Primeira retentativa após reprovação de A.3 | `0.5` |
| Candidato 3 | Segunda retentativa | `1.0` |
| Candidato 4 | Terceira retentativa | `1.0` |
| Candidato 5 | Quarta e última retentativa | `1.0` |

Regras de integração obrigatórias:

1. Os valores são exatos: não somar `0.5` à temperatura da sessão, não usar crescimento ilimitado e não aplicar `max(temperatura_da_sessão, 0.5)`.
2. A.3 usa a temperatura da sessão em toda avaliação nova. A.4 e as chamadas novas das outras fases também mantêm sua política atual.
3. Se A.2, A.3 ou outra fase produzir saída inválida ou vazia, a recuperação continua usando `1.0`, na janela da mesma execução, conforme o mecanismo existente.
4. Uma recuperação estrutural não cria outro candidato, não consome uma revisão semântica de A.2 e não altera o próximo índice da tabela.
5. Exemplo: candidato 1 em `0.2` → correção de JSON em `1.0` → A.3 em `0.2` reprova → candidato 2 em `0.5` → correção de JSON em `1.0` → A.3 em `0.2` reprova → candidato 3 em `1.0`.
6. Uma recuperação do parecer inválido de A.3 não deve disparar revisão de A.2 antes de existir um parecer válido.
7. B.1 após reprovação de B.2 continua usando `1.0`; B.2 seguinte volta à temperatura da sessão. C.2 não recebe essa escala de candidatos, pois não participa do ciclo A.2/A.3.
8. A temperatura configurada da sessão não pode ser sobrescrita. Passe a temperatura efetiva por execução/chamada, seguindo a arquitetura existente. Se precisar ampliar o contrato de execução de fase, atualize suas implementações e duplos, preservando os padrões das outras chamadas.
9. A temperatura enviada ao provedor e a registrada em cada invocação devem coincidir, incluindo recuperações. Preserve auditoria, contabilidade e limites.
10. O índice de revisão é local à sessão e ao ciclo de planejamento. Não vaze temperatura ou contadores entre sessões.

### 6. Comparações — aplicar condições consistentes e justificar a preferência

**Estado atual e problema:** há comparações que rejeitam um candidato por omitir uma exigência e aceitam a mesma omissão em outro. Também há preferências por explicações “mais gerais” ou “mais completas” sem demonstrar por que isso é decisivo no pedido.

**Comportamento requerido em B.1/B.2:**

- Comparar hipóteses, ações ou explicações sob as mesmas condições relevantes e o mesmo padrão de suporte, inclusive para conteúdo implícito.
- Quando os candidatos tiverem naturezas diferentes, explicar quais exigências realmente se aplicam a cada um; consistência não significa exigir características irrelevantes de todos.
- Uma característica compartilhada não distingue os candidatos. Para justificar preferência, mostrar a diferença pertinente ao objetivo e por que ela importa.
- Separar “é a melhor explicação para o aspecto pedido” de “as demais afirmações são falsas”. Pode haver conteúdo verdadeiro em vários candidatos e ainda existir uma preferência sustentada.
- Não inventar critérios para forçar unicidade. Preservar melhor ajuste, eliminação e aproximação quando fundamentados, sem exigir que todas as outras possibilidades sejam falsas.
- Na comparação matemática, não criar exclusões inexistentes entre categorias; por exemplo, linearidade é um caso de dependência polinomial, não sua negação.

**Exemplo real:** na questão dos plasmídeos, a ausência de um procedimento foi usada contra A, mas D também não apresentava procedimento. B.2 deveria perceber que essa ausência não sustenta a preferência por D. Isso não obriga escolher A: exige outro fundamento pertinente para a comparação.

**Exemplo aberto para testes:** o pedido exige o menor custo com entrega em até cinco dias. Serviço X custa R$ 100 e entrega em três dias; Y custa R$ 80 e entrega em cinco. Preferir X apenas por ser mais rápido troca o objetivo. Ambos satisfazem o prazo, e a diferença de custo deve ser analisada segundo o critério solicitado. Se o pedido priorizasse rapidez, a análise seria outra.

Não acrescente um schema especializado de alternativas, ranking programático ou regra de desempate exclusiva para múltipla escolha.

### 7. C.3 — preservar a conclusão aprovada e seus identificadores

**Estado atual e problema:** C.3 já possui uma conferência de fidelidade na própria chamada. Mesmo assim, na questão do butadieno os resultados indicavam o par `s-trans, s-cis`, associado a A, e C.1 confirmou a associação; a resposta final preservou o par no texto, mas escreveu `FINAL_ANSWER: C`.

**Comportamento requerido:**

- Reforçar a preservação da determinação dos resultados vigentes aprovados: objeto, sentido, sinal, unidade, período, condições e qualificadores.
- Conferir que o identificador apresentado corresponde literalmente ao conteúdo aprovado. Isso vale para nome de entidade, código de produto, número de amostra, mês ou letra de uma alternativa.
- Preservar a distinção entre resultado calculado e escolha aprovada por melhor ajuste. C.3 não pode rejeitar uma escolha aprovada por exigir uma exatidão que não foi requerida.
- Tradução e formatação podem mudar a redação, não a conclusão. Se o rascunho contradiz os resultados, corrigir o rascunho a partir deles.
- Usar as notas do enunciado para associações literais; elas não substituem os resultados como fonte da resposta analítica.
- Não criar C.4, chamada adicional de conferência, correção automática de letras, comparação por gabarito ou revalidação analítica em C.3.
- Não fazer C.3 consumir relatórios de C.1 como fonte substituta dos resultados. Preserve as entradas previstas no fluxo.
- Se faltar um vínculo indispensável à apresentação, não autorizar C.3 a inventá-lo ou resolver a lacuna. Preserve o tratamento existente em C.1/C.2; esta entrega não amplia o papel de C.1 para uma nova auditoria geral.

**Exemplo aberto:** resultado aprovado: “o estoque diminuiu na unidade leste e aumentou na oeste”. C.3 pode resumir ou traduzir, mas não trocar as unidades. Inclua também pareamento literal entre um objeto aprovado e seu código, sem lógica específica de benchmark.

Não declare implementada uma nova proteção apenas por duplicar instruções que C.3 já recebe. Aproveite o mecanismo atual, refine onde houver lacuna e acrescente evidências de regressão pertinentes.

## Limites obrigatórios de escopo

- Preserve o fluxo descrito no paper adaptado e suas extensões atuais. Não crie novas fases, votações, ensembles, solucionador paralelo ou obrigação de consulta externa.
- Mantenha a versão de fluxo 2 para a topologia atual e a leitura histórica da versão 1. Não renumere novamente A.3/A.4 nem faça migração desnecessária.
- Não aumente os limites de cinco candidatos e cinco tentativas por tarefa. Não altere orçamento, teto de tarefas ou rodadas de C.2.
- B.2 não pode dispensar critério planejado inválido. Se o critério impuser um resultado incompatível, ele continua não atendido, mesmo que TECH aprove uma resolução tecnicamente válida. Não force o cálculo errado para cumprir o critério.
- Não reabra resultados nem retire aprendizados fora do mecanismo de revisão já existente. A distinção de procedência não é uma nova política de invalidação.
- Não altere frontend, API pública, formato da resposta simples ou critérios de pontuação para implementar estes ajustes internos.
- Não use IDs, disciplinas, opções ou respostas dos benchmarks como regras de produção. Exemplos de múltipla escolha podem existir nos testes, junto de problemas abertos.
- Preserve alterações locais anteriores. Não reverta nem incorpore modificações alheias à tarefa apenas para obter uma árvore limpa.

## Método de desenvolvimento

Use **TDD**: escreva primeiro testes do comportamento esperado, execute-os para confirmar a falha e só então implemente o necessário para passarem. Reaproveite os duplos, parsers, recorder e cenários de integração existentes.

Separe explicitamente dois tipos de evidência:

1. **Testes determinísticos:** demonstram parâmetros enviados ao provedor, contexto e feedback transportados, procedência renderizada, contratos, fila, limites e persistência.
2. **Avaliação semântica:** verifica se um modelo real identifica o defeito correto sem rejeitar casos válidos. Respostas roteirizadas e assertivas sobre o texto do prompt não provam essa capacidade.

Não resuma a validação a procurar palavras-chave ou manter snapshots integrais dos prompts. Testes de contrato podem conferir instruções relevantes, mas precisam ser acompanhados dos testes de integração e dos casos semânticos correspondentes.

### Cobertura mínima de testes e casos de avaliação

**Planejamento:**

- Plano omite uma condição decisiva; plano muda o referente; plano impõe prioridade não fornecida.
- Plano preserva dados explícitos sem merecer reprovação por antecipação.
- Par de casos “determinar se X” e “demonstrar X”: somente o segundo impõe conclusão desconhecida.
- Interpretação aberta, dependência válida e hipótese explicitamente investigada devem permanecer admitidas.
- Reprovação exige problema bloqueante e ajuste real. A contradição textual “reprovar, mas não há defeito” precisa constar da avaliação semântica, sem fingir que o parser entende essa contradição por palavras-chave.
- A.3 continua sem receber histórico; somente o candidato aprovado entra na fila.

**TECH, hipóteses e comparações:**

- Resultado que parece plausível, mas viola a própria equação ou tabela; justificativa aponta a relação concreta.
- Conclusão que repete uma premissa não sustentada do plano ou apresenta resultado condicionado como garantia.
- Caso positivo de aproximação válida e caso positivo de inferência contextual, para evitar rigor indevido.
- Comparação com exigência aplicada seletivamente e comparação válida com preferência fundamentada, mesmo havendo conteúdo verdadeiro nos demais candidatos.
- Feedback orienta o solver a corrigir o defeito sem entregar a solução; a nova tentativa recebe o material atual pelo mecanismo existente.

**Procedência:**

- Nota do enunciado, nota de tarefa e nota com múltiplas fontes vigentes.
- Retirada da primeira fonte com manutenção de outra: o texto continua visível, com procedência correta.
- Retirada de todas as fontes da tarefa, restauração e preservação da fonte do enunciado.
- Deduplicação não muda por causa dos rótulos. Prefixos de origem não contaminam `Learning.content` nem as respostas extraídas por B.4.
- Hipóteses, qualificadores e associações entre grandezas sobrevivem à renderização.
- As fases B/C recebem a representação pertinente; os aprendizados não passam a contar como critérios ou como resultados armazenados.

**Temperaturas:**

- Primeiro candidato aprovado: temperatura da sessão, sem usar `0.5` ou criar retentativa desnecessária.
- Reprovações sucessivas: A.2 segue `[sessão, 0.5, 1.0, 1.0, 1.0]`; cada nova A.3 segue a temperatura da sessão.
- Saída inválida ou vazia em A.2 e A.3: recuperação em `1.0`, sem avançar indevidamente o contador de candidatos.
- Recuperação de A.2 no segundo candidato: primeira chamada `0.5`, correção `1.0`, próxima A.3 na temperatura da sessão.
- A temperatura da sessão permanece intacta após aprovação, esgotamento ou recuperação. Sessões sucessivas não compartilham o índice.
- Retentativa de B.1 permanece em `1.0`; B.2 e chamadas novas de outras fases preservam sua política.
- A temperatura registrada nas invocações corresponde à efetivamente enviada ao provedor.
- Esgotamento no quinto candidato preserva a falha e a auditoria atuais, sem sexto candidato e sem execução de plano recusado.

**Apresentação:**

- Código correto para o conteúdo aprovado; conclusão e justificativa na mesma direção.
- Tradução preserva nomes, unidades, sinais, hipóteses e aproximações.
- Ausência de nova análise, novo validador ou correção automática por alternativa.
- O teste roteirizado comprova o material enviado a C.3 e o protocolo. A fidelidade de uma geração real deve ser avaliada separadamente.

### Suítes existentes a aproveitar

Investigue as suítes correspondentes em `apps/backend/tests/`, especialmente:

- `application/usecases/test_ralph_planning_validation_integration.py`;
- `application/usecases/test_ralph_technical_validation_integration.py`;
- `application/usecases/test_ralph_final_answer_fidelity_integration.py`;
- `application/phases/test_base_thinking_phase*.py`;
- `domain/services/test_learnings_memory*.py`;
- `infra/providers/test_decomposition_validation_contracts.py`, `test_technical_validation_contracts.py` e `test_final_answer_fidelity_contracts.py`.

Amplie as matrizes semânticas pertinentes em `apps/backend/tests/fixtures/`, incluindo `decomposition_validation_v1.json` e `technical_validation_v1.json`, preservando ou explicitando seu versionamento. Acrescente os casos de apresentação no local apropriado da estrutura existente. Gabaritos e campos de referência da avaliação nunca devem ser enviados ao modelo como parte da pergunta avaliada nem importados pelo código de produção.

Execute os testes específicos durante o TDD e, depois, os checks exigidos pelo backend. A documentação atual estabelece, em `apps/backend`:

```bash
flake8 src tests
pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

Não reduza os limiares, não remova testes para esconder regressões e não altere comportamento alheio à tarefa para contornar dependência indisponível. Registre limitações de ambiente quando existirem.

Se não houver condições para avaliação com modelo real, deixe as matrizes prontas e documente que a avaliação semântica não foi executada. Não dispare baterias completas como substituto dos testes de desenvolvimento e não declare ganho de acurácia sem comparação controlada.

## Documentação das alterações

**Obrigatório: documente todas as sete mudanças em `NOVAS_REGRAS_RALPH_LOOP.md`, o documento de mudanças já existente. Não crie outro documento para substituí-lo.**

Acrescente uma seção identificável para esta entrega e atualize o resumo e as referências pertinentes. Para cada mudança, registre:

1. Estado anterior e defeito observado.
2. Regra ou refinamento implementado e fases afetadas.
3. Exemplo antes/depois, incluindo pelo menos um caso aberto generalista.
4. Limites: o que permanece julgamento do modelo e o que é garantido programaticamente.
5. Arquivos e testes que demonstram a implementação.
6. Relação com as regras anteriores: complementação, esclarecimento ou substituição.

Documente explicitamente:

- A escala de A.2: candidato inicial na temperatura da sessão, primeiro revisado em `0.5`, demais em `1.0`.
- A distinção entre revisão semântica do plano e recuperação de saída inválida ou vazia.
- O uso de fontes vigentes na memória, incluindo deduplicação e retirada/restauração.
- A manutenção do escopo local de B.2 e do papel de apresentação de C.3.
- Os resultados dos testes e o estado da avaliação semântica, sem confundir essas evidências.

Atualize também `RALPH_LOOP_ADAPTADO.md` para refletir o comportamento implementado, preservando a transcrição histórica da Metodologia e registrando os refinamentos na área de extensões. Harmonize as tabelas e regras atuais de temperatura: a afirmação geral “toda revisão de A.2 usa 1” passa a ter a exceção definida nesta entrega. Onde um trecho antigo for mantido por histórico, marque sua substituição e aponte a regra vigente.

Atualize `apps/backend/README.md` e o índice da feature apenas quando suas descrições de funcionamento ou validação ficarem desatualizadas. Não reescreva relatórios históricos como se os resultados antigos tivessem sido obtidos após estes ajustes.

## Critérios finais de entrega

- As sete mudanças foram tratadas sem criar outra arquitetura de execução.
- A escala de temperatura está implementada, enviada e auditada corretamente, independente de correções estruturais.
- A procedência usa metadados existentes, preserva fontes vigentes e não altera o conteúdo das notas.
- Prompts e descrição central de TECH não se contradizem nem ampliam indevidamente as responsabilidades de A.3, B.2 ou C.3.
- O harness continua utilizável em perguntas abertas, sem regras específicas de benchmark ou acesso a gabaritos.
- Os testes e checks pertinentes foram executados; falhas ou limitações estão identificadas.
- Todas as alterações estão registradas em `NOVAS_REGRAS_RALPH_LOOP.md` e a explicação vigente do método está atualizada.

Ao concluir, apresente um resumo do que mudou, os testes executados e seus resultados, os documentos atualizados e as limitações remanescentes. Identifique claramente o que foi verificado com código e o que ainda depende de avaliação semântica com modelo real.
