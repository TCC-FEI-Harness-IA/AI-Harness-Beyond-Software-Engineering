# Novas regras do Ralph Wiggum Loop adaptado

## Finalidade deste relatório

Este documento registra as alterações feitas no fluxo implementado depois da versão descrita na seção **Metodologia** do paper. Ele serve de base para atualizar o paper oficial: cada alteração traz o problema que a motivou, a regra nova, a expressão no formato usado na Metodologia, exemplos com o *input* de referência do paper, o que deixa de valer no texto atual e a validação na implementação.

A explicação geral do fluxo está em [`RALPH_LOOP_ADAPTADO.md`](RALPH_LOOP_ADAPTADO.md). Aquele arquivo mantém a transcrição literal da Metodologia e traz a nova etapa numa seção separada, **Extensões ao método do paper**.

## Resumo das alterações

| # | Alteração | Fase | Efeito principal |
|---|---|---|---|
| 1 | Nova etapa **A.3 — Aprendizados pontuais do enunciado** | A. Planejamento | Dados importantes da pergunta (valores com unidades, alternativas, fórmulas, condições) deixam de depender de a descrição das tarefas os repetir. |
| 2 | Área **Aprendizados Pontuais** em todo prompt das fases B e C | B. Execução em Loop e C. Criação da Resposta Final | Todos os aprendizados do fluxo chegam a B.1, B.2, B.4, C.1, C.2 e C.3, e não só a B.1. |
| 3 | **Temperatura 1 nas retentativas** | B e todas as fases com correção de saída | Retentativas deixam de repetir a mesma saída reprovada até esgotar as tentativas. |
| 4 | **Regras de redação das tarefas** (A.2 e C.2) | A. Planejamento e C. Planejamento Adicional | As tarefas deixam de declarar entradas e saída, têm critérios de aceite complementares (nunca mutuamente exclusivos) e exigem resultado acompanhado da explicação. |

---

## 5. Registro dos resultados parciais da tarefa aprovada em B.4

### 5.1 Problema

B.4 extrai os aprendizados pontuais depois que a tarefa é aprovada. Eles são a única memória que passa para as tarefas seguintes, que rodam em contexto novo (*Fresh Context*). O resultado completo aprovado é armazenado à parte, em B.3, e só alimenta a fase C. O Template B.4 já pedia "conclusões parciais, valores calculados (com unidades), propriedades verificadas ou relações objetivas", mas três problemas apareceram nas sessões gravadas:

1. **Conclusões omitidas.** No benchmark de Matemática ITA 2024 Q037, uma tarefa concluiu corretamente que a afirmação I é verdadeira, mas essa conclusão não foi salva nos aprendizados. A tarefa seguinte, que só enxerga a própria descrição e a memória, perdeu a informação. O modelo tende a omitir conclusões "simples" e a tratar uma lista vazia como resposta segura.
2. **Registros que não são fatos do problema.** Parte dos aprendizados anotava critérios de aceite ("A resposta atende a T1-AC2"), vereditos ou o processo de execução, em vez de fatos úteis do problema.
3. **B.4 herdava a conversa de B.1.** A extração rodava sobre a própria janela da tarefa: o prompt de B.4 era acrescentado ao fim da conversa de B.1, com os templates de B.1, as instruções de refazer e todas as respostas. A fase B.4 enxergava a conversa de outra fase em vez de entradas próprias e delimitadas. O template também não separava a conclusão aprovada das tentativas reprovadas.

### 5.2 Regra nova

B.4 registra **todo resultado parcial novo** da tarefa aprovada, com significado suficiente para ser usado sem o histórico anterior:

| Tipo de resultado | O que o aprendizado preserva |
|---|---|
| **Valor** | A grandeza (o que o valor mede e a que se refere), o valor, a unidade de medida e as condições relevantes (hipóteses, dados e aproximações sob os quais vale). |
| **Classificação** | A afirmação, alternativa ou item classificado, sua classificação (verdadeira/falsa, correta/incorreta, satisfaz/não satisfaz) e um motivo breve. |
| **Relação** | A fórmula ou relação e as hipóteses necessárias para que ela valha. |

Regras complementares:

- **Prioridade da conclusão aprovada.** O *Resultado aprovado* é a fonte principal. Valores, classificações ou relações que aparecem em tentativas reprovadas e foram refutados, corrigidos ou substituídos na tentativa aprovada **não** são aprendizados vigentes. Do histórico só se aproveitam fatos que continuam válidos e que o resultado aprovado não contradiz.
- **O que não se registra:** instruções da tarefa, critérios de aceite, o validador e seus vereditos, relatos do processo ou das tentativas, a cópia da resolução e fatos que já constam na memória, mesmo com outras palavras.
- **Autossuficiência.** Cada aprendizado nomeia explicitamente o objeto ("a afirmação I", "a velocidade média do carro"), nunca "ela", "o valor acima" ou "o caso analisado".
- **Conferência final.** Antes de responder, o modelo percorre o resultado aprovado conclusão por conclusão e confere se cada uma já consta na memória. Toda conclusão ausente deve estar na lista.
- **Lista vazia.** `{"learnings": []}` só é válido quando o resultado aprovado não traz nenhum fato novo ou quando todas as suas conclusões já estão registradas. A simplicidade de uma conclusão nova não justifica omiti-la.
- **Contrato mantido.** A saída continua `{"learnings": ["...", "..."]}`, uma lista de strings.

### 5.3 Fato compacto e breve explicação

A Metodologia pede aprendizados em "tópicos sucintos e secos, sem justificativas". A regra nova mantém o fato sucinto, mas acrescenta a ele uma **breve explicação**. Cada aprendizado é uma única frase com duas partes:

| Parte | Função | Exemplo |
|---|---|---|
| **Fato compacto** *(já previsto no paper)* | A conclusão em si, com tudo o que a torna utilizável sem o histórico: grandeza, valor, unidade e condições; afirmação e classificação; fórmula e hipóteses. | "A afirmação I é verdadeira" |
| **Breve explicação** *(nova)* | O motivo, a propriedade ou a fórmula que sustenta o fato, em poucas palavras. Permite que a tarefa seguinte confie no fato e o reutilize sem refazer a dedução. | "C ⊆ A implica A ∩ C = C, pela distributividade." |

Juntas: *"A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade."*

A breve explicação **não** é a resolução: não traz passo a passo, contas intermediárias nem trechos transcritos do resultado. A resolução completa continua só no resultado armazenado (B.3), que alimenta a fase C. Assim nenhuma resposta completa passa de uma tarefa para outra.

### 5.4 Entradas de B.4 e isolamento de contexto

B.4 passa a rodar numa **janela de contexto própria**: a conversa de B.1 não é reaproveitada. Tudo o que a extração precisa chega como entrada explícita do template, cada item na sua área:

| Área do Template B.4 | Conteúdo | Origem |
|---|---|---|
| **Tarefa** | Identificador, título e descrição (sem os critérios, que não são fatos do problema). | Tarefa de A.2/C.2. |
| **Resultado aprovado** (`<resultado_aprovado>`) | A saída da tentativa aprovada. | O mesmo conteúdo armazenado em B.3; B.4 só o lê. |
| **Histórico da tarefa** (`<historico_da_tarefa>`) | Todas as tentativas, em ordem: o resultado preliminar de cada tentativa reprovada, as saídas inválidas que o validador corrigiu e o veredito de cada tentativa. O resultado da tentativa aprovada não é repetido; o histórico aponta para a área própria. | Registro das tentativas da tarefa (`Task.attempts`), e não a janela de B.1. |
| **Aprendizados Pontuais** | Os aprendizados já registrados (A.3 e tarefas anteriores), para não repeti-los. | Memória de aprendizados (alteração 2). |

O histórico exigido pelo paper ("incluindo tentativas anteriores reprovadas e interações com o validador") continua disponível para a extração, mas como **dado delimitado**, separado da memória transversal de aprendizados. Ficam de fora as mensagens que só fazem sentido dentro da conversa de B.1: o template de B.1, a instrução "Refaça a resolução…" e as correções de formato pedidas ao resolvedor.

Expressão no formato da Metodologia:

> *Tarefa* + *Resultado Aprovado* + *Histórico da Tarefa* + *Aprendizados Pontuais* + *Template B.4* → *Novos Aprendizados Pontuais*

em substituição a

> *Contexto Completo da Tarefa* + *Template B.4* → *Aprendizados Pontuais*

As demais separações continuam: os aprendizados nunca entram nos resultados armazenados que alimentam C.1 e C.3, e a tarefa seguinte recebe só a memória, nunca o histórico nem o resultado completo da anterior.

### 5.5 Exemplo: ITA 2024 Q037 (classificação)

**Enunciado (resumo).** Sejam A, B, C ⊆ ℝ com C ⊆ A. Afirmações: I. (A ∩ B) ∪ C = A ∩ (B ∪ C); II. A ∩ B = C ∪ (B ∩ (ℝ − C)); III. A ∩ (B − C) = (A ∩ B) − C. Alternativas: A) apenas I e II; B) apenas I e III; C) apenas II; D) apenas III; E) I, II e III.

