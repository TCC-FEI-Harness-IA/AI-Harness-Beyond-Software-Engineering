# Orientações para escrever o artigo resumido do INOVA FEI

O artigo do INOVA FEI deve permitir que o leitor compreenda o problema investigado, a solução proposta, a forma de avaliação e os principais resultados em até duas páginas. A redação deve selecionar uma contribuição central do TCC e apresentar evidências suficientes para que o leitor avalie seu alcance.

Este relatório reúne a estrutura observada nos anais, as instruções do modelo disponível no repositório e exemplos de redação aplicados ao TCC sobre o Ralph Loop adaptado. Os trechos de exemplo ajudam a construir o artigo; a distribuição final precisa ser conferida no PDF diagramado.

## Base da análise

Foram examinadas as estruturas dos 145 artigos dos dois volumes em `analise/inova_antigo`, com leitura mais detalhada dos 23 trabalhos de Ciência da Computação.

| Volume | Total de artigos | Artigos de Ciência da Computação |
| --- | ---: | ---: |
| [Anais do segundo semestre de 2024](inova_antigo/Anais_inovaFEI_2_24_-_vfinal_rev031126.pdf) | 89 | 13 |
| [Anais do primeiro semestre de 2025](inova_antigo/Anais%20inovaFEI%201-25.pdf) | 56 | 10 |
| **Total** | **145** | **23** |

Entre os cursos, há um núcleo recorrente: resumo, introdução, objetivo, metodologia, resultados, conclusão e referências. Os nomes e agrupamentos das seções variam. Trabalhos de Administração incluem com maior frequência fundamentação conceitual, entrevistas e análises organizacionais; nos de Computação, destacam-se algoritmos, arquiteturas, bases de dados e avaliações experimentais.

Nos artigos de Computação, o objetivo pode aparecer em uma seção própria ou integrado à introdução. Alguns também reúnem método e resultados em uma seção de experimento. Para organizar o artigo em duas páginas, a sequência recomendada é: **problema, objetivo, método, resultados e contribuição**.

## Exigências do modelo disponível

O [modelo em LaTeX](Template_INOVA/main.tex) contém as seguintes instruções:

| Elemento | Instrução do modelo |
| --- | --- |
| Extensão e idioma | Até duas páginas A4, em português. O texto informa que, em trabalhos maiores, somente as duas primeiras páginas serão publicadas. |
| Corpo do artigo | Duas colunas, espaçamento simples e fonte Times New Roman tamanho 10. |
| Termos estrangeiros | Devem ser grafados em itálico. |
| Título | Arial tamanho 18, negrito, alinhado à esquerda e com iniciais maiúsculas. |
| Identificação | Autores, curso, contatos, orientador e departamento do orientador. |
| Resumo | Texto claro e objetivo, com as principais ideias do desenvolvimento e os principais resultados, quando houver, em até dez linhas. |
| Palavras-chave | Até seis, separadas por vírgulas. |
| Conteúdo | Resumo, introdução, objetivos, metodologia, resultados, conclusões e eventuais referências. |
| Seções | Títulos numerados em algarismos romanos; subseções identificadas por letras. |
| Figuras e tabelas | Legíveis, numeradas e citadas no texto. Legenda abaixo das figuras e acima das tabelas. |
| Referências | Citações numéricas no texto, como [1], com descrição bibliográfica ao final. |
| Cabeçalho e rodapé | Devem ser preservados. |

As sugestões de tamanho e organização apresentadas a seguir são escolhas de redação. O modelo local admite seções adicionais, mas cada uma ocupa espaço que precisa ser dividido com os resultados e as referências.

## Estrutura recomendada e exemplos de redação

### Título e identificação

O título deve identificar a proposta e seu contexto de aplicação. Uma versão curta facilita a leitura e preserva espaço para o conteúdo.

**Exemplo de título:**

> Adaptação do Ralph Wiggum Loop para Resolução de Perguntas em Linguagem Natural

Use o bloco de identificação do modelo para apresentar os autores e o orientador. A explicação da proposta começa no resumo.

### Resumo e palavras-chave

Organize o resumo em quatro movimentos: problema, proposta, avaliação e principal conclusão. Inclua resultados concretos quando a avaliação estiver concluída. O resumo precisa fazer sentido sem a leitura das demais seções.

**Exemplo adaptado aos resultados registrados no repositório:**

> Este trabalho adapta o Ralph Wiggum Loop para a resolução de perguntas em linguagem natural, combinando planejamento, validação iterativa e reinicialização de contexto. A abordagem foi comparada à inferência direta em 743 questões pareadas de vestibulares brasileiros, MMLU e GPQA Diamond. Na avaliação de ponta a ponta, o *harness* obteve 85,73% de acurácia, contra 87,75% da inferência direta. Nos 711 pares sem falhas operacionais, alcançou 89,45%, contra 88,19%, sem diferença global estatisticamente significativa. Nesse recorte, o consumo total de *tokens* correspondeu a 98,36 vezes o da inferência direta. Os resultados indicam ganhos condicionais de qualidade, acompanhados de custo elevado e limitações de confiabilidade operacional.

