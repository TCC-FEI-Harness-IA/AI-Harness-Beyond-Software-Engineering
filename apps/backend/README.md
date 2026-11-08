# Backend

## Boas práticas de desenvolvimento

Este guia reúne as convenções de `feature_ralph/README.md` (seções 3.1–3.3) e os padrões
encontrados em `src/` e `tests/`. Use os exemplos indicados como referência para novas implementações.

### Separação de responsabilidades e dependências

- **Mantenha as dependências voltadas para o domínio.** `domain/` contém entidades, enums,
  erros, serviços e interfaces, sem importar `application/` ou `infra/`. `application/`
  coordena os casos de uso usando os contratos do domínio e seus próprios DTOs.
  Integrações com FastAPI, provedores e armazenamento ficam em `infra/`.
- **Injete dependências pelos contratos.** Declare portas com `ABC` e `@abstractmethod` em
  `domain/interfaces/`, como `ISessionRepository` e `ILLMCompletions`. Receba essas portas
  pelo construtor, como faz `DefaultMessageUseCase`, permitindo substituí-las por duplos nos testes.
- **Monte os casos de uso nos startups.** `infra/startups/` concentra a composição dos grafos
  de dependências e a tradução entre DTOs de transporte e de aplicação. Quando a criação depende
  da configuração, use factories, como `LLMServiceFactory` e `SessionRepositoryFactory`.
- **Deixe as rotas responsáveis pelo transporte.** Valide o payload, delegue ao startup e
  traduza resultados e erros para HTTP ou WebSocket. Regras de negócio ficam nos casos de uso
  e no domínio.

Exemplos: [`DefaultMessageUseCase`](src/application/usecases/default_message_usecase.py),
[`DefaultMessageStartup`](src/infra/startups/default_message_startup.py) e
[`ISessionRepository`](src/domain/interfaces/session_repository_interface.py).

### Modelagem, organização e legibilidade

- **Use dataclasses para dados internos.** Entidades ficam em `domain/entities/`, agrupadas
  por assunto. Prefira `frozen=True` para objetos de valor, como `GenaiModel` e `TokensUsage`;
  agregados que evoluem durante a execução, como `Session`, permanecem mutáveis. DTOs de
  aplicação também são dataclasses e ficam em `application/dtos/`.
- **Separe os contratos de transporte.** Modelos Pydantic ficam em `infra/routes/.../dtos/`,
  com validação de tipos, limites e campos na fronteira da API. Não os importe nos casos de uso.
- **Declare uma classe por arquivo.** Use nomes em `snake_case`; interfaces seguem o padrão
  `*_interface.py` e enums ficam em `domain/enums/`, um por arquivo, com sufixo `_enum.py`.
  Reserve `domain/services/` para serviços com comportamento, como `TaskQueue`.
- **Explicite a API pública.** Use o prefixo `__` nos métodos auxiliares privados, seguindo
  exemplos como `DefaultMessageUseCase.__infer`.
- **Documente e tipe as assinaturas.** Use type hints modernos (`str | None`, `list[str]`) e
  docstrings em português no formato Google, com `Args:`, `Returns:` e `Raises:` quando aplicáveis.

### Configuração e integração com serviços externos

- **Centralize configurações em `Settings`.** Caminhos, credenciais, modelos, timeouts e limites
  configuráveis devem ser expostos como propriedades tipadas de `ISettings`; a leitura e a
  conversão das variáveis de ambiente ficam em `infra/config/settings.py`.
- **Mantenha prompts em arquivos Markdown.** Carregue-os pela porta `IPromptTemplateProvider`,
  implementada por `FilePromptTemplateProvider`, em vez de embuti-los nos casos de uso. Os prompts
  do Ralph Loop e todo texto que chega ao modelo dentro do fluxo (correções, motivos de recusa,
  histórico das tentativas) são escritos em inglês; a resposta final segue o idioma da pergunta.
- **Isole integrações em adapters e repositories.** `SessionDocumentMapper` converte entidades
  em documentos; os repositórios JSON e MongoDB cuidam do armazenamento. O caso de uso depende
  de `ISessionRepository`, sem conhecer o formato persistido.
- **Reaproveite o fluxo comum dos provedores.** `BaseChatCompletionsService` aplica Template
  Method para compartilhar validação, chamada HTTP e leitura da resposta. As subclasses
  especializam URL, autenticação e parâmetros específicos.
- **Preserve o event loop.** Use I/O assíncrono, como `httpx.AsyncClient` nas chamadas HTTP;
  operações bloqueantes de arquivo são delegadas a `asyncio.to_thread` no repositório JSON.
- **Torne efeitos externos substituíveis.** Use `IClock` e `IIdGenerator` para tempo e IDs,
  registre mensagens e métricas via `ISessionRecorder` e injete o logger pelo construtor.
  Isso permite verificar resultados e efeitos sem depender de serviços reais.

### Testes e critérios de qualidade

O plano de desenvolvimento estabelece **TDD**: escreva um teste de comportamento, confirme a
falha e implemente o necessário para fazê-lo passar. A estrutura de `tests/` acompanha as
camadas de `src/`; duplos reutilizáveis ficam em `tests/doubles/`, como `FakeClock`,
`FakeLLMCompletions` e `InMemorySessionRepository`.

- Verifique entradas, saídas, erros e efeitos observáveis, como o estado persistido da sessão.
- Substitua chamadas de rede por fakes ou transportes HTTP de teste. Use `tmp_path` para
  arquivos temporários e não dependa de credenciais reais.
- Mantenha o `flake8` sem erros: `setup.cfg` define linhas de até 120 caracteres e
  complexidade máxima de 12.
- Execute o `pytest` com cobertura mínima de **100%** em `src/`. A configuração de cobertura
  habilita a medição de branches e exclui interfaces e arquivos `__init__.py` do relatório.

Na pasta `apps/backend`, com as dependências de desenvolvimento instaladas:

