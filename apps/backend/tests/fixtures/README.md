# Matriz semântica de planejamento — versão 1

`planning_semantics_v1.json` contém oito casos sintéticos, generalistas, independentes de datasets
ou gabaritos. Cada caso registra o pedido, critérios gerais de referência, uma proposta de tarefas,
um critério inadequado e uma rubrica de inspeção (`review_checks`). Os casos de C.2 também incluem
resultados existentes, aprendizados e uma lacuna concreta. Os exemplos são material de avaliação;
não entram nos templates de produção nem no contexto de outros pedidos.

Os testes automatizados renderizam os templates reais com essas entradas e verificam o transporte
e o contrato JSON. O teste do parser aceita inclusive o critério inadequado propositalmente:
aceitação estrutural não certifica a semântica. As propostas de referência não são saídas de um
modelo real, e os testes não classificam planos por palavras, número de tarefas ou gabarito.

Para uma avaliação semântica posterior, preserve a versão, o pedido, o template/commit e a saída
bruta do modelo. Inspecione cada plano com a rubrica do caso e registre evidência textual para:

1. Obrigações de conteúdo e apresentação extraídas do pedido, sem novas exigências.
2. Separação entre dados literais, método, hipótese e resultados a obter.
3. Critérios verificáveis sem conclusão quantitativa ou qualitativa antecipada.
4. Preservação de dados, unidades e referências, incluindo dependências pela memória.
5. Cobertura até a determinação final e permissão para essa análise na tarefa responsável.
6. Em C.2, investigação da lacuna concreta sem predeterminar a correção nem criar tarefa de redação.

O julgamento deve considerar significado, aplicabilidade e encadeamento do plano. A presença de uma
frase de proibição ou a validade do JSON não prova obediência. Não há execução paga ou pontuação
semântica automática nesta etapa. Mudanças substanciais na rubrica ou nos casos devem gerar nova
versão para manter a comparação rastreável.

# Matriz semântica de validação — versão 1

`validation_semantics_v1.json` contém 15 casos sintéticos e generalistas para B.2 e C.1, ligados à
política única de evidência dos templates (`## Evidence and consistency policy`). Cada caso traz a
fase, a categoria (`exact`, `approximation`, `elimination`, `estimate`, `identifiable_error`,
`contradiction`, `no_contradiction`, `missing_content`, `presentation_only`, `implicit_content`,
`false_equality`), os critérios, os aprendizados, o resultado preliminar (B.2) ou os resultados
armazenados (C.1), o veredito de referência com justificativa e a rubrica `review_checks`. Os casos
reprovados trazem ainda o resultado corrigido e, em C.1, uma investigação de referência para C.2.

Há casos positivos sem coincidência exata (17,76 → 18 meses; 23 → 20; eliminação sem cálculo;
estimativa aberta; 47 → 44 explicitamente por melhor ajuste; conteúdo implícito; só apresentação;
hipóteses diferentes) e negativos (erro de condicionamento local e na união; contradição real;
razão de distâncias sem período; igualdade falsa 47 = 44).

Os testes automatizados usam a matriz para renderizar os templates reais, conferir que o veredito de
referência não vaza para o prompt, mostrar que o parser aceita relatórios coerentes nos dois
sentidos (logo não julga semântica) e roteirizar o fluxo completo. **O veredito de referência não é
gabarito nem pontuação automática.** Para avaliar um modelo real, envie o prompt renderizado de cada
caso, preserve versão da matriz, commit, modelo, temperatura e saída bruta, compare a decisão com a
referência e registre evidência textual para cada `review_check` — por exemplo, se a reprovação do
condicionamento nomeia a dupla contagem e não a distância entre as opções. Mudanças substanciais nos
casos ou na rubrica devem gerar uma nova versão.

# Matriz de regressões integradas — versão 1

`integration_regressions_v1.json` contém os 12 casos da etapa 07 (Marte — recuperação e cobertura,
colisões, tacho, microscópio, geografia, probabilidade, contagem de listas, química, aproximação
legítima, pergunta aberta e revisão confirmatória). Cada caso registra as frentes envolvidas
(`structure_recovery`, `learnings`, `planning`, `validation`, `synthesis`), um pedido sintético, o
defeito original, o comportamento programático exercitado, os nomes dos testes determinísticos em
`tests/application/usecases/test_ralph_five_fronts_integration.py` e a rubrica `review_checks`.

**Finalidade.** Os testes determinísticos usam só a pergunta: as saídas do modelo são roteirizadas e
provam fiação, estado vigente, auditoria, contabilização e o material entregue a cada fase. O campo
`reference_oracle` (valores, escolha, derivação ou conclusão esperados) pertence **exclusivamente ao
avaliador** de uma avaliação semântica futura: não é enviado ao modelo, não é lido pelo código de
produção, e um teste de contrato verifica que nenhum oráculo aparece nos nove templates; os cenários
também verificam que o harness não o injeta nos prompts de planejamento.

Para avaliar um modelo real, envie apenas a pergunta pelo fluxo completo, preserve versão da matriz,
commit dos templates, modelo, temperatura, saída bruta e sessão exportada, compare com o oráculo e
registre evidência textual para cada `review_check`. Uma resposta roteirizada correta nos testes não é
evidência de acurácia; mudanças substanciais nos casos ou no oráculo devem gerar uma nova versão.

# Matriz da validação da decomposição — versão 1

`decomposition_validation_v1.json` contém sete casos sintéticos e abertos para a nova A.3 (Task
Decomposition Validator), sem relação com questões de benchmark: três planos com defeito (condição
omitida, resultado antecipado, tarefa só de apresentação) e quatro válidos (dados numéricos copiados,
método com hipótese verificada na execução, dependência declarada e estimativa explicada). Cada caso traz
o pedido, critérios gerais, o plano candidato, um parecer esperado para leitura humana
(`expected_review`) e um relatório de referência no contrato de A.3 (`reference_report`).