**Exemplo de palavras-chave:** modelos de linguagem, orquestração de inferência, Ralph Wiggum Loop, validação iterativa, avaliação experimental.

Confira o limite de dez linhas depois de inserir o resumo no modelo. A quantidade de palavras que cabe depende da diagramação.

### Introdução e objetivo

A introdução deve apresentar o problema específico, sua relevância e a contribuição pretendida. Condense os conceitos necessários para entender o trabalho e use poucas referências diretamente relacionadas ao problema ou à abordagem.

**Exemplo de introdução:**

> A resolução de perguntas por modelos de linguagem pode ser organizada em etapas de planejamento, execução e verificação. Esse encadeamento permite revisar respostas intermediárias, mas também acrescenta chamadas ao modelo e pontos de falha. Este trabalho investiga uma adaptação do Ralph Wiggum Loop, originalmente voltado ao desenvolvimento de software, para a resolução de perguntas em linguagem natural.

**Exemplo de objetivo, que pode encerrar a introdução:**

> O objetivo é implementar e avaliar essa adaptação em comparação à inferência direta, considerando acurácia, falhas operacionais e consumo de tokens em diferentes conjuntos de questões.

Esse recorte fornece uma pergunta central para o artigo: **em quais condições a orquestração altera a qualidade das respostas e qual custo acompanha essa alteração?** A seleção dos resultados deve responder a essa pergunta.

### Metodologia

Explique como a solução funciona e como o experimento permite avaliá-la. Para um trabalho de Computação, priorize os componentes que distinguem a proposta, a origem dos dados, o método de comparação e as métricas.

No caso deste TCC, a metodologia precisa esclarecer:

- As três macrofases: planejamento, execução e validação de tarefas, e síntese final.
- A reinicialização de contexto e a persistência explícita de resultados e aprendizados entre etapas.
- A comparação pareada com a inferência direta, usando o mesmo modelo e as mesmas questões.
- Os conjuntos avaliados e os tamanhos das amostras efetivamente pareadas.
- A contabilização das falhas e a análise complementar dos pares sem falha em nenhum dos fluxos.

**Exemplo de descrição condensada:**

> O fluxo proposto compreende planejamento, execução iterativa de tarefas e síntese da resposta final. As etapas utilizam contextos reinicializados e compartilham resultados e aprendizados por registros explícitos. A avaliação compara o harness à inferência direta com o mesmo modelo de linguagem nas mesmas questões. Foram analisados 268 pares de vestibulares brasileiros, 285 do MMLU e 190 do GPQA Diamond. As métricas incluem acurácia, falhas operacionais e consumo de tokens. Na análise de ponta a ponta, as falhas contam como respostas não corretas; uma análise complementar considera apenas os pares sem falha em ambos os fluxos.

Complete a versão final com a identificação do modelo, o protocolo de resposta, as configurações relevantes e a referência dos conjuntos de dados. Uma figura pequena pode representar as macrofases e o caminho de retorno quando uma tarefa é reprovada. Detalhes de interface, infraestrutura e ferramentas de desenvolvimento só precisam entrar quando ajudam a explicar o comportamento avaliado.

### Resultados e discussão

Apresente primeiro o resultado que responde ao objetivo geral. Em seguida, explique os recortes que ajudam a compreender o comportamento observado. Cada comparação deve informar a amostra, os métodos, a métrica e as condições de avaliação.

Uma tabela pode concentrar os valores; o texto deve explicar o achado principal, sua relevância e seus limites. Quando houver testes estatísticos, mantenha a conclusão compatível com a incerteza observada.

**Exemplo de tabela compacta para o resultado global:**

| Avaliação | Pares | Inferência direta | Harness | Diferença |
| --- | ---: | ---: | ---: | ---: |
| Ponta a ponta | 743 | 87,75% | 85,73% | -2,02 p.p. |
| Sem falhas em ambos os fluxos | 711 | 88,19% | 89,45% | +1,27 p.p. |

A diferença corresponde à acurácia do harness menos a acurácia da inferência direta. A unidade é ponto percentual, abreviada como p.p. Os percentuais e as diferenças são arredondados separadamente a partir das contagens originais.

**Exemplo de interpretação:**

> Na avaliação de ponta a ponta, o *harness* apresentou acurácia 2,02 pontos percentuais inferior à inferência direta. Ao considerar os 711 pares sem falha em ambos os fluxos, observou-se ganho de 1,27 ponto percentual. As diferenças globais não atingiram significância de 5% pelo teste de McNemar exato. Nesse segundo recorte, o consumo total de *tokens* correspondeu a 98,36 vezes o da inferência direta. A comparação evidencia a importância de avaliar conjuntamente qualidade das respostas, confiabilidade operacional e custo computacional.

Os números deste exemplo constam no [relatório detalhado dos resultados](RELATORIO_DETALHADO_RESULTADOS_RALPH_LOOP.md), especialmente nas seções de resultado global e custo. Uma tabela por benchmark também pode ser usada, desde que permaneça legível e preserve a distinção entre avaliação completa e pares sem falha.

