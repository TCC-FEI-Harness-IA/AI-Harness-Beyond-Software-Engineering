# Serviço de autenticação

Serviço independente (FastAPI + MongoDB) que cadastra contas, faz login e logout e informa ao
backend, por uma rota interna autenticada, se o cookie de sessão de uma requisição vale.

**Premissa desta entrega:** como o método de login não foi especificado, ele é **e-mail e senha**.
Não há confirmação de e-mail nem recuperação de senha.

## Modelo de segurança

| Aspecto | Decisão |
|---|---|
| Senhas | Argon2id (`argon2-cffi`), sal aleatório por hash, parâmetros configuráveis (padrão RFC 9106 baixa memória: t=3, m=64 MiB, p=4; em produção abaixo do mínimo da OWASP é recusado). Rehash transparente no login quando os parâmetros mudam. Nunca há criptografia reversível. |
| Política de senha | 12 a 128 caracteres, sem regras de composição (orientação OWASP/NIST); só espaços é recusado. |
| E-mail | Normalizado (NFKC, sem espaços nas pontas, minúsculas) e único por **índice único** no MongoDB. |
| Identificador | `usr_` + 128 bits aleatórios, estável: é o dono dos dados no backend. |
| Sessão | Token opaco de 256 bits só no cookie; no banco fica o SHA-256 (índice único). Expira **24 h depois do login**, sem renovação por atividade (`agora < expires_at`; no instante exato do prazo já não vale). Logout grava `revoked_at`: a mesma cópia do cookie nunca volta a valer. Índice TTL limpa sessões vencidas. Sobrevive a reinícios enquanto o volume do MongoDB existir. |
| Cookie | `ralph_session` (`__Host-ralph_session` com `Secure`): HttpOnly, `SameSite=Lax`, `Path=/`, sem `Domain`, `Max-Age` até o fim absoluto. |
| CSRF | Login/cadastro/logout recusam `Origin` fora de `PUBLIC_ORIGINS`. Cada sessão tem um token anti-CSRF (*synchronizer token*) devolvido em `/auth/login` e `/auth/me`; logout e todas as escritas do backend exigem `X-CSRF-Token`. |
| Tentativas de login | Janela fixa por e-mail **e** por IP (`AUTH_LOGIN_MAX_ATTEMPTS` em `AUTH_LOGIN_WINDOW_SECONDS`), guardada no MongoDB (vale entre instâncias). Excedido: `429` com `Retry-After`. O IP vem de `X-Real-IP` só com `AUTH_TRUST_PROXY_HEADERS=true` (atrás do Nginx do projeto). E-mail inexistente e senha errada têm a mesma resposta e o mesmo custo (verificação fictícia de Argon2). |
| Administradores | Nunca pelo cadastro público (o campo `role` do corpo é ignorado) e sem credenciais padrão: só pela linha de comando. |
| Logs | Filtro de redação para `Bearer`, cookies `ralph_*`, chaves `sk-or-…` e campos `password`. |

Coleções (banco `AUTH_MONGODB_DATABASE`, padrão `tcc_auth`): `users`, `sessions`, `login_attempts`.

## API

| Rota | Acesso | Descrição |
|---|---|---|
| `POST /auth/register` | público (origem verificada) | `{email, password}` → `201 {user}`; não abre sessão. `400` dados inválidos, `409` e-mail indisponível. |
| `POST /auth/login` | público (origem verificada) | `{email, password}` → `200 {user, session: {expires_at}, csrf_token}` + cookie. `401`, `429`. |
| `GET /auth/me` | cookie | Conta, fim da sessão e token anti-CSRF; `401` sem sessão válida. |
| `POST /auth/logout` | cookie + `X-CSRF-Token` | Revoga a sessão e remove os cookies de sessão e da credencial LLM (`Path=/v1`). Sem sessão válida, só limpa os cookies. |
| `POST /internal/sessions/verify` | `Authorization: Bearer <AUTH_INTERNAL_TOKEN>` | Usada só pelo backend: `{token}` → `{user_id, role, session_id, expires_at, csrf_token}` ou `401`. Não é exposta pelo Nginx. |
| `GET /health` | — | Saúde. |

Todas as respostas de `/auth` e `/internal` usam `Cache-Control: no-store`.
Erros de validação (`422`) devolvem apenas localização, tipo e descrição do erro, sem ecoar senhas,
tokens, corpos de requisição ou o contexto de validação recebido.

## Provisionamento administrativo

Dentro do container `auth` (ou com o venv local e o `.env`):

```bash
# Conta administradora nova: a senha é pedida sem eco (nunca como argumento)
docker compose exec auth python -m src.infra.cli.admin_cli create-admin --email admin@exemplo.com

# Não interativo: a senha vem da entrada padrão
printf '%s\n' "$SENHA_ADMIN" | docker compose exec -T auth \
  python -m src.infra.cli.admin_cli create-admin --email admin@exemplo.com --password-stdin

# Promover uma conta já cadastrada (mantém senha e identificador)
docker compose exec auth python -m src.infra.cli.admin_cli create-admin --email conta@exemplo.com --promote
```

O comando imprime o identificador da conta (`usr_...`), usado por exemplo para atribuir o histórico
legado no backend (`legacy_data_cli assign --owner usr_...`).

## Configuração

Veja `.env.example`. Segredos aceitam a variante `*_FILE` (segredos do Docker):

| Variável | Padrão | Descrição |
|---|---|---|
| `APP_ENV` | `development` | `production` exige `AUTH_COOKIE_SECURE=true`, origens `https`, Argon2 ≥ mínimo OWASP e sessão de 86400 s. |
| `AUTH_MONGODB_URI` / `AUTH_MONGODB_DATABASE` | `mongodb://localhost:27017` / `tcc_auth` | Banco próprio do serviço. |
| `AUTH_INTERNAL_TOKEN` / `_FILE` | — (obrigatório) | Segredo compartilhado com o backend (≥ 32 caracteres). |
| `PUBLIC_ORIGINS` | `http://localhost:5173` | Origens do frontend (CSV). |
| `AUTH_COOKIE_SECURE` | `false` | Cookies `Secure` (+ prefixo `__Host-`). |
| `AUTH_SESSION_TTL_SECONDS` | `86400` | Validade absoluta da sessão. |
| `AUTH_LOGIN_MAX_ATTEMPTS` / `AUTH_LOGIN_WINDOW_SECONDS` | `5` / `900` | Limite de falhas de login por e-mail e por IP. |
| `AUTH_TRUST_PROXY_HEADERS` | `false` | Usa `X-Real-IP` (só atrás do Nginx do projeto). |
| `AUTH_PASSWORD_MIN_LENGTH` / `AUTH_PASSWORD_MAX_LENGTH` | `12` / `128` | Política de senha. |
| `AUTH_ARGON2_TIME_COST` / `_MEMORY_COST_KIB` / `_PARALLELISM` | `3` / `65536` / `4` | Parâmetros do Argon2id. |

## Desenvolvimento e testes

Mesmas convenções do backend (camadas `domain` → `application` → `infra`, injeção pelo construtor,
TDD, cobertura de 100%):

```bash
cd apps/auth
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/flake8 src tests
.venv/bin/pytest            # cobertura mínima de 100% (setup.cfg)
.venv/bin/uvicorn src.main:create_app --factory --port 8001 --reload
```

Os testes usam o Argon2id real (com custo baixo), o gerador de tokens real, relógio controlável e
um MongoDB em memória (`mongomock-motor`; datas de teste no futuro porque ele aplica índices TTL
contra o relógio real).
