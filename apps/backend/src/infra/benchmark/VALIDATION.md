# Validação da ampliação do benchmark Vestibulares

Conferência: 7 de novembro de 2026.

O corpus passou de 90 para 270 questões: 30 de História, 30 de Geografia, 30 de Filosofia e Sociologia (categoria conjunta), 30 de Biologia, 50 de Matemática, 50 de Química e 50 de Física. São 180 questões adicionadas, sem alterações nos 180 arquivos das 90 questões anteriores.

As origens continuam sendo ENEM, FUVEST, ITA e UNICAMP. Cada nova área contempla ENEM, FUVEST e UNICAMP e pelo menos três anos de edição. Os itens de Física, Matemática e Química continuam presentes nas quatro instituições. O primeiro dia do ENEM usa o caderno 1 azul; o segundo dia usa o caderno 7 azul. A edição ENEM 2020 foi aplicada em janeiro de 2021.

## Gabaritos e fontes

A partir de `apps/backend`, com PyMuPDF instalado como dependência opcional de auditoria:

```sh
python scripts/verify_benchmark_sources.py
```

Resultado: os 24 PDFs mantêm os hashes registrados; os gabaritos das 12 fontes são reextraídos e coincidem com `official_answer_keys.json`; as páginas referenciadas existem; as 270 respostas selecionadas coincidem com os gabaritos oficiais. Questões anuladas não entram na seleção. No primeiro dia do ENEM, a transcrição do gabarito inclui apenas as questões 46–90 de Humanas. Na FUVEST, utiliza-se a prova V e a correção definitiva.

A revisão do conteúdo combinou leitura dos textos extraídos com inspeção visual das páginas renderizadas para fórmulas, radicais, tabelas e trechos repartidos entre colunas. Foram recompostos, por exemplo, os radicais do ENEM 2024 Q149, os expoentes do ENEM 2020 Q107 e as frações e reações do ITA 2025. As tabelas do ENEM 2022 Q115, Q171 e Q177 foram transcritas integralmente. O diagrama espacial do ENEM 2025 Q126 recebeu uma descrição textual das mesmas coordenadas fornecidas no enunciado. Gabaritos e metadados de procedência ficam fora dos prompts.

## Integridade e integração

A partir de `apps/backend`:

```sh
python -m pytest --no-cov \
  tests/infra/providers/test_benchmark_dataset_integrity.py \
  tests/infra/providers/test_file_benchmark_question_provider.py \
  tests/infra/routes/test_benchmark_end_to_end.py \
  tests/infra/startups/test_benchmark_startups.py
```

Resultado: **51 testes passaram**. A suíte verifica quantidades por disciplina, instituições e anos, IDs e conteúdo sem duplicatas, estrutura de arquivos, alternativas consecutivas, identidade entre o texto do gabarito e sua alternativa, hashes, ausência de arquivos órfãos e preservação byte a byte das questões anteriores.

O teste de bateria completa executa as 270 questões nos dois fluxos com transporte de LLM simulado e verifica as 540 sessões resultantes. A API descreve as 270 questões disponíveis e rejeita uma solicitação de 271 questões antes de chamar o provedor. Essa validação exercita o carregamento e a execução da bateria; não mede o desempenho de um modelo real.

`git diff --check` também passou. O [catálogo](sources/CATALOG.md), o [manifesto](sources/manifest.json) e os PDFs arquivados permitem revisar cada item individualmente.
