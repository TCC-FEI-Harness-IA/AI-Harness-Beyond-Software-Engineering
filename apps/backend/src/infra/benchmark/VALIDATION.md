# Validação da expansão do benchmark

Conferência concluída em 25 de outubro de 2026.

## Isolamento e revisão

- Worktree exclusiva: `/private/tmp/ai-harness-benchmark-90`.
- Branch: `feat/benchmark-90`.
- A worktree foi criada antes de qualquer edição de arquivo, a partir de `cb59966`.
- A implementação em andamento foi copiada por leitura para a worktree e registrada no snapshot `605efd0`, sem aplicar alterações à árvore original. Esse snapshot permite revisar a expansão separadamente das alterações preexistentes.
- Para revisar somente esta tarefa: `git diff 605efd0..feat/benchmark-90`.
- A árvore original permaneceu na branch `feature/realph-loop`. As edições da expansão foram limitadas ao corpus e à documentação do benchmark, ao seu carregador, ao script de auditoria e aos testes associados, todos na worktree exclusiva.
- Os 30 arquivos das 15 questões preexistentes foram comparados byte a byte com `605efd0` e por SHA-256 com os arquivos da árvore original. Resultado: todos idênticos. Os hashes estão em `sources/preserved_originals.json`.

## Composição final

| Disciplina | ENEM | FUVEST | ITA | UNICAMP | Total |
| --- | --- | --- | --- | --- | --- |
| Física | 17 | 1 | 9 | 3 | 30 |
| Matemática | 16 | 1 | 8 | 5 | 30 |
| Química | 14 | 1 | 11 | 4 | 30 |
| Total | 47 | 3 | 28 | 12 | 90 |

São 90 pastas, 90 enunciados e 90 arquivos de alternativa correta, incluindo as 15 questões originais e 75 adições. As edições vão de 2022 a 2025. Cada disciplina contém os quatro vestibulares e ao menos três anos de edição. As 12 questões da UNICAMP mantêm quatro alternativas; as outras 78 mantêm cinco.

## Conteúdo e procedência

As 75 adições foram conferidas com os PDFs oficiais, por extração de texto e inspeção das páginas renderizadas. A revisão incluiu acentuação, índices, expoentes, unidades, frações, alternativas, tabelas, constantes gerais e textos comuns. Foram selecionadas questões que dispensam figuras e gráficos. As tabelas necessárias foram transcritas integralmente para Markdown. As quatro alternativas da UNICAMP não foram ampliadas artificialmente.

O catálogo registra cada questão com sua edição, fase, caderno e número original, ligando-a à prova e ao gabarito oficial. O manifesto inclui as páginas do PDF e hashes dos arquivos. As fontes são os acervos oficiais do Inep, FUVEST, ITA e Comvest. Os 14 PDFs oficiais completos foram arquivados sem alteração em `sources/`.

Foram utilizados os gabaritos já com suas retificações e anulações: em especial, FUVEST 2024 retificado em 24/11/2023 e UNICAMP 2025 Q/Z `FINAL_site`. Nenhuma questão anulada foi selecionada. A auditoria extraiu novamente 540 entradas dos sete gabaritos, conferiu sua transcrição e confirmou as 90 respostas selecionadas. A FUVEST foi conferida exclusivamente na coluna V; ENEM no caderno 7 azul; UNICAMP em Q/Z; ITA na primeira fase da edição correspondente.

## Verificações automáticas

Comandos executados a partir de `apps/backend` na worktree. Para a suíte e o lint, foi usado o Python do ambiente já instalado no repositório original, somente como executável e fonte de dependências; o diretório de execução e o código importado foram os da worktree. A auditoria de PDF usou um ambiente temporário separado com PyMuPDF 2.0.

```sh
python -m pytest
```

Resultado final: **1371 testes passaram**, com **100% de cobertura** (3616 instruções e 514 ramificações; nenhuma falta). A suíte exige cobertura mínima de 100%, que foi atendida.

```sh
python -m pytest --no-cov tests/infra/providers \
  tests/infra/startups/test_benchmark_startups.py \
  tests/infra/routes/test_benchmark_end_to_end.py
```

Resultado: **59 testes passaram** após a revisão final do conteúdo. Incluem integridade do corpus, metadados, preservação dos originais, ausência de gabaritos órfãos, duplicatas normalizadas e recursos ausentes; carregamento de quatro e cinco alternativas; recusa de gabarito E em questão de quatro alternativas; API de consulta; aceitação de 90 questões e recusa de 91.

A integração completa executou as 90 questões em inferência simples e Ralph, com transporte HTTP simulado: **180 execuções de fluxo**, **810 chamadas HTTP simuladas**, 90 questões concluídas e 90 respostas avaliadas como corretas em cada fluxo. Não houve chamadas a provedores externos de modelos.

```sh
python scripts/verify_benchmark_sources.py
```

Resultado: hashes dos **14 PDFs** e transcrição dos **sete gabaritos oficiais** íntegros; **90/90 respostas coincidem** com os documentos oficiais definitivos; nenhuma questão selecionada anulada e nenhuma página referenciada fora do documento.

```sh
python -m flake8 \
  src/infra/providers/file_benchmark_question_provider.py \
  tests/infra/providers/test_file_benchmark_question_provider.py \
  tests/infra/providers/test_benchmark_dataset_integrity.py \
  tests/infra/routes/test_benchmark_end_to_end.py \
  tests/infra/startups/test_benchmark_startups.py \
  scripts/verify_benchmark_sources.py
git diff --check
```

Resultado: sem erros de lint ou espaços em branco indevidos. Não foram encontrados limites fixos que impeçam a execução das 90 questões: o limite de quantidade é calculado a partir do corpus; o limite de paralelismo é independente.

## Pendências

Nenhuma pendência impede os critérios solicitados. A branch fica disponível para revisão e integração com a implementação em andamento; a árvore original não foi mesclada nem sobrescrita.
