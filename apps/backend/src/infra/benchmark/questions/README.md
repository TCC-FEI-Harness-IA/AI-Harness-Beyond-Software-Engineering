# Questões de benchmark

90 questões reais de múltipla escolha: 30 de Física, 30 de Matemática e 30 de Química. As 15 questões preexistentes do ENEM 2023 foram preservadas byte a byte. As 75 novas questões provêm de provas realizadas do ENEM, FUVEST, ITA e UNICAMP, com respostas verificadas nos gabaritos oficiais definitivos.

| Disciplina | ENEM | FUVEST | ITA | UNICAMP | Total |
| --- | --- | --- | --- | --- | --- |
| Física | 17 | 1 | 9 | 3 | 30 |
| Matemática | 16 | 1 | 8 | 5 | 30 |
| Química | 14 | 1 | 11 | 4 | 30 |
| Total | 47 | 3 | 28 | 12 | 90 |

As edições utilizadas são ENEM 2022, 2023 e 2024; FUVEST 2024; ITA 2024 e 2025; UNICAMP 2025. O ano no identificador é o da edição de ingresso, que pode diferir do ano de realização da prova. Cada disciplina contém questões dos quatro vestibulares e de pelo menos três anos de edição.

Cada subpasta contém exatamente dois arquivos:

- `enunciado.md`: enunciado completo e alternativas originais em Markdown.
- `alternativa_correta.md`: somente a letra e o texto exato da alternativa indicada pelo gabarito oficial.

Os identificadores originais foram mantidos. Novos identificadores seguem `DISCIPLINA_EXAME_ANO_[F1_]CADERNO_QNNN`; `F1` identifica a primeira fase, `UNICA` o caderno único do ITA, `V` a versão da FUVEST e `QZ` as versões equivalentes Q e Z da UNICAMP. O ENEM usa o segundo dia da aplicação regular, caderno 7 azul.

O carregador associa os dois arquivos pela pasta, ordena os identificadores e aceita quatro (`A)` a `D)`) ou cinco (`A)` a `E)`) alternativas consecutivas. As 12 questões da UNICAMP preservam suas quatro alternativas originais. Os gabaritos e metadados ficam fora do enunciado enviado ao modelo. Não há limite fixo de 15 questões: a quantidade permitida é determinada pelo dataset carregado.

As quebras de impressão foram substituídas por parágrafos, tabelas Markdown, índices e expoentes Unicode e fórmulas LaTeX. Os textos, valores, unidades e alternativas foram conferidos nas páginas dos PDFs oficiais, incluindo as continuações em outras páginas. Foram selecionadas questões que dispensam imagens ou gráficos; as tabelas necessárias foram integralmente transcritas. Dados gerais e textos comuns da prova necessários para interpretar questões isoladas foram incluídos no próprio enunciado. Na prova do ITA 2024, a unidade de G foi preservada como impressa, inclusive o expoente `kg³`.

A procedência individual, as páginas, os links oficiais e as versões dos gabaritos estão no [catálogo de fontes](../sources/CATALOG.md) e no [manifesto estruturado](../sources/manifest.json). As cópias oficiais completas e seus hashes SHA-256 estão em [sources](../sources/README.md), fora do diretório percorrido pelo carregador. O [registro dos arquivos preexistentes](../sources/preserved_originals.json) permite verificar sua preservação.

A autoria das questões pertence às respectivas instituições. A página oficial do Inep informa a licença [Creative Commons Atribuição-SemDerivações 3.0 Não Adaptada](https://creativecommons.org/licenses/by-nd/3.0/deed.pt_BR). A transcrição muda a apresentação para Markdown, preservando o conteúdo.

Consulte os comandos e resultados da conferência em [VALIDATION.md](../VALIDATION.md).