```bash
flake8 src tests
pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

A metodologia e a explicação do Ralph Loop estão na [documentação da raiz](../../README.md)
e em [`RALPH_LOOP_ADAPTADO.md`](../../RALPH_LOOP_ADAPTADO.md).
As seções seguintes documentam a execução e os contratos técnicos da API.

---

## Sumário

- [Boas práticas de desenvolvimento](#boas-práticas-de-desenvolvimento)
- [Provedores de LLM](#provedores-de-llm)
- [Como rodar](#como-rodar)
- [Endpoints HTTP](#endpoints-http)
  - [`POST /v1/message/default`](#post-v1messagedefault)
  - [`GET /v1/sessions`](#get-v1sessions)
  - [`GET /v1/sessions/{session_id}`](#get-v1sessionssession_id)
  - [`GET /v1/health`](#get-v1health)
  - [`GET /v1/limits`](#get-v1limits)
  - [`GET /v1/models`](#get-v1models)
  - [`POST /v1/models`](#post-v1models)
  - [`PUT /v1/models/{model_name}`](#put-v1modelsmodel_name)
  - [`DELETE /v1/models/{model_name}`](#delete-v1modelsmodel_name)
  - [Catálogo de modelos e allowlist](#catálogo-de-modelos-e-allowlist)
- [Endpoint WebSocket](#endpoint-websocket)
  - [`WS /v1/message/reasoning`](#ws-v1messagereasoning)
- [Benchmark](#benchmark)
  - [`WS /v1/benchmark/run`](#ws-v1benchmarkrun)
  - [`GET /v1/benchmark/sessions`](#get-v1benchmarksessions)
  - [`GET /v1/benchmark/sessions/{benchmark_session_id}`](#get-v1benchmarksessionsbenchmark_session_id)
  - [`GET /v1/benchmark/sessions/{benchmark_session_id}/ralph-loop-errors/export`](#get-v1benchmarksessionsbenchmark_session_idralph-loop-errorsexport)
  - [`WS /v1/benchmark/sessions/{benchmark_session_id}/questions/{question_id}/rerun`](#ws-v1benchmarksessionsbenchmark_session_idquestionsquestion_idrerun)
  - [`GET /v1/benchmark/questions`](#get-v1benchmarkquestions)
- [Garantias do harness e encerramento sem conclusão](#garantias-do-harness-e-encerramento-sem-conclusão)
  - [Planejamento e cobertura do pedido — etapa 03](#planejamento-e-cobertura-do-pedido--etapa-03)
  - [Integração das cinco frentes — etapa 07](#integração-das-cinco-frentes--etapa-07)
  - [Planejamento aprovado antes da execução — nova fase de validação 01](#planejamento-aprovado-antes-da-execução--nova-fase-de-validação-01)
- [Contratos (DTOs)](#contratos-dtos)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Arquitetura em uma imagem](#arquitetura-em-uma-imagem)

---

## Provedores de LLM

A aplicação fala com três provedores — **OpenRouter**, **OpenAI** e **Azure AI Foundry** — e o
`provider` do corpo da requisição decide qual atende cada chamada; `LLM_PROVIDER` é apenas o
padrão. Os três expõem a mesma API de chat completions, então o esqueleto
"validar → montar payload → POST → extrair texto, tokens e motivo de término" vive uma única vez
em `BaseChatCompletionsService`. Cada implementação varia só o que é próprio dela:

| Provedor | URL | Autenticação | Esforço de raciocínio |
|---|---|---|---|
| OpenRouter | `OPENROUTER_API_URL`, fixa | `Authorization: Bearer` | bloco `reasoning` próprio (permite desligar com `enabled: false`) |
| OpenAI | `OPENAI_API_URL`, fixa | `Authorization: Bearer` | `reasoning_effort` |
| Azure AI Foundry | `{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=...` | `api-key` | `reasoning_effort` |

`LLMServiceFactory` instancia um serviço por provedor e o `LLMCompletionsAdapter` escolhe, a
cada chamada, aquele que atende o `provider` pedido. Um provedor fora do enum é recusado com
`422` na fronteira; um fora de `GENAI_AVAILABLE_PROVIDERS` é recusado pelo catálogo.

---

## Como rodar

```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env   # preencha LLM_PROVIDER/LLM_MODEL, a credencial do provedor e GENAI_AVAILABLE_*

uvicorn src.main:app --reload --port 8000
```

Verificação (lint + testes + cobertura):

```bash
flake8 src tests
pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

---

## Endpoints HTTP

Base path: `/v1`.

### `POST /v1/message/default`

Executa uma chamada direta ao modelo.

**Requisição** — [`DefaultInputDTO`](#defaultinputdto):

```json
{
  "message": { "user_input": "Qual dos seguintes números é primo, par e maior que 2?" },
  "llm_model_config": {
    "provider": "open_router",
    "provider_config": { "model_name": "openai/gpt-4o-mini" },
    "max_tokens": 512,
    "temperature": 0.3
  }
}
```

**Resposta `200`** — [`DefaultOutputDTO`](#defaultoutputdto):

```json
{
  "message": "Qual dos seguintes números é primo, par e maior que 2?",
  "response": "A resposta correta é a alternativa D.",
  "session_id": "sess_ab12cd34ef56",
  "tokens_input": 42,
  "tokens_output": 118,
  "inference_time_ms": 812
}
```

**Erros**
| Status | Quando |
|---|---|
| `422` | Corpo fora do contrato (`message` ausente, `temperature` fora de `[0, 1]` ou não finita, `max_tokens <= 0` ou acima de `LLM_MAX_TOKENS`, `provider` desconhecido, etc.). |
| `500` | Falha ao chamar o provedor ou qualquer outra exceção não tratada. `detail` traz a mensagem da exceção. |

```bash
curl -X POST http://localhost:8000/v1/message/default \
  -H "Content-Type: application/json" \
  -d '{
    "message": { "user_input": "Qual dos seguintes números é primo, par e maior que 2?" },
    "llm_model_config": {
      "provider": "open_router",
      "provider_config": { "model_name": "openai/gpt-4o-mini" },
      "max_tokens": 512,
      "temperature": 0.3
    }
  }'
```

### `GET /v1/sessions`

Lista os identificadores de todas as sessões persistidas.

**Resposta `200`**:

```json
{ "session_ids": ["sess_ab12cd34ef56", "sess_9f8e7d6c5b4a"] }
```

```bash
curl http://localhost:8000/v1/sessions
```

### `GET /v1/sessions/{session_id}`

Consulta o documento completo de uma sessão: pergunta, configuração efetiva da inferência
(modelo, provedor, `max_tokens` e `temperature` exatamente como pedidos), todo o histórico de
mensagens (uma por etapa do fluxo, com fase, tokens e tempo de inferência), **uma invocação por
chamada ao modelo**, totais agregados, o motivo estruturado de uma eventual interrupção e a
resposta final.

**Resposta `200`**:

```json
{
  "id": "sess_ab12cd34ef56",
  "user_question": "Qual dos seguintes números é primo, par e maior que 2?",
  "flow": "A1",
  "model_name": "openai/gpt-4o-mini",
  "max_tokens": 1200,
  "temperature": 0.3,
  "status": "completed",
  "created_at": "2026-09-11T23:18:06.314083+00:00",
  "updated_at": "2026-09-11T23:18:07.668445+00:00",
  "final_answer": "D) Nenhuma das anteriores",
  "provider": "open_router",
  "failure": null,
  "legacy_totals": false,
  "totals": {
    "total_messages": 15,
    "total_llm_calls": 7,
    "tokens_input": 4210,
    "tokens_output": 1830,
    "total_tokens": 6040,
    "inference_time_ms": 5230,
    "wall_time_ms": 6100
  },
  "messages": [
    {
      "id": "msg_01",
      "order": 0,
      "timestamp": "2026-09-11T23:18:06.320000+00:00",
      "phase": "A1",
      "source": "user",
      "content": "Qual dos seguintes números é primo, par e maior que 2?",
      "task_id": null,
      "context_id": null,
      "tokens_input": 0,
      "tokens_output": 0,
      "total_tokens": 0,
      "inference_time_ms": 0,
      "model_name": null,
      "prompt_input": []
    },
    {
      "id": "msg_02",
      "order": 1,
      "timestamp": "2026-09-11T23:18:07.150000+00:00",
      "phase": "A1",
      "source": "llm_agent",
      "content": "{\"general_acceptance_criteria\": [...]}",
      "task_id": null,
      "context_id": "b5a9c2e",
      "tokens_input": 310,
      "tokens_output": 128,
      "total_tokens": 438,
      "inference_time_ms": 812,
      "model_name": "openai/gpt-4o-mini",
      "prompt_input": [
        {
          "source": "user",
          "text": "Template A.1 já preenchido com a pergunta...",
          "creation_timestamp": "2026-09-11T23:18:06.325000+00:00"
        }
      ]
    }
  ],
  "invocations": [
    {
      "id": "3c1d5a7e9b2f",
      "phase": "A1",
      "task_id": null,
      "context_id": "b5a9c2e",
      "model_name": "openai/gpt-4o-mini",
      "provider": "open_router",
      "started_at": "2026-09-11T23:18:06.330000+00:00",
      "outcome": "success",
      "duration_ms": 812,
      "tokens_input": 310,
      "tokens_output": 128,
      "finish_reason": "stop",
      "provider_response_id": "gen-1",
      "temperature": 0.3
    }
  ],
  "degradations": [],
  "result_revisions": [],
  "flow_version": 2
}
```

**Versão do fluxo e subtipo das mensagens.** `flow_version` diz como ler as fases do histórico: `2` nas
sessões Ralph novas (A3 = validação da decomposição, A4 = aprendizados do enunciado); sessões Ralph
gravadas antes do campo são devolvidas com `1` (A3 = aprendizados do enunciado), sem que o arquivo
persistido seja reescrito; a inferência direta tem `null`. Cada mensagem traz `subtype`, o subtipo do
evento emitido com ela (`plan_candidate`, `plan_rejected`, `plan_approved`, `tasks`, `reset`, ...), ou
`null` em registros sem evento (a pergunta, a auditoria de uma saída recusada) e em sessões antigas.

**Revisões de resultados.** `result_revisions` lista, em ordem, as revisões aprovadas em B.2 e
aplicadas em B.3: `revising_task_id`, `reason` (motivo planejado em C.2), `verdicts`
(`task_id`, `verdict` `confirmed`/`superseded`, `justification`), `superseded_task_ids` e
`confirmed_task_ids` (derivados dos vereditos), `approval_justification` (veredito de B.2 para o
critério `<id>-REV`), `suspended_task_ids`, `reinstated_task_ids`, `withdrawn_learnings`,
`restored_learnings`, `current_task_ids` e `occurred_at`. As conclusões substituídas continuam nas
mensagens; o registro diz que deixaram de ser vigentes, por qual tarefa e por qual motivo. Uma
confirmação aprovada também é registrada (`confirmed_task_ids`) e, desde a etapa 07, aparece no
**Revision record** de C.1 e C.2 enquanto a revisora e o resultado confirmado forem vigentes.

`flow` identifica o tipo da sessão: `A1` para `/v1/message/reasoning` e `DIRECT` para
`/v1/message/default`.

**Temperatura efetiva.** O `temperature` da sessão é o pedido pelo usuário. O `temperature` de cada
invocação é o que foi de fato enviado naquela chamada: no harness, toda chamada de retentativa sai com
temperatura `1` (ver [Garantias do harness](#garantias-do-harness-e-encerramento-sem-conclusão)).
Invocações gravadas antes deste campo voltam com `temperature: null`.

**Prompt de entrada.** `content` é a saída; `prompt_input` é a conversa exatamente como foi enviada
ao modelo na chamada que produziu essa saída, em ordem (`source` `user` para prompts e correções,
`llm_agent` para respostas anteriores da mesma janela). Toda execução de fase começa numa janela nova,
então a primeira chamada de cada fase leva só o prompt dela. Quando a fase precisou de correção de JSON,
é a conversa da última chamada, já com todas as saídas recusadas e mensagens de correção **integrais**,
em ordem, inclusive quando ultrapassam 1.000 caracteres (o template não é repetido). A auditoria de
uma saída inválida (`source` `system`) guarda a conversa da chamada que a
produziu e o tipo de defeito (erro de sintaxe, violação de contrato ou interrupção por comprimento). A pergunta do usuário e as etapas
programáticas têm `prompt_input` vazio, assim como sessões gravadas antes deste campo existir.

**Totais e invocações.** `total_llm_calls`, `tokens_*` e `inference_time_ms` vêm exclusivamente
das `invocations`: cada chamada enviada ao modelo é registrada depois da autorização e antes do
envio, e concluída em qualquer desfecho (`success`, `empty_completion` ou `provider_error`). Uma
tentativa de correção de JSON, uma completion vazia que foi repetida e uma fase que acabou falhando
contam como chamadas, e o consumo que o provedor informou não se perde. O consumo mostrado em cada
mensagem é uma agregação da fase, só para exibição, e não é somado de novo nos totais. Consumo que o
provedor não informou fica `null` na invocação (desconhecido, e não zero), mas a chamada é contada;
isso vale por contador: se o provedor informa só `prompt_tokens`, a entrada é registrada e a saída
fica `null`.

**Recusa local não é chamada.** Antes de contar e registrar uma chamada, o harness a valida
localmente (`ILLMCompletions.validate_conversation`: conversa, modelo, `max_tokens`, temperatura,
provedor e credenciais do provedor). O que é recusado aí nunca foi enviado: não consome orçamento, não
gera invocação e não entra em `total_llm_calls`. Por exemplo, com `OPENROUTER_API_KEY` vazia a sessão
termina `failed` (`technical_error`) com zero invocações. Uma falha depois do envio (HTTP, rede)
continua sendo uma chamada, com desfecho `provider_error`.

**Saídas inválidas na auditoria.** Cada saída recusada pelo parser (JSON inválido, relatório
incompleto ou contraditório, lote acima do teto) é registrada na sessão como uma etapa programática
`Saída inválida descartada na fase ...`, com o motivo e a saída bruta, no momento da recusa. O registro
independe de a fase terminar bem: quando as correções se esgotam e a execução é interrompida, as
saídas inválidas continuam no documento.
O texto completo auditado também permanece na janela enviada à correção da mesma execução;
nenhum resumo, corte ou ponteiro para essa auditoria o substitui. `PhaseOutcome.raw_output` e
`parsed` vêm somente da resposta aceita, sem concatenação ou união com partes das recusas.

**Encerramento e persistência.** Uma sessão só vale como encerrada depois de gravada. Se a gravação
do encerramento falha, a sessão em memória volta a `running` e a falha original é propagada, em vez
de um erro de estado; o tratamento da falha pode então encerrá-la como `failed`.
Isso vale para os dois fluxos e para toda gravação posterior à criação da sessão, inclusive a da pergunta
do usuário e a da resposta do baseline: uma falha de persistência nunca deixa a sessão `running` se o
repositório voltar a responder. Se ele segue indisponível, a falha original é a que sobe ao chamador no
baseline, e o motivo de não ter sido possível encerrar fica no log.

**Falha estruturada.** Uma sessão que terminou sem conclusão tem `status: "failed"`,
`final_answer: null` e `failure` preenchido:

```json
{
  "reason": "resource_limit",
  "phase": "B2",
  "description": "Execução interrompida pelo limite 'task_attempts' ... Consumo conhecido: 1840 tokens em 9 chamadas ao modelo. ...",
  "occurred_at": "2026-09-11T23:18:09.100000+00:00",
  "limit": "task_attempts",
  "task_id": "T2",
  "pending_criteria_ids": []
}
```

`reason` é `resource_limit` (um limite operacional impediu de seguir sem violar o método; `limit` o
identifica) ou `technical_error` (provedor, parsing ou persistência; `limit` é `null`).
`phase` é sempre a fase que estava em execução quando a falha ocorreu (por exemplo, B2 ou B4), e não a
origem da janela de contexto usada.
`pending_criteria_ids` lista os critérios gerais que a última verificação global deu como pendentes.

**Sessões antigas.** Documentos gravados antes do registro por invocação continuam legíveis: não têm
`invocations`, trazem `legacy_totals: true` (os totais são os históricos, sem chamadas individuais
correspondentes, e nenhuma chamada passada é inventada) e `provider`/`failure` nulos. Sessões
`degraded` e a lista `degradations` também continuam legíveis, sem reclassificação; o fluxo atual não
produz mais nenhuma das duas.
Documentos sem `result_revisions` são lidos com a lista vazia: nenhuma revisão é presumida.

**Erros**
| Status | Quando |
|---|---|
| `404` | `session_id` não existe. |
| `400` | Documento persistido inválido (chave obrigatória ausente, enum ou data malformados). |
| `500` | Qualquer outra exceção não tratada. |

```bash
curl http://localhost:8000/v1/sessions/sess_ab12cd34ef56
```

### `GET /v1/health`

Verificação simples de disponibilidade.

**Resposta `200`**: `{ "status": "ok" }`

### `GET /v1/limits`

Limites do backend que o cliente precisa respeitar ao montar uma requisição. O front usa
`max_tokens_limit` para que o limite de tokens por sessão pedido nunca passe do limite do backend.

**Resposta `200`**: `{ "max_tokens_limit": 120000 }` (o valor de `LLM_MAX_TOKENS`)

### `GET /v1/models`

Lista o catálogo de modelos guardado no MongoDB (coleção `MONGODB_MODELS_COLLECTION`, padrão `models`). O
front usa para montar a lista de escolha do modelo, com preço, contexto máximo e vazão, ordenável pelas
colunas.

**Resposta `200`**:

```json
{
  "models": [
    {
      "model_name": "openai/gpt-5-nano",
      "display_name": "OpenAI: GPT-5 Nano",
      "input_price_per_million_tokens": 0.05,
      "output_price_per_million_tokens": 0.4,
      "context_length": 400000,
      "throughput_tokens_per_second": 114
    }
  ]
}
```

- Ordem alfabética de `model_name`. Preços em USD por 1 milhão de tokens; contexto em tokens; vazão em
  tokens por segundo.
- Todo campo além de `model_name` pode ser `null` (dado desconhecido).
- Cada documento tem `_id` igual a `model_name`, então o banco não aceita dois cadastros do mesmo modelo.

### `POST /v1/models`

Cadastra um modelo. Corpo: o mesmo objeto de um item de `GET /v1/models` (só `model_name` é obrigatório).

- **`201`**: o modelo cadastrado.
- **`409`**: já existe um modelo com o mesmo `model_name`.
- **`422`**: `model_name` vazio, preço negativo, ou contexto/vazão menor ou igual a zero.

### `PUT /v1/models/{model_name}`

Substitui as informações de um modelo cadastrado. O identificador vai no caminho, com a barra
(`/v1/models/meta-llama/llama-3.1-8b-instruct`); o corpo traz os demais campos. **`200`** com o modelo,
**`404`** quando ele não está cadastrado, **`422`** para valores fora da faixa.

### `DELETE /v1/models/{model_name}`

Remove um modelo do catálogo. **`204`** sem corpo, ou **`404`** quando ele não está cadastrado.

### Catálogo de modelos e allowlist

Um modelo cadastrado no catálogo fica liberado para execução, além dos que estão em
`GENAI_AVAILABLE_MODELS`. Cada execução consulta o cadastro do modelo pedido, com espera máxima de 2 s:
com o MongoDB fora do ar, os modelos da allowlist continuam funcionando.

O `context_length` cadastrado também limita o `max_tokens` de cada chamada. O limite de tokens da
sessão pode passar do contexto do modelo (ex.: 500 mil numa sessão com um modelo de 131 mil), e o
provedor recusa a chamada quando entrada + saída não cabem. Por isso a saída pedida é reduzida ao
contexto menos uma estimativa conservadora da entrada (3 caracteres por token). Sem `context_length`
no catálogo, o valor segue como foi pedido.

Para preencher o catálogo com os modelos iniciais (valores da OpenRouter, consultados em 2026-11-07):

```bash
python scripts/seed_models.py              # cadastra só os que ainda não existem
python scripts/seed_models.py --overwrite  # substitui os já cadastrados
```

Os preços na OpenRouter variam por provedor. O seed usa, para cada modelo, os números de um único
provedor: o primeiro da lista da OpenRouter, que é o de menor preço de entrada. A exceção é a camada
`flex` da OpenAI, que fica de fora por ser a camada lenta. A vazão é a mediana (p50) dos últimos 30
minutos desse mesmo provedor. Depois do seed, os valores podem ser ajustados na tela "Modelos" do front.

---

## Endpoint WebSocket

### `WS /v1/message/reasoning`

Emite eventos de processamento e a resposta final da sessão. Ao final, fecha a conexão.

**Protocolo**

1. Cliente abre a conexão e envia **um único frame de texto** com o payload (mesmo formato do
   `POST /v1/message/default`, sem `reasoning_config`):

   ```json
   {
     "message": { "user_input": "Qual dos seguintes números é primo, par e maior que 2?" },
     "llm_model_config": {
       "provider": "open_router",
       "provider_config": { "model_name": "openai/gpt-4o-mini" },
       "max_tokens": 1200,
       "temperature": 0.3
     }
   }
   ```

2. Servidor responde com um frame JSON por evento de pensamento (contrato completo abaixo).
3. Quando o fluxo conclui, o último frame tem `"type": "result"` e traz a resposta final em
   `content`. Em seguida o servidor fecha a conexão com `1000`.
4. Quando o fluxo é interrompido ou falha, o último frame tem `"type": "error"` (um único evento
   `error` do domínio, com a causa) e o servidor fecha com `1011`. Nunca há `result` nesse caso: o
   harness só responde depois de uma aprovação global sobre resultados aprovados individualmente.

**Códigos de fechamento**

| Código | Motivo |
|---|---|
| `1000` | Fluxo concluído normalmente (último frame `result`). |
| `1003` | Payload inválido (JSON malformado ou fora do contrato de `ReasoningInputDTO`) — precedido de um frame `{"type": "error", "content": "<detalhe>"}`. |
| `1009` | Frame de abertura maior que `RALPH_WEBSOCKET_MAX_MESSAGE_BYTES`. |
| `1011` | Fluxo interrompido (limite de recursos) ou falho (erro técnico) — precedido de **um** frame de erro: o evento `error` do domínio quando o caso de uso o emitiu (o normal), ou o frame genérico `{"type": "error", "content": "<detalhe>"}` quando a falha ocorreu fora dele. Nunca os dois. |

Se o cliente desconectar no meio da execução, o servidor não levanta exceção: encerra o gerador,
finaliza a sessão como `failed` (se ela ainda estiver em execução — uma sessão já encerrada não é
encerrada de novo) e apenas registra um log — não há frame nem fechamento adicional (não há mais
ninguém do outro lado para recebê-los).

**Exemplo com `websocat`**

```bash
websocat ws://localhost:8000/v1/message/reasoning
# cole o frame de abertura e pressione Enter
```

**Exemplo em JavaScript** (é assim que `apps/frontend/src/App.tsx` consome o endpoint):

```ts
const ws = new WebSocket(`ws://${location.host}/v1/message/reasoning`)
ws.onopen  = () => ws.send(JSON.stringify(payload))
ws.onmessage = (e) => handleEvent(JSON.parse(e.data))
ws.onclose = () => setDone(true)
```

---

## Contratos (DTOs)

Todos os payloads são JSON. Campos sem valor default são obrigatórios.

### `MessageInputDTO`

| Campo | Tipo | Regra |
|---|---|---|
| `user_input` | `string` | `min_length=1` |

### `ProviderConfigDTO`

| Campo | Tipo | Regra |
|---|---|---|
| `model_name` | `string` | obrigatório |
| `endpoint` | `string \| null` | opcional, default `null` |

### `ModelConfigDTO`

| Campo | Tipo | Regra |
|---|---|---|
| `provider` | `"open_router" \| "azure_ai_foundry" \| "openai"` | obrigatório; decide qual adapter atende a chamada |
| `provider_config` | [`ProviderConfigDTO`](#providerconfigdto) | obrigatório |
| `max_tokens` | `int` | `> 0` e `<= LLM_MAX_TOKENS`. É o limite de tokens (entrada + saída) **da sessão inteira**, e não de cada chamada; cada chamada ao modelo recebe como teto de saída o saldo que resta dele (ver [Limite de tokens por sessão](#limite-de-tokens-por-sessão)) |
| `temperature` | `float` | `[0, 1]`, finita; **só** ausente ou `null` vira `0.7`; `0` é preservado e o valor nunca é arredondado — chega ao provedor exatamente como pedido e é registrado na sessão |

### `DefaultInputDTO`

Corpo de `POST /v1/message/default`.

| Campo | Tipo |
|---|---|
| `message` | [`MessageInputDTO`](#messageinputdto) |
| `llm_model_config` | [`ModelConfigDTO`](#modelconfigdto) |

### `DefaultOutputDTO`

Resposta `200` de `POST /v1/message/default`.

| Campo | Tipo | Descrição |
|---|---|---|
| `message` | `string` | Pergunta original. |
| `response` | `string` | Resposta do modelo. |
| `session_id` | `string` | Sessão gravada (`flow = DIRECT`). |
| `tokens_input` | `int` | Tokens de entrada da chamada. |
| `tokens_output` | `int` | Tokens de saída da chamada. |
| `inference_time_ms` | `int` | Tempo da chamada ao modelo. |

### `ReasoningInputDTO`

Frame de abertura de `WS /v1/message/reasoning` — **idêntico ao `DefaultInputDTO`**, apenas com
outro nome de classe. `reasoning_config` não faz parte do contrato: se enviado, é ignorado.

| Campo | Tipo |
|---|---|
| `message` | [`MessageInputDTO`](#messageinputdto) |
| `llm_model_config` | [`ModelConfigDTO`](#modelconfigdto) |

### `ContextWindowDTO`

| Campo | Tipo | Descrição |
|---|---|---|
| `context_id` | `string` | Identidade da janela de contexto no momento do evento. |
| `context_size` | `int` | Consumo acumulado de tokens das chamadas feitas sobre a janela atual. Cada chamada reenvia o histórico, então a soma o conta de novo: é consumo, **não** o comprimento corrente da janela, e não mede mitigação de *context rot*. |

### `ReasoningEventDTO`

Cada frame emitido por `WS /v1/message/reasoning`. **Exatamente estes 10 campos, sem extras.**

| Campo | Tipo | Descrição |
|---|---|---|
| `type` | `string` | `thinking` \| `result` \| `degraded` \| `error`. `degraded` é legado: o fluxo atual não o emite. |
| `subtype` | `string` | `setup`, `plan_candidate`, `plan_rejected`, `plan_approved`, `tasks`, `execute`, `reasoning`, `verify_pass`, `verify_fail`, `store`, `learn`, `reset`, `compile`, `replan`. `plan_candidate` (A.2) é um plano **ainda não executável**; `plan_rejected`/`plan_approved` (A.3) são os relatórios da validação da decomposição; `tasks` é emitido **uma única vez**, em A.3, quando o plano aprovado é confirmado na fila. `learn` é emitido em A.4 (aprendizados do enunciado, `task = setup`) e em B.4 (aprendizados de cada tarefa). |
| `phase` | `string` | `A1`, `A2`, `A3`, `A4`, `B1`, `B2`, `B3`, `B4`, `C1`, `C2`, `C3`. No fluxo versão 2, `A3` é a validação da decomposição e `A4` a extração do enunciado. |
| `task` | `string` | Id da tarefa (`T1`, `T2`, ...), ou `setup` / `synthesis` para etapas globais. |
| `session_id` | `string` | Sessão em execução. |
| `content` | `string` | Markdown pronto para renderização. |
| `total_tokens` | `int` | Acumulado da sessão; **nunca decresce**. |
| `context_window` | [`ContextWindowDTO`](#contextwindowdto) | Janela de contexto no momento do evento. |
| `inference_time_ms` | `int` | Tempo da chamada ao modelo; `0` em eventos sem inferência. |
| `flow_version` | `int` | Versão do fluxo Ralph da sessão (`2` nas sessões novas). Acompanha todo frame para que o cliente saiba o que `A3` significa antes de interpretar o evento. |

Frames de erro fora do fluxo normal (payload inválido, ou o frame genérico que precede o
fechamento `1011`) usam um formato reduzido, **fora** deste contrato de 10 campos:

```json
{ "type": "error", "content": "<detalhe do erro>" }
```

---

## Garantias do harness e encerramento sem conclusão

O harness reproduz o fluxo de [`RALPH_LOOP_ADAPTADO.md`](../../RALPH_LOOP_ADAPTADO.md) e preserva as
condições de aprovação do método. Uma sessão `completed` significa, necessariamente: todo resultado
armazenado foi aprovado por um relatório de B.2 completo e consistente; C.1 aprovou o conjunto desses
resultados com um relatório completo e consistente; C.3 produziu uma síntese válida; e a sessão foi
persistida antes do evento `result`.

| Situação | Comportamento |
|---|---|
| A.2 gera um plano candidato | O candidato não entra na fila nem consome espaços de tarefa: A.3 o julga numa janela nova, com o pedido original, os critérios gerais de A.1 e só esse candidato, pela rubrica fixa do template. |
| A.3 reprova e ainda há candidatos (`RALPH_MAX_PLANNING_ATTEMPTS`) | A.2 roda numa janela nova, com temperatura `1`, recebendo só o último candidato e o relatório dele (`<previous_candidate>` e `<validation_report>`); a A.3 seguinte volta à temperatura da sessão e não vê candidatos nem relatórios anteriores. |
| A.3 reprova o último candidato permitido | A execução é interrompida (`failure.limit = planning_attempts`, fase `A3`), sem confirmar plano, sem A.4, tarefas ou síntese. |
| A.3 aprova | O plano aprovado é confirmado na fila uma única vez (evento `tasks` em A.3) e só então A.4 anota os pontos de atenção do enunciado (valores com unidades, alternativas, fórmulas, condições) numa janela própria; as anotações entram na memória de aprendizados antes de qualquer tarefa. Lista vazia é válida. |
| Qualquer prompt de B.1, B.2, B.4, C.1, C.2 ou C.3 é montado | O template tem a área **Aprendizados Pontuais** (`## Key Learnings`), preenchida com todos os aprendizados acumulados até aquele momento (anotações de A.4 seguidas dos aprendizados de B.4), ou com o aviso de que ainda não há nenhum. Os aprendizados nunca entram nos resultados armazenados. |
| Qualquer fase é executada | A execução abre uma janela nova, da própria fase: tarefa diferente e mudança de fase (inclusive B.1 → B.2, B.2 → B.1, B.1 → B.4 e C.1 → C.2/C.3) nunca herdam a conversa anterior. Só as correções de saída da própria execução reaproveitam a janela. Só os aprendizados atravessam fases como memória; as demais entradas chegam explicitamente pelo template. |
| B.2 aprova | B.3 armazena só essa resposta; B.4 roda numa janela nova e recebe o histórico completo da tarefa (tarefa, tentativas, saídas descartadas e vereditos) como material delimitado `<task_history>`. |
| B.2 reprova e há tentativas | B.1 repete numa janela nova, com temperatura `1`; as tentativas reprovadas e os vereditos chegam pela variável `previous_attempts` do Template B.1, delimitados por `<previous_attempts>`, seguidos da instrução de tratar o problema concreto apontado e manter as conclusões não refutadas. A verificação dessa tentativa e as fases seguintes voltam à temperatura do usuário. |
| B.2 reprova e as tentativas acabam | Nada é armazenado, B.4 não roda, a execução é interrompida. |
| B.2/C.1 devolve um relatório vazio, incompleto, duplicado, com ID desconhecido ou contraditório | O verificador é chamado de novo, na mesma janela e com temperatura `1`, para conferir e corrigir o próprio relatório (chamada contada); não consome tentativa de B.1. O veredito nunca é ajustado automaticamente. Sem correção, a fase falha. |
| Qualquer saída estruturada é recusada e há retentativa | A resposta bruta completa e os feedbacks permanecem na janela da execução, sem corte aos 1.000 caracteres nem repetição do template. A correção de contrato pede saída completa e preservação do conteúdo não afetado e das etapas necessárias. |
| A.2/C.2 precisa corrigir o planejamento | A instrução exige manter a cobertura da determinação solicitada, inclusive os passos finais. Um título ausente não autoriza remover outras tarefas necessárias. Excesso de tarefas e IDs duplicados podem exigir alterar o lote; quantidade, IDs e conteúdo não são congelados. A cobertura semântica continua dependendo do modelo. |
| Qualquer fase devolve um JSON ilegível ou interrompido pelo limite de comprimento | Erro de sintaxe: o modelo é chamado de novo para devolver o mesmo conteúdo em JSON válido, sem nova resolução. Interrupção por comprimento: pede-se uma nova saída completa e concisa, nunca a continuação da anterior. Os únicos reparos locais são a extração de cercas e o fechamento estrutural inequívoco. |
| C.1 reprova e há recursos | C.2 cria tarefas para os critérios pendentes, que entram no topo da fila. O template recebe o **Prompt Original**, o relatório de C.1 com os motivos das lacunas em **Global verification feedback**, em **Resultados já armazenados** só o enunciado e a conclusão (campo `conclusion` de B.1) de cada resultado **vigente**, sem a resolução completa, e o **Revision record**; C.1 e C.3 continuam recebendo as resoluções completas dos resultados vigentes. |
| C.2 planeja uma revisora e B.2 a aprova | B.3 aplica os vereditos `confirmed`/`superseded`: substituídos e dependentes declarados deixam de ser vigentes (sem serem apagados), seus aprendizados exclusivos saem da memória vigente e a revisão fica em `result_revisions`. Uma confirmação mantém o resultado vigente e passa a constar no **Revision record** de C.1/C.2 com o motivo aprovado. Depois do loop, nova C.1; a aprovação global vale só para os vigentes que ela avaliou. |
| C.1 reprova e não há recursos para C.2 | A execução é interrompida; os critérios pendentes ficam em `failure`. Nunca há C.3. |
| C.1 aprova e C.3 falha ou não pode rodar | A execução termina sem resposta final. Isso inclui a guarda da etapa 06: se os resultados vigentes não forem mais os que a aprovação global avaliou, C.3 não é chamada e a sessão falha como erro técnico. |
| Qualquer limite é atingido em qualquer fase ou retentativa | A execução é interrompida (`failure.reason = resource_limit`), sem nenhuma chamada depois do bloqueio. |

**Verificações determinísticas.** Os relatórios de B.2 e C.1 são validados contra os critérios
esperados da chamada, entregues ao parser como dados (`ValidationContext`), e não lidos do prompt:
uma avaliação para cada critério, sem omissões, repetições ou IDs extras; `unmet_criteria_ids`
exatamente igual aos critérios com `met=false`; `approved` somente com todos `met=true`. Isso garante
a consistência estrutural do relatório; não garante que o julgamento do modelo verificador esteja
semanticamente correto.

**Recuperação integral de saídas.** `BaseThinkingPhase` mantém na mesma execução todas as respostas
recusadas e correções, enviadas integralmente à chamada seguinte. A sintaxe inválida pede o mesmo
conteúdo em JSON válido, sem nova resolução; o contrato inválido pede a saída completa corrigida,
preservando conteúdo não afetado; a interrupção por comprimento pede uma nova saída completa e
concisa, sem continuar a anterior. As instruções são em inglês e Markdown e não repetem o template.
A abreviação de `PhaseParsingError.raw_output` para erro/log não altera o texto usado na janela
nem confirma `finish_reason=length`. JSON legível com contrato inválido e término `length` continua
sendo defeito de contrato; JSON válido para o contrato com `length` continua aceito com diagnóstico
de corte confirmado e sem garantia semântica.

Em A.2/C.2, a orientação de cobertura inclui os passos finais necessários e, em C.2, as lacunas
restantes a partir dos resultados aprovados. O parser continua validando o contrato, sem verificar
semanticamente se o plano é suficiente. A nova orientação não compara significados por regex,
não completa campos localmente e não promove objetos recusados. O detalhe e o exemplo de três
tarefas com título ausente estão em
[Melhorias do thinking — 01](../../NOVAS_REGRAS_RALPH_LOOP.md#melhorias-do-thinking--01-recuperação-integral-de-saídas).

Reenviar conteúdo longo pode aumentar tokens de entrada, latência e espaço no contexto e no
armazenamento dos `prompt_input`. Cada chamada mantém seu consumo, diagnóstico, temperatura e
vínculo à invocação original; a chamada aceita resolve a recuperação. Os limites de retentativa,
chamadas, tokens e tempo seguem valendo. Se faltar orçamento, a execução é interrompida conforme
a política existente, sem encurtar a conversa para forçar nova tentativa. Cancelamento controlado
persiste as recuperações pendentes como `failed` e é propagado. A fase/tarefa seguinte recebe
janela nova e a temperatura da sessão, conforme suas regras próprias de retentativa.

**O que não vem do paper.** O paper repete até aprovar e não define limites de recursos nem estados
de interrupção. Os limites (`RALPH_*` e o limite de tokens por sessão) e o encerramento sem conclusão são
um tratamento operacional adicional, que nunca promove material reprovado nem sintetiza sem aprovação
global. A reserva de tokens é uma margem de melhor esforço, não uma garantia de conclusão.

### Memória de aprendizados: etapa 02

`a3_planning_learnings.md` recebe somente `user_question`, preserva dados literais e suas associações
e pede revisão de completude na própria chamada: nomes, siglas definidas, símbolos/referentes,
tabelas/listas, alternativas integrais com identificadores, valores/unidades, condições e o que
se solicita determinar. Não corrige dados, resolve ambiguidades, converte unidades ou infere definições.

`b4_learnings_extraction.md` recebe `task_description`, `approved_result`, `task_history` e
`learnings` em áreas separadas. Registra todo fato novo útil sustentado pela execução aprovada,
com motivo breve e referência explícita, conservando hipóteses, unidades, sinais, referenciais e
aproximações. Valor calculado e escolha por melhor ajuste não são igualados. Não copia raciocínio
completo, critérios ou vereditos; uma conclusão refutada não vira memória vigente.

Ambos mantêm `{"learnings": ["..."]}`; uma lista vazia é válida. O parser valida estrutura, não
completude ou verdade semântica. `RalphThinkingUseCase` converte as strings sem interpretação para
`Learning(content, source_task_id)`: origem `None` para A.3 e ID da tarefa para B.4.
`LearningsMemory.append` descarta brancos e repetidos comparando apenas espaços; conserva o
primeiro conteúdo e origem, sem unificar caixa, unidades ou condições. `render()` entrega todos
os textos na ordem, sem resumo, para `## Key Learnings` de B.1/B.2/B.4/C.1/C.2/C.3, inclusive
nas tarefas adicionais. B.4 vê a memória anterior à própria extração. Os eventos `learn` e as
mensagens da sessão auditam o que entrou e as repetições descartadas.

Os resultados aprovados continuam armazenados separadamente; notas não são critérios nem cobrem
evidência ausente. Cada fase recebe sua janela e suas entradas explícitas. Não houve mudança de
schema, helper compartilhado, recuperação ou política de planejamento/validação nesta etapa.
Não há dependência de integração com 01/03; os arquivos novos de testes são exclusivos de 02.
Os prompts recebem texto genérico, sem acesso a `question.options` ou a gabaritos.

Os testes novos estão em `test_learnings_annotation_contract.py`,
`test_ralph_learnings_self_contained_integration.py` e `test_learnings_memory_associations.py`.
Eles verificam instruções nos templates reais, transporte, referências, condições, aproximações,
ordem, origem, deduplicação, auditoria e isolamento usando respostas roteirizadas. Não medem
acurácia de extração ou correção semântica de um LLM. Exemplos e resultados da execução estão na
seção **Melhorias do thinking — 02** de
[`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md).

### Planejamento e cobertura do pedido — etapa 03

Os templates A.1/A.2/C.2 extraem as obrigações reais e planejam investigações sem fixar respostas
quantitativas ou qualitativas ainda desconhecidas. A.1 distingue conteúdo obrigatório de
apresentação opcional. A.2/C.2 separam dados literais, método pertinente, hipótese a verificar e
resultado a obter: usar uma lei física é permitido; impor uma condição não fornecida para aplicá-la
ou adivinhar a conclusão anterior não é. Descrições conservam dados, unidades e referências
relevantes, com dependências explícitas pelos aprendizados.

Objetivo único admite dependência lógica. A tarefa que detém a determinação final pode fazer a
última análise, integração ou comparação, e B.1 permite concluí-la com explicação. C.3 aplica idioma,
formato e pareamento literal já sustentado. A.2/C.2 revisam a cobertura dentro da própria geração:
razão de distâncias não basta para período em meses. Não há fase extra de revisão, número fixo de
tarefas, detector semântico no parser ou dado específico de benchmark injetado.

C.2 recebe a nova variável `global_verification_feedback`, renderizada com o relatório de C.1 já
validado (decisão, avaliações, justificativas e IDs), usando o mesmo renderizador do registro da fase.
Ela complementa `unmet_criteria`, que preserva os critérios pendentes sem modificá-los. Feedback não
vira resultado nem aprendizado. A tarefa corretiva pode investigar um erro ou contradição concreta
em resultados existentes, sem predeterminar qual conclusão está errada. Os schemas, limites,
retentativas e chamadas do fluxo permanecem iguais.

Critérios admitem paráfrases, inferência contextual e aproximação fundamentada. Escolher uma opção
não basta para provar acerto. Explicação interna continua obrigatória mesmo para resposta final
curta ou com justificativa opcional. A política completa dos validadores B.2/C.1 foi alinhada na
etapa 04 (seção seguinte); a etapa 03 não alterou esses templates.

Os testes novos estão em
[`test_planning_instruction_contracts.py`](tests/infra/providers/test_planning_instruction_contracts.py)
e [`test_ralph_planning_evidence_integration.py`](tests/application/usecases/test_ralph_planning_evidence_integration.py).
A [matriz semântica versionada](tests/fixtures/planning_semantics_v1.json) e seu
[guia de inspeção](tests/fixtures/README.md) distinguem contratos automatizados de avaliação humana
posterior. As saídas e os vereditos de LLM são roteirizados: testam dados, fases, memória, isolamento
e persistência, sem comprovar obediência de um modelo real. Cobertura semântica é orientada no
planejamento e julgada depois em C.1, nunca certificada pela contagem de tarefas ou aceitação do JSON.

Na integração anterior à etapa 04, conferir as instruções de recuperação de A.2/C.2 da etapa 01:
uma regeneração completa precisa preservar dados e cobrir a última determinação, sem virar mera
compactação ou reparo de um fragmento. Conferir também a passagem dos resultados efetivamente
obtidos pela memória da etapa 02. A etapa 03 não edita a fase base, A.3/B.4 ou os contratos de memória.
Os detalhes e resultados de testes estão na seção **Melhorias do thinking — 03** de
[`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md).

### Validação, consistência e aproximações — etapa 04

`b1_task_resolution.md`, `b2_task_verification.md` e `c1_global_verification.md` compartilham a
seção `## Evidence and consistency policy`, com texto idêntico (verificado por teste): resultado
exato e aproximação/melhor ajuste fundamentados são aceitos; contradição real e conteúdo essencial
ausente pedem revisão ou complementação. A diferença numérica isolada não decide; não há tolerância
percentual, regra “qualquer divergência reprova” nem “escolheu uma opção, aprova”.

| Template | Seções novas ou reescritas |
|---|---|
| B.1 | `Calculated result and chosen option` (valor obtido ≠ opção escolhida; estimativa rotulada; erro identificável corrigido antes da comparação); `Previous attempts` mantém conclusões não refutadas; `Conclusion field`. |
| B.2 | `Technical verification of the local criteria` (explicação presente não é explicação correta; conteúdo implícito com a mesma régua para as opções) e `Selection criteria` (seleção fundamentada, nunca a mais próxima de um valor com erro). Removida a aprovação por “selecionar explicitamente uma opção”. |
| C.1 | `Consistency of the union`, `Justification of each verdict` e exemplos de aceitação sem coincidência exata e de reprovações reais. Removida a aprovação de aproximação “desde que uma opção seja escolhida”. |
| C.2/C.3/A.1/A.2 | Investigação do defeito com resultado explicado; apresentação de aproximação como aproximação; critérios sem exigência universal de coincidência exata. |

Em `RalphThinkingUseCase`, `_RETRY_INSTRUCTION_CONTENT` passou a pedir que a nova tentativa trate o
problema concreto apontado por cada veredito e mantenha as conclusões que ele não refutou, em vez de
“corrigir exatamente esses pontos”. Nenhum schema, variável de template, fase, limite ou regra do
parser mudou: o parser segue validando IDs, cobertura, pendências e coerência da decisão, sem juízo
semântico, sem converter reprovação e sem relaxar tipos.

B.1 preserva os dados literais fornecidos pelo usuário e distingue deles os valores derivados,
conclusões e hipóteses introduzidos pelo planejamento que precisam de verificação. Os exemplos de
produção usam também volume, inventário e decisão coletiva; os casos de regressão do benchmark
permanecem nos testes, sem injeção no núcleo. As guardas dessa separação estão em
[`test_validation_generalist_boundaries.py`](tests/infra/providers/test_validation_generalist_boundaries.py).

Os testes novos estão em
[`test_validation_policy_contracts.py`](tests/infra/providers/test_validation_policy_contracts.py),
[`test_validation_semantics_matrix.py`](tests/infra/providers/test_validation_semantics_matrix.py) e
[`test_ralph_validation_consistency_integration.py`](tests/application/usecases/test_ralph_validation_consistency_integration.py),
sobre a matriz [`validation_semantics_v1.json`](tests/fixtures/validation_semantics_v1.json). Os
vereditos de LLM são roteirizados: os testes comprovam transporte, transições
(C.1 → C.2 → B → C.1 → C.3), recuperação e contabilização, não a capacidade do modelo de reconhecer
erros. Detalhes e resultados na seção **Melhorias do thinking — 04** de
[`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md).

### Revisão auditável de resultados — etapa 05

Contrato opcional (sem os campos, tudo segue como antes):

| Fase | JSON | Validação (`ValidationContext`) |
|---|---|---|
| A.2/C.2 | `"depends_on": ["T1"]` por tarefa | Tarefa anterior do lote ou resultado vigente (`dependable_task_ids`); sem autorreferência, dependência futura, repetição ou dependência do próprio alvo. |
| C.2 | `"review": {"task_ids": ["T3"], "reason": "..."}` por tarefa | Alvos armazenados vigentes ou em revalidação (`reviewable_task_ids`); sem autorrevisão, tarefa do lote, alvo substituído, repetição ou o mesmo alvo em duas tarefas. Critério `<id>-REV` reservado. |
| B.1 | `"revision": [{"task_id", "verdict": "confirmed"\|"superseded", "justification"}]` | Só numa revisora (`review_target_ids`): exatamente um veredito por alvo. Numa tarefa normal, ausente, `null` ou `[]`. |

Recusas usam o código de diagnóstico `task_references` (ou `duplicate_id`, `schema_type`,
`missing_field`, `empty_value`, `invalid_value`) e seguem a recuperação de contrato existente.

`ResultsLedger` (`IResultsLedger`, injetado no caso de uso) substitui o dicionário de B.3 e mantém o
estado de cada resultado: `current`, `superseded` ou `awaiting_revalidation`. `LearningsMemory` guarda
as fontes de cada fato (`withdraw`/`restore`); `all()` e `render()` devolvem só a visão vigente.
B.1 recebe `results_under_review`; B.2, `revision_proposal` e o critério gerado `<id>-REV`; C.1 e C.2,
`result_revisions`. A sessão ganhou `result_revisions` (auditoria estruturada, lida como lista vazia
em documentos antigos), visível em `GET /v1/sessions/{session_id}` e na exportação de erros do
benchmark. Detalhes, exemplo completo e limites na seção **Melhorias do thinking — 05** de
[`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md).

### Fidelidade da síntese final — etapa 06

Nenhuma fase, chamada, schema, regra do parser ou limite novo. C.3 continua sendo uma única execução
de `FinalAnswerPhase`, com saída `{"final_answer": "..."}` e a recuperação de saída inválida existente.

| Ponto | Contrato |
|---|---|
| `GlobalApproval` | Ganhou `learnings` (a área **Key Learnings** renderizada para a C.1 aprovadora) e `ensure_current(current_task_ids)`. `task_ids` passou a ser capturado no mesmo instante em que os resultados são renderizados para C.1, e não depois da resposta. |
| `__run_final_answer` | Chama `approval.ensure_current(...)` antes de abrir a janela de C.3 (`ValueError` se o conjunto vigente mudou; a sessão falha em C.3 sem chamada ao modelo) e monta as variáveis com `approval.stored_results` e `approval.learnings`. Os critérios gerais não mudam depois de A.1 e continuam renderizados por `__synthesis_variables`. |
| `c3_final_answer.md` | Nova seção `## Fidelity check before answering`, dentro da mesma chamada e antes de `final_answer`: conteúdo aprovado; aspectos preservados (significado, direção, sinais, unidades/referencial, referências, hipóteses, condições, qualificações); resultado calculado × escolha aprovada; identificadores por pareamento literal; pareamento literal × seleção analítica; justificativa coerente com a conclusão. Exemplos novos de fidelidade e extrapolação. A conferência não é mencionada na resposta. |
| `c1_global_verification.md` | Nova seção `## Identifiers and faithful presentation` e dois exemplos: vínculo item–identificador exigido e não disponível → `met: false` para C.2; pedido só de conteúdo → sem lacuna; marcador, idioma e formato continuam com C.3. |

As variáveis dos templates C.1/C.3 não mudaram (`stored_results`, `general_acceptance_criteria`,
`learnings`; C.1 também `result_revisions`). Não há entrada especializada do benchmark nem
`question.options`: as associações vêm dos resultados ou das anotações de A.3. Testes:
[`test_final_answer_fidelity_contracts.py`](tests/infra/providers/test_final_answer_fidelity_contracts.py),
[`test_ralph_final_answer_fidelity_integration.py`](tests/application/usecases/test_ralph_final_answer_fidelity_integration.py)
e [`test_global_approval.py`](tests/domain/entities/thinking/test_global_approval.py). Detalhes e
limites na seção **Melhorias do thinking — 06** de
[`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md).

### Integração das cinco frentes — etapa 07

Nenhuma fase, chamada, campo de schema, regra do parser ou limite novo. A etapa exercitou em conjunto
estrutura/recuperação, aprendizados, planejamento, validação e síntese, e corrigiu as incompatibilidades
encontradas entre as etapas 01–06:

| Ponto | Antes | Depois |
|---|---|---|
| `__render_revision_record` (C.1/C.2) | Listava substituídos e resultados aguardando revalidação; depois de uma confirmação aprovada, dizia `No stored result has been revised or suspended.` | Também lista `### Results confirmed by an approved review`: `` `T3` — título: confirmed by `T4`. Approved reason: … `` para cada veredito `confirmed` de uma revisora vigente cujo alvo continua vigente. |
| `_PLANNING_RECOVERY_INSTRUCTIONS` (A.2/C.2) | Cobertura e “approved results”, sem orientação para defeitos de `review`/`depends_on`. | “current approved results” e: corrigir as referências para identificadores permitidos, sem abandonar a investigação dirigida de um defeito apontado nem uma dependência efetivamente usada só para satisfazer o parser. |
| `c2_additional_planning.md` | Formato de saída com `"id": "T1"` (o parser recusa IDs já usados); área de resultados descrita como “each task already approved”. | Formato com `T{{next_task_number}}`; área descrita como resultados vigentes; **Revision record** explica que um confirmado continua vigente pela investigação, não pela recência. |
| `c1_global_verification.md` | Regra de recência sem menção a confirmações. | O registro inclui confirmados; um resultado confirmado por revisão aprovada continua vigente e o mesmo conflito não é reaberto sem novo motivo concreto. |
| `a2_task_decomposition.md` | `depends_on` descrito só em seção própria. | O formato de saída documenta `depends_on` como opcional, sem `review` (A.2 não revisa). |

Testes: [`test_ralph_five_fronts_integration.py`](tests/application/usecases/test_ralph_five_fronts_integration.py)
(matriz de 12 regressões e fluxos de revisão aprovada, rejeitada, recuperação de contrato, orçamento
real esgotado e cancelamento, com templates, parser, livro, memória e persistência reais),
[`test_integration_prompt_contracts.py`](tests/infra/providers/test_integration_prompt_contracts.py)
(coerência conjunta dos nove templates e das mensagens de recuperação) e a fixture
[`integration_regressions_v1.json`](tests/fixtures/integration_regressions_v1.json), cujo oráculo é só
do avaliador. Os cenários são roteirizados: provam fiação, estado e contratos, não acurácia. Detalhes na
seção **Melhorias do thinking — 07** de [`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md)
e em [`RELATORIO_VALIDACAO_MELHORIAS_THINKING.md`](../../RELATORIO_VALIDACAO_MELHORIAS_THINKING.md).

### Planejamento aprovado antes da execução — nova fase de validação 01

Fluxo versão 2 (`flow_version = 2`):

```text
A.1 → A.2 (plano candidato) → A.3 (Task Decomposition Validator)
        ↑ reprovado: último candidato + relatório ┘   └ aprovado → confirma na fila → A.4 → B/C
```

| Peça | Implementação |
|---|---|
| Fases | `TaskDecompositionPhase` (A.2), `DecompositionValidationPhase` (A.3, `a3_decomposition_validation.md`), `PlanningLearningsPhase` (A.4, `a4_planning_learnings.md`, mesma extração da antiga A.3). `ThinkingPhaseEnum` tem `A3_DECOMPOSITION_VALIDATION = "A3"` e `A4_PLANNING_LEARNINGS = "A4"`, sem aliases. |
| A.2 | Template simplificado: regras de geração (dados literais, métodos sem aplicabilidade presumida, resultados em aberto, objetivo único, critérios complementares com explicação, dependências, parcimônia, cobertura e teto). A autoavaliação extensa saiu para A.3. Recebe `plan_revision`: `None: this is the first candidate plan.` ou o último candidato e o relatório. |
| A.3 | Recebe `user_question`, `general_acceptance_criteria` e `candidate_plan` (só o candidato atual, com descrições, critérios e dependências). Rubrica fixa: fidelidade, neutralidade, aplicabilidade, critérios, coerência, cobertura e necessidade. Não resolve, não escolhe resposta, não devolve plano substituto. |
| Contrato de A.3 | `{"approved": bool, "issues": [{"task_id", "criterion_id", "problem", "adjustment"}]}`, com `PlanValidationReport`/`PlanValidationIssue`. Booleano real; aprovação com `issues: []`; reprovação com ao menos um problema; `task_id`/`criterion_id` obrigatórios no objeto e anuláveis; critério precisa pertencer à tarefa no candidato julgado (`ValidationContext.candidate_plan`). Reprovação coerente é saída aceita; contrato inválido segue a recuperação estrutural existente. |
| Fila | Só o plano aprovado entra em `TaskQueue` e em `register_task_created`; candidatos recusados não consomem espaços nem reservam IDs. O teto de tarefas continua valendo para cada candidato. |
| Limite | `RALPH_MAX_PLANNING_ATTEMPTS` (padrão `5`), `CostBudget.max_planning_attempts`, `ICostGuard.register_planning_attempt`/`can_retry_planning`, `BudgetLimitEnum.PLANNING_ATTEMPTS`. Correções de JSON/contrato não contam como candidato; independe de `RALPH_MAX_TASK_ATTEMPTS` (5), `RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS` (2) e `RALPH_JSON_PARSE_MAX_RETRIES` (2). Os outros tetos continuam podendo interromper antes. |
| Auditoria | Cada candidato (A2, `plan_candidate`) e cada relatório (A3, `plan_rejected`/`plan_approved`) é uma mensagem própria, com janela, `prompt_input`, invocação e consumo; a confirmação é uma etapa programática (A3, `tasks`). O campo `subtype` das mensagens guarda o subtipo do evento; a auditoria de saídas recusadas fica sem subtipo. |
| Versão | `Session.flow_version` (`RalphFlowVersionEnum`): `2` nas sessões Ralph novas; sessões Ralph gravadas sem o campo são lidas como `1` (A3 = extração); inferência direta fica `null`. A leitura não reescreve arquivos; `GET /v1/sessions/{id}`, exportações e importação preservam versão, fases, subtipos e conteúdo. |
| C.2 | Não usa A.3: os lotes de planejamento adicional seguem o fluxo anterior. |

Testes: [`test_ralph_planning_validation_integration.py`](tests/application/usecases/test_ralph_planning_validation_integration.py)
(protocolo completo, revisões, fila isolada, cinco tentativas, temperaturas, recuperação, A.4, orçamento,
provedor), [`test_structured_response_parser_plan_validation.py`](tests/infra/adapters/test_structured_response_parser_plan_validation.py)
(contrato), [`test_decomposition_validation_contracts.py`](tests/infra/providers/test_decomposition_validation_contracts.py)
(template e matriz sintética [`decomposition_validation_v1.json`](tests/fixtures/decomposition_validation_v1.json)),
[`test_session_document_mapper_flow_version.py`](tests/infra/mappers/test_session_document_mapper_flow_version.py) e
[`test_flow_version_persistence_round_trip.py`](tests/infra/services/test_flow_version_persistence_round_trip.py)
(persistência, consulta e pacotes). As saídas são roteirizadas: provam o protocolo, não que um modelo real
identificará todo plano ruim. Detalhes em **Nova fase de validação — 01** de
[`NOVAS_REGRAS_RALPH_LOOP.md`](../../NOVAS_REGRAS_RALPH_LOOP.md).

### Limite de tokens por sessão

Todo limite de tokens vale para a **sessão**, nunca para uma rodada ou chamada isolada. Há dois:

1. **Backend — `LLM_MAX_TOKENS`.** Teto absoluto por sessão. Exposto em `GET /v1/limits`.
2. **Cliente — `llm_model_config.max_tokens`.** Limite pedido para a sessão; nunca pode passar do
   limite do backend (`422`/`1003` na fronteira, e `ValueError` se chegar ao composition root).

O limite efetivo da sessão é o `max_tokens` pedido. Na inferência simples, que faz uma única chamada,
ele é o teto de saída dessa chamada. No Ralph, ele é o orçamento do guardião de custo: cada chamada recebe
como teto de saída o saldo que resta dele, ou seja, o limite menos os tokens (entrada + saída) já consumidos
e, fora de C.3, menos também a reserva da resposta final. Com o saldo zerado, a chamada é negada
(`session_token_budget`). A entrada não é estimada, então o consumo real pode ultrapassar o limite em até o
tamanho da entrada da última chamada. Um saldo grande pode passar da janela de contexto do modelo; nesse
caso, peça um limite menor.

**Benchmark.** O único executor de dataset é o [benchmark](#benchmark) de questões de múltipla
escolha, com avaliação determinística pelo gabarito. O backend também oferece MMLU e GPQA Diamond pelo seletor da página BenchMark.

---

## Variáveis de ambiente

As configurações de execução são lidas por `Settings` (`src/infra/config/settings.py`).
Ver `.env.example` para o arquivo completo.

| Variável | Default | Descrição |
|---|---|---|
| `APP_TITLE` | `TCC API` | Título exposto pelo FastAPI. |
| `APP_VERSION` | `0.1.0` | Versão exposta pelo FastAPI. |
| `LOG_LEVEL` | `INFO` | Nível global de log. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Origens liberadas (CSV). |
| `LLM_PROVIDER` | `open_router` | Provedor usado quando a requisição não especifica: `open_router`, `azure_ai_foundry` ou `openai`. |
| `LLM_MODEL` | *(vazio)* | Modelo padrão quando a requisição não especifica. |
| `LLM_MAX_TOKENS` | `120000` | Limite de tokens (entrada + saída) **por sessão** imposto pelo backend, nos dois fluxos e no benchmark. O `max_tokens` pedido é o limite da sessão e nunca pode passar dele (`422` no HTTP, `1003` nos WebSockets). Também é o orçamento do guardião de custo do Ralph. |
| `LLM_TEMPERATURE` | `0.7` | Temperatura padrão. |
| `LLM_TIMEOUT_SECONDS` | `30` | Timeout das chamadas HTTP, em qualquer provedor. |
| `LLM_REASONING_EFFORT` | *(vazio)* | Esforço de raciocínio (`minimal`/`low`/`medium`/`high`); vazio não envia o parâmetro. Como o teto de saída de cada chamada cobre raciocínio **e** resposta, limitá-lo evita que o modelo gaste o saldo da sessão pensando e devolva conteúdo vazio. |
| `OPENROUTER_API_URL` | `https://openrouter.ai/api/v1/chat/completions` | Endpoint de chat completions. |
| `OPENROUTER_API_KEY` | *(vazio)* | Chave da API. Obrigatória para usar o provedor. |
| `OPENROUTER_HTTP_REFERER` | *(vazio)* | Header `HTTP-Referer`, opcional. |
| `OPENROUTER_X_TITLE` | *(vazio)* | Header `X-Title`, opcional. |
| `OPENAI_API_URL` | `https://api.openai.com/v1/chat/completions` | Endpoint de chat completions. |
| `OPENAI_API_KEY` | *(vazio)* | Chave da API. Obrigatória para usar o provedor. |
| `OPENAI_ORGANIZATION` | *(vazio)* | Header `OpenAI-Organization`, opcional. |
| `AZURE_AI_FOUNDRY_ENDPOINT` | *(vazio)* | Origem do recurso (ex.: `https://meu-recurso.services.ai.azure.com`), sem barra final. Obrigatória para usar o provedor. |
| `AZURE_AI_FOUNDRY_API_KEY` | *(vazio)* | Chave do recurso, enviada no header `api-key`. Obrigatória para usar o provedor. |
| `AZURE_AI_FOUNDRY_API_VERSION` | `2024-10-21` | Versão da API passada na query string. |
| `AZURE_AI_FOUNDRY_DEPLOYMENT` | *(vazio)* | Nome do deployment. Vazio usa o próprio `model_name` da requisição. |
| `GENAI_AVAILABLE_MODELS` | *(vazio)* | Allowlist de modelos (JSON array ou CSV). Os modelos do catálogo no MongoDB também ficam liberados. |
| `GENAI_AVAILABLE_PROVIDERS` | *(vazio)* | Allowlist de provedores (JSON array ou CSV). |
| `RALPH_SESSION_STORAGE_BACKEND` | `json_file` | Backend de persistência de sessões: `json_file` ou `mongodb`. |
| `RALPH_SESSIONS_STORAGE_PATH` | `./data/sessions` | Diretório dos JSON de sessão, quando o backend é `json_file`. |
| `MONGODB_URI` | `mongodb://localhost:27017` | URI de conexão do MongoDB (catálogo de modelos e, com o backend `mongodb`, as sessões). |
| `MONGODB_DATABASE` | `tcc` | Banco de dados usado no MongoDB. |
| `MONGODB_SESSIONS_COLLECTION` | `sessions` | Coleção que guarda os documentos de sessão no MongoDB. |
| `MONGODB_MODELS_COLLECTION` | `models` | Coleção do catálogo de modelos (`/v1/models`). |
| `RALPH_SESSION_FLUSH_EVERY_MESSAGE` | `true` | Persiste a sessão após cada mensagem registrada. |
| `RALPH_SESSION_ID_PREFIX` | `sess` | Prefixo do identificador de sessão. |
| `RALPH_MAX_TASK_ATTEMPTS` | `5` | Máximo de tentativas por tarefa, incluindo a inicial (até cinco pares B.1/B.2). Esgotado sem aprovação, a execução é interrompida: nenhum resultado reprovado é armazenado ou sintetizado. |
| `RALPH_MAX_PLANNING_ATTEMPTS` | `5` | Planos candidatos do planejamento inicial (A.2 avaliado por A.3), incluindo o primeiro: até quatro revisões. Correções de saída inválida não contam. Esgotado sem aprovação, a sessão termina (`planning_attempts`) sem confirmar plano, sem A.4, tarefas ou síntese. Independe das tentativas por tarefa e das rodadas de C.2. |
| `RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS` | `2` | Máximo de rodadas de planejamento adicional por sessão. Esgotado com a verificação global ainda reprovada, a execução é interrompida (sem síntese). |
| `RALPH_MAX_TASKS_PER_SESSION` | `12` | Total máximo de tarefas por sessão. Vale para o plano inicial e para cada planejamento adicional: um lote acima do espaço restante é devolvido ao planejador para correção, nunca truncado. |
| `RALPH_MAX_LLM_CALLS_PER_SESSION` | `60` | Teto absoluto de chamadas ao modelo. Toda chamada enviada conta, inclusive correções de JSON e completions vazias repetidas. |
| `RALPH_FINAL_ANSWER_TOKEN_RESERVE` | `4000` | Margem de tokens, descontada do limite da sessão, que só C.3 enxerga, de melhor esforço: **não garante** a síntese (C.1 também precisa de recursos antes dela). O limite da sessão precisa ser maior que ela; do contrário o Ralph é recusado antes de qualquer chamada. |
| `RALPH_SESSION_TIMEOUT_SECONDS` | `600` | Tempo máximo de parede da sessão, verificado antes de cada chamada. O timeout HTTP de uma chamada (`LLM_TIMEOUT_SECONDS`) não é limitado ao tempo restante da sessão. |
| `RALPH_PROMPT_TEMPLATES_PATH` | `src/infra/templates` | Diretório dos templates `.md`. |
| `RALPH_JSON_PARSE_MAX_RETRIES` | `2` | Retentativas quando o modelo devolve JSON inválido, relatório de verificação inconsistente, lote de tarefas inválido ou completion vazia. Cada retentativa é uma chamada contada, feita com temperatura `1`; a temperatura do usuário volta na chamada seguinte às retentativas. |
| `RALPH_WEBSOCKET_MAX_MESSAGE_BYTES` | `1048576` | Tamanho máximo do frame recebido no WebSocket (vale também para `WS /v1/benchmark/run`). |
| `RALPH_BENCHMARK_SESSIONS_STORAGE_PATH` | `./data/benchmark-sessions` | Diretório dos JSON das baterias de benchmark, quando o backend é `json_file`. |
| `MONGODB_BENCHMARK_SESSIONS_COLLECTION` | `benchmark_sessions` | Coleção das baterias de benchmark no MongoDB. |
| `RALPH_BENCHMARK_QUESTIONS_PATH` | `src/infra/benchmark/questions` | Dataset de questões: uma pasta por questão, com `enunciado.md` e `alternativa_correta.md`. |
| `RALPH_BENCHMARK_PROMPT_PATH` | `src/infra/benchmark/prompts/vestibular.md` | Instrução de resposta, em português, anexada ao enunciado de cada questão dos vestibulares. MMLU e GPQA usam as próprias instruções em inglês, em `src/infra/benchmark/prompts/`. |
| `RALPH_BENCHMARK_MAX_PARALLEL` | `10` | Limite superior de `max_parallel` numa bateria. |
| `RALPH_BENCHMARK_PROGRESS_INTERVAL_SECONDS` | `1` | Intervalo máximo entre dois frames `progress` sem mudança de estado, para manter o tempo decorrido atualizado. |

---

## Arquitetura em uma imagem

```
infra/routes        HTTP + WebSocket — só traduz DTO ↔ caso de uso, sem regra de negócio
infra/startups       Composition root — instancia e injeta tudo (Settings, adapters, fases)
application          Use cases + Phases (Strategy) — regra de negócio, depende só de domain
domain               Entidades, enums, erros e interfaces (ABC)
infra/*              Adapters, repositório, mapper, provider de templates, config
```

A persistência de sessões é compartilhada pelos endpoints de mensagens e pode ser consultada
pelos endpoints `GET /v1/sessions*`.


## Benchmark

O benchmark compara a inferência simples e o Ralph Loop sobre questões de múltipla escolha de
vestibulares brasileiros, do MMLU ou do GPQA Diamond. É uma funcionalidade da API: a página **BenchMark** do front-end inicia uma
bateria pelo WebSocket, acompanha o progresso e consulta as baterias pelos endpoints `GET`.

**Seleção do benchmark.** Vestibulares continuam sendo o padrão. GPQA oferece Diamond (198 questões),
Main (448) e Extended (546), com protocolo generativo 0-shot, filtros por disciplina e amostragem reproduzível. Consulte
[GPQA na aplicação](src/infra/benchmark/gpqa/README.md) para fonte, protocolo e execução.
A página também oferece MMLU
generativo 0-shot ou 5-shot, com filtro por disciplina e amostra reproduzível por semente. As 14.042
questões de teste e os 285 exemplos de desenvolvimento estão incluídos localmente, com revisão e
hashes fixados. Consulte [MMLU na aplicação](src/infra/benchmark/mmlu/README.md) para o protocolo,
limites de comparabilidade, exemplo de API e auditoria dos dados.

**Dataset.** Vestibulares reúne 270 questões reais: 30 de História, 30 de Geografia, 30 de Filosofia e
Sociologia (categoria conjunta), 30 de Biologia e 50 de cada uma de Matemática, Química e Física. As
90 questões anteriores foram preservadas. Consulte o [catálogo de fontes oficiais](src/infra/benchmark/sources/CATALOG.md).
As questões ficam em [`src/infra/benchmark/questions`](src/infra/benchmark/questions/README.md),
no mesmo formato de antes: uma pasta por questão, com `enunciado.md` (enunciado e quatro ou cinco alternativas, de `A)` a
`D)` ou `E)`) e `alternativa_correta.md` (letra e texto do gabarito). O dataset inteiro é validado antes de qualquer
chamada ao modelo. Cada benchmark tem a própria instrução de resposta, comum aos dois fluxos e no idioma das
suas questões, em [`src/infra/benchmark/prompts/`](src/infra/benchmark/prompts): `vestibular.md` em português
(última linha `RESPOSTA_FINAL: LETRA`), `mmlu.md` e `gpqa.md` em inglês (última linha `FINAL_ANSWER: LETTER`).
O gabarito nunca entra no prompt.

**Bateria (`BenchmarkSession`).** Cada execução cria uma `BenchmarkSession`, persistida no mesmo backend
das sessões (JSON em `RALPH_BENCHMARK_SESSIONS_STORAGE_PATH` ou a coleção
`MONGODB_BENCHMARK_SESSIONS_COLLECTION`). Ela agrupa a configuração do modelo, o paralelismo, o estado de
cada questão e o desfecho de cada fluxo (sessão gerada, alternativa escolhida, acerto, falha, tokens e
duração). Os totais — progresso, tokens, sessões e, por fluxo, acertos, erros, falhas, acurácia, tokens e
tempo — são derivados das questões. Cada fluxo grava a própria `Session` normal, com `benchmark_details`
preenchido e `run_id` igual ao `id` da bateria.

**Execução.** As questões escolhidas entram numa fila FIFO, na ordem do dataset, consumida por até
`max_parallel` workers. Cada worker executa a questão inteira em sequência: inferência simples e depois
Ralph Loop, pelos mesmos composition roots dos endpoints de mensagem. Falhas de um fluxo (provedor, limite
do Ralph, resposta sem alternativa) viram erro avaliado e não impedem o outro fluxo nem as próximas
questões. A bateria é gravada no início, a cada desfecho de fluxo e no encerramento.

**Avaliação.** Determinística: a última linha `RESPOSTA_FINAL: A` (ou `FINAL_ANSWER: A`, nos benchmarks em
inglês), uma letra isolada ou uma alternativa completa isolada. Respostas ambíguas, sem alternativa e falhas técnicas contam como erro, com diagnóstico
em `error`. A acurácia de um fluxo é `correct / executed`.

### `WS /v1/benchmark/run`

1. O cliente abre a conexão e envia **um único frame** de abertura:

   ```json
   {
     "question_count": 10,
     "max_parallel": 5,
     "llm_model_config": {
       "provider": "open_router",
       "provider_config": { "model_name": "deepseek/deepseek-v4-flash-0731" },
       "max_tokens": 4096,
       "temperature": 0
     }
   }
   ```

   `question_count` (opcional, `>= 1`) executa as primeiras questões do dataset; ausente, executa todas.
   Em Vestibulares, a opção **Por matéria** permite definir uma quantidade para cada disciplina,
   com total calculado automaticamente. Na API, envie `subject_counts`, por exemplo:

   ```json
   {
     "subject_counts": { "HISTORIA": 5, "FILOSOFIA_SOCIOLOGIA": 3, "MATEMATICA": 10 },
     "question_count": 18,
     "max_parallel": 5,
     "llm_model_config": {
       "provider": "open_router",
       "provider_config": { "model_name": "deepseek/deepseek-v4-flash-0731" },
       "max_tokens": 4096,
       "temperature": 0
     }
   }
   ```

   As chaves são os IDs de matérias de `GET /v1/benchmark/questions`: `HISTORIA`, `GEOGRAFIA`,
   `FILOSOFIA_SOCIOLOGIA`, `BIOLOGIA`, `MATEMATICA`, `QUIMICA` e `FISICA`. As cotas são inteiros de
   zero até a quantidade disponível em cada matéria. Matérias omitidas ou com zero ficam fora da
   bateria; a soma deve ser positiva. Filosofia e Sociologia constituem uma única categoria.
   São usadas as primeiras questões de cada matéria, mantendo a ordem do dataset.
   `question_count` pode ser omitido nesse modo; quando enviado, deve coincidir com a soma das cotas.
   Matérias desconhecidas, cotas acima do disponível e totais divergentes são
   recusados antes de criar a bateria ou chamar o modelo. Sem `subject_counts`, a seleção por total
   mantém o comportamento anterior. A distribuição escolhida fica registrada em `questions[].subject`
   e as matérias com cota positiva em `benchmark.subjects`.

   Para MMLU, envie `benchmark: "mmlu"`, `few_shot: 0` ou `5`, `subjects: []` (todas) ou uma lista de
   disciplinas e `sample_seed` (padrão 42). A quantidade passa a representar uma amostra distribuída entre
   as disciplinas selecionadas. A bateria persiste esse protocolo no campo `benchmark`.
   Em MMLU e GPQA também vale `subject_counts` (ex.: `{"physics": 10, "biology": 5}`) com cotas de zero até
   o total de cada disciplina; cada cota é uma amostra da disciplina definida por `sample_seed`, e aumentar
   a cota só acrescenta questões à amostra anterior. Não pode ser combinado com `subjects`, e
   `question_count`, se enviado, deve coincidir com a soma.
   `max_parallel` (default `5`) vai de `1` a `RALPH_BENCHMARK_MAX_PARALLEL`. `llm_model_config` é o
   [`ModelConfigDTO`](#modelconfigdto) dos endpoints de mensagem e vale para todos os fluxos; seu
   `max_tokens` vai de `1` a `LLM_MAX_TOKENS` e é o limite de tokens de **cada sessão** gerada pela bateria
   (uma por fluxo e questão), e não de cada chamada. Ver [Limite de tokens por sessão](#limite-de-tokens-por-sessão).

2. O servidor envia um frame `{"type": "progress", "benchmark_session": {...}}` a cada mudança (questão ou
   fluxo começando ou terminando, consumo de tokens do Ralph) e, sem mudanças, a cada
   `RALPH_BENCHMARK_PROGRESS_INTERVAL_SECONDS`. `benchmark_session` é o documento completo da bateria (abaixo).
3. O último frame é `{"type": "result", "benchmark_session": {...}}`, com a bateria encerrada.

| Código | Motivo |
|---|---|
| `1000` | Bateria concluída (`status = completed`). |
| `1003` | Abertura fora do contrato, ou `question_count`/`max_parallel`/`max_tokens` acima do permitido — precedido de `{"type": "error", "content": "<detalhe>"}`; nenhuma bateria é criada. |
| `1009` | Frame de abertura maior que `RALPH_WEBSOCKET_MAX_MESSAGE_BYTES`. |
| `1011` | Bateria encerrada sem concluir (`failed`, depois do frame `result`) ou erro fora do caso de uso (frame `error`). |

**Desconexão.** Se o cliente fecha a conexão, a bateria é interrompida: os workers são cancelados, as
sessões em execução são encerradas como `failed`, as questões em execução ficam `interrupted`, as que
nem começaram ficam `pending` e a bateria é gravada com `status = interrupted`.

**Documento da bateria** (o mesmo de `GET /v1/benchmark/sessions/{id}`):

```json
{
  "_id": "bench_3f2a…", "id": "bench_3f2a…",
  "status": "running",
  "model_name": "deepseek/deepseek-v4-flash-0731", "provider": "open_router",
  "max_tokens": 4096, "temperature": 0, "max_parallel": 5, "question_count": 10,
  "created_at": "2026-10-25T12:00:00+00:00", "updated_at": "…", "finished_at": null,
  "wall_time_ms": 61250, "error": null,
  "progress": { "total": 10, "pending": 3, "running": 5, "finished": 2, "interrupted": 0 },
  "total_tokens": 48211,
  "session_ids": ["sess_…", "sess_…"],
  "summary": {
    "simple": { "executed": 7, "correct": 4, "wrong": 3, "failures": 0, "accuracy": 0.571, "total_tokens": 5120, "duration_seconds": 21.4 },
    "ralph":  { "executed": 2, "correct": 2, "wrong": 0, "failures": 0, "accuracy": 1.0, "total_tokens": 38000, "duration_seconds": 95.0 }
  },
  "questions": [
    {
      "question_id": "FISICA_ENEM_2023_AZUL_Q108", "expected_alternative": "D",
      "status": "running", "current_mode": "ralph", "current_tokens": 5091, "total_tokens": 5731,
      "simple": { "mode": "simple", "session_id": "sess_…", "selected_alternative": "D", "is_correct": true,
                  "error": null, "duration_seconds": 3.2, "total_tokens": 640 },
      "ralph": null
    }
  ]
}
```

`status` da bateria: `running`, `completed`, `failed` (erro técnico da bateria, como persistência
indisponível; detalhe em `error`) ou `interrupted`. `status` da questão: `pending`, `running`, `finished`
ou `interrupted`. `total_tokens` inclui o consumo já informado pelos fluxos em execução.

### `GET /v1/benchmark/sessions`

Lista as baterias, da mais recente para a mais antiga: `{ "benchmark_sessions": [<documento>, ...] }`.

### `GET /v1/benchmark/sessions/{benchmark_session_id}`

Documento de uma bateria. `404` quando não existe; `400` para identificador ou documento persistido
inválido; `500` para outras falhas. As sessões de cada fluxo são consultadas por `GET /v1/sessions/{id}`.

### `PUT /v1/benchmark/sessions/{benchmark_session_id}/alias`

Define ou edita o título de uma bateria encerrada (`completed`, `failed` ou `interrupted`). Envie
`{ "alias": "Comparação de temperatura" }`; o texto tem até 120 caracteres, com espaços das pontas
removidos. `null` ou texto vazio remove o alias. A resposta é o documento atualizado da bateria.
O campo `alias` também aparece no detalhe e na listagem; documentos antigos recebem `null`.
O título fica no documento da bateria no MongoDB (ou no arquivo JSON, conforme o backend configurado).
No frontend, use **Adicionar alias** ou **Editar alias** no detalhe da bateria; o título aparece também
no cartão da listagem. `404` para bateria inexistente, `409` para bateria em execução, `422` para corpo
inválido, `400` para identificador inválido e `500` para outras falhas.

### `GET /v1/benchmark/sessions/{benchmark_session_id}/ralph-loop-errors/export`

Baixa um ZIP (`application/zip`, `benchmark-session-<id>-ralph-loop-errors.zip`) com uma pasta
`questao-<id>/` para cada questão com desfecho incorreto no Ralph Loop (falhas técnicas e respostas
inválidas contam como erro; questões certas e o fluxo simples ficam de fora). Usa só o que já está
gravado — não executa o benchmark de novo. Cada pasta tem:

- `questao.json` — `id`, `statement` (enunciado com as alternativas) e `options`;
- `execucao-ralph-loop.json` — `outcome` do Ralph Loop e `session`, o documento completo da sessão
  (`GET /v1/sessions/{id}`: mensagens, invocações, `final_answer`, `benchmark_details`);
- `resposta-esperada.json` — `alternative` (letra), `text` e `answer` (`LETRA) texto`).

`statement`/`options`/`text`/`answer` e `session` são `null` quando a questão saiu do dataset ou a
sessão não existe mais (por exemplo, o fluxo falhou antes de criá-la). `409` quando a bateria ainda
está em execução ou nenhuma questão errou no Ralph Loop (nunca devolve um ZIP vazio); `404` quando a
bateria não existe; `400` para identificador inválido; `500` para outras falhas.

### `WS /v1/benchmark/sessions/{benchmark_session_id}/questions/{question_id}/rerun`

Reexecuta uma questão de uma bateria já encerrada, para conferir se uma correção no código resolveu
um erro. Não há frame de abertura: o modelo, o provedor, `max_tokens` e a temperatura vêm da própria
bateria, e o prompt segue o dataset e o protocolo (few-shot) dela. Só os fluxos (`simple`/`ralph`)
com desfecho errado ou com falha são refeitos, cada um numa sessão nova; o novo desfecho substitui o
anterior na bateria, que é gravada a cada fluxo refeito (as sessões antigas continuam em
`GET /v1/sessions/{id}`, mas deixam de constar em `session_ids` da bateria). Os fluxos que já
acertaram não rodam de novo.

Os frames são os mesmos de `WS /v1/benchmark/run`: `progress` a cada mudança e um `result` final,
com o documento inteiro da bateria; enquanto o fluxo roda, `questions[].current_mode` indica qual
é, com a questão ainda `finished`. O `status` da bateria não muda. Fecha com `1000` ao terminar.
Pedidos recusados (bateria inexistente, ainda em execução ou já em reexecução, questão que não
pertence à bateria, não existe mais no dataset ou não tem fluxo errado) geram um frame
`{ "type": "error", "content": "..." }` e fecham com `1003`. Se o cliente desconecta, o fluxo em
andamento é cancelado e o desfecho anterior permanece. Só uma reexecução por bateria roda por vez.

### `GET /v1/benchmark/questions`

Aceita `?benchmark=mmlu` para descrever MMLU ou `?benchmark=gpqa` para GPQA (Diamond por padrão; `gpqa_subset=main` ou `extended` escolhe as outras variantes); sem o parâmetro, preserva vestibulares. A resposta
também traz `benchmark` (proveniência) e `subjects` (identificador e quantidade de questões por disciplina).
Em Vestibulares, `subjects` informa os limites das sete matérias para configurar `subject_counts`.

Questões do dataset, na ordem de execução, e os limites de paralelismo e de `max_tokens` (tokens por
sessão, igual a `LLM_MAX_TOKENS`):
`{ "question_ids": ["FISICA_ENEM_2023_AZUL_Q108", ...], "max_parallel_limit": 10, "max_tokens_limit": 120000 }`.

### Metadados nas sessões

`Session.benchmark_details` usa a classe `BenchmarkDetails`, com os campos `is_banchmark`, `question_name`,
`corret_answer`, `providade_answer`, `inference_mode` (`simple`/`ralph`), `run_id` (o `id` da bateria),
`expected_alternative`, `selected_alternative`, `is_correct`, `duration_seconds` e `error`. Os nomes preservam o
contrato solicitado. Sessões comuns têm `is_banchmark=false` e os demais campos nulos; documentos antigos
sem `benchmark_details` recebem esse padrão na leitura.
