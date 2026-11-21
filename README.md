<p align="center">
  <img src="apps/frontend/src/assets/ralph_image.png" alt="Ralph, ícone do projeto" height="140" />
</p>

# Aprimoramento de outputs de Inteligência Artificial

Este repositório contém o projeto de TCC **“Um Harness de IA para Resolução de Perguntas em Linguagem Natural: Adaptando o Ralph Wiggum Loop Além do Desenvolvimento de Software”**. A aplicação compara uma resposta obtida por inferência direta com outra produzida pelo Ralph Loop Adaptado.

## Estrutura do projeto

### Front

O frontend fica em [`apps/frontend/`](apps/frontend/) e foi desenvolvido com React, TypeScript e Vite. Ele permite comparar os dois fluxos para uma mesma pergunta: a inferência direta (baseline) e o harness baseado no Ralph Loop. No fluxo adaptado, a interface acompanha a decomposição em tarefas, as tentativas e validações, a reinicialização de contexto (*fresh context*) e a síntese da resposta final. Consulte o [README do frontend](apps/frontend/README.md) para detalhes de execução e arquitetura.

A página **BenchMark** permite escolher entre vestibulares brasileiros, **MMLU** e **GPQA**, com protocolos
generativos (0-shot; também 5-shot no MMLU), filtro de disciplina, amostras reproduzíveis e histórico identificado por
dataset e protocolo. Os dados MMLU já estão incluídos no backend. Consulte o
[guia do MMLU](apps/backend/src/infra/benchmark/mmlu/README.md) para configuração e metodologia.
O [guia do GPQA](apps/backend/src/infra/benchmark/gpqa/README.md) descreve as variantes Diamond (198 questões),
Main (448) e Extended (546), o protocolo generativo 0-shot e a execução pela interface ou API. O dataset oficial protegido já está incluído.

### Back

O backend fica em [`apps/backend/`](apps/backend/) e fornece a API que executa os fluxos de inferência e registra as sessões. O fluxo do harness foi construído a partir do que é proposto no paper do TCC: planejamento, execução e validação iterativas de tarefas, uso de *fresh context* entre tarefas e síntese de uma resposta final. A implementação também oferece o fluxo de inferência direta para servir de baseline na comparação. A metodologia e sua adaptação estão descritas em [`RALPH_LOOP_ADAPTADO.md`](RALPH_LOOP_ADAPTADO.md); detalhes técnicos da API estão no [README do backend](apps/backend/README.md).

### Outros diretórios e arquivos

- `docs/` — materiais do TCC, incluindo paper, análises e diagramas.
- `docker-compose.yml` e `docker-compose.dev.yml` — configurações para executar a aplicação em containers.

Os enunciados de fase usados para orientar a implementação do backend e do frontend ficam em `feature_ralph/` e `feature_front/`, respectivamente. Esses diretórios são locais, estão no `.gitignore` e não fazem parte do histórico do repositório.

## Conteúdo de `RALPH_LOOP_ADAPTADO.md`

O documento apresenta a adaptação do Ralph Wiggum Loop, originalmente voltado à engenharia de software, para a resolução de perguntas em linguagem natural. Ele contém:

- um resumo da proposta e dos conceitos do Ralph Wiggum Loop;
- um guia operacional para agentes de desenvolvimento CLI, derivado da metodologia;
- a transcrição literal da seção **“Metodologia”** do paper, que detalha planejamento (A), execução em loop (B) e criação da resposta final (C).

O guia operacional é uma orientação derivada, enquanto a seção identificada como transcrição preserva o texto original do paper. As regras acrescentadas depois do paper (hoje, a etapa **A.3 — Task Decomposition Validator**, que aprova o plano antes da execução, a etapa **A.4 — Aprendizados pontuais do enunciado** (A.3 nas sessões antigas), a verificação da **tarefa inteira em B.2**, com a descrição da tarefa e o critério técnico obrigatório **`<task_id>-TECH`**, a área de **Aprendizados Pontuais** em todo prompt das fases B e C, a **temperatura 1 nas retentativas** (com a primeira revisão de A.2 a 0,5), a **procedência visível** dos aprendizados (`[Question]`, `[Task T1]`), as **regras de redação das tarefas** e a **reinicialização de contexto entre fases** com recuperação de saídas inválidas) ficam numa seção própria do documento e são detalhadas, com exemplos, em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md), base para atualizar o paper. O documento também explicita essa distinção e descreve as etapas, os critérios de aceite e a separação de contexto e resultados entre as tarefas.

## Uso multiusuário

A aplicação aceita visitantes e contas:

| Perfil | Benchmarks e análises oficiais | Chamadas LLM | Dados pessoais | Publicar resultados oficiais |
|---|---|---|---|---|
| Visitante | Sim | Não | Não | Não |
| Usuário autenticado | Sim | Sim, com a própria chave OpenRouter | Só os próprios | Não |
| Administrador | Sim | Sim, com a própria chave | Os próprios + operações administrativas (CLI) | Sim |

- **Serviços:** `apps/frontend` (React), `apps/auth` (cadastro/login por e-mail e senha — premissa
  desta entrega), `apps/backend` (API e fluxos LLM) e MongoDB. Frontend, `/auth` e `/v1` ficam na
  mesma origem por proxy de caminhos (Vite em desenvolvimento, Nginx em produção).
