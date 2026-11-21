# Questões de benchmark — Vestibulares

270 questões reais de múltipla escolha, aplicadas no ENEM, na FUVEST, no ITA e na UNICAMP. Esta ampliação acrescenta 180 questões e preserva byte a byte as 90 anteriores, incluindo as 15 questões originais do ENEM 2023.

| Disciplina | ENEM | FUVEST | ITA | UNICAMP | Total |
| --- | --- | --- | --- | --- | --- |
| História | 28 | 1 | 0 | 1 | 30 |
| Geografia | 28 | 1 | 0 | 1 | 30 |
| Filosofia e Sociologia | 28 | 1 | 0 | 1 | 30 |
| Biologia | 28 | 1 | 0 | 1 | 30 |
| Matemática | 36 | 1 | 8 | 5 | 50 |
| Química | 22 | 1 | 23 | 4 | 50 |
| Física | 34 | 1 | 12 | 3 | 50 |
| Total | 204 | 7 | 43 | 16 | 270 |

Filosofia e Sociologia formam uma única categoria, com 30 questões no total. Cada disciplina abrange pelo menos três anos de edição. As quatro novas áreas contêm questões do ENEM, da FUVEST e da UNICAMP; o ITA não oferece essas disciplinas na primeira fase considerada. Física, Matemática e Química continuam representando as quatro instituições.

As edições são ENEM 2020, 2022, 2023, 2024 e 2025; FUVEST 2024; ITA 2024 e 2025; UNICAMP 2025. O ano do identificador é o da edição, podendo diferir do ano de aplicação: o segundo dia do ENEM 2020 ocorreu em 24/01/2021. Não foram incluídas questões anuladas.

Cada subpasta contém exatamente dois arquivos:

- `enunciado.md`: enunciado e alternativas em Markdown.
- `alternativa_correta.md`: somente a letra e o texto da alternativa indicada pelo gabarito oficial.

Os identificadores seguem `DISCIPLINA_EXAME_ANO_[F1_]CADERNO_QNNN`. `F1` identifica a primeira fase, `UNICA` o caderno único do ITA, `V` a versão da FUVEST e `QZ` as versões equivalentes Q e Z da UNICAMP. No ENEM, Humanas usa o primeiro dia da aplicação regular, caderno 1 azul, e as demais áreas usam o segundo dia, caderno 7 azul. `FILOSOFIA_SOCIOLOGIA` identifica a categoria conjunta. A disciplina é uma classificação de curadoria: o ENEM organiza os cadernos por áreas, e alguns itens são interdisciplinares.

O carregador lê o diretório inteiro, ordena os identificadores e aceita quatro (`A)` a `D)`) ou cinco (`A)` a `E)`) alternativas consecutivas. As 16 questões da UNICAMP preservam suas quatro alternativas originais. A API e a interface obtêm o limite de questões a partir do dataset carregado: agora a bateria completa contém 270 questões, executadas nos dois fluxos. A ordenação começa por Biologia; históricos anteriores continuam vinculados aos seus identificadores.

As transcrições preservam os textos, valores, unidades e alternativas, substituindo quebras de impressão por Markdown e recompondo índices, expoentes e fórmulas. Tabelas foram transcritas integralmente. Os itens foram selecionados para uso textual; o diagrama espacial do ENEM 2025 Q126 foi descrito em texto, com as mesmas coordenadas dadas no enunciado. Dados gerais necessários do ITA foram incluídos no próprio item. Peculiaridades de redação e afirmações incorretas nas alternativas foram mantidas.

As fontes, páginas dos PDFs, gabaritos e hashes de cada questão estão no [catálogo](../sources/CATALOG.md) e no [manifesto](../sources/manifest.json), fora dos prompts enviados ao modelo. As cópias oficiais completas e os registros de preservação estão em [sources](../sources/README.md). A autoria das questões e dos excertos citados pertence às respectivas instituições e autores.

Consulte os comandos e resultados de auditoria em [VALIDATION.md](../VALIDATION.md).