Ganhos em um subconjunto devem aparecer acompanhados de seu tamanho amostral e do critério de seleção. As falhas fazem parte do desempenho do sistema completo; removê-las define uma análise condicional. Da mesma forma, a existência de reinicialização de contexto na arquitetura, isoladamente, não demonstra que uma eventual melhora foi causada pela redução de degradação do contexto: essa atribuição exige uma comparação que isole o mecanismo.

### Conclusão

Retome o objetivo e diga o que a avaliação permite concluir. Destaque a contribuição, uma limitação que afete sua interpretação e um próximo passo ligado aos achados.

**Exemplo de conclusão:**

> A adaptação implementada permite aplicar planejamento e validação iterativa à resolução de perguntas em linguagem natural. Na amostra avaliada, os ganhos observados entre pares sem falhas coexistem com perda de desempenho de ponta a ponta e elevado consumo de tokens. O experimento não demonstrou superioridade global do harness. Como continuidade, propõe-se reduzir falhas de orquestração e investigar critérios para aplicar o fluxo a questões nas quais o benefício potencial justifique o custo adicional.

### Referências

Selecione as fontes necessárias para sustentar o problema, o método original, os conjuntos de avaliação e a comparação utilizada. Cite cada fonte no ponto em que ela fundamenta uma afirmação. A quantidade deve acompanhar essa necessidade e o espaço disponível.

Use os dados bibliográficos das fontes efetivamente consultadas. Os artigos dos anais servem como exemplos de organização; suas referências precisam ser verificadas antes de serem incorporadas ao novo artigo.

## Distribuição sugerida nas duas páginas

| Área | Conteúdo prioritário |
| --- | --- |
| Início da primeira página | Título, identificação, resumo e palavras-chave. |
| Corpo da primeira página | Introdução, objetivo e início da metodologia. |
| Transição entre as páginas | Conclusão da metodologia e, se útil, uma figura do fluxo. |
| Corpo da segunda página | Tabela ou gráfico principal, interpretação dos resultados e limites da avaliação. |
| Final da segunda página | Conclusão e referências. |

Como ponto de partida, reserve aproximadamente 20% do corpo técnico para introdução e objetivo, 30% para metodologia, 40% para resultados e discussão e 10% para a conclusão. Essas proporções excluem identificação, resumo e referências e devem ser ajustadas à legibilidade das figuras e tabelas.

Para este TCC, uma figura do fluxo e uma tabela comparativa são uma combinação inicial adequada. Escreva o primeiro rascunho já no modelo. Se exceder duas páginas, reduza repetições entre resumo e introdução, definições de conhecimento geral e detalhes que não ajudam a interpretar o experimento. Preserve as informações que sustentam os resultados e a conclusão.

## Exemplos dos anais para consultar

As páginas indicadas abaixo são as impressas nos anais. Os links abrem a página correspondente no arquivo PDF, cuja contagem inclui as páginas iniciais do volume.

| Trabalho | Localização | Aspecto útil para a redação |
| --- | --- | --- |
| [Análise e Combinação de LLMs para Correção Automática de Questões Dissertativas](inova_antigo/Anais%20inovaFEI%201-25.pdf#page=33) | 2025/1, pp. 31 a 32 | Descreve dados, divisão entre treino e teste e métricas de erro em pouco espaço. |
| [Modelagem Segura e Avaliação de Desempenho de Protocolos de Exclusão Mútua Escaláveis em Rust para Ambientes Concorrentes](inova_antigo/Anais%20inovaFEI%201-25.pdf#page=47) | 2025/1, pp. 45 a 46 | Especifica ambiente experimental, carga de trabalho e condições da comparação. |
| [Aplicação de Embedding na Busca Contextualizada de Documentos Científicos](inova_antigo/Anais_inovaFEI_2_24_-_vfinal_rev031126.pdf#page=48) | 2024/2, pp. 47 a 48 | Compara métodos com a busca por palavras-chave e reúne os resultados em tabelas. |
| [Implementação de um Ambiente Virtual Gamificado](inova_antigo/Anais_inovaFEI_2_24_-_vfinal_rev031126.pdf#page=40) | 2024/2, pp. 39 a 40 | Relata a avaliação com 44 participantes e apresenta desempenho, usabilidade e motivação. |

## Revisão antes da entrega

- [ ] O título identifica a proposta e seu contexto de aplicação.
- [ ] O resumo apresenta objetivo, método e resultado principal em até dez linhas.
- [ ] Há no máximo seis palavras-chave.
- [ ] A introdução define o problema e o objetivo do trabalho.
- [ ] A metodologia permite compreender a solução e a comparação experimental.
- [ ] Os resultados informam métricas, unidades e tamanhos das amostras.
- [ ] Ganhos, perdas, falhas e recortes estão descritos de maneira consistente.
- [ ] As afirmações de significância correspondem aos testes realizados.
- [ ] Figuras e tabelas são legíveis no tamanho final e citadas no texto.
- [ ] A conclusão responde ao objetivo e respeita o alcance dos resultados.
- [ ] As citações correspondem às referências bibliográficas.
- [ ] O PDF completo, incluindo referências, contém no máximo duas páginas e preserva o formato do modelo.
