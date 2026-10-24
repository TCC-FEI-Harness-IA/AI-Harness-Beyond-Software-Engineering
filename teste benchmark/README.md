# Teste benchmark

Executa todas as questões de `teste benchmark/QUESTOES_BENCHMARK` pelos fluxos existentes do backend: inferência simples (`DefaultMessageStartup`) e RALPH LOOP adaptado (`RalphThinkingStartup`, incluindo A.3). Não é necessário iniciar FastAPI, WebSocket nem MongoDB.

Uma `asyncio.Queue` FIFO distribui as questões para **5 workers**, por padrão. Cada worker executa **simples → Ralph** para a mesma questão antes de retirar a próxima. Assim, há no máximo cinco questões em processamento simultâneo. A ordem de conclusão pode variar. Cada fluxo recebe uma instância nova do startup, com sessão, memórias e limites próprios.

O modelo é **`deepseek/deepseek-v4-flash-0731`**, via OpenRouter, tanto na chamada simples quanto em todas as fases e retentativas do Ralph. O script fixa modelo, provedor e allowlists apenas no próprio processo, sem editar o `.env` do projeto. Os limites operacionais `RALPH_*` e o timeout HTTP vêm das configurações existentes do backend. Ambos os fluxos usam os mesmos parâmetros de geração: por padrão, `max_tokens=4096` e `temperature=0.0`.

## Executar

Na raiz do projeto, com Python **3.11 ou superior** e as dependências de `apps/backend/requirements.txt` instaladas:

```bash
# Valida as 15 questões e mostra os dois fluxos; não faz chamadas nem exige credenciais.
python3 "teste benchmark/executar.py" --dry-run

# Usa o ambiente virtual existente do backend.
apps/backend/.venv/bin/python "teste benchmark/executar.py"
```

Configure `OPENROUTER_API_KEY` no ambiente ou em `apps/backend/.env`. Variáveis já exportadas têm precedência sobre o arquivo. Para usar outro arquivo:

```bash
apps/backend/.venv/bin/python "teste benchmark/executar.py" --env-file /caminho/credenciais.env
```

Outras opções:

```bash
apps/backend/.venv/bin/python "teste benchmark/executar.py" \
  --concurrency 5 \
  --max-tokens 4096 \
  --temperature 0 \
  --questions-dir "teste benchmark/QUESTOES_BENCHMARK" \
  --output-dir "teste benchmark/resultados"
```

Os caminhos padrão são resolvidos a partir da localização do script; caminhos fornecidos na CLI são relativos ao diretório de onde ele é chamado. A execução real faz chamadas cobradas pelo provedor.

## Avaliação e relatório

O enunciado original recebe as mesmas instruções de `prompt.md` nos dois fluxos. A última linha da resposta deve ser `RESPOSTA_FINAL: A`, substituindo `A` pela letra escolhida. O gabarito e a resposta da inferência simples **não são enviados ao Ralph**. A avaliação é local e determinística, sem chamada a outro modelo.

O avaliador usa somente o marcador final, uma letra isolada ou uma alternativa completa isolada. Letras citadas no raciocínio não são interpretadas como resposta. Respostas ambíguas, ausência de resposta final e falhas técnicas contam como **erros**, com diagnóstico separado. Uma falha no simples não impede o Ralph; uma falha em uma questão não impede as próximas. Não há retentativas adicionais do benchmark; o simples continua sendo uma única inferência e o Ralph mantém suas próprias retentativas.

Cada execução cria uma pasta exclusiva em `resultados/<data UTC>_<id>/`, com:

- `relatorio.md`: certo/errado e alternativa de cada fluxo por questão, mais totais de acertos, erros, acurácia e falhas.
- `resultados.json`: resultados completos, respostas brutas, alternativas esperadas e selecionadas, erros, tempos e IDs das sessões.
- `<questao>.json`: checkpoint atualizado após cada fluxo, inclusive antes de começar o Ralph.
- `<questao>_ralph_eventos.jsonl`: todos os eventos do Ralph; só o evento final `result` é usado como resposta.
- `sessions/`: sessões reais do backend com histórico, invocações e consumo de tokens.
- `execucao.json` e `prompt.md`: parâmetros iniciais, lista de questões e instruções usadas.

O terminal também mostra o andamento e os totais finais. Os relatórios mantêm a ordem dos nomes das questões, independentemente da ordem de conclusão. Em uma interrupção, os checkpoints e eventos já gravados permanecem disponíveis; os relatórios consolidados são gerados quando todas as questões terminam.

Códigos de saída: `0` se todos os fluxos devolverem respostas avaliáveis (mesmo que erradas), `1` se houver falhas técnicas ou respostas inválidas, `2` para configuração/dataset inválido e `130` para interrupção pelo teclado.

## Verificar sem consumir API

```bash
apps/backend/.venv/bin/python -m pytest "teste benchmark/tests" -q
apps/backend/.venv/bin/flake8 --config apps/backend/setup.cfg "teste benchmark"
```

Os testes verificam concorrência de cinco questões, ordem simples → Ralph, continuidade após falhas, avaliação sem falsos positivos, somas dos relatórios e integração com os dois fluxos reais usando transporte HTTP simulado. Nenhum teste acessa o provedor.
