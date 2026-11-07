# A.1 — Definição dos critérios de aceite gerais

Analise o enunciado abaixo e produza as diretrizes que a **resposta final** entregue ao
usuário deverá satisfazer.

## Enunciado

{{user_question}}

## Instruções

Identifique, a partir do próprio enunciado:

1. **Idioma** — o idioma em que a resposta final deve ser escrita.
2. **Estrutura e formato** — a forma solicitada da saída, por exemplo a seleção de uma alternativa
   entre as oferecidas, ou o desenvolvimento textual de uma explicação. Na ausência de formato
   explícito, registre apenas o que decorre do tipo de pedido, sem inventar obrigações de apresentação.
3. **Termos e restrições obrigatórios** — os termos, condições e limites que o enunciado impõe
   e que a resposta final precisa respeitar.
4. **Tópicos-chave** — os tópicos que precisam constar no conteúdo final para que a resposta
   seja considerada completa.

Os critérios descrevem **a resposta final**, não o processo de resolução. Não escreva critérios
sobre como raciocinar, quais passos seguir ou como dividir o trabalho.

Registre as restrições reais do pedido. Orientações genéricas como "seja objetivo" ou "responda
brevemente" não autorizam limites arbitrários de linhas ou palavras. Limites numéricos só entram
quando foram pedidos explicitamente. Diferencie justificativa opcional de obrigatória: se o usuário
disser "pode justificar", não exija justificativa; se disser "justifique", preserve essa obrigação
de conteúdo. A explicação interna das tarefas não torna a explicação obrigatória na resposta final.

**Não resolva a pergunta nesta etapa.** Nenhum critério pode conter, sugerir ou antecipar a
resposta ao enunciado, nem listar conceitos, termos ou afirmações das alternativas para
aprová-los ou descartá-los de antemão.

Em **questões de múltipla escolha**, defina que a alternativa correta deve ser aquela
**relativamente mais coerente e melhor sustentada** pelo enunciado em comparação às demais
(melhor ajuste por eliminação). Não exija correspondência 100% literal palavra por palavra nem
proíba paráfrases, sínteses ou inferências interpretativas razoáveis que tornem todas as opções
inválidas. Quando a escolha depender de um valor calculado, não exija correspondência numérica
exata nem proíba a escolha da alternativa de valor mais próximo: uma aproximação é aceitável desde
que uma das alternativas seja selecionada.

Cada critério recebe um identificador próprio, na forma `AC1`, `AC2`, e assim por diante.

## Exemplos de critérios válidos e inválidos

- Pedido: "Indique a alternativa de forma objetiva; pode justificar". Válido: "Indicar a alternativa
  correta de forma objetiva, com justificativa opcional". Inválido: "Usar exatamente duas linhas e
  justificar obrigatoriamente" — ambas as obrigações foram inventadas.
- Pedido: "Responda em duas linhas e justifique". Válido: preservar as duas linhas e a justificativa
  obrigatória. Inválido: tratar a justificativa pedida como opcional por ser uma resposta curta.
- Pedido: "Responda apenas com a letra". Válido: restringir a apresentação final à letra.
  Inválido: proibir explicações nos resultados internos ou exigir que cada tarefa já contenha
  a resposta no formato final. Este exemplo não determina qual letra é correta.

## Formato de saída

Responda **exclusivamente** com um objeto JSON, sem nenhum texto antes ou depois e sem cerca de
código, no formato:

{"general_acceptance_criteria": [{"id": "AC1", "description": "..."}]}
