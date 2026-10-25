# Teste benchmark no container

O script executa as 15 questões pelos mesmos composition roots usados pela API (`DefaultMessageStartup` e `RalphThinkingStartup`). Cada questão passa pela inferência simples e depois pelo RALPH LOOP adaptado. Uma fila FIFO distribui o trabalho entre cinco workers por padrão, sempre com o modelo `deepseek/deepseek-v4-flash-0731` via OpenRouter.

As sessões, mensagens, invocações e métricas são persistidas **no armazenamento normal do backend**, conforme `RALPH_SESSION_STORAGE_BACKEND`: MongoDB ou JSON. O script herda as configurações e credenciais do container. Não há leitor de históricos locais nem configuração `BENCHMARK_RESULTS_PATH`.

## Executar com Docker Compose

Na raiz do projeto, atualize o backend e o front-end, incluindo o volume com o script e as questões:

```bash
docker compose up -d --build backend frontend
```

Valide o dataset sem chamar modelos nem gerar sessões:

```bash
docker compose exec -T backend python /opt/benchmark/executar.py --dry-run
```

Execute o benchmark real:

```bash
docker compose exec -T backend python /opt/benchmark/executar.py
```

As credenciais de `apps/backend/.env` já são fornecidas ao container pelo Compose. O script usa o mesmo banco ou diretório de sessões da API. A execução real faz chamadas cobradas pelo provedor.

Para o ambiente de desenvolvimento, use o mesmo arquivo Compose em todos os comandos:

```bash
docker compose -f docker-compose.dev.yml up -d --build backend frontend
docker compose -f docker-compose.dev.yml exec -T backend python /opt/benchmark/executar.py
```

Parâmetros opcionais:

```bash
docker compose exec -T backend python /opt/benchmark/executar.py \
  --concurrency 5 --max-tokens 4096 --temperature 0
```

O modelo é fixado no processo do benchmark; os limites de recursos `RALPH_*` e os timeouts são os mesmos configurados no backend. A inferência simples continua sendo uma única chamada; o Ralph mantém suas próprias fases e retentativas.

## Metadados persistidos em Session

Cada sessão contém `benchmark_details`, uma instância da classe dedicada `BenchmarkDetails`. Os nomes abaixo foram mantidos conforme o contrato solicitado:

| Campo | Conteúdo |
| --- | --- |
| `is_banchmark` | `true` quando criada pelo script; `false` em sessões comuns da API |
| `question_name` | Nome da pasta que identifica a questão |
| `corret_answer` | Alternativa correta completa, com letra e texto |
| `providade_answer` | Resposta bruta devolvida pelo fluxo |
| `inference_mode` | Enum `simple` ou `ralph` |
| `run_id` | Identificador único da execução do benchmark |
| `expected_alternative` | Letra esperada |
| `selected_alternative` | Letra identificada na resposta, ou `null` |
| `is_correct` | Acerto/erro; `null` enquanto a avaliação não terminou |
| `duration_seconds` | Duração do fluxo |
| `error` | Diagnóstico de falha técnica ou resposta inválida |

Nas sessões comuns, todos os campos são `null`, exceto `is_banchmark=false`. Sessões antigas sem esse campo continuam legíveis com esse mesmo valor padrão. Os metadados iniciais são persistidos desde a criação da sessão; ao terminar cada fluxo, o script grava a avaliação pelo mesmo recorder e repositório. Gabaritos e resultados do baseline não são enviados ao modelo nem ao Ralph.

A avaliação é determinística: usa a última linha `RESPOSTA_FINAL: A`, uma letra isolada ou uma alternativa completa isolada. Respostas ambíguas, ausência de alternativa e falhas técnicas contam como erros, com diagnóstico separado. Falhas não impedem a execução do outro fluxo ou das próximas questões.

## Front-end

O botão **BenchMark** reutiliza a lista e os detalhes do histórico, incluindo busca, filtro de fluxo, barra lateral e modos Chat/Gráfico. As sessões são carregadas pelos endpoints normais `GET /v1/sessions` e `GET /v1/sessions/{id}`. A separação vem de `benchmark_details.is_banchmark`, e a página mostra nome da questão, gabarito, alternativa escolhida e acerto/erro.

O Histórico normal mostra sessões comuns; BenchMark mostra as sessões identificadas pelo script. Os resultados antigos salvos apenas no computador não são importados automaticamente: eles permanecem preservados nos arquivos locais, e novas execuções pelo container passam a aparecer no histórico compartilhado.

## Relatórios

Além das sessões no armazenamento normal, cada execução gera relatórios e checkpoints em `/app/data/benchmark-reports/<execucao>/`, dentro do volume persistente `backend_data`:

- `relatorio.md`: resultado de cada questão nos dois fluxos e totais de acertos, erros e acurácia.
- `resultados.json`: respostas, avaliações, tempos e IDs das sessões.
- `<questao>.json`: checkpoint atualizado após cada fluxo.
- `<questao>_ralph_eventos.jsonl`: eventos completos do Ralph.
- `execucao.json` e `prompt.md`: parâmetros e instruções usadas.

O terminal informa o caminho exato do relatório. Para copiar os relatórios para o computador:

```bash
docker compose cp backend:/app/data/benchmark-reports "./teste benchmark/relatorios-container"
```

`--output-dir` pode mudar o diretório dos relatórios, mas não muda o repositório das sessões. O código e o dataset são montados em `/opt/benchmark` somente para leitura. Não use essa pasta como saída no container.

Códigos de saída: `0` para respostas avaliáveis, mesmo erradas; `1` para falhas ou respostas inválidas; `2` para configuração/dataset inválido; `130` para interrupção. Uma interrupção preserva as sessões e checkpoints já gravados; os relatórios consolidados são gerados ao terminar todas as questões.

## Testes sem chamadas pagas

Na raiz do projeto:

```bash
apps/backend/.venv/bin/python -m pytest "teste benchmark/tests" -q
apps/backend/.venv/bin/flake8 --config apps/backend/setup.cfg "teste benchmark"
```

Os testes exercitam fila, concorrência, avaliação e relatórios. A integração dos dois fluxos usa transporte HTTP simulado, verifica o modelo em todas as fases e comprova a persistência dos metadados tanto em JSON quanto em MongoDB simulado.