A tarefa T1 avalia a afirmação I. A primeira tentativa conclui, erradamente, que I é falsa e é reprovada; a segunda é aprovada. Prompt efetivamente enviado a B.4 (trecho, renderizado pelos testes com o template real):

```markdown
# B.4 — Extração dos aprendizados pontuais

Esta etapa roda numa janela de contexto própria, depois que a tarefa foi aprovada. […]

## Tarefa

### T1 — Avaliar a afirmação I

Com C ⊆ A, decida se (A ∩ B) ∪ C = A ∩ (B ∪ C), justificando.

## Resultado aprovado

<resultado_aprovado>
Pela distributividade da interseção sobre a união, A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C). Como C ⊆ A, tem-se A ∩ C = C; logo A ∩ (B ∪ C) = (A ∩ B) ∪ C. Conclusão: a afirmação I é verdadeira.
</resultado_aprovado>

## Histórico da tarefa

<historico_da_tarefa>
### Tentativa 1 — reprovada

**Resultado preliminar:**

A afirmação I é falsa, porque a união com C pode acrescentar elementos fora de A.

**Veredito do validador:**

**Decisão:** `reproved`

- `T1-AC1` — não atendido: […]

### Tentativa 2 — aprovada

**Resultado preliminar:** é o resultado aprovado, apresentado na área própria.

**Veredito do validador:**

**Decisão:** `approved`

- `T1-AC1` — atendido: […]
</historico_da_tarefa>

## Aprendizados Pontuais

[…]

- Hipótese: A, B, C ⊆ ℝ com C ⊆ A.
- Alternativas: A) apenas I e II; B) apenas I e III; C) apenas II; D) apenas III; E) I, II e III.

## Instruções
[…]
```

**Saída válida de B.4:**

```json
{"learnings": ["A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade."]}
```

**Saídas inválidas para a mesma tarefa:**

| Saída | Por que é inválida |
|---|---|
| `{"learnings": []}` | A conclusão sobre I é nova (não consta na memória); a lista vazia a perderia, como no benchmark. |
| `"A afirmação I é falsa: a união com C pode acrescentar elementos fora de A."` | Conclusão refutada na tentativa reprovada e substituída na aprovada. |
| `"A afirmação I é verdadeira."` | Fato compacto sem a breve explicação. |
| `"A resposta atende ao critério T1-AC1 ao concluir sobre a afirmação I."` | Critério e veredito, não fato do problema. |
| A resolução inteira copiada | Viola a regra de não transmitir respostas completas entre tarefas. |

**Na tarefa seguinte (T2, afirmação II)**, a área **Aprendizados Pontuais** de B.1 traz:

```markdown
- Hipótese: A, B, C ⊆ ℝ com C ⊆ A.
- Alternativas: A) apenas I e II; B) apenas I e III; C) apenas II; D) apenas III; E) I, II e III.
- A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade.
```

A conversa de T2 tem uma única mensagem (o Template B.1) e não contém a tentativa refutada, o resultado completo de T1, os vereditos nem o prompt de B.4.

### 5.6 Exemplo: conclusão numérica

Tarefa: "Um carro percorre 150 km em 2 h; calcule a velocidade média em m/s." Resultado aprovado: "vₘ = Δs / Δt = 150 km / 2 h = 75 km/h. Dividindo por 3,6: vₘ = 75 / 3,6 ≈ 20,83 m/s."

| Aprendizado | Avaliação |
|---|---|
| "A velocidade média do carro no percurso total de 150 km em 2 h é vₘ ≈ 20,83 m/s (75 km/h): vₘ = Δs/Δt, convertida de km/h para m/s dividindo por 3,6." | **Válido:** grandeza, valor, unidade e condição (percurso total, 150 km em 2 h), mais a breve explicação. |
| "vₘ ≈ 20,83." | Inválido: sem grandeza explícita, sem unidade e sem condições. |
| "A velocidade média é 270 km/h." | Inválido se veio de uma tentativa reprovada que multiplicou por 3,6 em vez de dividir: valor substituído. |
| "Distância percorrida: 150 km." | Inválido como aprendizado de B.4 quando A.3 já o registrou: repete a memória. |

Exemplo de **relação**: "A velocidade média é vₘ = Δs/Δt, com Δs o deslocamento total e Δt o tempo total; a relação não supõe velocidade constante no percurso."

### 5.7 Duplicatas e ausência legítima de fatos novos

Além da instrução do template, a memória de aprendizados descarta, de forma programática, todo aprendizado **em branco** ou **igual a um já registrado** (inclusive no mesmo lote), a menos de maiúsculas e espaços. A regra vale para A.3 e B.4. O evento `learn` mostra o que entrou e, numa seção à parte, o que foi descartado:

```markdown
## Aprendizados extraídos

- A afirmação II é falsa: com B = ∅ e C ≠ ∅, A ∩ B = ∅ e o lado direito vale C.

## Aprendizados repetidos descartados

- a afirmação I é VERDADEIRA: C ⊆ A implica A ∩ C = C, pela distributividade.
- Hipótese: A, B, C ⊆ ℝ com C ⊆ A.
```

Quando nada novo entra, o evento traz "Nenhum aprendizado foi extraído desta tarefa." (seguido dos descartados, se houver). Uma lista vazia **legítima** (por exemplo, uma tarefa de comparação cuja única conclusão já consta na memória) não interrompe o fluxo: a memória fica como estava e as fases seguintes recebem a mesma área de aprendizados.

### 5.8 O que muda no texto do paper

| Trecho atual da Metodologia | Ajuste necessário |
|---|---|
| Seção B.4: "registrando-os em formato de tópicos sucintos e secos, sem justificativas ou descrições narrativas de processo" | Manter "sem descrições narrativas de processo", mas trocar "sem justificativas" por "cada um acompanhado de uma breve explicação que o sustente, sem reproduzir a resolução". |
| Seção B.4: "Esses aprendizados não devem ser conceitos redundantes ou óbvios, mas sim dados de controle, metadados operacionais e restrições práticas" | Para perguntas em linguagem natural: os aprendizados são os **resultados parciais** da tarefa aprovada (valores com grandeza, unidade e condições; classificações com motivo; relações com hipóteses). Uma conclusão nova não deve ser omitida por parecer simples. |
| Seção B.4: "A extração de aprendizados considera o contexto completo da tarefa, incluindo as tentativas reprovadas" | Manter o acesso ao histórico, mas como entrada explícita de B.4, numa janela própria; acrescentar que prevalece a conclusão aprovada e que valores refutados nas tentativas não são registrados. |
| Expressão (eq:fluxo_b4): *Contexto Completo da Tarefa* + *Template B.4* → *Aprendizados Pontuais* | *Tarefa* + *Resultado Aprovado* + *Histórico da Tarefa* + *Aprendizados Pontuais* + *Template B.4* → *Novos Aprendizados Pontuais*. |
| Exemplo de B.4: "Um número primo é aquele que só é divisível por 1 e por ele mesmo." | Substituir por um resultado parcial com explicação, por exemplo: "Entre as opções 2, 4 e 6, somente o número 2 é primo: 4 e 6 têm divisores além de 1 e de si mesmos." |
| Distinção entre resultado armazenado e aprendizado | Mantém-se. Acrescentar que o aprendizado é o fato compacto com breve explicação e o resultado é a resolução completa. |

Parágrafo sugerido para substituir o segundo parágrafo da seção B.4 no paper, no estilo da Metodologia:

> A extração de conhecimento é estruturada ao aplicar o Template B.4, em um contexto próprio, sobre entradas explícitas: a descrição da tarefa, o resultado aprovado, o histórico das tentativas (aprovadas ou não, com os respectivos vereditos do validador) e os aprendizados já registrados. A instrução exige que o modelo registre todo resultado parcial novo da tarefa aprovada — valores com a grandeza, a unidade e as condições em que valem; classificações com um motivo breve; relações com as hipóteses necessárias —, cada um como um fato compacto seguido de uma breve explicação que o sustente, sem reproduzir a resolução nem descrever o processo. Prevalece a conclusão finalmente aprovada: valores refutados ou substituídos durante as tentativas não são registrados. Uma lista vazia só é admitida quando a tarefa não produziu fato novo ou quando todas as suas conclusões já constam na memória.

### 5.9 Decisões de projeto

| Decisão | Justificativa |
|---|---|
| Montar o histórico a partir do registro das tentativas (`Task.attempts`), e não da janela de B.1. | Mantém B.4 isolado da conversa de outra fase e deixa o histórico delimitado, sem os templates de B.1, a instrução de refazer e as correções de formato do resolvedor, que não são conteúdo do problema. |
| Guardar na tentativa as saídas inválidas que o validador corrigiu (`TaskAttempt.invalid_verifier_outputs`). | O paper inclui as "interações com o validador" no histórico; antes elas só existiam na janela de B.1. |
| Separar *Resultado aprovado* e *Histórico da tarefa* em áreas próprias, sem repetir o resultado aprovado no histórico. | Torna explícita a prioridade da conclusão aprovada e evita mandar o mesmo texto duas vezes. |
| Não enviar os critérios de aceite da tarefa a B.4. | Critérios não são fatos do problema e não devem virar aprendizados; os vereditos do histórico já identificam o que foi reprovado. |
| Exigir o fato compacto **e** a breve explicação numa única string. | Mantém o contrato `learnings: list[str]` e a área de aprendizados igual para todas as fases. |
| Descartar duplicatas na memória (normalização de maiúsculas e espaços), além da instrução do template. | Repetições literais são detectáveis com segurança; reformulações não, e continuam a cargo do template. O evento `learn` mostra os descartados, para auditoria. |
| A.3 não muda. | A.3 continua anotando os dados do enunciado sem resolver; só B.4 registra resultados. A deduplicação apenas impede que B.4 repita um dado já anotado por A.3. |

