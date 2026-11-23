# syntax=docker/dockerfile:1

# ─── deps ───────────────────────────────────────────────────────────────────
FROM node:24-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# ─── dev ────────────────────────────────────────────────────────────────────
# Código entra via bind mount (docker-compose.dev.yml); roda o servidor Vite com
# hot-reload, exposto em todas as interfaces para ser alcançável fora do container.
FROM deps AS dev

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# ─── build ──────────────────────────────────────────────────────────────────
# `.env` do projeto (VITE_*, config pública) é lido pelo Vite neste passo e fica
# embutido no bundle estático — variáveis VITE_ não são segredo, são config de cliente.
FROM deps AS build

COPY . .
RUN npm run build

# ─── prod ───────────────────────────────────────────────────────────────────
# Imagem final: só o estático compilado, servido por Nginx.
FROM nginx:1.27-alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