- **Sessão:** cookie HttpOnly com token opaco, 24 h absolutas a partir do login, revogada no logout.
- **Chave OpenRouter:** informada no login (ou depois), validada com a OpenRouter e guardada **no
  navegador**, cifrada (JWE) num cookie HttpOnly vinculado à conta e à sessão; nunca é gravada no
  servidor. Não existe chave do servidor nem fallback.
- **Dados:** histórico, baterias e modelos são da conta (isolados em JSON e no MongoDB).
- **Resultados oficiais:** cópias preservadas das últimas baterias concluídas de vestibular, MMLU e
  GPQA, públicas em `/v1/public/benchmarks`; trocá-las exige comando de administrador.

Detalhes: [backend](apps/backend/README.md#uso-multiusuário-autenticação-credenciais-e-resultados-oficiais),
[autenticação](apps/auth/README.md) e [frontend](apps/frontend/README.md#contas-sessão-e-chave-openrouter).

## Como rodar com Docker

### 1. Configuração e segredos (uma vez)

```bash
cp apps/backend/.env.example apps/backend/.env
cp apps/auth/.env.example apps/auth/.env
cp apps/frontend/.env.example apps/frontend/.env
cp .env.example .env                 # PUBLIC_HOST/PUBLIC_ORIGIN/portas (produção)
./scripts/generate-secrets.sh        # cria ./secrets (fora do Git): chave do cookie da credencial e segredo backend<->auth
```

Os segredos de infraestrutura nunca vão para o repositório nem para o frontend: os containers os
recebem como segredos do Compose (`/run/secrets/*`, variáveis `*_FILE`). A chave de criptografia da
credencial é a mesma para todas as instâncias do backend e não muda a cada reinício. Para trocá-la,
`./scripts/generate-secrets.sh --rotate-credential-key` e reinicie o backend: os cookies de credencial
existentes deixam de valer e cada usuário informa a chave de novo (o login continua válido).
`--rotate-internal-token` troca o segredo entre backend e auth (reinicie os dois).

### 2. Desenvolvimento (hot-reload)

```bash
docker compose -f docker-compose.dev.yml up --build     # http://localhost:5173
```

Diferenças só do desenvolvimento: HTTP (cookies sem `Secure`), `APP_ENV=development` e portas do
backend (8000), auth (8001) e MongoDB (27017) publicadas para depuração.

### 3. Produção

```bash
# Certificados TLS em deploy/certs/{fullchain,privkey}.pem (teste local: ./scripts/generate-local-cert.sh)
docker compose up --build -d                              # https://PUBLIC_HOST
```

Só o Nginx publica portas (80 → redireciona para 443; 443 com TLS e WSS). Backend, auth e MongoDB
ficam na rede interna; `/internal` do auth nunca sai pelo proxy. Cookies `Secure` com prefixos
`__Host-`/`__Secure-`, HSTS e CSP; os logs do Nginx não registram cookies nem corpos e as
aplicações redigem chaves e tokens. Os dados ficam nos volumes `backend_data` e `mongo_data`
(sobrevivem a `down`; só `down -v` apaga).

### 4. Administrador

```bash
docker compose exec auth python -m src.infra.cli.admin_cli create-admin --email admin@exemplo.com
```

Não há cadastro público de administradores nem credenciais padrão (ver [apps/auth](apps/auth/README.md)).

### 5. Resultados oficiais

```bash
docker compose exec backend python -m src.infra.cli.official_publications_cli discover
docker compose exec backend python -m src.infra.cli.official_publications_cli inspect --source legacy
docker compose exec backend python -m src.infra.cli.official_publications_cli publish-initial \
  --source legacy --published-by "admin" --apply
# Substituição explícita, mais tarde:
docker compose exec backend python -m src.infra.cli.official_publications_cli replace \
  --source owner:usr_... --benchmark-session-id bench_... --published-by "admin" --apply
```

`legacy` é o histórico pessoal anterior às contas (dados sem dono no armazenamento configurado).
Sem `--apply`, nada é gravado. Antes de gravar, o armazenamento oficial vai para
`data/backups/official`. Para recuperar o histórico pessoal antigo numa conta (cópia, sem alterar
a origem): `docker compose exec backend python -m src.infra.cli.legacy_data_cli assign --owner usr_... --apply`.

### 6. Backup

- MongoDB (contas, sessões de login, catálogos e, se configurado, dados do backend):
  `docker compose exec mongo mongodump --archive > backup-mongo.archive`
- Arquivos do backend (histórico JSON e publicações oficiais):
  `docker run --rm -v <projeto>_backend_data:/data -v "$PWD":/out alpine tar czf /out/backend_data.tgz -C /data .`
- Guarde também `./secrets` em local seguro: sem a chave de aplicação, os cookies de credencial
  emitidos deixam de abrir (os dados não dependem dela).

### 7. Verificações

```bash
(cd apps/backend && .venv/bin/flake8 src tests && .venv/bin/pytest)       # cobertura 100%
(cd apps/auth && .venv/bin/flake8 src tests && .venv/bin/pytest)          # cobertura 100%
(cd apps/frontend && npm run lint && npm run typecheck && npm run test:coverage && npm run build)
docker compose config --quiet && docker compose -f docker-compose.dev.yml config --quiet
apps/backend/.venv/bin/python integration/run_integration.py   # proxy TLS, cookies, CSRF e WebSockets reais, OpenRouter falsa
```

Para parar: `docker compose down` (ou `-f docker-compose.dev.yml down`).
