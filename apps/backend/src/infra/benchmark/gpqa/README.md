# GPQA na aplicação

O terceiro benchmark da página **BenchMark** oferece as três variantes oficiais do GPQA.
Escolha **GPQA** e, em **Variante GPQA**, selecione Diamond, Main ou Extended. A quantidade
padrão inclui todos os itens da variante; é possível reduzir a amostra ou filtrar uma disciplina.

| Variante | Questões | Biologia | Química | Física |
|---|---:|---:|---:|---:|
| Diamond | 198 | 19 | 93 | 86 |
| Main | 448 | 78 | 183 | 187 |
| Extended | 546 | 105 | 214 | 227 |

Os conjuntos se sobrepõem e devem ser avaliados separadamente. Todas as questões são de
pós-graduação em inglês. Configure semente, modelo, tokens, temperatura e paralelismo como nos
outros benchmarks. Os dados já estão incluídos; a execução não baixa dados nem exige conta
Hugging Face. Cada questão passa pela inferência simples e pelo Ralph Loop.

## Fonte e reprodução

Fonte: David Rein et al., [GPQA: A Graduate-Level Google-Proof Q&A Benchmark](https://arxiv.org/abs/2311.12022).
O [repositório oficial](https://github.com/idavidrein/gpqa) fornece `dataset.zip` com senha pública.
Usamos `dataset/gpqa_diamond.csv`, `dataset/gpqa_main.csv` ou `dataset/gpqa_extended.csv` na revisão `56686c06f5e19865c153de0fdb11be3890014df7`.
A licença do dataset é **CC BY 4.0**, reproduzida em `LICENSE`.

Os autores [pedem para não publicar exemplos em texto ou imagens na internet](https://huggingface.co/datasets/Idavidrein/gpqa).
Por isso versionamos o ZIP original protegido, sem converter questões para arquivos de texto aberto.
O provider lê apenas a variante selecionada em memória, usando a senha pública `deserted-untie-orchid`.
Histórico, sessões e arquivos de erros continuam contendo os dados necessários à análise local;
evite publicar esses artefatos com enunciados e alternativas.

`manifest.json` registra URL fixada, revisão, licença, hashes SHA-256 do ZIP e de cada CSV,
contagens por variante e disciplina e semente das alternativas. Antes de chamar modelos, o provider verifica
hashes, revisão, contagens, IDs únicos, campos obrigatórios e domínios. Os IDs usam `Record ID`
do arquivo original, com prefixo `GPQA_diamond_`, `GPQA_main_` ou `GPQA_extended_`. Textos e distratores duplicados do original
são preservados. Apenas `Question`, `Correct Answer` e `Incorrect Answer 1–3` definem o item;
explicações e colunas de revisões anteriores não entram no prompt.

Para restaurar o arquivo oficial, execute de `apps/backend`:

```sh
curl -L --fail https://raw.githubusercontent.com/idavidrein/gpqa/56686c06f5e19865c153de0fdb11be3890014df7/dataset.zip -o src/infra/benchmark/gpqa/dataset.zip
python -m pytest tests/infra/providers/test_gpqa_benchmark_question_provider.py --no-cov
```

## Protocolo adaptado

- **GPQA generativo 0-shot**, uma passagem por questão e por fluxo, sem exemplos.
  O campo persistido `split` identifica a variante (`diamond`, `main` ou `extended`); não é um split de treino.
- As quatro alternativas são permutadas no subconjunto inteiro, na ordem original do CSV, com
  `random.Random(0).sample(range(4), 4)`, e o gabarito é remapeado pela mesma permutação.
  A ordem fica igual para os dois fluxos, filtros, amostras, reexecuções e exportações.
  A semente fixa de alternativas faz parte deste protocolo e é independente de `sample_seed`.
- `sample_seed` (padrão 42) controla a seleção/ordem das questões. Como no MMLU, a amostra alterna
  entre disciplinas embaralhadas, sem reposição. Um filtro vazio inclui todas. A execução integral
  usa todos os itens da variante; amostras equilibradas não têm a mesma distribuição do corpus integral.
- O gabarito é usado somente após a execução. Ambos os fluxos recebem o mesmo enunciado,
  alternativas e instrução em inglês ([`../prompts/gpqa.md`](../prompts/gpqa.md)), solicitando uma
  escolha final `FINAL_ANSWER: A` (ou B–D).
  O avaliador comum também aceita letra isolada ou alternativa completa isolada. Respostas
  ambíguas, alternativas inválidas e falhas técnicas contam como erro, com diagnóstico separado.
- A acurácia de cada fluxo é `acertos / questões executadas`. Tentativas internas do Ralph não
  são votos adicionais; somente sua resposta final é corrigida. Mantêm-se orçamento por sessão,
  política de retentativas, cancelamento por desconexão e ausência de retomada automática.
- Histórico e detalhes preservam dataset, revisão, protocolo, subconjunto, disciplinas, semente,
  IDs executados e disciplina de cada questão. Reexecução e exportação restauram a variante persistida e verificam revisão e subconjunto.
  Baterias Diamond anteriores mantêm seus IDs, alternativas, gabaritos e protocolo.

O [baseline original](https://github.com/idavidrein/gpqa) oferece vários protocolos.
A [implementação de referência do simple-evals](https://github.com/openai/simple-evals/blob/main/gpqa_eval.py)
usa Diamond, permuta alternativas e pontua por acurácia, com repetições e formato de saída próprios.
Esta integração adapta esses princípios ao avaliador e aos dois fluxos da aplicação. Não reproduz
automaticamente uma pontuação de ranking: reporte **GPQA [Diamond/Main/Extended] generativo 0-shot**, amostra,
fluxo, configuração do modelo e revisão. A semente reproduz a seleção, não garante saídas idênticas do LLM.

## API

`GET /v1/benchmark/questions?benchmark=gpqa` descreve Diamond, preservando os clientes anteriores.
Para escolher outra variante, use `?benchmark=gpqa&gpqa_subset=main` ou
`?benchmark=gpqa&gpqa_subset=extended`. A descrição inclui IDs e contagens por disciplina,
sem enunciados nem gabaritos. O frame inicial de `WS /v1/benchmark/run` aceita:

```json
{
  "benchmark": "gpqa",
  "gpqa_subset": "extended",
  "few_shot": 0,
  "subjects": [],
  "sample_seed": 42,
  "question_count": 546,
  "max_parallel": 5,
  "llm_model_config": {
    "provider": "open_router",
    "provider_config": { "model_name": "seu-modelo" },
    "max_tokens": 50000,
    "temperature": 0
  }
}
```

`gpqa_subset` aceita `diamond` (padrão), `main` ou `extended`. Valores desconhecidos e a seleção
de Main/Extended em pedidos de outros benchmarks são recusados.
Omitir `question_count` executa todos os itens das disciplinas escolhidas. Para escolher uma quantidade
por disciplina, envie `subject_counts` (ex.: `{"physics": 20, "chemistry": 0}`), de zero até o total de cada
uma, sem `subjects`; cada cota é uma amostra definida por `sample_seed`. `few_shot` só aceita 0;
`subjects` aceita `biology`, `chemistry` e `physics`; `sample_seed` aceita inteiros de 0 a 4294967295.
Os limites são verificados antes de persistir a bateria ou chamar modelos. Comece com uma amostra
pequena para estimar tempo e custo: uma bateria integral cria 396 sessões em Diamond, 896 em Main
ou 1.092 em Extended, e o Ralph faz várias chamadas.