Os testes renderizam o template real de A.3 com essas entradas, conferem que o parecer esperado não é
injetado no prompt e que o relatório de referência passa no parser. Isso verifica transporte e contrato,
não acurácia: o relatório de referência não é saída de um modelo. Uma avaliação posterior deve registrar a
saída bruta do modelo e julgá-la pelos sete critérios da rubrica, observando também se planos válidos são
aprovados — um validador que reprova tudo não representa melhora.

# Matriz da validação técnica das tarefas — versão 1

`technical_validation_v1.json` contém onze casos sintéticos e generalistas para o critério técnico fixo
`<task_id>-TECH` de B.2 (nova fase de validação — 02), sem relação com questões de benchmark. São cinco
negativos — premissa não fornecida tratada como fato, método fora das suas condições, direção incompatível
com uma tabela, causa de outra etapa temporal e escolha por proximidade sobre cálculo inválido — e seis
controles positivos — tarefa intermediária correta, estimativa de pergunta aberta, hipótese justificada,
aproximação legítima, inferência contextual e ausência de justificativa final não pedida. Cada caso traz a
tarefa (identificação, título e descrição), os critérios planejados, os aprendizados, o resultado preliminar,
a referência (`reference`: decisão, veredito por critério efetivo e justificativa) e a rubrica
`review_checks`. Nos negativos, os critérios planejados estão atendidos e só TECH falha.

Os testes renderizam o template real de B.2 com essas entradas, roteirizam o fluxo completo (inclusive a
retentativa dos negativos, com a justificativa de referência como feedback), conferem que a referência e a
rubrica não chegam ao modelo nem aos templates e que o parser aceita relatórios coerentes nos dois sentidos.
**A referência não é gabarito nem pontuação automática:** para avaliar um modelo real, envie o prompt de B.2
de cada caso, preserve versão da matriz, commit dos templates, modelo, temperatura e saída bruta, compare a
decisão e os vereditos com a referência e registre evidência textual para cada `review_check` — por exemplo,
se a reprovação nomeia a premissa ou a relação que falha, e se os controles positivos são aprovados. Um
validador que reprova tudo não representa melhora. Mudanças substanciais exigem nova versão.

# Matrizes dos refinamentos 03 — validação da decomposição v2, validação técnica v2 e apresentação v1

`decomposition_validation_v2.json` e `technical_validation_v2.json` declaram `"extends"` e trazem só os casos
novos: a matriz da versão 2 é a da versão 1, **inalterada** (um teste confere a igualdade), seguida deles.
`final_answer_fidelity_v1.json` é nova. Nenhum caso vem do benchmark ou de um gabarito.

- **A.3 v2 (8 casos):** condição perdida na junção de tarefas, referente trocado (receita × contribuição),
  prioridade imposta (“mais geral”), condição do usuário copiada (válido), o par “determinar se” (válido) ×
  “demonstrar que” (antecipação), interpretação aberta (válido) e verificação de necessidade de correção
  (válido). Este último traz também um `contradictory_report` — reprovação cujo problema diz não haver
  defeito —, que o parser aceita: só a avaliação semântica detecta essa contradição.
- **TECH v2 (10 casos, todos sobre `T2`):** raiz que falha na substituição, total que contradiz a tabela,
  premissa do planejamento repetida como fato, estimativa condicionada transformada em garantia (e o
  controle positivo que a mantém condicionada), omissão compartilhada usada contra um só candidato, troca
  do objetivo (rapidez × custo), linear tratado como não polinomial, aproximação conferida por substituição
  e preferência justificada com conteúdo verdadeiro nos demais candidatos. Cada nota tem `content` e `source`
  (`null` = enunciado, `"T1"` = tarefa anterior); os testes de fluxo fazem `T1` registrar essas notas, para
  que cheguem a B.2 com o rótulo real (`[Question]`, `[Task T1]`).
- **C.3 v1 (4 casos):** letra da linha marcadora × item aprovado, tradução que preserva filiais, direção e
  condição, código pareado literalmente com o objeto aprovado e melhor ajuste apresentado como tal. Cada
  caso traz o material que C.3 recebe (`stored_results`, notas) e, só para o avaliador, `reference_answer`,
  `invalid_presentation` e `review_checks`.
- **C.3 v2 (1 caso novo sobre os 4 da v1):** `final_answer_fidelity_v2.json` declara `extends` e preserva
  a v1. O resultado determina inequivocamente a bomba como equipamento reprovado, mas anexa o código da
  válvula; a nota do enunciado associa explicitamente cada equipamento ao código correto. A apresentação
  deve conservar a bomba e usar seu código literal, sem escolher outro objeto nem reescrever resultados.
  O caso verifica o material entregue à fase e integra a avaliação semântica futura; uma resposta final
  roteirizada não comprova que o modelo real obedece à regra.

Os testes renderizam os templates reais, conferem que nenhum campo de referência chega ao modelo ou aos
templates, que a produção não lê as matrizes e que o parser aceita relatórios coerentes nos dois sentidos.
**Isso não mede acurácia.** Para avaliar um modelo real, envie o prompt renderizado (ou a pergunta pelo
fluxo completo, no caso de C.3), preserve versão da matriz, commit, modelo, temperatura e saída bruta,
compare com a referência e registre evidência textual para cada `review_check` — por exemplo, se A.3 nomeia
a condição perdida sem calcular a resposta, se aprova os planos válidos, se B.2 cita a substituição e não a
“plausibilidade”, e se C.3 mantém a letra do item aprovado. Um validador que reprova tudo não representa
melhora. Mudanças substanciais exigem nova versão.
