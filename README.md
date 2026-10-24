# Aprimoramento de outputs de Inteligência Artificial

Este repositório contém o projeto de TCC **“Um Harness de IA para Resolução de Perguntas em Linguagem Natural: Adaptando o Ralph Wiggum Loop Além do Desenvolvimento de Software”**. A aplicação compara uma resposta obtida por inferência direta com outra produzida pelo Ralph Loop Adaptado.

## Estrutura do projeto

### Front

O frontend fica em [`apps/frontend/`](apps/frontend/) e foi desenvolvido com React, TypeScript e Vite. Ele permite comparar os dois fluxos para uma mesma pergunta: a inferência direta (baseline) e o harness baseado no Ralph Loop. No fluxo adaptado, a interface acompanha a decomposição em tarefas, as tentativas e validações, a reinicialização de contexto (*fresh context*) e a síntese da resposta final. Consulte o [README do frontend](apps/frontend/README.md) para detalhes de execução e arquitetura.

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

O guia operacional é uma orientação derivada, enquanto a seção identificada como transcrição preserva o texto original do paper. O documento também explicita essa distinção e descreve as etapas, os critérios de aceite e a separação de contexto e resultados entre as tarefas.

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

Para parar os containers, use `docker compose down` (ou `docker compose -f docker-compose.dev.yml down`). Os dados do MongoDB ficam em um volume nomeado e sobrevivem ao `down`; só `docker compose down -v` os apaga.
