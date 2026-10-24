# TCC-1-Aprimoramento-de-outputs-de-Inteligencia-Artificial

## Como rodar com Docker

Pré-requisito: copiar os arquivos de ambiente e preenchê-los:

```bash
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env
```

Ambiente de desenvolvimento (código montado como volume, hot-reload no back e no front):

```bash
docker compose -f docker-compose.dev.yml up --build
```

Ambiente de produção (front compilado e servido por Nginx, back sem reload):

```bash
docker compose up --build
```

Serviços após subir:

| Serviço | Dev | Prod |
|---|---|---|
| Frontend | http://localhost:5173 | http://localhost:3000 |
| Backend (API) | http://localhost:8000 | http://localhost:8000 |
| MongoDB | localhost:27017 | — (apenas na rede interna do Compose) |

Para parar os containers, use `docker compose down` (ou `docker compose -f docker-compose.dev.yml down`).
Os dados do MongoDB ficam em um volume nomeado e sobrevivem ao `down`; só `docker compose down -v` os apaga.

## Estrutura do repositório

- `apps/backend/` — API do harness (Ralph Loop Adaptado) e do fluxo de inferência simples.
- `apps/frontend/` — interface que compara os dois fluxos (ver `apps/frontend/README.md`).
- `docs/` — material do TCC (paper, análises, desenhos).

Os enunciados de fase usados para guiar a implementação do backend e do frontend ficam em
`feature_ralph/` e `feature_front/`, respectivamente. Esses diretórios existem apenas localmente
(estão no `.gitignore`) e não fazem parte do histórico do repositório.