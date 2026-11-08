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