### 5.10 Limitações

- Os testes usam respostas simuladas: verificam o prompt enviado, a fiação, a persistência e o descarte de repetições, mas **não comprovam** que um LLM real nunca omitirá uma conclusão. O ganho precisa ser medido nas baterias de benchmark (por exemplo, reexecutando a Q037).
- A deduplicação programática só reconhece repetições literais, a menos de maiúsculas e espaços. Uma reformulação do mesmo fato não é detectada.
- A breve explicação aumenta um pouco o tamanho da memória e, portanto, os tokens de entrada de todas as fases B e C.
- O prompt de B.4 passa a incluir o resultado aprovado e o histórico como texto, em vez de reaproveitar a conversa já enviada; em tarefas com muitas tentativas longas, o prompt continua proporcional ao histórico.

### 5.11 Validação na implementação

A suíte do backend passa por completo (1524 testes, cobertura de 100%, exigida pelo projeto). Os testes cobrem:

- **Prompt efetivamente enviado a B.4** (templates reais): uma única mensagem numa janela nova, diferente da janela de B.1, sem o template de B.1 nem a instrução de refazer; a tarefa, o resultado aprovado dentro de `<resultado_aprovado>` (uma única vez), o histórico com a tentativa reprovada, a aprovada e os vereditos dentro de `<historico_da_tarefa>`, e a memória na área **Aprendizados Pontuais**. As saídas inválidas do validador entram no histórico antes do veredito.
- **Classificação (Q037):** o aprendizado da afirmação I é persistido na memória (com a tarefa de origem) e na mensagem da sessão; chega à B.1 da tarefa seguinte, cuja conversa não contém a tentativa refutada, o resultado completo, os vereditos nem o prompt de B.4; os aprendizados não entram nos resultados armazenados que C.3 recebe.
- **Conclusão numérica:** o aprendizado com grandeza, valor, unidade e condição chega intacto à tarefa seguinte, sem o resultado completo.
- **Duplicatas:** repetições da memória (com outra caixa e outros espaços) e anotações de A.3 são descartadas; só o fato novo entra; o evento lista os descartados; quando tudo já consta, o evento diz que nada foi extraído e a memória não duplica o fato. Aprendizados em branco não entram nem são listados.
- **Ausência legítima de fatos novos:** `{"learnings": []}` mantém a memória e o fluxo segue até a resposta final.
- **Template real:** áreas delimitadas antes das instruções; registro de todo resultado parcial novo "sem o histórico anterior"; regras para valores, classificações e relações; fato compacto e breve explicação com o exemplo da afirmação I; prioridade da conclusão aprovada; proibição de instruções, critérios, vereditos, relatos e duplicatas; lista vazia só sem fato novo.

Arquivos principais:

| Arquivo | Papel |
|---|---|
| `apps/backend/src/infra/templates/b4_learnings_extraction.md` | Novo Template B.4: áreas Tarefa, Resultado aprovado, Histórico da tarefa e Aprendizados Pontuais; regras dos resultados parciais. |
| `apps/backend/src/application/usecases/ralph_thinking_usecase.py` | B.4 em janela própria, variáveis explícitas, histórico montado das tentativas, evento `learn` com os descartados. |
| `apps/backend/src/domain/entities/thinking/task_attempt.py`, `task.py` | Saídas inválidas do validador na tentativa; `Task.verified_attempts()`. |
| `apps/backend/src/domain/services/learnings_memory.py`, `domain/interfaces/learnings_memory_interface.py` | Descarte de aprendizados em branco ou repetidos; `append` devolve os efetivamente acumulados. |
| `apps/backend/tests/application/usecases/test_ralph_learnings_extraction.py` | Testes de fluxo com os templates reais (Q037, numérico, duplicatas, lista vazia, isolamento). |
| `apps/backend/tests/infra/providers/test_prompt_templates_content.py`, `tests/domain/...` | Testes do template, da memória e das entidades. |
