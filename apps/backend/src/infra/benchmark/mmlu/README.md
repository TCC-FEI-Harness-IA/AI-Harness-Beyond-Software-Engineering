# MMLU na aplicação

A página **BenchMark** permite escolher entre **Vestibulares brasileiros** (padrão, preservando
o fluxo existente) e **MMLU**. Os dois datasets comparam a inferência simples e o Ralph Loop pelo
mesmo executor, com sessões independentes, correção determinística e medição de tokens e duração.

O MMLU incluído contém as 14.042 questões de `test` e os 285 exemplos de `dev` de
[`cais/mmlu`](https://huggingface.co/datasets/cais/mmlu), revisão
`c30699e8356da336a370243923dbaf21066bb9fe`. São 57 disciplinas, em inglês, com quatro alternativas
preservadas em sua ordem original. Não há download nem dependência de Hugging Face ou PyArrow
durante a execução da aplicação, inclusive em Docker.

## Protocolo

- **Generativo 0-shot:** cabeçalho da disciplina, questão de teste, alternativas A–D e instrução de resposta.
- **Generativo 5-shot:** acrescenta os cinco exemplos respondidos do `dev` da mesma disciplina, na ordem original.
  É o protocolo inicialmente selecionado na interface MMLU.
- Os dois fluxos recebem o mesmo prompt externo. Apenas os exemplos `dev` levam suas respostas no prompt;
  o gabarito do item `test` só é usado pelo avaliador depois da execução.
- O modelo pode explicar sua resposta e deve terminar com `RESPOSTA_FINAL: A` (ou B, C, D).
  Também são aceitas uma letra isolada ou a alternativa completa isolada, como no benchmark existente.
  Respostas ambíguas, alternativas inexistentes e falhas técnicas contam como erro, com diagnóstico separado.
- A acurácia global é `acertos / questões executadas`. Uma bateria interrompida contém resultados parciais.
  Tentativas internas do Ralph não são tentativas extras de pontuação: somente sua resposta final é corrigida.
- O Ralph mantém sua política vigente de retentativas, incluindo temperatura 1 em retentativas; a temperatura
  configurada continua sendo a temperatura inicial. O teto de tokens vale por sessão, em cada fluxo.

Este protocolo usa o dataset MMLU com geração de respostas. A referência original compara probabilidades
das letras A–D. O uso de geração, instrução de saída e Ralph altera o procedimento; resultados devem ser
identificados como **MMLU generativo 0-shot/5-shot**, com amostra e configuração, e comparados a avaliações
que usem o mesmo protocolo. Não são uma reprodução automática de pontuações de rankings externos.
Referências: [artigo](https://arxiv.org/abs/2009.03300),
[avaliação original](https://github.com/hendrycks/test/blob/master/evaluate.py),
[variantes do LM Evaluation Harness](https://github.com/EleutherAI/lm-evaluation-harness/tree/main/lm_eval/tasks/mmlu).

## Amostras e reprodução

Na interface, escolha todas as disciplinas ou uma disciplina específica, a quantidade de questões,
o protocolo e a semente. A API também aceita uma lista de disciplinas. A seleção embaralha os itens de
cada disciplina e alterna entre elas, sem reposição, usando um gerador aleatório local. Assim, uma
amostra pequena não fica restrita às primeiras matérias em ordem alfabética. Em uma bateria completa,
todos os itens selecionados são executados uma vez; a ordem também é determinada pela semente.

A interface começa com até **285 questões de teste**, uma amostra exploratória de cinco por disciplina
quando todas estão selecionadas. Essas questões não são os 285 exemplos `dev`. Amostras equilibradas
entre disciplinas têm composição diferente do teste integral: sua acurácia descreve a amostra, não deve
ser reportada como a pontuação do MMLU completo. Para executar o teste integral, informe 14.042 questões
com todas as disciplinas selecionadas (ou omita `question_count` na API). Também é possível escolher
a quantidade de cada disciplina (de zero ao total dela) com `subject_counts`, em vez de uma amostra
equilibrada; cada cota é amostrada com a mesma semente.

A bateria preserva dataset, revisão, protocolo, split, disciplinas filtradas, semente e os IDs efetivamente
executados. Cada questão preserva sua disciplina. O histórico anterior sem esses campos é interpretado
como Vestibulares. A exportação de erros consulta a origem da bateria e verifica a revisão MMLU.

Um teste completo cria 28.084 sessões; o Ralph pode fazer várias chamadas por sessão. Comece por uma
amostra para dimensionar tokens e tempo. O processamento mantém o comportamento do WebSocket existente:
fechar ou recarregar a página interrompe a bateria; navegar dentro da aplicação mantém a conexão.
Não há retomada automática de baterias interrompidas. A tabela da interface pagina 100 questões por vez.

## API

`GET /v1/benchmark/questions` continua descrevendo vestibulares.
`GET /v1/benchmark/questions?benchmark=mmlu` descreve MMLU, incluindo a revisão e a quantidade por disciplina.
Valor desconhecido de `benchmark` é recusado com HTTP 422.

Frame inicial de `WS /v1/benchmark/run`:

```json
{
  "benchmark": "mmlu",
  "few_shot": 5,
  "subjects": ["college_physics", "high_school_physics"],
  "sample_seed": 42,
  "question_count": 20,
  "max_parallel": 5,
  "llm_model_config": {
    "provider": "open_router",
    "provider_config": { "model_name": "seu-modelo" },
    "max_tokens": 50000,
    "temperature": 0
  }
}
```

`benchmark` ausente equivale a `vestibular`; `few_shot` ausente equivale a 0. `subjects` ausente ou vazio
seleciona todas as disciplinas; `sample_seed` tem padrão 42 e aceita inteiros de 0 a 4.294.967.295.
Vestibulares continuam selecionando as primeiras N questões na ordem vigente; `subjects` e exemplos
5-shot não são aceitos em Vestibulares. GPQA também aceita disciplinas, mas somente 0-shot.
Os limites são validados antes de persistir uma bateria ou chamar um modelo.

## Procedência e auditoria

`manifest.json` fixa revisão, licença, URLs originais, hashes SHA-256 dos Parquets e dos JSONL, contagens e
distribuição por disciplina. O provider verifica os hashes e contagens antes de executar modelos. Os IDs
contêm disciplina, split e posição original dentro da disciplina. Os textos não foram traduzidos ou corrigidos.
`LICENSE` reproduz a licença MIT publicada pelo repositório original do benchmark.

Para reconstruir os JSONL, baixe os dois Parquets dos URLs fixados no manifesto e salve-os como
`test.parquet` e `dev.parquet` em um diretório temporário. Instale `pyarrow==19.0.1` apenas no ambiente
de auditoria e execute, de `apps/backend`:

```sh
python scripts/import_mmlu.py --source-dir /caminho/para/parquets
```

O importador verifica os hashes dos arquivos de origem antes da conversão. A saída é determinística.
O teste `tests/infra/providers/test_mmlu_benchmark_question_provider.py` confere o corpus local inteiro,
incluindo suas 57 disciplinas, e testa a separação entre exemplos de desenvolvimento e questões de teste.
