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
  implementada por `FilePromptTemplateProvider`, em vez de embuti-los nos casos de uso.
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
- [Endpoint WebSocket](#endpoint-websocket)
  - [`WS /v1/message/reasoning`](#ws-v1messagereasoning)
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
| `422` | Corpo fora do contrato (`message` ausente, `temperature` fora de `[0, 1]`, `max_tokens <= 0`, `provider` desconhecido, etc.). |
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

Consulta o documento completo de uma sessão: pergunta, todo o histórico de mensagens (uma por
etapa do fluxo, com fase, tokens e tempo de inferência), totais agregados, degradações e resposta
final.

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
      "model_name": null
    }
  ],
  "degradations": []
}
```

`flow` identifica o tipo da sessão: `A1` para `/v1/message/reasoning` e `DIRECT` para
`/v1/message/default`.

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
3. O último frame tem `"type": "result"` e traz a resposta final em `content`. Em seguida o
   servidor fecha a conexão.

**Códigos de fechamento**

| Código | Motivo |
|---|---|
| `1000` | Fluxo concluído normalmente. |
| `1003` | Payload inválido (JSON malformado ou fora do contrato de `ReasoningInputDTO`) — precedido de um frame `{"type": "error", "content": "<detalhe>"}`. |
| `1009` | Frame de abertura maior que `RALPH_WEBSOCKET_MAX_MESSAGE_BYTES`. |
| `1011` | Exceção durante a execução do fluxo — precedido de um frame de erro (o próprio evento `error` do domínio e, em seguida, um frame genérico `{"type": "error", "content": "<detalhe>"}`). |

Se o cliente desconectar no meio da execução, o servidor não levanta exceção: encerra o gerador,
finaliza a sessão como `failed` e apenas registra um log — não há frame nem fechamento adicional
(não há mais ninguém do outro lado para recebê-los).

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
| `max_tokens` | `int` | `> 0` |
| `temperature` | `float` | `[0, 1]`; ausente ou `0`/`null` vira `0.7`; arredondada para 1 casa decimal |

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
| `context_size` | `int` | Tokens acumulados na janela de contexto atual. |

### `ReasoningEventDTO`

Cada frame emitido por `WS /v1/message/reasoning`. **Exatamente estes 9 campos, sem extras.**

| Campo | Tipo | Descrição |
|---|---|---|
| `type` | `string` | `thinking` \| `result` \| `degraded` \| `error`. |
| `subtype` | `string` | `setup`, `tasks`, `execute`, `reasoning`, `verify_pass`, `verify_fail`, `store`, `learn`, `reset`, `compile`, `replan`. |
| `phase` | `string` | `A1`, `A2`, `B1`, `B2`, `B3`, `B4`, `C1`, `C2`, `C3`. |
| `task` | `string` | Id da tarefa (`T1`, `T2`, ...), ou `setup` / `synthesis` para etapas globais. |
| `session_id` | `string` | Sessão em execução. |
| `content` | `string` | Markdown pronto para renderização. |
| `total_tokens` | `int` | Acumulado da sessão; **nunca decresce**. |
| `context_window` | [`ContextWindowDTO`](#contextwindowdto) | Janela de contexto no momento do evento. |
| `inference_time_ms` | `int` | Tempo da chamada ao modelo; `0` em eventos sem inferência. |

Frames de erro fora do fluxo normal (payload inválido, ou o frame genérico que precede o
fechamento `1011`) usam um formato reduzido, **fora** deste contrato de 9 campos:

```json
{ "type": "error", "content": "<detalhe do erro>" }
```

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
| `LLM_MAX_TOKENS` | `1024` | Teto de tokens de saída padrão. |
| `LLM_TEMPERATURE` | `0.7` | Temperatura padrão. |
| `LLM_TIMEOUT_SECONDS` | `30` | Timeout das chamadas HTTP, em qualquer provedor. |
| `LLM_REASONING_EFFORT` | *(vazio)* | Esforço de raciocínio (`minimal`/`low`/`medium`/`high`); vazio não envia o parâmetro. Como `max_tokens` cobre raciocínio **e** resposta, limitá-lo evita que o modelo gaste o orçamento inteiro pensando e devolva conteúdo vazio. |
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
| `GENAI_AVAILABLE_MODELS` | *(vazio)* | Allowlist de modelos (JSON array ou CSV). |
| `GENAI_AVAILABLE_PROVIDERS` | *(vazio)* | Allowlist de provedores (JSON array ou CSV). |
| `RALPH_SESSION_STORAGE_BACKEND` | `json_file` | Backend de persistência de sessões: `json_file` ou `mongodb`. |
| `RALPH_SESSIONS_STORAGE_PATH` | `./data/sessions` | Diretório dos JSON de sessão, quando o backend é `json_file`. |
| `MONGODB_URI` | `mongodb://localhost:27017` | URI de conexão, quando o backend é `mongodb`. |
| `MONGODB_DATABASE` | `tcc` | Banco de dados usado no MongoDB. |
| `MONGODB_SESSIONS_COLLECTION` | `sessions` | Coleção que guarda os documentos de sessão no MongoDB. |
| `RALPH_SESSION_FLUSH_EVERY_MESSAGE` | `true` | Persiste a sessão após cada mensagem registrada. |
| `RALPH_SESSION_ID_PREFIX` | `sess` | Prefixo do identificador de sessão. |
| `RALPH_MAX_TASK_ATTEMPTS` | `3` | Máximo de tentativas por tarefa. |
| `RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS` | `2` | Máximo de rodadas de planejamento adicional por sessão. |
| `RALPH_MAX_TASKS_PER_SESSION` | `12` | Total máximo de tarefas por sessão. |
| `RALPH_MAX_LLM_CALLS_PER_SESSION` | `60` | Teto absoluto de chamadas ao modelo. |
| `RALPH_SESSION_TOKEN_BUDGET` | `120000` | Teto de tokens (input + output) da sessão. |
| `RALPH_FINAL_ANSWER_TOKEN_RESERVE` | `4000` | Reserva de tokens configurada para a resposta final. |
| `RALPH_SESSION_TIMEOUT_SECONDS` | `600` | Tempo máximo de parede da sessão. |
| `RALPH_PROMPT_TEMPLATES_PATH` | `src/infra/templates` | Diretório dos templates `.md`. |
| `RALPH_JSON_PARSE_MAX_RETRIES` | `2` | Retentativas quando o modelo devolve JSON inválido. |
| `RALPH_WEBSOCKET_MAX_MESSAGE_BYTES` | `1048576` | Tamanho máximo do frame recebido no WebSocket. |

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
